"""
Hippocampus Agent Module
海马体智能体模块 - 情节记忆存储、检索和巩固

拆分说明:
- core.py: 核心类定义和初始化
- storage.py: 存储和索引管理
- retrieval.py: 基本检索和搜索
- consolidation.py: 记忆巩固
- forgetting.py: 遗忘机制
- advanced_search.py: 高级搜索(事件分割、时间推理、实体动作绑定)
"""

from .core import EpisodicMemory, HippocampusAgentCore
from .storage import StorageMixin
from .retrieval import RetrievalMixin
from .consolidation import ConsolidationMixin
from .forgetting import ForgettingMixin
from .advanced_search import AdvancedSearchMixin


class HippocampusAgent(
    StorageMixin,
    RetrievalMixin,
    ConsolidationMixin,
    ForgettingMixin,
    AdvancedSearchMixin,
    HippocampusAgentCore
):
    """
    海马体智能体 - 整合所有功能的完整类

    继承顺序说明:
    - Mixin类优先(提供具体功能)
    - Core类最后(提供基础结构)
    - Python MRO确保方法正确解析
    """
    pass


__all__ = [
    'HippocampusAgent',
    'EpisodicMemory',
    'HippocampusAgentCore',
    'StorageMixin',
    'RetrievalMixin',
    'ConsolidationMixin',
    'ForgettingMixin',
    'AdvancedSearchMixin',
]
