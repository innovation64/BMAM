"""
Adversarial Reasoning Mixin - 对抗性问题推理
使用 Theory of Mind Agent 进行意图推断和欺骗检测

核心功能:
1. 检测对抗性问题 (false premise, presupposition violation等)
2. 验证问题预设与记忆事实的一致性
3. 生成合适的回应策略

Author: BMAM Team
Date: 2025-12-17
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class AdversarialReasoningMixin:
    """对抗性推理混入类"""

    async def _adversarial_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus_agent: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        对抗性问题推理 - 检测并处理欺骗性问题

        Args:
            query: 用户问题
            memories: 检索到的记忆
            hippocampus_agent: 海马体agent
            memories_by_region: 按脑区组织的记忆

        Returns:
            推理结果
        """
        logger.debug(f"🎭 Adversarial reasoning for: {query[:50]}...")

        # 1. 获取 Theory of Mind Agent
        try:
            from ...brain_regions.theory_of_mind_agent import get_theory_of_mind_agent
            tom_agent = get_theory_of_mind_agent()
        except Exception as e:
            logger.error(f"Failed to get ToM agent: {e}")
            # 降级到普通推理
            return await self._general_reasoning(query, memories)

        # 2. 提取记忆中的已知事实
        known_facts = self._extract_facts_from_memories(memories)

        # 3. 使用 ToM 进行意图分析
        intent_analysis = await tom_agent.infer_intent(query, known_facts[:5])

        # 4. 如果检测到对抗性问题，进行欺骗检测
        if intent_analysis.is_adversarial:
            logger.info(f"🚨 Adversarial query detected: type={intent_analysis.adversarial_type}")

            # 检测具体的欺骗类型
            deception = await tom_agent.detect_deception(query, known_facts)

            if deception.is_deceptive:
                # 生成针对欺骗性问题的回应
                return self._build_adversarial_response(
                    query=query,
                    intent=intent_analysis,
                    deception=deception,
                    memories=memories
                )

        # 5. 如果不是对抗性问题或无法确定，使用普通推理
        # 但添加 ToM 分析结果作为上下文
        result = await self._general_reasoning(query, memories)

        # 添加 ToM 元数据
        result['tom_analysis'] = {
            'surface_intent': intent_analysis.surface_intent,
            'deep_intent': intent_analysis.deep_intent,
            'is_adversarial': intent_analysis.is_adversarial,
            'confidence': intent_analysis.confidence
        }

        return result

    async def check_adversarial_before_reasoning(
        self,
        query: str,
        memories: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        在主推理前检查是否为对抗性问题

        Args:
            query: 用户问题
            memories: 检索到的记忆

        Returns:
            如果是对抗性问题且需要特殊处理，返回结果；否则返回 None
        """
        try:
            from ...brain_regions.theory_of_mind_agent import get_theory_of_mind_agent
            tom_agent = get_theory_of_mind_agent()
        except Exception as e:
            logger.debug(f"ToM agent not available: {e}")
            return None

        # 快速意图检查
        known_facts = self._extract_facts_from_memories(memories[:10])
        intent = await tom_agent.infer_intent(query, known_facts[:3])

        if not intent.is_adversarial:
            return None

        # 确认欺骗性
        deception = await tom_agent.detect_deception(query, known_facts)

        if deception.is_deceptive and deception.confidence >= 0.7:
            logger.info(f"🎭 Pre-reasoning adversarial check: {deception.deception_type}")
            return self._build_adversarial_response(
                query=query,
                intent=intent,
                deception=deception,
                memories=memories
            )

        return None

    def _extract_facts_from_memories(self, memories: List[Dict]) -> List[str]:
        """从记忆中提取事实"""
        facts = []
        for mem in memories:
            content = mem.get('content', '')
            if isinstance(content, str) and content.strip():
                # 清理内容
                clean_content = content.strip()[:200]  # 限制长度
                facts.append(clean_content)
        return facts

    def _build_adversarial_response(
        self,
        query: str,
        intent: Any,
        deception: Any,
        memories: List[Dict]
    ) -> Dict[str, Any]:
        """
        构建对抗性问题的回应

        Args:
            query: 原始问题
            intent: 意图分析结果
            deception: 欺骗检测结果
            memories: 记忆列表

        Returns:
            推理结果
        """
        # 根据欺骗类型生成回应
        if deception.deception_type == 'false_premise':
            answer = self._handle_false_premise(query, deception, memories)
        elif deception.deception_type == 'presupposition_violation':
            answer = self._handle_presupposition_violation(query, deception, memories)
        elif deception.deception_type == 'entity_confusion':
            answer = self._handle_entity_confusion(query, deception, memories)
        elif deception.deception_type == 'temporal_impossibility':
            answer = self._handle_temporal_impossibility(query, deception, memories)
        else:
            # 通用处理
            answer = deception.suggested_response or "I cannot find evidence to support the premise of this question."

        return {
            'answer': answer,
            'confidence': 0.85,  # 高置信度拒绝虚假前提
            'reasoning_chain': [
                f"Detected adversarial question type: {deception.deception_type}",
                f"Intent analysis: {intent.reasoning}",
                f"Violated facts: {deception.violated_facts}",
                f"Response strategy: Challenge false premise"
            ],
            'evidence': deception.violated_facts,
            'is_adversarial': True,
            'adversarial_type': deception.deception_type,
            'tom_analysis': {
                'surface_intent': intent.surface_intent,
                'deep_intent': intent.deep_intent,
                'deception_detected': True,
                'deception_type': deception.deception_type
            }
        }

    def _handle_false_premise(
        self,
        query: str,
        deception: Any,
        memories: List[Dict]
    ) -> str:
        """处理虚假前提问题"""
        # 提取被假设的虚假实体/关系
        violated = deception.violated_facts

        if violated:
            return f"No, there is no evidence to support this. {deception.suggested_response}"
        else:
            return "The question contains an assumption that is not supported by the available information."

    def _handle_presupposition_violation(
        self,
        query: str,
        deception: Any,
        memories: List[Dict]
    ) -> str:
        """处理预设违反问题"""
        if deception.suggested_response:
            return deception.suggested_response
        return "The question assumes something that did not happen according to the available information."

    def _handle_entity_confusion(
        self,
        query: str,
        deception: Any,
        memories: List[Dict]
    ) -> str:
        """处理实体混淆问题"""
        return f"There seems to be some confusion in the question. {deception.suggested_response}"

    def _handle_temporal_impossibility(
        self,
        query: str,
        deception: Any,
        memories: List[Dict]
    ) -> str:
        """处理时间不可能问题"""
        return f"The timeline in the question doesn't match the available records. {deception.suggested_response}"

    async def validate_question_presuppositions(
        self,
        query: str,
        memories: List[Dict]
    ) -> Dict[str, Any]:
        """
        验证问题中的预设

        Args:
            query: 用户问题
            memories: 相关记忆

        Returns:
            {
                'is_valid': bool,
                'invalid_presuppositions': List[str],
                'explanation': str
            }
        """
        try:
            from ...brain_regions.theory_of_mind_agent import get_theory_of_mind_agent
            tom_agent = get_theory_of_mind_agent()
        except Exception as e:
            return {'is_valid': True, 'invalid_presuppositions': [], 'explanation': ''}

        facts = self._extract_facts_from_memories(memories)
        is_valid, explanation = await tom_agent.validate_presupposition(query, facts)

        return {
            'is_valid': is_valid,
            'invalid_presuppositions': [] if is_valid else [explanation],
            'explanation': explanation
        }
