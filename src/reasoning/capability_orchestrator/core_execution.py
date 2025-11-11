"""
Core Execution for Capability Orchestrator
核心执行模块 - 编排执行流程
"""

import logging
import asyncio
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class CoreExecutionMixin:
    """Core execution mixin for CapabilityOrchestrator"""

    async def execute(
        self,
        query: str,
        capabilities: List[Dict[str, Any]],
        memories: List[Dict],
        execution_plan: str
    ) -> Dict[str, Any]:
        """
        执行推理能力组合

        Args:
            query: 用户问题
            capabilities: CapabilityAnalyzer返回的能力列表
            memories: 检索到的记忆
            execution_plan: 执行计划描述

        Returns:
            {
                'answer': '最终答案',
                'confidence': 0.0-1.0,
                'reasoning_chain': ['step1', 'step2', ...],
                'capabilities_used': ['cap1', 'cap2', ...]
            }
        """
        logger.info(f"🎯 Orchestrating capabilities: {[c['name'] for c in capabilities]}")

        # 🔥 STEP 1: 迭代检索增强记忆 (解决Q2/Q4 Psychology缺失)
        initial_memory_count = len(memories)
        if self.hippocampal_loop and len(memories) > 0:
            logger.debug("🧠 Starting HippocampalPrefrontalLoop iterative retrieval...")
            try:
                enhanced_retrieval = await self.hippocampal_loop.iterative_retrieval(
                    query=query,
                    initial_memories=memories,
                    max_iterations=2  # 最多2轮补充检索
                )
                memories = enhanced_retrieval['memories']
                logger.debug(f"✅ Enhanced memories: {len(memories)} (initial: {initial_memory_count}, added: {len(memories) - initial_memory_count})")
            except Exception as e:
                logger.warning(f"⚠️ HippocampalPrefrontalLoop failed: {e}, using original memories")

        # 执行状态
        context = {
            'query': query,
            'memories': memories,
            'intermediate_results': {},
            'reasoning_chain': [f"📋 Initial Plan: {execution_plan}"]
        }

        # 🔥 STEP 2: 动态脑区激活分析 (解决Q5 relationship vs identity)
        try:
            activation_map = await self.region_activation.compute_activation_map(
                query=query,
                memories=memories,
                current_activation={}
            )
            logger.debug(f"🧠 Region activation: {activation_map}")

            # 根据激活强度重新排序capabilities (不是硬编码priority)
            sorted_caps = self._reorder_by_activation(capabilities, activation_map)
            logger.info(f"📋 Dynamic execution order (by activation): {[c['name'] for c in sorted_caps]}")
        except Exception as e:
            logger.warning(f"⚠️ Region activation failed: {e}, using default priority")
            # Fallback: 按hardcoded priority排序
            sorted_caps = sorted(capabilities, key=lambda c: c.get('priority', 99))
            logger.info(f"📋 Execution order (default priority): {[c['name'] for c in sorted_caps]}")

        # 🚀 性能优化: 根据配置选择执行模式
        if ENABLE_PARALLEL_EXECUTION:
            # 🚀 并行执行所有能力 (快2-3倍!)
            logger.debug(f"🚀 Parallel execution mode: executing {len(sorted_caps)} capabilities concurrently")

            tasks = []
            for cap in sorted_caps:
                task = self._execute_capability(cap['name'], context)
                tasks.append((cap['name'], task))

            # 并行执行
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

            # 收集结果
            for (cap_name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"  ❌ {cap_name} failed: {result}")
                    context['reasoning_chain'].append(f"❌ {cap_name}: failed ({str(result)})")
                else:
                    context['intermediate_results'][cap_name] = result
                    context['reasoning_chain'].append(
                        f"✅ {cap_name}: {str(result.get('summary', 'completed'))}"
                    )
        else:
            # 传统串行执行模式(带动态约束)
            if ENABLE_DYNAMIC_CONSTRAINTS:
                logger.debug("🔍 Analyzing initial constraints...")
                constraints_json = await self.constraint_engine.analyze_constraints(
                    query=query,
                    capabilities=capabilities,
                    memories=memories,
                    intermediate_results={}
                )
                if constraints_json:
                    logger.info(f"🔧 Applying {len(constraints_json)} initial constraints")
                    capabilities = self.constraint_engine.apply_constraints(capabilities, constraints_json)
                    context['reasoning_chain'].append(f"🔧 Applied {len(constraints_json)} initial constraints")

            # 串行执行
            for i, cap in enumerate(sorted_caps):
                cap_name = cap['name']
                logger.debug(f"  ▶️ Executing: {cap_name}")

                try:
                    result = await self._execute_capability(cap_name, context)
                    context['intermediate_results'][cap_name] = result
                    context['reasoning_chain'].append(
                        f"✅ {cap_name}: {str(result.get('summary', 'completed'))}"
                    )

                    # 动态约束检查
                    if ENABLE_DYNAMIC_CONSTRAINTS and i < len(sorted_caps) - 1:
                        logger.debug(f"🔍 Checking dynamic constraints after {cap_name}...")
                        dynamic_constraints = await self.constraint_engine.analyze_constraints(
                            query=query,
                            capabilities=sorted_caps[i+1:],
                            memories=memories,
                            intermediate_results=context['intermediate_results']
                        )

                        if dynamic_constraints:
                            logger.info(f"🔧 Applying {len(dynamic_constraints)} dynamic constraints")
                            remaining_caps = self.constraint_engine.apply_constraints(
                                sorted_caps[i+1:],
                                dynamic_constraints
                            )
                            sorted_caps = sorted_caps[:i+1] + sorted(remaining_caps, key=lambda c: c.get('priority', 99))
                            context['reasoning_chain'].append(f"🔧 Applied {len(dynamic_constraints)} dynamic constraints")

                except Exception as e:
                    logger.error(f"  ❌ {cap_name} failed: {e}")
                    context['reasoning_chain'].append(f"❌ {cap_name}: failed ({str(e)})")

        # 组合最终答案
        final_result = await self._synthesize_answer(context)

        # 答案后处理: 针对特定问题类型优化答案格式
        refined_answer = await self._refine_answer(
            query=query,
            answer=final_result.get('answer'),
            primary_capability=final_result.get('primary_capability')
        )

        return {
            'answer': refined_answer,
            'confidence': final_result.get('confidence', 0.7),
            'reasoning_chain': context['reasoning_chain'],
            'capabilities_used': [c['name'] for c in sorted_caps],
            'intermediate_results': context['intermediate_results']
        }


    async def _execute_capability(
        self,
        capability_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个推理能力

        根据capability_name,调用对应的推理方法
        """
        query = context['query']
        memories = context['memories']
        intermediate = context['intermediate_results']

        # 🔥 能力实现路由表
        capability_implementations = {
            'memory_retrieval': self._memory_retrieval,
            'fact_extraction': self._fact_extraction,
            'temporal_calculation': self._temporal_calculation,
            'duration_inference': self._duration_inference,
            'identity_inference': self._identity_inference,
            'pattern_recognition': self._pattern_recognition,
            'interest_inference': self._interest_inference,
            'causal_reasoning': self._causal_reasoning,
            'counterfactual_reasoning': self._counterfactual_reasoning,
            'comparison': self._comparison,
            'multi_hop_inference': self._multi_hop_inference
        }

        if capability_name in capability_implementations:
            return await capability_implementations[capability_name](query, memories, intermediate)
        else:
            logger.warning(f"⚠️ Unknown capability: {capability_name}")
            return {'error': f'Unknown capability: {capability_name}'}

    # ========== 能力实现 (Capability Implementations) ==========


    def _reorder_by_activation(
        self,
        capabilities: List[Dict],
        activation_map: Dict[str, float]
    ) -> List[Dict]:
        """
        根据脑区激活强度动态排序capabilities

        不使用硬编码priority,而是使用动态计算的激活强度
        """
        # Capability → 脑区映射
        cap_to_region = {
            'fact_extraction': 'fact_extraction',
            'temporal_calculation': 'temporal_calculation',
            'identity_inference': 'identity_inference',
            'relationship_inference': 'relationship_inference',
            'interest_inference': 'interest_inference',
            'pattern_recognition': 'pattern_recognition',
            'multi_hop_inference': 'reflection'
        }

        # 为每个capability分配动态激活分数
        for cap in capabilities:
            region = cap_to_region.get(cap['name'], cap['name'])
            cap['dynamic_activation'] = activation_map.get(region, 0.5)
            logger.info(f"  {cap['name']}: activation={cap['dynamic_activation']:.2f}")

        # 按动态激活排序 (高激活 = 高优先级)
        sorted_caps = sorted(
            capabilities,
            key=lambda c: c.get('dynamic_activation', 0.5),
            reverse=True
        )

        return sorted_caps
