"""
Retrieval Feedback Mixin - 检索反馈混入类

功能:
1. 当推理置信度低时，通知海马体优化检索策略
2. 使用 ContrastiveKeyOptimizer 进行在线学习
3. 支持显式和隐式反馈

🔧 2025-12-12: 新增，解决脑区协作反馈问题
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RetrievalFeedbackMixin:
    """
    检索反馈混入类

    当推理结果置信度低或无法回答时，向海马体发送反馈信号
    海马体可以根据反馈调整检索权重或策略
    """

    # 触发反馈的置信度阈值 (可配置)
    FEEDBACK_CONFIDENCE_THRESHOLD = 0.5

    async def _send_retrieval_feedback(
        self,
        query: str,
        memories: List[Dict],
        reasoning_result: Dict[str, Any],
        hippocampus_agent: Optional[Any] = None,
        feedback_type: str = "implicit"
    ) -> Dict[str, Any]:
        """
        发送检索反馈给海马体

        Args:
            query: 原始查询
            memories: 检索到的记忆
            reasoning_result: 推理结果
            hippocampus_agent: 海马体 agent (如果可用)
            feedback_type: 反馈类型 (explicit/implicit/automatic)

        Returns:
            反馈处理结果
        """
        confidence = reasoning_result.get('confidence', 0)
        answer = reasoning_result.get('answer', '')

        # 判断是否需要反馈
        needs_feedback = (
            confidence < self.FEEDBACK_CONFIDENCE_THRESHOLD or
            not answer or
            answer.lower() in ['unknown', 'not found', 'cannot determine', 'n/a']
        )

        if not needs_feedback:
            return {'feedback_sent': False, 'reason': 'confidence_sufficient'}

        # 构建反馈信号
        feedback_signal = {
            'query': query,
            'confidence': confidence,
            'answer': answer,
            'memory_count': len(memories),
            'feedback_type': feedback_type,
            'timestamp': datetime.now().isoformat(),
            # 提取检索到的记忆 ID (用于负样本标记)
            'retrieved_memory_ids': [
                m.get('id') or m.get('memory', {}).get('id')
                for m in memories if m
            ],
            # 推理失败的原因提示 (不是硬编码规则，而是 LLM 推断的 hints)
            'failure_hints': reasoning_result.get('evidence', {}).get('reasoning_chain', []),
        }

        logger.info(
            f"📤 Sending retrieval feedback: confidence={confidence:.2f}, "
            f"memory_count={len(memories)}, type={feedback_type}"
        )

        # 方式1: 直接调用海马体的反馈接口 (如果可用)
        if hippocampus_agent:
            try:
                result = await self._notify_hippocampus(
                    hippocampus_agent, feedback_signal
                )
                return {'feedback_sent': True, 'method': 'direct', 'result': result}
            except Exception as e:
                logger.warning(f"Direct hippocampus feedback failed: {e}")

        # 方式2: 通过 ContrastiveKeyOptimizer (如果集成)
        if hasattr(self, 'key_optimizer') and self.key_optimizer:
            try:
                await self._update_key_optimizer(feedback_signal)
                return {'feedback_sent': True, 'method': 'key_optimizer'}
            except Exception as e:
                logger.warning(f"Key optimizer feedback failed: {e}")

        # 方式3: 记录到反馈历史 (延迟处理)
        if not hasattr(self, 'pending_feedback'):
            self.pending_feedback = []
        self.pending_feedback.append(feedback_signal)

        return {'feedback_sent': True, 'method': 'deferred'}

    async def _notify_hippocampus(
        self,
        hippocampus_agent: Any,
        feedback_signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        直接通知海马体处理反馈

        海马体可以:
        1. 调整检索权重
        2. 触发额外的语义搜索
        3. 标记相关记忆为 "需要补充"
        """
        # 检查海马体是否支持反馈接口
        if hasattr(hippocampus_agent, 'receive_retrieval_feedback'):
            return await hippocampus_agent.receive_retrieval_feedback(feedback_signal)

        # 或者使用消息传递
        if hasattr(hippocampus_agent, 'process_message'):
            from ....base import AgentMessage
            message = AgentMessage(
                sender='reasoning_validator',
                content={
                    'action': 'retrieval_feedback',
                    'feedback': feedback_signal
                }
            )
            return await hippocampus_agent.process_message(message)

        logger.warning("Hippocampus agent does not support feedback interface")
        return {'success': False, 'reason': 'no_feedback_interface'}

    async def _update_key_optimizer(
        self,
        feedback_signal: Dict[str, Any]
    ) -> None:
        """
        使用 ContrastiveKeyOptimizer 进行在线学习

        将检索失败的记忆标记为负样本
        """
        if not hasattr(self, 'key_optimizer'):
            return

        retrieved_ids = feedback_signal.get('retrieved_memory_ids', [])
        query = feedback_signal.get('query', '')

        # 如果置信度低，说明检索到的记忆不相关 → 负样本
        if feedback_signal.get('confidence', 0) < self.FEEDBACK_CONFIDENCE_THRESHOLD:
            self.key_optimizer.add_implicit_feedback(
                query_text=query,
                negative_ids=retrieved_ids,
                feedback_source='reasoning_validator'
            )

    def get_pending_feedback(self) -> List[Dict[str, Any]]:
        """获取待处理的反馈"""
        return getattr(self, 'pending_feedback', [])

    def clear_pending_feedback(self) -> None:
        """清空待处理的反馈"""
        self.pending_feedback = []
