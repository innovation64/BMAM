"""
Feedback Refinement Search - 反馈精化检索
海马体-皮层双向交互

Neural Basis: Hippocampus-Cortex Bidirectional Interaction
Reference: Norman & O'Reilly (2003), Ranganath & Ritchey (2012)
"""

import logging
from typing import Dict, List, Any

from ..core import EpisodicMemory
from .feedback_filters import FeedbackFilters
from .feedback_supplementer import FeedbackSupplementer

logger = logging.getLogger(__name__)


class FeedbackRefinementMixin:
    """
    反馈精化检索混入类 (Feedback Refinement Mixin)

    Neural Science Basis | 神经科学依据:
    - Prefrontal control of hippocampal retrieval
    - Hippocampus-cortex bidirectional interaction

    Features | 功能:
    - Multi-dimensional filtering | 多维度过滤
    - Missing aspect supplementation | 缺失维度补充
    """

    async def refine_search_with_feedback(
        self,
        query: str,
        initial_results: List[Dict],
        feedback: Dict[str, Any]
    ) -> List[Dict]:
        """
        反馈精化检索 - Refine Search with Feedback

        Feedback Dimensions | 反馈维度:
        - irrelevant_ids, preferred_time_range, preferred_entities
        - min_importance, min_emotion_intensity, missing_aspects

        Args:
            query: 原始查询
            initial_results: 初次检索结果
            feedback: 推理层反馈

        Returns:
            精化后的记忆列表
        """
        # Convert to EpisodicMemory objects
        initial_memories = self._convert_to_memories(initial_results)

        if not initial_memories:
            logger.warning("No valid initial memories found")
            return []

        # Apply filters
        filters = FeedbackFilters(self)
        refined = filters.apply_all(initial_memories, feedback)

        # Supplement if insufficient
        if len(refined) < 5 and 'missing_aspects' in feedback:
            supplementer = FeedbackSupplementer(self)
            refined = await supplementer.supplement(query, refined, feedback)

        return [self._memory_to_dict(m) for m in refined]


    def _convert_to_memories(
        self,
        results: List[Dict]
    ) -> List[EpisodicMemory]:
        """转换结果为EpisodicMemory对象"""
        memories = []
        for result_dict in results:
            mem_id = result_dict.get('id')
            if mem_id and mem_id in self.memory_dict:
                memories.append(self.memory_dict[mem_id])
        return memories
