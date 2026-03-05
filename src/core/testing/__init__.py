"""
Core Testing Package
核心测试包

Testing infrastructure and utilities
测试基础设施和工具

Exports:
- Mock factories for all interfaces
- Test container for DI testing
- Pytest fixtures
"""

from .mock_factories import (
    MockMemorySystem,
    MockAgent,
    MockMessageBus,
    MockEmbeddingService,
    MockVectorDatabase,
    create_mock_memory_system,
    create_mock_agent,
    create_mock_message_bus,
    create_mock_embedding_service,
    create_mock_vector_database,
    create_mock_container
)

from .test_container import TestContainer

# Fixtures are imported in test files via:
# from src.core.testing.fixtures import *

__all__ = [
    # Mock classes
    'MockMemorySystem',
    'MockAgent',
    'MockMessageBus',
    'MockEmbeddingService',
    'MockVectorDatabase',
    # Factory functions
    'create_mock_memory_system',
    'create_mock_agent',
    'create_mock_message_bus',
    'create_mock_embedding_service',
    'create_mock_vector_database',
    'create_mock_container',
    # Test utilities
    'TestContainer',
]
