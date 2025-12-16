"""
Advanced Memory System V2 with Dependency Injection
高级记忆系统V2：基于依赖注入

This version eliminates import-time side effects and uses dependency
injection for all components, making it fully testable and configurable.
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio

from src.core.interfaces.memory_interface import (
    IMemorySystem,
    IEmbeddingService,
    IVectorDatabase
)
from src.core.config import MemorySystemConfig, get_config
from .database_manager import DatabaseManager
from .memory_storage import MemoryStorageMixin
from .semantic_search import SemanticSearchMixin
from .hybrid_search import HybridSearchMixin
from .keyword_search import KeywordSearchMixin
from .memory_maintenance import MemoryMaintenanceMixin

logger = logging.getLogger(__name__)


class AdvancedMemorySystemV2(
    MemoryStorageMixin,
    SemanticSearchMixin,
    HybridSearchMixin,
    KeywordSearchMixin,
    MemoryMaintenanceMixin,
    IMemorySystem
):
    """
    Advanced Memory System V2 with Dependency Injection
    高级记忆系统V2：依赖注入版本

    Key improvements over V1:
    - No import-time side effects
    - All dependencies injected via constructor
    - Lazy initialization of expensive resources
    - Fully testable with real or mock components
    - Configuration via dataclass instead of globals

    Architecture:
        Uses same mixin pattern as V1 but with DI:
        - Dependencies passed to constructor
        - Lazy initialization on first use
        - Configuration-driven behavior

    Example:
        >>> from src.core.container import get_container
        >>> from src.core.config import get_config
        >>>
        >>> # Get dependencies from DI container
        >>> container = get_container()
        >>> embedder = container.resolve(IEmbeddingService)
        >>> vector_db = container.resolve(IVectorDatabase)
        >>>
        >>> # Create system with injected dependencies
        >>> system = AdvancedMemorySystemV2(
        ...     embedder=embedder,
        ...     vector_db=vector_db,
        ...     config=get_config().memory
        ... )
        >>>
        >>> # Use normally
        >>> memory_id = await system.store_memory("Test")
        >>> results = await system.search_memories("Test", k=5)
    """

    def __init__(
        self,
        embedder: IEmbeddingService,
        vector_db: IVectorDatabase,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[MemorySystemConfig] = None
    ):
        """
        Initialize Memory System V2 with Dependency Injection
        初始化记忆系统V2（依赖注入）

        Args:
            embedder: Embedding service (injected)
            vector_db: Vector database (injected)
            db_manager: Database manager (optional, created if None)
            config: Memory system configuration (optional, uses global if None)

        Note:
            This constructor does NOT initialize expensive resources.
            Resources are initialized lazily on first use.
        """
        logger.debug("Initializing AdvancedMemorySystemV2 (no side effects)...")

        # Store injected dependencies
        self.embedding_service = embedder
        self.vector_db = vector_db
        self.db_manager = db_manager or DatabaseManager()
        self._config = config or get_config().memory

        # Lazy initialization flag
        self._initialized = False
        self._init_lock = asyncio.Lock()

        logger.debug("AdvancedMemorySystemV2 created (resources not yet initialized)")

    async def _ensure_initialized(self):
        """
        Ensure system is initialized (lazy initialization)
        确保系统已初始化（延迟初始化）

        This is called automatically before any operation.
        Initialization is done only once, on first use.
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:  # Double-check pattern
                return

            logger.info("Initializing AdvancedMemorySystemV2 resources...")

            # Initialize any lazy resources here
            # (Currently mixins handle their own initialization)

            self._initialized = True
            logger.info("AdvancedMemorySystemV2 initialization complete")

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
        Store Memory with Lazy Initialization
        存储记忆（延迟初始化）

        Args:
            content: Memory content
            memory_type: Type of memory (episodic/semantic/procedural)
            importance: Importance score (0.0-1.0)
            emotion_tags: List of emotion labels
            context_tags: List of context tags
            metadata: Additional metadata dictionary

        Returns:
            Memory ID if successful, None if failed
        """
        await self._ensure_initialized()
        return await super().store_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            emotion_tags=emotion_tags,
            context_tags=context_tags,
            metadata=metadata
        )

    async def retrieve_memories(
        self,
        query: str,
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Memories with Lazy Initialization
        检索记忆（延迟初始化）

        Args:
            query: Search query
            k: Number of results
            threshold: Similarity threshold
            **filters: Additional filters

        Returns:
            List of memory results
        """
        await self._ensure_initialized()
        # Use semantic search as default
        return await self.semantic_search(
            query=query,
            k=k,
            threshold=threshold,
            **filters
        )

    async def search_memories(
        self,
        query: str,
        search_type: str = "semantic",
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Search Memories using Various Strategies
        使用多种策略搜索记忆

        Args:
            query: Search query
            search_type: Type of search ("semantic", "hybrid", "keyword")
            k: Number of results
            threshold: Similarity threshold
            **filters: Additional filters

        Returns:
            List of memory results
        """
        await self._ensure_initialized()

        if search_type == "semantic":
            return await self.semantic_search(query, k, threshold)
        elif search_type == "hybrid":
            return await self.hybrid_search(query, k, threshold, **filters)
        elif search_type == "keyword":
            return await self.keyword_search(query, k, **filters)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get Memory System Statistics
        获取记忆系统统计信息

        Returns:
            Dictionary with system statistics
        """
        # Can call without initialization (just reads current state)
        return super().get_system_stats()

    async def compact_index(self) -> Dict[str, Any]:
        """
        Compact Vector Index
        压缩向量索引

        Returns:
            Compaction results
        """
        await self._ensure_initialized()
        return await super().compact_index()

    def __repr__(self) -> str:
        """String representation"""
        init_status = "initialized" if self._initialized else "not initialized"
        return f"AdvancedMemorySystemV2({init_status})"
