"""
Environment Agent Module
环境智能体模块 - 环境状态、奖励和反馈管理

拆分说明:
- data_models.py: 数据模型和枚举
- core.py: 核心类定义和消息处理
- state_manager.py: 状态管理
- reward_manager.py: 奖励系统
- feedback_manager.py: 反馈系统
- exploration_manager.py: 外部探索和数据源管理
"""

from .data_models import (
    StateType, RewardType, EnvironmentState, RewardSignal, FeedbackEvent
)
from .core import EnvironmentAgentCore
from .state_manager import StateManagerMixin
from .reward_manager import RewardManagerMixin
from .feedback_manager import FeedbackManagerMixin
from .exploration_manager import ExplorationManagerMixin


class EnvironmentAgent(
    ExplorationManagerMixin,
    FeedbackManagerMixin,
    RewardManagerMixin,
    StateManagerMixin,
    EnvironmentAgentCore
):
    """
    环境智能体 - 整合所有功能的完整类

    继承顺序说明:
    - Mixin类优先(提供具体功能)
    - Core类最后(提供基础结构)

    功能模块:
    1. StateManagerMixin: 状态跟踪和转换
    2. RewardManagerMixin: 奖励信号发布和调节
    3. FeedbackManagerMixin: 反馈事件创建和传递
    4. ExplorationManagerMixin: 外部数据源探索
    """
    pass


__all__ = [
    'EnvironmentAgent',
    'EnvironmentAgentCore',
    'StateType',
    'RewardType',
    'EnvironmentState',
    'RewardSignal',
    'FeedbackEvent',
    'StateManagerMixin',
    'RewardManagerMixin',
    'FeedbackManagerMixin',
    'ExplorationManagerMixin',
]
