"""
Environment Agent Module - 环境智能体模块
Phase 4: 增强环境Agent (状态/奖励/反馈)
"""

from .environment_agent import (
    EnvironmentAgent,
    StateType,
    RewardType,
    EnvironmentState,
    RewardSignal,
    FeedbackEvent
)

__all__ = [
    'EnvironmentAgent',
    'StateType',
    'RewardType',
    'EnvironmentState',
    'RewardSignal',
    'FeedbackEvent'
]
