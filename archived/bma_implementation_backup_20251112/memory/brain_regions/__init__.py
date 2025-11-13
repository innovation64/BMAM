"""
Brain Region Memory Modules
脑区记忆模块 - 分布式记忆表征

每个脑区存储不同类型的记忆"侧面"

Phase 2 Note:
- PrefrontalInferenceRules has been deprecated (removed in Phase 2)
- Hardcoded if-then rules replaced with LLM-based reasoning
- See: BMAM分布式存储层问题分析_其他脑区.md (优化6)
"""

from .hippocampal_event_graph import HippocampalEventGraph
from .temporal_concept_graph import TemporalConceptGraph
from .amygdala_emotion_tags import AmygdalaEmotionTags

__all__ = [
    'HippocampalEventGraph',
    'TemporalConceptGraph',
    'AmygdalaEmotionTags'
]
