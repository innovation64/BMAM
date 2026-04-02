"""
Advanced Memory System with FAISS Vector Database
高级记忆系统：基于FAISS向量数据库

Integrated memory system combining embedding generation, vector search,
database persistence, and multiple search strategies through elegant
mixin composition.
"""

from typing import List, Dict, Any
import logging

from .embedding_service import EmbeddingService
from .vector_database import FAISSVectorDatabase
from .database_manager import DatabaseManager
from .database_queries import DatabaseQueryMixin
from .memory_storage import MemoryStorageMixin
from .semantic_search import SemanticSearchMixin
from .hybrid_search import HybridSearchMixin
from .keyword_search import KeywordSearchMixin
from .memory_maintenance import MemoryMaintenanceMixin

logger = logging.getLogger(__name__)


class AdvancedMemorySystem(
    MemoryStorageMixin,
    SemanticSearchMixin,
    HybridSearchMixin,
    KeywordSearchMixin,
    MemoryMaintenanceMixin
):
    """
    Integrated Memory System with FAISS Vector Search
    集成的FAISS向量搜索记忆系统

    Provides comprehensive memory operations through elegant composition:
    - Storage: Store new memories with embeddings
    - Semantic Search: Vector similarity-based retrieval
    - Hybrid Search: Combine semantic + metadata filtering
    - Keyword Search: Simple text-based retrieval
    - Maintenance: Index compaction and statistics

    Architecture:
        Uses mixin pattern for clean separation of concerns.
        Each mixin provides focused functionality and can be
        tested independently.

    Attributes:
        embedding_service: Text embedding generation
        vector_db: FAISS vector similarity search
        db_manager: SQLAlchemy persistence layer

    Example:
        >>> system = AdvancedMemorySystem()
        >>> mem_id = await system.store_memory("AI is fascinating")
        >>> results = await system.search_memories("AI", search_type="semantic")
        >>> stats = system.get_system_stats()
    """

    def __init__(self) -> None:
        """
        Initialize Advanced Memory System
        初始化高级记忆系统

        Sets up embedding service, vector database, and persistence layer.
        """
        logger.debug("Initializing Advanced Memory System...")

        # Initialize core components
        self.embedding_service = EmbeddingService()
        self.vector_db = FAISSVectorDatabase(
            dimension=self.embedding_service.dimension
        )
        self.db_manager = DatabaseManager()

        logger.debug("Advanced Memory System initialized successfully")

    async def search_memories(
        self,
        query: str,
        search_type: str = "semantic",
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Search Memories using Various Methods
        使用多种方法搜索记忆

        Unified search interface supporting multiple search strategies.

        Args:
            query: Search query text
            search_type: Type of search ("semantic", "hybrid", "keyword")
            k: Number of results to return
            threshold: Minimum similarity threshold (semantic/hybrid only)
            **filters: Additional filters for hybrid/keyword search

        Returns:
            List of memory dictionaries with search metadata

        Example:
            >>> # Semantic search
            >>> results = await system.search_memories(
            ...     "artificial intelligence",
            ...     search_type="semantic",
            ...     k=5
            ... )
            >>> # Hybrid search with filters
            >>> results = await system.search_memories(
            ...     "machine learning",
            ...     search_type="hybrid",
            ...     memory_type="semantic",
            ...     min_importance=0.7
            ... )
            >>> # Keyword search
            >>> results = await system.search_memories(
            ...     "neural network",
            ...     search_type="keyword",
            ...     limit=10
            ... )
        """
        try:
            # Extract user_id for all search paths
            user_id = filters.pop('user_id', None)
            if search_type == "semantic":
                return await self.semantic_search(
                    query, k, threshold, user_id=user_id
                )
            elif search_type == "hybrid":
                if user_id:
                    filters['user_id'] = user_id
                return await self.hybrid_search(query, k, threshold, **filters)
            else:
                if user_id:
                    filters['user_id'] = user_id
                return self.keyword_search(query, **filters)

        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return []


# Global memory system instance (lazy initialization)
# Use get_memory_system() to access instead of direct import
_memory_system_instance = None


def get_memory_system() -> AdvancedMemorySystem:
    """
    Get or Create Global Memory System Instance
    获取或创建全局记忆系统实例

    Lazy initialization pattern to avoid import-time side effects.

    Returns:
        Global AdvancedMemorySystem instance
    """
    global _memory_system_instance
    if _memory_system_instance is None:
        _memory_system_instance = AdvancedMemorySystem()
    return _memory_system_instance


# Deprecated: Direct instance access (for backward compatibility)
# TODO: Remove in next major version
def __getattr__(name):
    """Provide backward compatibility for direct memory_system access"""
    if name == "memory_system":
        import warnings
        warnings.warn(
            "Direct import of memory_system is deprecated. "
            "Use get_memory_system() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return get_memory_system()
    raise AttributeError(f"module has no attribute '{name}'")
