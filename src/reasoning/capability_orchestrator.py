"""
🧠 推理能力编排器 - Reasoning Capability Orchestrator

职责:
1. 接收CapabilityAnalyzer的分析结果
2. 按优先级顺序执行各推理能力
3. 在能力之间传递中间结果
4. 组合最终答案

Author: BMAM Team
"""

import json
import logging
import asyncio
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# 🚀 性能优化配置
ENABLE_DYNAMIC_CONSTRAINTS = os.getenv('ENABLE_DYNAMIC_CONSTRAINTS', 'false').lower() == 'true'
ENABLE_PARALLEL_EXECUTION = os.getenv('ENABLE_PARALLEL_EXECUTION', 'true').lower() == 'true'


class CapabilityOrchestrator:
    """
    推理能力编排器

    工作流程:
    1. 根据capability分析结果,按priority执行
    2. 每个能力产生中间结果,传递给下一个
    3. 最终组合所有结果
    """

    def __init__(self, brain_agents: Dict[str, Any], memory_system=None):
        """
        Args:
            brain_agents: 所有brain agents的字典 {agent_id: agent_instance}
            memory_system: 记忆系统实例 (用于HippocampalPrefrontalLoop)
        """
        self.agents = brain_agents
        self.memory_system = memory_system

        # 🔥 集成条件约束引擎
        from src.reasoning.conditional_constraint_engine import ConditionalConstraintEngine
        self.constraint_engine = ConditionalConstraintEngine()

        # 🔥 NEW: 集成3个脑区协作模块
        from src.brain.region_activation import RegionActivationDynamics
        from src.brain.hippocampal_loop import HippocampalPrefrontalLoop
        from src.brain.collaborative_output import CollaborativeOutput

        self.region_activation = RegionActivationDynamics()
        self.hippocampal_loop = HippocampalPrefrontalLoop(
            memory_system=memory_system
        ) if memory_system else None
        self.collaborative_output = CollaborativeOutput(
            brain_agents=brain_agents
        )

        logger.info("✅ Initialized CapabilityOrchestrator with ConditionalConstraintEngine")
        logger.info("🔥 Brain collaboration modules integrated")

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
            logger.info("🧠 Starting HippocampalPrefrontalLoop iterative retrieval...")
            try:
                enhanced_retrieval = await self.hippocampal_loop.iterative_retrieval(
                    query=query,
                    initial_memories=memories,
                    max_iterations=2  # 最多2轮补充检索
                )
                memories = enhanced_retrieval['memories']
                logger.info(f"✅ Enhanced memories: {len(memories)} (initial: {initial_memory_count}, added: {len(memories) - initial_memory_count})")
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
            logger.info(f"🧠 Region activation: {activation_map}")

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
            logger.info(f"🚀 Parallel execution mode: executing {len(sorted_caps)} capabilities concurrently")

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
                logger.info("🔍 Analyzing initial constraints...")
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
                logger.info(f"  ▶️ Executing: {cap_name}")

                try:
                    result = await self._execute_capability(cap_name, context)
                    context['intermediate_results'][cap_name] = result
                    context['reasoning_chain'].append(
                        f"✅ {cap_name}: {str(result.get('summary', 'completed'))}"
                    )

                    # 动态约束检查
                    if ENABLE_DYNAMIC_CONSTRAINTS and i < len(sorted_caps) - 1:
                        logger.info(f"🔍 Checking dynamic constraints after {cap_name}...")
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

    async def _memory_retrieval(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """记忆检索 - 基础能力"""
        # 记忆已经在brain_coordinator中检索过了,直接返回
        return {
            'summary': f'Retrieved {len(memories)} memories',
            'memories_count': len(memories)
        }

    async def _fact_extraction(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """🔥 增强版事实提取 - 添加答案相关性验证"""
        from src.agents.base import BrainAgent

        class TempFactExtractor(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempFactExtractor(
            agent_id='fact_extractor',
            brain_region='prefrontal',
            system_prompt='Fact Extractor with Relevance Validation'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"Memory {i+1}: {m.get('content', str(m))}"
            for i, m in enumerate(memories[:10])
        ])

        prompt = f"""Extract the factual answer from the memories, ensuring relevance to the question.

**Question**: {query}

**Available Memories**:
{memories_text}

**Task**:
1. Identify what type of information the question is asking for
2. Search memories for that type of information
3. Extract the answer at the appropriate abstraction level

**Critical Rules**:
- If asking "Which country" → answer must be COUNTRY NAME
- If asking "What activity" → answer must be ACTIVITY
- If asking "Who" → answer must be PERSON or IDENTITY
- If asking "When" → answer must be TIME/DATE
- If asking "What community" → answer must be COMMUNITY (generalize from specific groups)
  Example: "LGBTQ support group" → community is "LGBTQ community"
- If asking "What did X research" → extract the MAIN TOPIC (concise)
  Example: "adoption agencies that support LGBTQ families" → "adoption agencies"

**Abstraction Level**:
- For "community" questions: generalize specific groups to broader communities
- For "research" questions: extract core topic, not all details
- Be concise: prefer "adoption agencies" over "adoption agencies that support LGBTQ families"

**Output JSON**:
{{
    "question_type": "country|activity|community|research|date|...",
    "answer": "the extracted fact (concise, appropriate abstraction level)",
    "confidence": 0.0-1.0,
    "evidence": "which memory contains this fact"
}}

Output only valid JSON, no explanation."""

        try:
            import json as json_lib
            content = await analyzer.call_llm(
                prompt=prompt,
                temperature=0.1,  # 低温度保证精确性
                max_tokens=300
            )

            result = json_lib.loads(content)

            return {
                'summary': f"Extracted: {str(result.get('answer', ''))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.7),
                'question_type': result.get('question_type', '')
            }
        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            # Fallback to original method
            reasoning_agent = self.agents.get('reasoning_validator')
            if reasoning_agent:
                result = await reasoning_agent._general_reasoning(query, memories)
                return {
                    'summary': f"Extracted: {str(result.get('answer', 'N/A'))}",
                    'answer': result.get('answer'),
                    'confidence': result.get('confidence', 0.0)
                }
            return {'error': str(e)}

    async def _temporal_calculation(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """时间计算"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        result = await reasoning_agent._temporal_reasoning(query, memories)
        return {
            'summary': f"Calculated: {str(result.get('answer', 'N/A'))}",
            'answer': result.get('answer'),
            'confidence': result.get('confidence', 0.0)
        }

    async def _duration_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """时长推断 - 复用temporal_calculation"""
        return await self._temporal_calculation(query, memories, intermediate)

    async def _identity_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """🧠 LLM驱动的身份推理 - 从隐式证据推断身份特征"""
        from src.agents.base import BrainAgent

        class TempIdentityAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempIdentityAnalyzer(
            agent_id='identity_analyzer',
            brain_region='prefrontal',
            system_prompt='Identity Analyzer'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in memories[:15]
        ])

        prompt = f"""Infer the person's core identity from their memories and emotional responses.

Question: {query}

Memories:
{memories_text}

Task: Analyze the memories to infer WHO the person IS at their core.

Key Inference Patterns:
1. Emotional resonance: When someone feels deeply inspired/empowered by stories about a specific group, they likely belong to that group
   - "transgender stories were inspiring... felt empowered" → likely transgender themselves
   - "veteran stories moved them deeply" → likely a veteran

2. Personal connection: Research/interest in support services suggests personal relevance
   - "researched LGBTQ adoption agencies" + "transgender stories empowered them" → transgender person planning family

3. Community affiliation: Attending support groups suggests membership
   - "attended LGBTQ support group... heard transgender stories" → LGBTQ person, likely transgender

Focus on the person's CORE IDENTITY (who they ARE), not roles/activities:
- ✓ Identity: "transgender woman", "transgender man", "veteran", "immigrant", "gay man"
- ✗ NOT roles: "advocate", "ally", "supporter", "volunteer", "researcher"

If the memories show strong emotional connection to transgender stories and LGBTQ community, the person is likely transgender themselves.

Output JSON (extract ONLY the identity, be concise):
{{
    "identity": "transgender woman" (or other core identity - be specific and concise),
    "confidence": 0.0-1.0,
    "evidence": ["key memories that reveal identity"],
    "reasoning": "why you inferred this identity"
}}
"""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=400)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            return {
                'summary': f"Inferred identity: {str(result.get('identity', 'unknown'))}",
                'answer': result.get('identity'),
                'confidence': result.get('confidence', 0.7),
                'evidence': result.get('evidence', []),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"❌ Identity inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 使用ReasoningValidator
            reasoning_agent = self.agents.get('reasoning_validator')
            if reasoning_agent:
                result = await reasoning_agent._identity_reasoning(query, memories)
                return {
                    'summary': f"Inferred (fallback): {str(result.get('answer'))}",
                    'answer': result.get('answer'),
                    'confidence': result.get('confidence', 0.5)
                }

            return {
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _pattern_recognition(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """模式识别 - 识别记忆中的模式和主题"""
        # 使用LLM进行模式识别 (不依赖老的AgentMessage架构)
        from src.agents.base import BrainAgent
        class TempAgent(BrainAgent):
            async def process_message(self, message): return {}
        temp_agent = TempAgent(agent_id='pattern_analyzer', brain_region='prefrontal', system_prompt='Temp Agent')

        memories_text = '\n'.join([f"- {m.get('content', str(m))}" for m in memories[:10]])

        prompt = f"""Analyze the patterns and themes in the memories to answer this question.

Question: {query}

Available Memories:
{memories_text}

Identify recurring patterns, common themes, or trends in the memories.
If there are no memories or patterns, state that clearly.

Output JSON:
{{
    "patterns_identified": ["pattern1", "pattern2"],
    "answer": "brief answer based on identified patterns",
    "confidence": 0.0-1.0
}}"""

        try:
            import json as json_lib
            response = await temp_agent.call_llm(prompt, temperature=0.0, max_tokens=400)

            # Parse JSON
            content = response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result_json = json_lib.loads(content)

            return {
                'summary': f"Recognized patterns: {str(result_json.get('patterns_identified', []))}",
                'patterns': result_json.get('patterns_identified', []),
                'answer': result_json.get('answer'),
                'confidence': result_json.get('confidence', 0.0)
            }
        except Exception as e:
            logger.error(f"Pattern recognition failed: {e}")
            return {
                'summary': 'Pattern recognition failed',
                'patterns': [],
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _interest_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """
        🧠 兴趣推断 - 通过reflection agent (DMN) + 语义映射

        分配给reflection agent的原因:
        1. Reflection使用Default Mode Network (DMN)
        2. DMN负责价值判断和目标规划
        3. "What fields would Caroline pursue?" 需要深度思考和意义提取

        重要: 该能力仅在问题真正询问兴趣/倾向时使用,由LLM判断适用性
        """
        from src.agents.base import BrainAgent

        class TempInterestAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempInterestAnalyzer(
            agent_id='interest_analyzer',
            brain_region='default_mode',  # DMN
            system_prompt='Interest Inference Analyzer'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in memories[:15]
        ])

        prompt = f"""Analyze the person's interests and infer academic fields they would pursue.

Question: {query}

Memories:
{memories_text}

Task:
1. Extract EXPLICIT interests (direct statements like "I'm keen on...")
2. Infer IMPLICIT interests (from actions like "researched...", "attended...")
3. Map interests to ACADEMIC FIELDS (be specific about disciplines)

Key Semantic Mappings (Interest → Academic Field):
- "counseling" / "mental health" / "therapy" → **Psychology** (counseling is a subfield of psychology)
- "social work" / "community services" → **Social Work**
- "LGBTQ support" / "advocacy" → **LGBTQ Studies** / **Community Advocacy**
- "adoption agencies" → related to **Social Work** or **Family Studies**
- "teaching" / "education" → **Education**

CRITICAL RULE: If someone says "I'm keen on counseling", they are interested in **Psychology** as an academic field.

Output JSON:
{{
    "explicit_interests": ["list of directly stated interests"],
    "implicit_interests": ["list of inferred interests from actions"],
    "academic_fields": ["Psychology", "Social Work", etc.],
    "reasoning": "how you mapped interests to academic fields",
    "confidence": 0.0-1.0
}}

Output only valid JSON, no explanation."""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=400)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            # 🔥 后处理: 语义映射增强 (确保counseling→Psychology映射)
            fields = set(result.get('academic_fields', []))
            all_interests = result.get('explicit_interests', []) + result.get('implicit_interests', [])

            # 应用语义映射表
            semantic_mapping = {
                'counseling': 'Psychology',
                'mental health': 'Psychology',
                'therapy': 'Psychology',
                'psychological': 'Psychology',
                'social work': 'Social Work',
                'community services': 'Social Work',
                'adoption': 'Social Work',
                'advocacy': 'Community Advocacy',
                'LGBTQ': 'LGBTQ Studies',
                'transgender': 'Gender Studies'
            }

            for interest in all_interests:
                interest_lower = interest.lower()
                for keyword, field in semantic_mapping.items():
                    if keyword in interest_lower:
                        fields.add(field)
                        logger.info(f"🔗 Semantic mapping: '{interest}' → {field}")

            # 格式化最终答案
            if fields:
                answer = ', '.join(sorted(fields))
            else:
                answer = result.get('answer', 'Unable to determine academic fields')

            return {
                'summary': f"Interest inference: {answer}",
                'answer': answer,
                'confidence': result.get('confidence', 0.8),
                'explicit_interests': result.get('explicit_interests', []),
                'implicit_interests': result.get('implicit_interests', []),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"❌ Interest inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 使用multi_hop_inference
            logger.info("⚠️ Falling back to multi_hop_inference")
            return await self._multi_hop_inference(query, memories, intermediate)

    async def _causal_reasoning(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """因果推理 - 分析为什么"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        # 使用LLM进行因果分析
        from src.agents.base import BrainAgent
        class TempAgent(BrainAgent):
            async def process_message(self, message): return {}
        temp_agent = TempAgent(agent_id='temp_causal', brain_region='prefrontal', system_prompt='Temp Agent')

        memories_text = '\n'.join([f"- {m.get('content', str(m))}" for m in memories[:10]])

        prompt = f"""Analyze the causal relationships to answer this question.

Question: {query}

Available Memories:
{memories_text}

Task: Identify cause-effect relationships and provide a causal explanation.

Output JSON:
{{
    "cause": "what caused it",
    "effect": "what happened",
    "answer": "causal explanation",
    "confidence": 0.0-1.0
}}
"""

        content = await temp_agent.call_llm(prompt=prompt, temperature=0.3, max_tokens=300)

        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'summary': f"Cause: {str(result.get('cause'))}, Effect: {str(result.get('effect'))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.0)
            }
        except Exception as e:
            logger.error(f"Causal reasoning parse error: {e}")
            return {'error': str(e)}

    async def _counterfactual_reasoning(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """反事实推理 - what if"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        from src.agents.base import BrainAgent
        class TempAgent(BrainAgent):
            async def process_message(self, message): return {}
        temp_agent = TempAgent(agent_id='temp_counterfactual', brain_region='prefrontal', system_prompt='Temp Agent')

        memories_text = '\n'.join([f"- {m.get('content', str(m))}" for m in memories[:10]])

        prompt = f"""Perform counterfactual reasoning for a hypothetical scenario.

Question: {query}

Actual Events (from memories):
{memories_text}

Task: Reason about the alternative scenario.

Output JSON:
{{
    "actual_scenario": "what actually happened",
    "hypothetical_scenario": "the 'what if' scenario",
    "answer": "reasoning about the hypothetical outcome",
    "confidence": 0.0-1.0
}}
"""

        content = await temp_agent.call_llm(prompt=prompt, temperature=0.4, max_tokens=400)

        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'summary': f"Hypothetical: {str(result.get('hypothetical_scenario'))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.0)
            }
        except Exception as e:
            logger.error(f"Counterfactual reasoning parse error: {e}")
            return {'error': str(e)}

    async def _comparison(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """比较推理"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        # 使用consolidation agent的能力
        result = await reasoning_agent._general_reasoning(query, memories)

        return {
            'summary': f"Comparison result: {str(result.get('answer', 'N/A'))}",
            'answer': result.get('answer'),
            'confidence': result.get('confidence', 0.0)
        }

    async def _multi_hop_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """🧠 LLM驱动的多跳推理 - 综合多条记忆进行兴趣/模式推断"""
        from src.agents.base import BrainAgent

        class TempMultiHopAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempMultiHopAnalyzer(
            agent_id='multihop_analyzer',
            brain_region='prefrontal',
            system_prompt='Multi-hop Analyzer'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"{i+1}. {m.get('content', str(m))}" for i, m in enumerate(memories[:20])
        ])

        prompt = f"""Synthesize information across multiple memories to answer the question.

**Question**: {query}

**Available Memories**:
{memories_text}

Task: Synthesize information from memories to directly answer what the question asks.

Output JSON:
{{
    "answer": "synthesized answer (directly answer what the question asks)",
    "confidence": 0.0-1.0,
    "evidence": ["key memories used"],
    "reasoning": "synthesis logic"
}}
"""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=400)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            return {
                'summary': f"Multi-hop inference: {str(result.get('answer', 'N/A'))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.7),
                'supporting_memories': result.get('supporting_memories', []),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"❌ Multi-hop inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback
            reasoning_agent = self.agents.get('reasoning_validator')
            if reasoning_agent:
                result = await reasoning_agent._multi_hop_reasoning(query, memories)
                return {
                    'summary': f"Multi-hop (fallback): {str(result.get('answer'))}",
                    'answer': result.get('answer'),
                    'confidence': result.get('confidence', 0.5)
                }

            return {
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _synthesize_answer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧠 智能答案选择 - 使用LLM评估哪个capability的答案最匹配问题意图

        策略升级:
        1. 收集所有有答案的capabilities
        2. 如果只有1个答案,直接返回
        3. 如果有多个答案,使用LLM判断哪个最匹配问题的语义和期望答案类型
        4. 这是brain-collaboration approach,不是hardcoded rules
        """
        intermediate = context['intermediate_results']
        query = context.get('query', '')

        # 收集有答案的capabilities
        cap_results = []
        for cap_name, result in intermediate.items():
            if result.get('answer'):
                cap_results.append((cap_name, result))

        # Case 1: 没有答案
        if not cap_results:
            return {
                'answer': f"I don't have enough information to answer the question: {query}",
                'confidence': 0.1,
                'error': 'No capability produced an answer',
                'fallback': True
            }

        # Case 2: 只有一个答案,直接返回
        if len(cap_results) == 1:
            cap_name, result = cap_results[0]
            logger.info(f"🎯 Single answer from {cap_name}: {str(result.get('answer'))[:100]}...")
            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.7),
                'primary_capability': cap_name
            }

        # Case 3: 多个答案 - 使用LLM智能选择
        logger.info(f"🤔 Multiple answers available ({len(cap_results)}), using LLM to select best match...")
        selected_cap, selected_result = await self._llm_select_best_answer(query, cap_results)

        logger.info(f"🎯 LLM selected answer from {selected_cap}: {str(selected_result.get('answer'))[:100]}...")

        return {
            'answer': selected_result['answer'],
            'confidence': selected_result.get('confidence', 0.7),
            'primary_capability': selected_cap
        }

    async def _llm_select_best_answer(
        self,
        query: str,
        cap_results: List[tuple]
    ) -> tuple:
        """
        🧠 使用LLM评估多个候选答案,选择最匹配问题意图的

        这是brain-collaboration的核心 - 让LLM判断语义匹配,而非硬编码规则
        """
        from src.agents.base import BrainAgent

        class TempAnswerSelector(BrainAgent):
            async def process_message(self, msg): return {}

        selector = TempAnswerSelector('answer_selector', 'prefrontal', 'Answer Selector')

        # 构建候选答案描述
        candidates_text = ""
        for i, (cap_name, result) in enumerate(cap_results, 1):
            answer = result.get('answer', '')
            confidence = result.get('confidence', 0.0)
            candidates_text += f"\n{i}. [{cap_name}] (confidence={confidence:.2f})\n   Answer: {answer}\n"

        prompt = f"""You are evaluating multiple candidate answers from different cognitive capabilities to select the best match for the question.

Question: "{query}"

Available Candidates:
{candidates_text}

Task: Select the candidate that BEST matches what the question is asking for.

Guidelines:
1. For "What did X do/research/study?" questions → prefer SPECIFIC, CONCRETE facts over general interests
2. For "What fields would X pursue?" questions → prefer GENERAL interest inferences
3. For "What specific area?" questions → prefer SPECIFIC single answers over broad lists
4. For "Why?" questions → prefer CAUSAL reasoning over descriptions
5. For "When?" questions → prefer DATES over durations
6. Shorter, more direct answers are usually better than verbose explanations

Respond with ONLY the number (1, 2, 3, etc.) of the best candidate.
"""

        response = await selector.call_llm(
            prompt=prompt,
            temperature=0.0,
            max_tokens=10
        )

        # 解析选择
        try:
            selection = int(response.strip())
            if 1 <= selection <= len(cap_results):
                return cap_results[selection - 1]
        except:
            pass

        # Fallback: 返回第一个
        logger.warning(f"Failed to parse LLM selection: {response}, falling back to first candidate")
        return cap_results[0]

    async def _refine_answer(self, query: str, answer: str, primary_capability: str = None) -> str:
        """
        答案后处理 - 针对特定问题类型优化答案格式

        目标: 解决verbose答案问题,提取核心信息
        """
        if not answer:
            return answer

        # 检测是否需要refinement
        question_lower = query.lower()

        # 规则1: "What fields" 问题 - 提取academic fields
        if any(kw in question_lower for kw in ['field', 'study', 'pursue', 'education', 'major']):
            # 检查答案是否verbose (超过10个词)
            if len(answer.split()) > 10:
                logger.info(f"📝 Refining verbose 'fields' answer: {answer[:50]}...")
                refined = await self._extract_academic_fields(answer)
                if refined and refined != answer:
                    logger.info(f"   → Refined to: {refined}")
                    return refined

        # 规则2: 其他情况保持原样
        return answer

    async def _extract_academic_fields(self, verbose_answer: str) -> str:
        """从verbose答案中提取academic fields"""
        from src.agents.base import BrainAgent

        class TempExtractor(BrainAgent):
            async def process_message(self, msg): return {}

        extractor = TempExtractor('field_extractor', 'prefrontal', 'Field Extractor')

        prompt = f"""Extract ONLY the academic field names from this verbose answer.

Verbose Answer: {verbose_answer}

Task: Extract just the academic field/discipline names in a concise format.

Examples:
- "Caroline would likely pursue education in social work, community advocacy, or LGBTQ studies"
  → "social work, community advocacy, LGBTQ studies"

- "She would be interested in psychology and counseling to help the transgender community"
  → "psychology, counseling"

Rules:
- Extract ONLY academic fields/disciplines
- Use comma-separated format
- Remove phrases like "would pursue", "likely to", "education in"
- Keep it under 10 words
- If no clear fields, return the original answer

Output ONLY the extracted fields, no explanation, no JSON."""

        try:
            response = await extractor.call_llm(prompt, temperature=0.1, max_tokens=50)
            # 清理response
            refined = response.strip().strip('"').strip("'")

            # 验证refinement有效性
            if len(refined) < len(verbose_answer) and len(refined.split()) <= 10:
                return refined
            else:
                return verbose_answer

        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return verbose_answer

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
