"""
Keyword-Based Search for Memory Retrieval
基于关键词的记忆检索

Provides simple text-based search with optional metadata filtering
for fast, deterministic memory retrieval.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class KeywordSearchMixin:
    """
    Keyword Search Operations Mixin
    关键词搜索操作混入类

    Implements simple text-matching search with optional filtering.
    Useful for deterministic retrieval and testing.

    Note:
        This mixin requires the class to have:
        - self.db_manager: DatabaseManager instance with search_memories()
    """

    def keyword_search(
        self,
        query: str,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Simple Keyword-Based Search
        简单的基于关键词的搜索

        Searches for memories containing the query text (case-insensitive)
        with optional metadata filtering.

        Args:
            query: Search query text
            **filters: Additional filters (passed to db_manager):
                - memory_type: Filter by type
                - brain_region: Filter by brain region
                - min_importance: Minimum importance
                - consolidation_level: Filter by consolidation
                - limit: Maximum results (default: 100)

        Returns:
            List of matching memory dictionaries

        Example:
            >>> results = searcher.keyword_search(
            ...     "neural network",
            ...     memory_type="semantic",
            ...     limit=10
            ... )
        """
        # Fetch memories with database filters
        memories = self.db_manager.search_memories(**filters)

        # Apply keyword matching
        results = []
        query_lower = query.lower()

        for memory in memories:
            if query_lower in memory.content.lower():
                result = memory.to_dict()
                result['search_type'] = 'keyword'
                results.append(result)

        logger.info(
            f"Keyword search for '{query}' found {len(results)} results"
        )
        return results
