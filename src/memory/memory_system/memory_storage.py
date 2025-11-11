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
        metadata: Dict[str, Any] = None
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

            # Generate embedding
            try:
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
