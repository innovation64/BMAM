"""
Reasoning Validator Agent - 推理验证器
模拟前额叶的推理和验证功能

核心功能:
1. 从记忆中提取证据并推理
2. 与海马体双向反馈(不够就再检索)
3. 输出结构化推理结果(答案+置信度+推理链)

🔧 2025-12-12: 添加检索反馈回路
- 当推理置信度低时，通知海马体优化检索策略
- 支持在线学习 (ContrastiveKeyOptimizer)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ...base import BrainAgent

from .identity_reasoning import IdentityReasoningMixin
from .temporal_reasoning import TemporalReasoningMixin
from .multi_hop_reasoning import MultiHopReasoningMixin
from .general_reasoning import GeneralReasoningMixin
from .retrieval_feedback import RetrievalFeedbackMixin
from .retrieval_guidance import RetrievalGuidanceMixin

logger = logging.getLogger(__name__)


class ReasoningValidatorAgent(
    BrainAgent,
    IdentityReasoningMixin,
    TemporalReasoningMixin,
    MultiHopReasoningMixin,
    GeneralReasoningMixin,
    RetrievalFeedbackMixin,
    RetrievalGuidanceMixin
):
    """
    推理验证器: 模拟前额叶的推理功能

    脑区映射: Prefrontal Cortex (前额叶)
    认知功能: 工作记忆、推理、决策、验证
    """

    def __init__(self, llm_client=None, reflection_agent=None, consolidation_agent=None):
        super().__init__(
            agent_id="reasoning_validator",
            brain_region="prefrontal",
            system_prompt="Reasoning Validator - validates inferences from memories",
            client=llm_client
        )
        self.reasoning_history = []  # 推理历史

        # 🧠 协作推理: 引用其他脑区agents
        self.reflection_agent = reflection_agent  # 用于pattern-based推理
        self.consolidation_agent = consolidation_agent  # 用于fact integration推理

    async def process_message(self, message: Any) -> Dict[str, Any]:
        """实现抽象方法 process_message (required by BrainAgent)"""
        return await self.process(message)

    async def process(self, message: Any) -> Dict[str, Any]:
        """处理推理请求"""
        content = message.content if hasattr(message, 'content') else message
        action = content.get('action', 'validate_reasoning')

        # 🔄 BrainNetwork compatibility: 'stimulus' or 'query'
        query = content.get('query') or content.get('stimulus')
        if not query:
            # BrainNetwork模式: 从nested context提取
            ctx = content.get('context', {})
            query = ctx.get('query') or ctx.get('user_input', '')

        if not query:
            return {'error': 'No query/stimulus provided'}

        # 🔥 2025-12-12: 前额叶检索指导
        if action == 'provide_guidance':
            return await self.provide_retrieval_guidance(
                query=query,
                context=content.get('context')
            )

        if action == 'validate_reasoning':
            return await self.validate_reasoning(
                query=query,
                memories=content.get('memories', []),
                question_type=content.get('question_type', 'general'),
                hippocampus_agent=content.get('hippocampus_agent'),  # 用于双向反馈
                memories_by_region=content.get('memories_by_region')  # 🔥 按脑区组织的记忆
            )
        else:
            return {'error': f'Unknown action: {action}'}

    async def validate_reasoning(
        self,
        query: str,
        memories: List[Dict],
        question_type: str,
        hippocampus_agent: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        验证推理: 从记忆中推断答案

        Args:
            query: 用户问题
            memories: 检索到的记忆
            question_type: 问题类型(identity/temporal/research/multi_hop)
            hippocampus_agent: 海马体agent(用于双向反馈)
            memories_by_region: 按脑区组织的记忆 (新增)

        Returns:
            {
                'answer': 推断的答案,
                'confidence': 置信度(0-1),
                'reasoning_chain': 推理步骤列表,
                'evidence': 使用的证据,
                'refined_query': 如果需要再检索,返回优化的查询
            }
        """
        logger.debug(f"🧠 Reasoning Validator: {question_type} question")

        # 根据问题类型选择推理策略
        if question_type == 'identity':
            result = await self._identity_reasoning(query, memories, hippocampus_agent, memories_by_region)
        elif question_type == 'temporal':
            result = await self._temporal_reasoning(query, memories, hippocampus_agent, memories_by_region)
        elif question_type == 'research':
            result = await self._research_reasoning(query, memories, hippocampus_agent, memories_by_region)
        elif question_type == 'factual':
            # 事实查询 (relationship, location等) - 使用general_reasoning
            result = await self._general_reasoning(query, memories)
        elif question_type == 'multi_hop':
            result = await self._multi_hop_reasoning(query, memories, hippocampus_agent, memories_by_region)
        else:
            result = await self._general_reasoning(query, memories)

        # 记录推理历史
        self.reasoning_history.append({
            'query': query,
            'question_type': question_type,
            'result': result,
            'timestamp': datetime.now()
        })

        # 🔥 检索反馈: 当推理置信度低时，通知海马体
        await self._send_retrieval_feedback(
            query=query,
            memories=memories,
            reasoning_result=result,
            hippocampus_agent=hippocampus_agent,
            feedback_type="automatic"
        )

        return result

    def get_reasoning_stats(self) -> Dict[str, Any]:
        """获取推理统计"""
        if not self.reasoning_history:
            return {'total': 0}

        total = len(self.reasoning_history)
        by_type = {}
        avg_confidence = 0

        for r in self.reasoning_history:
            q_type = r['question_type']
            by_type[q_type] = by_type.get(q_type, 0) + 1
            avg_confidence += r['result'].get('confidence', 0)

        return {
            'total': total,
            'by_type': by_type,
            'avg_confidence': avg_confidence / total if total > 0 else 0
        }
