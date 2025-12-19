"""
Scenario Simulation Mixin
情景模拟混入类 - 提供"如果...会怎样"的前瞻性推理

🔥 2025-12-19: P1 创造性组合与未来情景
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """情景模拟结果"""
    scenario_id: str
    condition: str  # "如果..."条件
    prediction: str  # 预测结果
    confidence: float  # 置信度 (0-1)
    is_speculation: bool  # 是否为推测 (记忆不足时为True)
    supporting_memories: List[str]  # 支持此预测的记忆ID
    reasoning_chain: List[str]  # 推理链
    alternative_outcomes: List[str]  # 备选结果
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScenarioSimulationMixin:
    """
    情景模拟混入类

    提供前瞻性推理能力:
    - "如果...会怎样" 场景推演
    - 记忆 + 想象 组合生成
    - 明确标注推测 vs 有据推断
    """

    # 推测阈值: 低于此置信度时标记为推测
    SPECULATION_THRESHOLD = 0.4

    # 最小支持记忆数: 低于此数量时标记为推测
    MIN_SUPPORTING_MEMORIES = 2

    async def simulate_scenario(
        self,
        condition: str,
        memories: List[Dict[str, Any]] = None,
        context: Dict[str, Any] = None
    ) -> ScenarioResult:
        """
        模拟"如果...会怎样"场景

        Args:
            condition: 假设条件 (e.g., "如果用户换工作")
            memories: 相关记忆列表 (可选，会自动检索)
            context: 额外上下文

        Returns:
            ScenarioResult 情景模拟结果
        """
        scenario_id = f"scenario_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 1. 检索相关记忆 (如果未提供)
        if memories is None:
            memories = await self._retrieve_scenario_relevant_memories(condition)

        # 2. 分析记忆支持度
        supporting_memories = self._identify_supporting_memories(condition, memories)
        support_count = len(supporting_memories)

        # 3. 基于记忆生成推理链
        reasoning_chain = await self._generate_reasoning_chain(
            condition, memories, context
        )

        # 4. 生成预测
        prediction_result = await self._generate_scenario_prediction(
            condition, memories, reasoning_chain, context
        )

        # 5. 计算置信度
        confidence = self._calculate_scenario_confidence(
            support_count, len(memories), reasoning_chain
        )

        # 6. 判断是否为推测
        is_speculation = (
            confidence < self.SPECULATION_THRESHOLD or
            support_count < self.MIN_SUPPORTING_MEMORIES
        )

        # 7. 生成备选结果
        alternative_outcomes = await self._generate_alternative_outcomes(
            condition, memories, prediction_result['prediction']
        )

        result = ScenarioResult(
            scenario_id=scenario_id,
            condition=condition,
            prediction=prediction_result['prediction'],
            confidence=confidence,
            is_speculation=is_speculation,
            supporting_memories=[m.get('id', str(i)) for i, m in enumerate(supporting_memories)],
            reasoning_chain=reasoning_chain,
            alternative_outcomes=alternative_outcomes,
            created_at=datetime.now().isoformat()
        )

        # 记录到洞察历史
        if hasattr(self, 'insight_history'):
            self.insight_history.append({
                'type': 'scenario_simulation',
                'scenario_id': scenario_id,
                'condition': condition,
                'confidence': confidence,
                'is_speculation': is_speculation,
                'timestamp': result.created_at
            })

        logger.info(
            f"🔮 Scenario simulated: '{condition[:30]}...' "
            f"(confidence={confidence:.2f}, speculation={is_speculation})"
        )

        return result

    async def _retrieve_scenario_relevant_memories(
        self,
        condition: str
    ) -> List[Dict[str, Any]]:
        """检索与场景相关的记忆"""
        # 如果有 db_manager，使用它检索
        if hasattr(self, 'db_manager') and self.db_manager:
            try:
                # 提取关键词
                keywords = self._extract_scenario_keywords(condition)

                # 检索相关记忆
                all_memories = self.db_manager.load_memories_by_criteria()
                relevant = []

                for mem in all_memories:
                    content = mem.content if hasattr(mem, 'content') else str(mem)
                    # 简单关键词匹配
                    if any(kw.lower() in content.lower() for kw in keywords):
                        relevant.append({
                            'id': mem.id if hasattr(mem, 'id') else str(id(mem)),
                            'content': content,
                            'importance': getattr(mem, 'importance', 0.5),
                            'timestamp': getattr(mem, 'timestamp', datetime.now()).isoformat()
                        })

                return relevant[:20]  # 限制数量
            except Exception as e:
                logger.warning(f"Failed to retrieve memories for scenario: {e}")
                return []

        return []

    def _extract_scenario_keywords(self, condition: str) -> List[str]:
        """从条件中提取关键词"""
        # 移除常见的假设词
        skip_words = {
            '如果', '假如', '假设', '要是', '若', '倘若',
            'if', 'what', 'when', 'would', 'could', 'might',
            '会', '怎样', '怎么', '会怎样', '会怎么'
        }

        words = condition.replace('?', '').replace('？', '').split()
        keywords = [w for w in words if w.lower() not in skip_words and len(w) > 1]

        return keywords[:5]  # 取前5个关键词

    def _identify_supporting_memories(
        self,
        condition: str,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """识别支持该场景的记忆"""
        keywords = self._extract_scenario_keywords(condition)

        supporting = []
        for mem in memories:
            content = mem.get('content', '')
            # 计算关键词匹配度
            matches = sum(1 for kw in keywords if kw.lower() in content.lower())
            if matches > 0:
                supporting.append(mem)

        # 按重要性排序
        supporting.sort(key=lambda m: m.get('importance', 0.5), reverse=True)
        return supporting

    async def _generate_reasoning_chain(
        self,
        condition: str,
        memories: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成推理链"""
        chain = []

        # 步骤1: 条件分析
        chain.append(f"分析条件: {condition}")

        # 步骤2: 记忆支持
        if memories:
            chain.append(f"找到 {len(memories)} 条相关记忆")
            for mem in memories[:3]:
                content = mem.get('content', '')[:50]
                chain.append(f"  - 相关记忆: {content}...")
        else:
            chain.append("未找到直接相关记忆，将基于一般知识推理")

        # 步骤3: 推理过程
        if hasattr(self, 'call_llm'):
            try:
                memory_context = '\n'.join([
                    f"- {m.get('content', '')[:100]}"
                    for m in memories[:5]
                ]) if memories else "无相关记忆"

                prompt = f"""
基于以下条件和记忆，生成简短的推理步骤列表（2-4步）:

条件: {condition}
相关记忆:
{memory_context}

仅输出推理步骤，每行一步，格式: "1. xxx"
"""
                response = await self.call_llm(prompt, temperature=0.3, max_tokens=200)
                steps = [s.strip() for s in response.strip().split('\n') if s.strip()]
                chain.extend(steps[:4])
            except Exception as e:
                logger.debug(f"LLM reasoning chain generation failed: {e}")
                chain.append("基于已知信息进行推理")

        return chain

    async def _generate_scenario_prediction(
        self,
        condition: str,
        memories: List[Dict[str, Any]],
        reasoning_chain: List[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成场景预测"""
        if hasattr(self, 'call_llm'):
            try:
                memory_context = '\n'.join([
                    f"- {m.get('content', '')[:100]}"
                    for m in memories[:5]
                ]) if memories else "无相关记忆"

                reasoning_text = '\n'.join(reasoning_chain)

                prompt = f"""
基于以下信息，预测"{condition}"的可能结果:

相关记忆:
{memory_context}

推理过程:
{reasoning_text}

请直接给出预测结果（1-3句话），不要有前缀。如果记忆不足，可以基于合理推测，但要保持谨慎。
"""
                prediction = await self.call_llm(prompt, temperature=0.4, max_tokens=200)
                return {'prediction': prediction.strip()}

            except Exception as e:
                logger.debug(f"LLM prediction generation failed: {e}")

        # 回退: 简单预测
        if memories:
            return {'prediction': f"基于已有记忆，可能会产生相关影响。"}
        else:
            return {'prediction': f"由于缺乏相关记忆，难以准确预测具体结果。"}

    def _calculate_scenario_confidence(
        self,
        support_count: int,
        total_memories: int,
        reasoning_chain: List[str]
    ) -> float:
        """计算场景预测的置信度"""
        # 基础置信度
        base_confidence = 0.3

        # 记忆支持加成
        if support_count >= 5:
            memory_bonus = 0.3
        elif support_count >= 3:
            memory_bonus = 0.2
        elif support_count >= 1:
            memory_bonus = 0.1
        else:
            memory_bonus = 0.0

        # 推理链完整度加成
        reasoning_bonus = min(0.2, len(reasoning_chain) * 0.05)

        confidence = base_confidence + memory_bonus + reasoning_bonus
        return min(1.0, confidence)

    async def _generate_alternative_outcomes(
        self,
        condition: str,
        memories: List[Dict[str, Any]],
        main_prediction: str
    ) -> List[str]:
        """生成备选结果"""
        alternatives = []

        if hasattr(self, 'call_llm'):
            try:
                prompt = f"""
对于条件 "{condition}"，除了 "{main_prediction[:50]}..." 之外，还有哪些可能的结果？

请给出2个简短的备选结果，每行一个。
"""
                response = await self.call_llm(prompt, temperature=0.6, max_tokens=150)
                alternatives = [
                    s.strip() for s in response.strip().split('\n')
                    if s.strip() and len(s.strip()) > 5
                ][:2]
            except Exception as e:
                logger.debug(f"Failed to generate alternatives: {e}")

        return alternatives

    def format_scenario_for_response(
        self,
        result: ScenarioResult,
        include_reasoning: bool = False
    ) -> str:
        """
        格式化场景结果为响应文本

        Args:
            result: 场景模拟结果
            include_reasoning: 是否包含推理链

        Returns:
            格式化的响应文本
        """
        parts = []

        # 条件
        parts.append(f"**场景假设**: {result.condition}")

        # 预测 (带推测标记)
        if result.is_speculation:
            parts.append(f"\n**预测** (这只是我的推测，缺乏足够记忆支持): {result.prediction}")
        else:
            parts.append(f"\n**预测**: {result.prediction}")

        # 置信度
        confidence_desc = (
            "高" if result.confidence >= 0.7 else
            "中等" if result.confidence >= 0.4 else
            "低"
        )
        parts.append(f"\n*置信度: {confidence_desc} ({result.confidence:.0%})*")

        # 推理链 (可选)
        if include_reasoning and result.reasoning_chain:
            parts.append("\n**推理过程**:")
            for step in result.reasoning_chain:
                parts.append(f"  - {step}")

        # 备选结果
        if result.alternative_outcomes:
            parts.append("\n**其他可能**:")
            for alt in result.alternative_outcomes:
                parts.append(f"  - {alt}")

        return '\n'.join(parts)

    async def batch_simulate_scenarios(
        self,
        conditions: List[str],
        shared_memories: List[Dict[str, Any]] = None
    ) -> List[ScenarioResult]:
        """
        批量模拟多个场景

        Args:
            conditions: 条件列表
            shared_memories: 共享的记忆 (避免重复检索)

        Returns:
            场景结果列表
        """
        results = []
        for condition in conditions:
            result = await self.simulate_scenario(condition, shared_memories)
            results.append(result)
        return results
