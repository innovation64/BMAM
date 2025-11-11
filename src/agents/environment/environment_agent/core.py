"""
Environment Agent Module - Core
环境智能体模块 - 核心类

包含核心类定义、初始化和消息处理。
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ...base import BrainAgent, AgentMessage, BrainRegion
from ..data_sources import (
    data_source_registry, initialize_default_sources
)
from .data_models import (
    StateType, RewardType, EnvironmentState, RewardSignal, FeedbackEvent
)

logger = logging.getLogger(__name__)


class EnvironmentAgentCore(BrainAgent):
    """
    环境智能体核心类

    Responsibilities:
    1. Track environment state transitions
    2. Generate reward signals based on outcomes
    3. Provide feedback for learning
    4. Maintain context awareness
    5. Interface with external systems
    """

    def __init__(self, brain_coordinator=None, client=None, data_source_config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="environment",
            brain_region=BrainRegion.PREFRONTAL,  # 环境感知涉及多个区域,归类为前额叶
            system_prompt="""You are the Environment agent, responsible for managing environment state, rewards, and feedback.
            You track state transitions, generate reward signals for learning, and provide feedback for agent improvement.
            You act as the interface between the internal brain system and the external world.""",
            client=client
        )

        # Brain coordinator reference
        self.brain_coordinator = brain_coordinator

        # State management
        self.current_state: Optional[EnvironmentState] = None
        self.state_history: List[EnvironmentState] = []
        self.max_history_length = 1000

        # Reward system
        self.reward_history: List[RewardSignal] = []
        self.cumulative_reward = 0.0
        self.reward_window = timedelta(hours=1)  # 1小时内的奖励窗口

        # Feedback system
        self.feedback_history: List[FeedbackEvent] = []
        self.pending_feedback: List[FeedbackEvent] = []

        # Statistics
        self.total_state_transitions = 0
        self.total_rewards_issued = 0
        self.total_feedback_issued = 0

        # External Data Sources (Phase 4 Enhancement)
        self.data_source_registry = data_source_registry
        self.exploration_count = 0

        # Initialize data sources
        initialize_default_sources(config=data_source_config)

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        # State management actions
        if action == 'update_state':
            return await self.update_state(
                state_type=StateType(message.content['state_type']),
                context=message.content.get('context', {})
            )

        elif action == 'get_current_state':
            return self.get_current_state()

        # Reward system actions
        elif action == 'issue_reward':
            return await self.issue_reward(
                reward_type=RewardType(message.content['reward_type']),
                reward_value=message.content['reward_value'],
                reason=message.content['reason'],
                associated_memory_id=message.content.get('associated_memory_id')
            )

        elif action == 'get_recent_rewards':
            return self.get_recent_rewards(
                time_window_seconds=message.content.get('time_window_seconds', 3600)
            )

        # Feedback system actions
        elif action == 'provide_feedback':
            return await self.provide_feedback(
                feedback_type=message.content['feedback_type'],
                content=message.content['content'],
                target_agent=message.content.get('target_agent'),
                severity=message.content.get('severity', 'info')
            )

        elif action == 'get_pending_feedback':
            return self.get_pending_feedback()

        # Exploration actions
        elif action == 'explore_external':
            return await self.explore_external(
                query=message.content['query'],
                query_type=message.content.get('query_type', 'general'),
                max_results=message.content.get('max_results', 5)
            )

        # Statistics
        elif action == 'get_statistics':
            return self.get_statistics()

        elif action == 'get_context_summary':
            return self.get_context_summary()

        return {'error': f'Unknown action: {action}'}


__all__ = ['EnvironmentAgentCore']
