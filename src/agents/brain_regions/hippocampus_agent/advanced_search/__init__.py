"""
Advanced Search Package - 高级检索包
海马体高级检索策略 (Hippocampus Advanced Search Strategies)

This package provides sophisticated search capabilities for the hippocampus agent,
including temporal reasoning, entity-action binding, and adaptive refinement.

本包提供海马体智能体的高级检索能力，包括时间推理、实体-动作绑定和自适应精化。

Neural Science Basis | 神经科学依据:
- Event Segmentation Theory | 事件分割理论 (Zacks et al., 2007)
- Time Cells in Hippocampus | 海马体时间细胞 (MacDonald et al., 2011)
- Relational Encoding | 关系编码 (Ranganath & Ritchey, 2012)
- Hippocampus-Cortex Interaction | 海马体-皮层交互 (Norman & O'Reilly, 2003)

Architecture | 架构:
- Mixin-based composition for clean separation
- Each module handles one search strategy
- LLM-powered dynamic reasoning (no hardcoded rules)

Modules | 模块:
- event_boundary: Event boundary detection | 事件边界检测
- temporal_reasoning: Time-based search with LLM reasoning | 时间推理检索
- entity_action: Entity-action binding search | 实体-动作绑定检索
- feedback_refinement: Multi-dimensional search refinement | 多维度精化检索
- core: Integrated mixin composition | 集成混入组合

Usage | 使用:
    from src.agents.brain_regions.hippocampus_agent.advanced_search import AdvancedSearchMixin

    class HippocampusAgent(AdvancedSearchMixin, ...):
        # Inherits all advanced search capabilities
        pass
"""

from .core import AdvancedSearchMixin
from .event_boundary import EventBoundaryMixin
from .temporal_reasoning import TemporalReasoningMixin
from .entity_action import EntityActionBindingMixin
from .feedback_refinement import FeedbackRefinementMixin

__all__ = [
    'AdvancedSearchMixin',
    'EventBoundaryMixin',
    'TemporalReasoningMixin',
    'EntityActionBindingMixin',
    'FeedbackRefinementMixin',
]

__version__ = '2.0.0'
__author__ = 'BMAM Team'
