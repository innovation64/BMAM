"""
Entity-Action Candidate Retrieval - 实体-动作候选检索
混合检索策略

Retrieves candidates using hybrid strategy
"""

import logging
from typing import Optional, List

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class EntityActionRetriever:
    """
    实体-动作检索器 (Entity-Action Retriever)

    Strategy | 策略:
    1. Entity index lookup
    2. Semantic search expansion
    """

    def __init__(self, agent):
        """Initialize retriever"""
        self.agent = agent


    async def retrieve(
        self,
        entity: Optional[str],
        action: Optional[str],
        query: str
    ) -> List[EpisodicMemory]:
        """
        检索候选记忆 - Retrieve Candidates

        Args:
            entity: 实体名称
            action: 动作
            query: 原始查询

        Returns:
            List of candidate memories
        """
        candidates = []

        # Strategy 1: Entity index lookup
        if entity and hasattr(self.agent, 'entity_index'):
            if entity in self.agent.entity_index:
                memory_ids = self.agent.entity_index[entity]
                candidates = [
                    self.agent.memory_dict[mid] for mid in memory_ids
                    if mid in self.agent.memory_dict
                ]

        # Strategy 2: Semantic search expansion
        search_result = await self.agent.search_memories(query=query, k=50)
        semantic_candidates = [
            self.agent.memory_dict[mem_dict['id']]
            for mem_dict in search_result['memories']
            if mem_dict['id'] in self.agent.memory_dict
            and self.agent.memory_dict[mem_dict['id']] not in candidates
        ]

        candidates.extend(semantic_candidates)

        return candidates
