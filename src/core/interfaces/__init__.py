"""
Core Interfaces Package
核心接口包

Defines contracts for all pluggable components
定义所有可插拔组件的契约
"""

from .memory_interface import (
    Memory,
    IMemorySystem,
    IMemoryRetriever,
    IMemoryStorer,
    IEmbeddingService,
    IVectorDatabase
)
from .agent_interface import (
    AgentMessage,
    IAgent,
    IAgentActivator
)
from .message_bus_interface import (
    IMessageBus,
    IMessageHandler,
    MessageHandler
)
from .search_interface import (
    ISearchStrategy,
    IHybridSearch,
    ISemanticSearch,
    IKeywordSearch
)

__all__ = [
    # Memory interfaces
    'Memory',
    'IMemorySystem',
    'IMemoryRetriever',
    'IMemoryStorer',
    'IEmbeddingService',
    'IVectorDatabase',
    # Agent interfaces
    'AgentMessage',
    'IAgent',
    'IAgentActivator',
    # Message bus interfaces
    'IMessageBus',
    'IMessageHandler',
    'MessageHandler',
    # Search interfaces
    'ISearchStrategy',
    'IHybridSearch',
    'ISemanticSearch',
    'IKeywordSearch',
]
