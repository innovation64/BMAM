"""
Temporal Candidate Retrieval - 时间候选检索
混合检索策略

Retrieves temporal candidates using hybrid strategy
"""

import logging
from typing import Dict, List

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class TemporalCandidateRetriever:
    """
    时间候选检索器 (Temporal Candidate Retriever)

    Strategy | 策略:
    - Semantic search (expanded k)
    - Time index (if explicit time)
    """

    def __init__(self, agent):
        """Initialize retriever"""
        self.agent = agent


    async def retrieve(
        self,
        query: str,
        temporal_cues: Dict
    ) -> List[EpisodicMemory]:
        """
        检索时间相关候选 - Retrieve Temporal Candidates

        Args:
            query: 查询文本
            temporal_cues: 时间线索

        Returns:
            List of candidate memories
        """
        # Semantic search with expanded k
        search_result = await self.agent.search_memories(query=query, k=50)

        # Convert to EpisodicMemory objects
        candidates = []
        for mem_dict in search_result['memories']:
            mem = self.agent.memory_dict.get(mem_dict['id'])
            if mem:
                candidates.append(mem)

        return candidates
