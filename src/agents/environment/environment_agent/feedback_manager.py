"""
Environment Agent Module - Feedback Manager
环境智能体模块 - 反馈管理器

处理反馈事件的创建和传递。
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .data_models import FeedbackEvent

logger = logging.getLogger(__name__)


class FeedbackManagerMixin:
    """反馈管理Mixin"""

    async def provide_feedback(
        self,
        feedback_type: str,
        content: str,
        target_agent: Optional[str] = None,
        severity: str = "info"
    ) -> Dict[str, Any]:
        """提供反馈"""
        # Create feedback event
        feedback = FeedbackEvent(
            feedback_id=uuid.uuid4().hex,
            feedback_type=feedback_type,
            content=content,
            timestamp=datetime.now(),
            target_agent=target_agent,
            severity=severity
        )

        # Store feedback
        self.feedback_history.append(feedback)
        self.pending_feedback.append(feedback)
        self.total_feedback_issued += 1

        # Deliver feedback to target agent
        delivery_success = False
        if target_agent and self.brain_coordinator:
            delivery_success = await self._deliver_feedback_to_agent(feedback, target_agent)

        return {
            'feedback_id': feedback.feedback_id,
            'feedback_type': feedback_type,
            'target_agent': target_agent,
            'severity': severity,
            'delivery_success': delivery_success
        }

    async def _deliver_feedback_to_agent(
        self,
        feedback: FeedbackEvent,
        target_agent_id: str
    ) -> bool:
        """传递反馈到目标智能体"""
        try:
            if hasattr(self.brain_coordinator, 'get_agent'):
                target_agent = self.brain_coordinator.get_agent(target_agent_id)
                if target_agent and hasattr(target_agent, 'receive_feedback'):
                    await target_agent.receive_feedback(feedback)
                    return True
        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to deliver feedback to agent {target_agent_id}: {e}")
        return False

    def get_pending_feedback(self) -> Dict[str, Any]:
        """获取待处理的反馈"""
        feedback_list = []
        for fb in self.pending_feedback:
            feedback_list.append({
                'feedback_id': fb.feedback_id,
                'feedback_type': fb.feedback_type,
                'content': fb.content,
                'timestamp': fb.timestamp.isoformat(),
                'target_agent': fb.target_agent,
                'severity': fb.severity
            })

        return {
            'pending_feedback_count': len(self.pending_feedback),
            'pending_feedback': feedback_list
        }

    def clear_pending_feedback(self):
        """清除待处理的反馈"""
        cleared_count = len(self.pending_feedback)
        self.pending_feedback = []
        return {
            'cleared_count': cleared_count,
            'remaining_count': 0
        }


__all__ = ['FeedbackManagerMixin']
