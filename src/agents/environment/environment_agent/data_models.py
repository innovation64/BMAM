"""
Environment Agent Module - Data Models
环境智能体模块 - 数据模型

包含所有的数据类和枚举定义。
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class StateType(Enum):
    """环境状态类型"""
    CONVERSATION = "conversation"  # 对话状态
    TASK_EXECUTION = "task_execution"  # 任务执行
    LEARNING = "learning"  # 学习状态
    IDLE = "idle"  # 空闲状态
    ERROR = "error"  # 错误状态


class RewardType(Enum):
    """奖励类型"""
    POSITIVE = "positive"  # 正向奖励 (成功、正确)
    NEGATIVE = "negative"  # 负向奖励 (失败、错误)
    NEUTRAL = "neutral"  # 中性 (无明确反馈)


@dataclass
class EnvironmentState:
    """
    环境状态

    跟踪环境在特定时刻的状态。
    """
    state_id: str
    state_type: StateType
    timestamp: datetime
    context: Dict[str, Any]  # 上下文信息
    previous_state_id: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardSignal:
    """
    奖励信号

    表示一个奖励事件，用于强化学习和记忆调制。
    """
    reward_id: str
    reward_type: RewardType
    reward_value: float  # -1.0 to 1.0
    reason: str  # 奖励原因
    timestamp: datetime
    associated_memory_id: Optional[str] = None  # 关联的记忆ID
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackEvent:
    """
    反馈事件

    表示一个反馈事件，用于学习和适应。
    """
    feedback_id: str
    feedback_type: str  # "correction", "reinforcement", "suggestion"
    content: str  # 反馈内容
    timestamp: datetime
    target_agent: Optional[str] = None  # 目标智能体
    severity: str = "info"  # "info", "warning", "error"
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    'StateType',
    'RewardType',
    'EnvironmentState',
    'RewardSignal',
    'FeedbackEvent',
]
