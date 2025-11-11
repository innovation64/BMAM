"""
Environment Agent Module - State Manager
环境智能体模块 - 状态管理器

处理环境状态跟踪和转换。
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .data_models import StateType, EnvironmentState

logger = logging.getLogger(__name__)


class StateManagerMixin:
    """状态管理Mixin"""

    async def update_state(
        self,
        state_type: StateType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新环境状态

        Args:
            state_type: 状态类型
            context: 上下文信息

        Returns:
            {'state_id': str, 'transition': bool}
        """
        # Calculate duration of previous state
        previous_state_id = None
        duration = 0.0

        if self.current_state:
            previous_state_id = self.current_state.state_id
            duration = (datetime.now() - self.current_state.timestamp).total_seconds()
            self.current_state.duration_seconds = duration

            # Archive to history
            self.state_history.append(self.current_state)

            # Trim history if needed
            if len(self.state_history) > self.max_history_length:
                self.state_history = self.state_history[-self.max_history_length:]

        # Create new state
        new_state = EnvironmentState(
            state_id=uuid.uuid4().hex,
            state_type=state_type,
            timestamp=datetime.now(),
            context=context,
            previous_state_id=previous_state_id
        )

        # Update current state
        old_state_type = self.current_state.state_type if self.current_state else None
        self.current_state = new_state
        self.total_state_transitions += 1

        # Trigger memory encoding for important state transitions
        if state_type != StateType.IDLE and self.brain_coordinator:
            await self._encode_state_transition_to_memory(new_state, old_state_type)

        return {
            'state_id': new_state.state_id,
            'transition': True,
            'previous_state': old_state_type.value if old_state_type else None,
            'current_state': state_type.value,
            'duration_previous': duration
        }

    async def _encode_state_transition_to_memory(
        self,
        new_state: EnvironmentState,
        old_state_type: Optional[StateType]
    ):
        """
        将重要的状态转换编码到记忆中

        Args:
            new_state: 新状态
            old_state_type: 旧状态类型
        """
        try:
            # Store state transition in Hippocampus as episodic memory
            if hasattr(self.brain_coordinator, 'hippocampus'):
                hippocampus = self.brain_coordinator.hippocampus

                # Create memory content
                if old_state_type:
                    content = f"State transition: {old_state_type.value} → {new_state.state_type.value}"
                else:
                    content = f"Initial state: {new_state.state_type.value}"

                # Add context details
                if new_state.context:
                    context_str = ", ".join([f"{k}={v}" for k, v in list(new_state.context.items())[:3]])
                    content += f" ({context_str})"

                # Determine importance based on state type
                importance_map = {
                    StateType.TASK_EXECUTION: 0.7,
                    StateType.LEARNING: 0.8,
                    StateType.ERROR: 0.9,
                    StateType.CONVERSATION: 0.5,
                    StateType.IDLE: 0.2
                }
                importance = importance_map.get(new_state.state_type, 0.5)

                # Store in Hippocampus
                await hippocampus.store_memory(
                    content=content,
                    entities=[new_state.state_type.value],
                    importance=importance,
                    emotion_tags=[],
                    emotion_intensity=0.3,
                    metadata={
                        'state_id': new_state.state_id,
                        'state_type': new_state.state_type.value,
                        'source': 'environment'
                    }
                )

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to encode state transition to memory: {e}")

    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.current_state:
            return {'current_state': None}

        return {
            'current_state': {
                'state_id': self.current_state.state_id,
                'state_type': self.current_state.state_type.value,
                'timestamp': self.current_state.timestamp.isoformat(),
                'context': self.current_state.context,
                'duration_seconds': self.current_state.duration_seconds
            }
        }

    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        context_summary = {
            'current_state': self.current_state.state_type.value if self.current_state else None,
            'recent_states': [],
            'recent_rewards': [],
            'pending_feedback_count': len(self.pending_feedback)
        }

        # Recent states (last 5)
        recent_states = self.state_history[-5:] if self.state_history else []
        for state in recent_states:
            context_summary['recent_states'].append({
                'type': state.state_type.value,
                'timestamp': state.timestamp.isoformat(),
                'duration': state.duration_seconds
            })

        # Recent rewards (last 5)
        recent_rewards = self.reward_history[-5:] if self.reward_history else []
        for reward in recent_rewards:
            context_summary['recent_rewards'].append({
                'type': reward.reward_type.value,
                'value': reward.reward_value,
                'reason': reward.reason,
                'timestamp': reward.timestamp.isoformat()
            })

        return context_summary


__all__ = ['StateManagerMixin']
