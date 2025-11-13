"""
Memory Maintenance Operations
记忆维护操作

Provides maintenance and cleanup operations including FAISS index
compaction, rebuilding, and storage limit enforcement.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MemoryMaintenanceMixin:
    """
    Memory Maintenance Operations Mixin
    记忆维护操作混入类

    Provides maintenance operations for keeping the memory system
    healthy and within configured limits.

    Note:
        This mixin requires the class to have:
        - self.embedding_service: EmbeddingService instance
        - self.vector_db: FAISSVectorDatabase instance
        - self.db_manager: DatabaseManager instance
    """

    async def enforce_storage_limits(
        self,
        max_vectors: int = 5000
    ) -> bool:
        """
        Enforce Storage Limits by Rebuilding FAISS Index
        通过重建FAISS索引强制执行存储限制

        If the vector count exceeds the configured limit, rebuilds
        the index with only the most recent memories.

        Args:
            max_vectors: Maximum number of vectors allowed

        Returns:
            True if compaction was performed, False otherwise

        Example:
            >>> compacted = await maintenance.enforce_storage_limits(5000)
            >>> if compacted:
            ...     print("Index was compacted")
        """
        if max_vectors <= 0:
            return False

        current_total = self.vector_db.index.ntotal
        if current_total <= max_vectors:
            return False

        logger.warning(
            f"FAISS index size {current_total} exceeds limit {max_vectors}; "
            f"rebuilding with most recent memories"
        )

        # Fetch recent memories
        recent_memories = self.db_manager.get_recent_memories(limit=max_vectors)
        if not recent_memories:
            logger.warning(
                "No recent memories available for compaction; aborting rebuild"
            )
            return False

        # Reset index
        self.vector_db.reset()

        # Rebuild with recent memories
        try:
            texts = [memory.content for memory in recent_memories]
            embeddings = await self.embedding_service.encode_batch(texts)

            # Verify alignment: embeddings list must match memories list length
            if len(embeddings) != len(recent_memories):
                logger.error(
                    f"Embedding count mismatch: {len(embeddings)} embeddings "
                    f"for {len(recent_memories)} memories. Aborting compaction."
                )
                return False
        except Exception as exc:
            logger.error(
                f"Failed to rebuild FAISS index during compaction: {exc}"
            )
            return False

        # Add vectors back (skip None embeddings to preserve alignment)
        success_count = 0
        for memory, embedding in zip(recent_memories, embeddings):
            if embedding is None:
                logger.warning(
                    f"Skipping memory {memory.id} due to failed embedding"
                )
                continue
            self.vector_db.add_vector(memory.id, embedding)
            success_count += 1

        # Persist changes
        self.vector_db.save_index()
        logger.info(
            f"FAISS index compacted: {success_count}/{len(recent_memories)} "
            f"vectors rebuilt (total: {self.vector_db.index.ntotal})"
        )
        return True

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get Comprehensive System Statistics
        获取综合系统统计信息

        Returns:
            Dictionary with database stats, vector stats, and model info

        Example:
            >>> stats = maintenance.get_system_stats()
            >>> print(stats['vectors']['vector_count'])
            >>> print(stats['database']['total_memories'])
        """
        db_stats = self.db_manager.get_memory_stats()
        vector_stats = {
            'vector_count': self.vector_db.index.ntotal,
            'vector_dimension': self.vector_db.dimension,
            'index_path': self.vector_db.index_path
        }

        return {
            'database': db_stats,
            'vectors': vector_stats,
            'embedding_model': self.embedding_service.model_name,
            'embedding_type': 'openai_cached'
        }
