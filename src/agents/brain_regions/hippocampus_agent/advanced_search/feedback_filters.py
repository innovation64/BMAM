"""
Feedback Filters - 反馈过滤器
多维度过滤算法

Multi-dimensional filtering for search refinement
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class FeedbackFilters:
    """
    反馈过滤器 (Feedback Filters)

    Applies multi-dimensional filters | 应用多维度过滤:
    - Irrelevant IDs | 不相关ID
    - Time range | 时间范围
    - Entities | 实体
    - Importance | 重要性
    - Emotion intensity | 情绪强度
    """

    def __init__(self, agent):
        """Initialize filters"""
        self.agent = agent


    def apply_all(self, memories: List[EpisodicMemory], feedback: Dict[str, Any]) -> List[EpisodicMemory]:
        """应用所有过滤器"""
        refined = memories.copy()
        refined = self._filter_irrelevant(refined, feedback)
        refined = self._filter_by_time_range(refined, feedback)
        refined = self._filter_by_entities(refined, feedback)
        refined = self._filter_by_importance(refined, feedback)
        refined = self._filter_by_emotion(refined, feedback)
        return refined


    def _filter_irrelevant(self, memories: List[EpisodicMemory], feedback: Dict) -> List[EpisodicMemory]:
        """过滤不相关记忆"""
        irrelevant_ids = set(feedback.get('irrelevant_ids', []))
        return [m for m in memories if m.id not in irrelevant_ids] if irrelevant_ids else memories

    def _filter_by_time_range(self, memories: List[EpisodicMemory], feedback: Dict) -> List[EpisodicMemory]:
        """时间范围过滤"""
        if 'preferred_time_range' not in feedback:
            return memories
        time_range = feedback['preferred_time_range']
        if not isinstance(time_range, tuple) or len(time_range) != 2:
            return memories
        start_str, end_str = time_range
        start_time = self._parse_datetime(start_str)
        end_time = self._parse_datetime(end_str)
        return [m for m in memories if start_time <= m.timestamp <= end_time]

    def _filter_by_entities(self, memories: List[EpisodicMemory], feedback: Dict) -> List[EpisodicMemory]:
        """实体过滤"""
        if 'preferred_entities' not in feedback:
            return memories
        preferred_entities = set(feedback['preferred_entities'])
        return [m for m in memories if any(e in preferred_entities for e in m.entities)]

    def _filter_by_importance(self, memories: List[EpisodicMemory], feedback: Dict) -> List[EpisodicMemory]:
        """重要性过滤"""
        if 'min_importance' not in feedback:
            return memories
        return [m for m in memories if m.importance >= feedback['min_importance']]

    def _filter_by_emotion(self, memories: List[EpisodicMemory], feedback: Dict) -> List[EpisodicMemory]:
        """情绪强度过滤"""
        if 'min_emotion_intensity' not in feedback:
            return memories
        return [m for m in memories if m.emotion_intensity >= feedback['min_emotion_intensity']]


    def _parse_datetime(self, dt_input: Any) -> datetime:
        """解析时间"""
        if isinstance(dt_input, str):
            return datetime.fromisoformat(dt_input)
        return dt_input
