"""
Temporal Reasoning Search - 时间推理检索
海马体时间细胞 (Time Cells)

Neural Basis: Time Cells (MacDonald et al., 2011)
"""

import logging
from typing import Dict, Any

from .temporal_cue_extraction import TemporalCueExtractor
from .temporal_candidate_retrieval import TemporalCandidateRetriever
from .temporal_ranking import TemporalRanker

logger = logging.getLogger(__name__)


class TemporalReasoningMixin:
    """
    时间推理检索混入类 (Temporal Reasoning Search Mixin)

    Neural Science Basis | 神经科学依据:
    - Time Cells in Hippocampus
    - Temporal reasoning, not simple indexing

    Problem Solved | 解决问题:
    - Q1: 区分多个时间候选
    - 理解"第一次"、"最近"等时间意图
    """

    async def search_with_temporal_reasoning(
        self,
        query: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        带时间推理的检索 - Temporal Reasoning Search

        Args:
            query: 查询（包含时间线索）
            k: 返回数量

        Returns:
            memories, temporal_analysis, most_relevant_time, count
        """
        # Extract temporal cues
        cue_extractor = TemporalCueExtractor(self)
        temporal_cues = await cue_extractor.extract(query)

        # Retrieve candidates
        candidate_retriever = TemporalCandidateRetriever(self)
        candidates = await candidate_retriever.retrieve(query, temporal_cues)

        if not candidates:
            return {
                'memories': [],
                'temporal_analysis': 'No relevant memories found',
                'most_relevant_time': None,
                'count': 0
            }

        # Rank by temporal relevance
        ranker = TemporalRanker(self)
        ranked_results = await ranker.rank(query, candidates, temporal_cues)

        # Build response
        top_results = ranked_results[:k]
        most_relevant_time = (
            top_results[0]['memory'].timestamp.isoformat()
            if top_results else None
        )

        return {
            'memories': [self._memory_to_dict(r['memory']) for r in top_results],
            'temporal_analysis': ranked_results[0].get('reasoning', '') if ranked_results else '',
            'most_relevant_time': most_relevant_time,
            'count': len(top_results)
        }
