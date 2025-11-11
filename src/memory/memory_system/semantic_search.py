"""
Semantic Search for Memory Retrieval
语义搜索记忆检索

Provides vector similarity-based semantic search with multi-tier
fallback strategies for robust retrieval.
"""

from typing import List, Dict, Any
import logging

import numpy as np

logger = logging.getLogger(__name__)


class SemanticSearchMixin:
    """
    Semantic Search Operations Mixin
    语义搜索操作混入类

    Implements vector similarity-based memory retrieval with
    intelligent threshold adjustment and fallback strategies.

    Note:
        This mixin requires the class to have:
        - self.embedding_service: EmbeddingService instance
        - self.vector_db: FAISSVectorDatabase instance
        - self.db_manager: DatabaseManager instance
    """

    async def semantic_search(
        self,
        query: str,
        k: int = 10,
        threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Perform Semantic Search using Vector Similarity
        使用向量相似度执行语义搜索

        Features multi-tier fallback strategy to ensure adequate recall
        even when initial threshold is too strict.

        Args:
            query: Search query text
            k: Number of results to return
            threshold: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of dictionaries with memory data and similarity scores

        Example:
            >>> results = await searcher.semantic_search("AI", k=5)
            >>> for r in results:
            ...     print(r['content'], r['similarity_score'])
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.encode_text(query)

            # Dynamic threshold adjustment (avoid too strict)
            effective_threshold = max(0.25, min(threshold, 0.75))

            # Search similar vectors
            similar_memories = self.vector_db.search(
                query_embedding,
                k,
                effective_threshold
            )

            # Multi-tier fallback for low recall
            similar_memories = await self._apply_fallback_strategy(
                query_embedding,
                similar_memories,
                k,
                effective_threshold
            )

        except Exception as e:
            logger.warning(
                f"Failed to generate query embedding for '{query}': {e}"
            )
            return []

        # Load full memory objects with quality filtering
        results = self._build_search_results(similar_memories)

        # Sort by similarity and return top-k
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = results[:k]

        logger.info(
            f"Semantic search for '{query}' found {len(results)} results "
            f"(threshold={effective_threshold:.2f})"
        )
        return results

    async def _apply_fallback_strategy(
        self,
        query_embedding: np.ndarray,
        similar_memories: List[tuple],
        k: int,
        effective_threshold: float
    ) -> List[tuple]:
        """
        Apply Multi-Tier Fallback for Low Recall
        应用多层次回退策略以提高召回率

        If initial search returns insufficient results, retry with
        progressively relaxed thresholds.
        """
        min_results = max(3, k // 2)

        if len(similar_memories) >= min_results:
            return similar_memories

        # Tier 2: Relaxed threshold with more results
        logger.warning(
            f"Low recall ({len(similar_memories)} results with "
            f"threshold={effective_threshold:.2f}), retrying with "
            f"relaxed threshold"
        )
        similar_memories = self.vector_db.search(
            query_embedding,
            k * 3,
            threshold=0.15
        )

        # Tier 3: Ultra-relaxed for edge cases
        if len(similar_memories) < 2:
            logger.warning("Ultra-low recall, trying threshold=0.05")
            similar_memories = self.vector_db.search(
                query_embedding,
                k * 5,
                threshold=0.05
            )

        return similar_memories

    def _build_search_results(
        self,
        similar_memories: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Build Search Results from Memory IDs
        从记忆ID构建搜索结果

        Loads full memory objects and filters out low-quality matches.
        """
        results = []
        for memory_id, similarity in similar_memories:
            # Quality validation: reject very low similarity
            if similarity < 0.1:
                continue

            memory = self.db_manager.load_memory(memory_id)
            if memory:
                result = memory.to_dict()
                result['similarity_score'] = similarity
                result['search_type'] = 'semantic'
                results.append(result)

        return results
