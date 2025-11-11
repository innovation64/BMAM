"""
Forgetting Agent Module
遗忘智能体模块 - 主动遗忘、记忆清理、干扰消除

Module structure (模块结构):
- core.py: 核心类定义和消息处理
- decay/: 被动衰减和遗忘曲线 (split into focused modules)
  - passive_decay.py: 被动衰减实现
  - ebbinghaus.py: 艾宾浩斯遗忘曲线
- interference.py: 记忆干扰消除和冲突解决
- pruning.py: 智能修剪和选择性遗忘
- context_dependent.py: 上下文依赖遗忘
- motivated_forgetting.py: 动机性遗忘（情感和创伤）
- retrieval_based_forgetting.py: 检索诱导遗忘（RIF）
"""

from .core import ForgettingAgentCore
from .decay import DecayMixin  # Now imports from decay/ subdirectory
from .interference import InterferenceMixin
from .pruning import PruningMixin
from .context_dependent import ContextDependentMixin
from .motivated_forgetting import MotivatedForgettingMixin
from .retrieval_based_forgetting import RetrievalBasedForgettingMixin


class ForgettingAgent(
    ContextDependentMixin,
    MotivatedForgettingMixin,
    RetrievalBasedForgettingMixin,
    DecayMixin,
    InterferenceMixin,
    PruningMixin,
    ForgettingAgentCore
):
    """
    遗忘智能体 - 整合所有功能的完整类

    继承顺序说明:
    - Mixin类优先(提供具体功能)
    - Core类最后(提供基础结构)

    功能模块:
    1. DecayMixin: 被动衰减和Ebbinghaus遗忘曲线
    2. InterferenceMixin: 记忆干扰消除和冲突解决
    3. PruningMixin: 智能修剪和选择性遗忘
    4. ContextDependentMixin: 上下文依赖遗忘
    5. MotivatedForgettingMixin: 动机性遗忘（情感/创伤抑制）
    6. RetrievalBasedForgettingMixin: 检索诱导遗忘（RIF）
    """
    pass


__all__ = [
    'ForgettingAgent',
    'ForgettingAgentCore',
    'DecayMixin',
    'InterferenceMixin',
    'PruningMixin',
    'ContextDependentMixin',
    'MotivatedForgettingMixin',
    'RetrievalBasedForgettingMixin',
]
