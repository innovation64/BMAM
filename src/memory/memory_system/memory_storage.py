"""
Memory Storage Operations
记忆存储操作

Handles the storage of new memories including embedding generation,
vector database indexing, and persistent storage.
"""

from typing import List, Dict, Any, Optional
import logging

from ..memory_item import MemoryItem

logger = logging.getLogger(__name__)


class MemoryStorageMixin:
    """
    Memory Storage Operations Mixin
    记忆存储操作混入类

    Provides methods for storing new memories with automatic
    embedding generation and vector indexing.

    Note:
        This mixin requires the class to have:
        - self.embedding_service: EmbeddingService instance
        - self.vector_db: FAISSVectorDatabase instance
        - self.db_manager: DatabaseManager instance
    """

    async def store_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        emotion_tags: List[str] = None,
        context_tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        embedding: Any = None  # 🔥 FIX: 接受预计算的 embedding
    ) -> Optional[str]:
        """
        Store New Memory with Embedding
        存储新记忆（包含嵌入）

        Creates a new memory item, generates its vector embedding,
        adds it to the vector database, and persists to storage.

        Args:
            content: Memory content text
            memory_type: Type of memory (episodic/semantic/procedural)
            importance: Importance score (0.0-1.0)
            emotion_tags: List of emotion labels
            context_tags: List of context tags
            metadata: Additional metadata dictionary
            embedding: Pre-computed embedding (optional, avoids recomputation)

        Returns:
            Memory ID if successful, None if failed

        Example:
            >>> memory_id = await storage.store_memory(
            ...     content="Learned about transformers",
            ...     memory_type="semantic",
            ...     importance=0.8,
            ...     context_tags=["AI", "NLP"]
            ... )
        """
        try:
            if metadata is None:
                metadata = {}

            # Create memory item
            memory = MemoryItem(
                content=content,
                memory_type=memory_type,
                importance=importance,
                emotion_tags=emotion_tags or [],
                context_tags=context_tags or [],
                metadata=metadata
            )

            # 🔥 FIX: 使用预计算的 embedding 或生成新的
            try:
                import numpy as np
                if embedding is not None:
                    # 使用预计算的 embedding
                    if isinstance(embedding, list):
                        memory.embedding = np.array(embedding)
                    else:
                        memory.embedding = embedding
                    logger.debug(f"Using pre-computed embedding for memory")
                else:
                    # 生成新的 embedding
                    memory.embedding = await self.embedding_service.encode_text(
                        content
                    )

                # Add to vector database
                faiss_id = self.vector_db.add_vector(memory.id, memory.embedding)
                memory.embedding_id = str(faiss_id)

            except Exception as e:
                logger.warning(f"Failed to generate embedding for memory: {e}")
                # Don't store memory without valid embedding
                return None

            # Save to persistent storage
            success = self.db_manager.save_memory(memory)

            if success:
                # Persist vector index
                self.vector_db.save_index()

                # Verify FAISS mapping
                if memory.id in self.vector_db.reverse_mapping:
                    faiss_id = self.vector_db.reverse_mapping[memory.id]
                    logger.debug(
                        f"Successfully stored memory {memory.id} -> "
                        f"FAISS index {faiss_id}"
                    )
                    logger.debug(
                        f"Vector DB stats: total_vectors="
                        f"{self.vector_db.index.ntotal}, "
                        f"mappings={len(self.vector_db.reverse_mapping)}"
                    )
                else:
                    logger.error(
                        f"Memory {memory.id} stored in DB but NOT in "
                        f"FAISS mapping!"
                    )

                return memory.id
            else:
                logger.error(f"Failed to store memory {memory.id}")
                return None

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return None

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Specific Memory by ID
        通过ID获取特定记忆

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory dictionary if found, None otherwise
        """
        memory = self.db_manager.load_memory(memory_id)
        return memory.to_dict() if memory else None

    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update Existing Memory (in-place, no duplication)
        更新现有记忆（原地更新，不重复）

        Args:
            memory_id: Memory ID to update
            updates: Fields to update (content, importance, emotion_tags, etc.)

        Returns:
            True if updated successfully, False if not found
        """
        # Load existing memory
        existing = self.db_manager.load_memory(memory_id)
        if not existing:
            logger.warning(f"Memory {memory_id} not found for update")
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        # Re-generate embedding if content changed
        if 'content' in updates:
            embedding = await self.embedding_service.get_embedding(updates['content'])
            # Update vector in FAISS
            idx = self.vector_db.get_index_for_id(memory_id)
            if idx is not None:
                self.vector_db.update_vector(idx, embedding)

        # Save to DB
        self.db_manager.save_memory(existing)
        logger.debug(f"Updated memory {memory_id}")
        return True

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete Memory from System
        从系统中删除记忆

        Removes the memory from both vector database (FAISS) and
        persistent storage (SQLite).

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted successfully, False if not found
        """
        # Check if memory exists
        existing = self.db_manager.load_memory(memory_id)
        if not existing:
            logger.warning(f"Memory {memory_id} not found for deletion")
            return False

        try:
            # Remove from vector database (FAISS)
            idx = self.vector_db.get_index_for_id(memory_id)
            if idx is not None:
                self.vector_db.remove_vector(idx)
                logger.debug(f"Removed vector for memory {memory_id}")

            # Remove from persistent storage (SQLite)
            # Mark as inactive instead of hard delete for safety
            existing.is_active = False
            self.db_manager.save_memory(existing)

            logger.info(f"Deleted memory {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False
