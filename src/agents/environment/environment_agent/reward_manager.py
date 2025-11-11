"""
Environment Agent Module - Reward Manager
环境智能体模块 - 奖励管理器

处理奖励信号的发布和调节。
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .data_models import RewardType, RewardSignal

logger = logging.getLogger(__name__)


class RewardManagerMixin:
    """奖励管理Mixin"""

    async def issue_reward(
        self,
        reward_type: RewardType,
        reward_value: float,
        reason: str,
        associated_memory_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """发布奖励信号"""
        # Clamp reward value
        reward_value = max(-1.0, min(1.0, reward_value))

        # Create reward signal
        reward = RewardSignal(
            reward_id=uuid.uuid4().hex,
            reward_type=reward_type,
            reward_value=reward_value,
            reason=reason,
            timestamp=datetime.now(),
            associated_memory_id=associated_memory_id
        )

        # Store reward
        self.reward_history.append(reward)
        self.cumulative_reward += reward_value
        self.total_rewards_issued += 1

        # Apply reward modulation to memory encoding
        modulation_applied = False
        if associated_memory_id and self.brain_coordinator:
            modulation_applied = await self._apply_reward_modulation(reward, associated_memory_id)

        return {
            'reward_id': reward.reward_id,
            'reward_type': reward_type.value,
            'reward_value': reward_value,
            'cumulative_reward': self.cumulative_reward,
            'modulation_applied': modulation_applied
        }

    async def _apply_reward_modulation(
        self,
        reward: RewardSignal,
        memory_id: str
    ) -> bool:
        """应用奖励调节到记忆编码"""
        try:
            if hasattr(self.brain_coordinator, 'amygdala'):
                amygdala = self.brain_coordinator.amygdala
                emotion_intensity = abs(reward.reward_value)
                
                emotion_tags = []
                if reward.reward_type == RewardType.POSITIVE:
                    emotion_tags = ["success", "satisfaction"]
                elif reward.reward_type == RewardType.NEGATIVE:
                    emotion_tags = ["failure", "disappointment"]
                else:
                    emotion_tags = ["neutral"]

                modulation_result = await amygdala.modulate_memory_encoding(
                    memory_id=memory_id,
                    emotion_intensity=emotion_intensity,
                    emotion_tags=emotion_tags
                )
                return modulation_result.get('modulated', False)

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to apply reward modulation: {e}")
            return False

    def get_recent_rewards(self, time_window_seconds: int = 3600) -> Dict[str, Any]:
        """获取最近的奖励"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)
        recent_rewards = [r for r in self.reward_history if r.timestamp >= cutoff_time]

        positive_count = sum(1 for r in recent_rewards if r.reward_type == RewardType.POSITIVE)
        negative_count = sum(1 for r in recent_rewards if r.reward_type == RewardType.NEGATIVE)
        neutral_count = sum(1 for r in recent_rewards if r.reward_type == RewardType.NEUTRAL)

        total_reward_value = sum(r.reward_value for r in recent_rewards)
        avg_reward = total_reward_value / len(recent_rewards) if recent_rewards else 0.0

        return {
            'time_window_seconds': time_window_seconds,
            'recent_rewards_count': len(recent_rewards),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'total_reward_value': total_reward_value,
            'average_reward': avg_reward,
            'cumulative_reward': self.cumulative_reward
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_state_transitions': self.total_state_transitions,
            'total_rewards_issued': self.total_rewards_issued,
            'total_feedback_issued': self.total_feedback_issued,
            'cumulative_reward': self.cumulative_reward,
            'current_state': self.current_state.state_type.value if self.current_state else None,
            'state_history_length': len(self.state_history),
            'reward_history_length': len(self.reward_history),
            'feedback_history_length': len(self.feedback_history),
            'pending_feedback_count': len(self.pending_feedback),
            'exploration_count': self.exploration_count
        }


__all__ = ['RewardManagerMixin']
