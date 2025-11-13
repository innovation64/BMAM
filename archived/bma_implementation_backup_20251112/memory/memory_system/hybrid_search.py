"""
Hybrid Search for Memory Retrieval
混合搜索记忆检索

Combines semantic vector search with structured metadata filtering
for precise and relevant memory retrieval.
"""

from typing import List, Dict, Any
import logging

from ..memory_item import MemoryItem

logger = logging.getLogger(__name__)


class HybridSearchMixin:
    """
    Hybrid Search Operations Mixin
    混合搜索操作混入类

    Combines semantic search with metadata filtering to provide
    highly targeted memory retrieval based on multiple criteria.

    Note:
        This mixin requires the class to have:
        - self.semantic_search(query, k, threshold) -> List[Dict]
    """

    async def hybrid_search(
        self,
        query: str,
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Combine Semantic Search with Metadata Filters
        结合语义搜索和元数据过滤

        Performs semantic search and then applies structured filters
        to refine results based on memory attributes.

        Args:
            query: Search query text
            k: Number of results to return
            threshold: Minimum similarity threshold
            **filters: Additional filters:
                - memory_type: Filter by type (episodic/semantic)
                - min_importance: Minimum importance score
                - brain_region: Filter by brain region
                - context_tags: Filter by context tags
                - emotion_tags: Filter by emotion tags

        Returns:
            List of filtered search results

        Example:
            >>> results = await searcher.hybrid_search(
            ...     "machine learning",
            ...     k=5,
            ...     memory_type="semantic",
            ...     min_importance=0.7
            ... )
        """
        # Start with semantic search (request more for filtering)
        semantic_results = await self.semantic_search(
            query,
            k * 2,
            threshold
        )

        # Apply metadata filters
        filtered_results = self._apply_metadata_filters(
            semantic_results,
            filters
        )

        # Limit to requested number
        filtered_results = filtered_results[:k]

        logger.info(
            f"Hybrid search for '{query}' found {len(filtered_results)} "
            f"results after filtering"
        )
        return filtered_results

    def _apply_metadata_filters(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply Metadata Filters to Search Results
        对搜索结果应用元数据过滤

        Filters results based on memory attributes like type,
        importance, brain region, and tags.
        """
        filtered_results = []

        for result in results:
            memory = MemoryItem.from_dict(result)

            # Apply type filter
            if filters.get('memory_type'):
                if memory.memory_type != filters['memory_type']:
                    continue

            # Apply importance filter
            if filters.get('min_importance'):
                if memory.importance < filters['min_importance']:
                    continue

            # Apply brain region filter
            if filters.get('brain_region'):
                if memory.brain_region != filters['brain_region']:
                    continue

            # Apply context tag filter
            if filters.get('context_tags'):
                required_tags = filters['context_tags']
                if isinstance(required_tags, str):
                    required_tags = [required_tags]
                if not any(tag in memory.context_tags for tag in required_tags):
                    continue

            # Apply emotion tag filter
            if filters.get('emotion_tags'):
                required_emotions = filters['emotion_tags']
                if isinstance(required_emotions, str):
                    required_emotions = [required_emotions]
                if not any(tag in memory.emotion_tags for tag in required_emotions):
                    continue

            # Mark as hybrid search result
            result['search_type'] = 'hybrid'
            filtered_results.append(result)

        return filtered_results
