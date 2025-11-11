"""
Entity-Action Binding Search - 实体-动作绑定检索
海马体关系编码 (Relational Encoding)

Neural Basis: Relational Encoding
Reference: Ranganath & Ritchey (2012)
"""

import logging
from typing import Dict, Any

from .entity_action_extraction import EntityActionExtractor
from .entity_action_retrieval import EntityActionRetriever
from .entity_action_ranking import EntityActionRanker

logger = logging.getLogger(__name__)


class EntityActionBindingMixin:
    """
    实体-动作绑定检索混入类 (Entity-Action Binding Mixin)

    Neural Science Basis | 神经科学依据:
    - Relational Encoding in Hippocampus
    - Remembers "who did what"

    Problem Solved | 解决问题:
    - Q3: 区分不同实体的动作
    - 精确绑定 (entity, action, object)
    """

    async def search_with_entity_action_binding(
        self,
        query: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        实体-动作绑定检索 - Entity-Action Binding Search

        Args:
            query: 查询（包含实体和动作）
            k: 返回数量

        Returns:
            memories, entity_action_analysis, extracted_entity, extracted_action
        """
        # Extract entity and action
        extractor = EntityActionExtractor(self)
        entity_action = await extractor.extract(query)

        if not entity_action.get('entity') and not entity_action.get('action'):
            # Fallback to semantic search
            search_result = await self.search_memories(query=query, k=k)
            return {
                'memories': search_result['memories'],
                'entity_action_analysis': 'No entity/action, fallback',
                'extracted_entity': None,
                'extracted_action': None,
                'count': search_result['count']
            }

        # Retrieve candidates
        retriever = EntityActionRetriever(self)
        candidates = await retriever.retrieve(
            entity_action.get('entity'),
            entity_action.get('action'),
            query
        )

        if not candidates:
            return {
                'memories': [],
                'entity_action_analysis': f"No memories for entity='{entity_action.get('entity')}'",
                'extracted_entity': entity_action.get('entity'),
                'extracted_action': entity_action.get('action'),
                'count': 0
            }

        # Rank by binding precision
        ranker = EntityActionRanker(self)
        ranked_results = await ranker.rank(
            query, candidates,
            entity_action.get('entity'),
            entity_action.get('action')
        )

        top_results = ranked_results[:k]

        return {
            'memories': [self._memory_to_dict(r['memory']) for r in top_results],
            'entity_action_analysis': ranked_results[0].get('reasoning', '') if ranked_results else '',
            'extracted_entity': entity_action.get('entity'),
            'extracted_action': entity_action.get('action'),
            'count': len(top_results)
        }
