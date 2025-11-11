"""
Core Adapters Package
核心适配器包

Adapters to bridge legacy implementations with new interfaces
桥接遗留实现与新接口的适配器

Exports:
- Memory system adapter
- Embedding service adapter
- Vector database adapter
- Agent adapters
"""

from .memory_system_adapter import MemorySystemAdapter
from .embedding_service_adapter import EmbeddingServiceAdapter
from .vector_database_adapter import VectorDatabaseAdapter
from .agent_adapter import AgentAdapter, BrainRegionAgentAdapter

__all__ = [
    'MemorySystemAdapter',
    'EmbeddingServiceAdapter',
    'VectorDatabaseAdapter',
    'AgentAdapter',
    'BrainRegionAgentAdapter',
]
