"""
Advanced Search Core - 高级检索核心
海马体高级检索策略集成

Corresponds to: 海马体高级检索功能
Neural Basis: Integrated search strategies in hippocampus
"""

from .event_boundary import EventBoundaryMixin
from .temporal_reasoning import TemporalReasoningMixin
from .entity_action import EntityActionBindingMixin
from .feedback_refinement import FeedbackRefinementMixin


class AdvancedSearchMixin(
    EventBoundaryMixin,
    TemporalReasoningMixin,
    EntityActionBindingMixin,
    FeedbackRefinementMixin
):
    """
    高级检索混入类 - Advanced Search Mixin

    Composition of Advanced Search Strategies | 高级检索策略组合:
    - Event Boundary Detection | 事件边界检测
    - Temporal Reasoning Search | 时间推理检索
    - Entity-Action Binding Search | 实体-动作绑定检索
    - Feedback Refinement Search | 反馈精化检索

    Neural Science Basis | 神经科学依据:
    - 海马体多策略检索能力
    - 事件分割 + 时间细胞 + 关系编码 + 双向反馈

    Design Pattern | 设计模式:
    - Mixin composition for clean separation
    - Each mixin handles one search strategy
    - No duplication, high cohesion
    """
    pass
