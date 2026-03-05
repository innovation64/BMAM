"""
Memory System Package
记忆系统包

Advanced memory system with FAISS vector database, multiple search
strategies, and brain-inspired architecture.

This package provides:
- Embedding generation with caching
- Vector similarity search
- Persistent storage with SQLAlchemy
- Multiple search strategies (semantic, hybrid, keyword)
- Memory maintenance and statistics

Architecture:
    The package uses elegant mixin composition to separate concerns:
    - Database models and persistence
    - Embedding and vector operations
    - Multiple search strategies
    - Maintenance and statistics

Example:
    >>> from memory.memory_system import AdvancedMemorySystem
    >>> system = AdvancedMemorySystem()
    >>> memory_id = await system.store_memory("Hello world")
    >>> results = await system.search_memories("Hello", search_type="semantic")

Backward Compatibility:
    All classes are re-exported at package level for backward compatibility:
    >>> from memory.memory_system import EmbeddingService, FAISSVectorDatabase
    >>> from memory.memory_system import DatabaseManager, MemoryRecord
"""

# Core system
from .advanced_memory_system import (
    AdvancedMemorySystem,
    get_memory_system
)

# Backward compatibility: memory_system will trigger deprecation warning
# when accessed via __getattr__ in advanced_memory_system.py

# Database layer
from .database_models import (
    Base,
    MemoryRecord
)
from .database_manager import DatabaseManager
from .database_queries import DatabaseQueryMixin

# Embedding and vector layer
from .embedding_service import EmbeddingService
from .vector_database import FAISSVectorDatabase

# Search strategies
from .semantic_search import SemanticSearchMixin
from .hybrid_search import HybridSearchMixin
from .keyword_search import KeywordSearchMixin

# Operations
from .memory_storage import MemoryStorageMixin
from .memory_maintenance import MemoryMaintenanceMixin

# Public API
__all__ = [
    # Main system
    'AdvancedMemorySystem',
    'get_memory_system',  # Recommended factory function
    'memory_system',      # Deprecated, kept for backward compatibility

    # Database
    'Base',
    'MemoryRecord',
    'DatabaseManager',
    'DatabaseQueryMixin',

    # Embedding & vectors
    'EmbeddingService',
    'FAISSVectorDatabase',

    # Search
    'SemanticSearchMixin',
    'HybridSearchMixin',
    'KeywordSearchMixin',

    # Operations
    'MemoryStorageMixin',
    'MemoryMaintenanceMixin',
]


def __getattr__(name):
    """
    Provide backward compatibility for deprecated memory_system access

    This allows existing code using `from memory.memory_system import memory_system`
    to continue working while showing a deprecation warning.
    """
    if name == "memory_system":
        import warnings
        warnings.warn(
            "Direct import of memory_system is deprecated and will be removed "
            "in a future version. Use get_memory_system() instead for lazy "
            "initialization without import-time side effects.",
            DeprecationWarning,
            stacklevel=2
        )
        return get_memory_system()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
