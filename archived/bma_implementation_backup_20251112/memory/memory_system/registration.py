"""
Memory System Registration for Dependency Injection
记忆系统DI注册

Registers memory system components in the DI container.
"""

from typing import Optional
import logging

from src.core.container import Container as DependencyContainer, get_container
from src.core.interfaces.memory_interface import (
    IMemorySystem,
    IEmbeddingService,
    IVectorDatabase
)
from src.core.adapters.embedding_service_adapter import EmbeddingServiceAdapter
from src.core.adapters.vector_database_adapter import VectorDatabaseAdapter
from src.core.config import get_config, MemorySystemConfig

from .embedding_service import EmbeddingService
from .vector_database import FAISSVectorDatabase
from .memory_system_v2 import AdvancedMemorySystemV2

logger = logging.getLogger(__name__)


def register_memory_system_components(
    container: Optional[DependencyContainer] = None
) -> None:
    """
    Register Memory System Components in DI Container
    在DI容器中注册记忆系统组件

    Registers:
    - IEmbeddingService (singleton)
    - IVectorDatabase (singleton)
    - IMemorySystem (singleton)

    Args:
        container: DI container (uses global if None)

    Example:
        >>> from src.core.container import get_container
        >>> container = get_container()
        >>> register_memory_system_components(container)
        >>> memory = container.resolve(IMemorySystem)
    """
    container = container or get_container()
    config = get_config().memory

    logger.info("Registering memory system components...")

    # Register Embedding Service
    from src.core.container import Lifecycle
    container.register(
        IEmbeddingService,
        factory=lambda c: EmbeddingServiceAdapter(
            EmbeddingService(
                model=config.embedding_model,
                dimension=config.embedding_dim,
                use_cache=config.use_embedding_cache
            )
        ),
        lifecycle=Lifecycle.SINGLETON
    )
    logger.debug("Registered IEmbeddingService")

    # Register Vector Database
    container.register(
        IVectorDatabase,
        factory=lambda c: VectorDatabaseAdapter(
            FAISSVectorDatabase(
                dimension=config.embedding_dim
            )
        ),
        lifecycle=Lifecycle.SINGLETON
    )
    logger.debug("Registered IVectorDatabase")

    # Register Memory System
    container.register(
        IMemorySystem,
        factory=lambda c: AdvancedMemorySystemV2(
            embedder=c.resolve(IEmbeddingService),
            vector_db=c.resolve(IVectorDatabase),
            config=config
        ),
        lifecycle=Lifecycle.SINGLETON
    )
    logger.debug("Registered IMemorySystem")

    logger.info("Memory system components registered successfully")


def create_memory_system(
    embedder: Optional[IEmbeddingService] = None,
    vector_db: Optional[IVectorDatabase] = None,
    config: Optional[MemorySystemConfig] = None,
    container: Optional[DependencyContainer] = None
) -> IMemorySystem:
    """
    Create Memory System with Dependency Injection
    使用依赖注入创建记忆系统

    Factory function for creating memory system instances.
    Uses DI container to resolve dependencies if not provided.

    Args:
        embedder: Embedding service (optional, resolved from container)
        vector_db: Vector database (optional, resolved from container)
        config: Memory configuration (optional, uses global config)
        container: DI container (optional, uses global container)

    Returns:
        IMemorySystem instance

    Example:
        >>> # Use default dependencies from container
        >>> memory = create_memory_system()
        >>>
        >>> # Provide custom dependencies
        >>> custom_embedder = MyEmbeddingService()
        >>> memory = create_memory_system(embedder=custom_embedder)
        >>>
        >>> # Use custom config
        >>> test_config = MemorySystemConfig(embedding_dim=512)
        >>> memory = create_memory_system(config=test_config)
    """
    container = container or get_container()
    config = config or get_config().memory

    # Ensure components are registered
    if not container.is_registered(IMemorySystem):
        register_memory_system_components(container)

    # Resolve or use provided dependencies
    if embedder is None:
        embedder = container.resolve(IEmbeddingService)

    if vector_db is None:
        vector_db = container.resolve(IVectorDatabase)

    # Create and return memory system
    return AdvancedMemorySystemV2(
        embedder=embedder,
        vector_db=vector_db,
        config=config
    )
