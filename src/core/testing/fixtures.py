"""
Common Test Fixtures
通用测试装置

Reusable test setup using pytest fixtures
使用pytest装置的可重用测试设置
"""

import pytest
from typing import Dict, List
from ..container import Container
from ..config import BMAMConfig
from ..interfaces import IMemorySystem, IMessageBus, IAgent, IEmbeddingService, IVectorDatabase
from .mock_factories import (
    create_mock_memory_system,
    create_mock_message_bus,
    create_mock_agent,
    create_mock_embedding_service,
    create_mock_vector_database,
    MockMemorySystem,
    MockMessageBus,
    MockAgent,
    MockEmbeddingService,
    MockVectorDatabase
)
from .test_container import TestContainer


# Configuration Fixtures

@pytest.fixture
def test_config() -> BMAMConfig:
    """
    Test configuration fixture
    测试配置装置

    Returns optimized configuration for testing
    返回针对测试优化的配置
    """
    return BMAMConfig.for_testing()


@pytest.fixture
def production_config() -> BMAMConfig:
    """
    Production configuration fixture
    生产配置装置

    Returns configuration from environment
    从环境返回配置
    """
    return BMAMConfig.from_env()


# Mock Component Fixtures

@pytest.fixture
def mock_memory_system() -> MockMemorySystem:
    """
    Mock memory system fixture
    模拟记忆系统装置

    Provides a fresh mock memory system for each test
    为每个测试提供一个新的模拟记忆系统
    """
    return create_mock_memory_system()


@pytest.fixture
def mock_message_bus() -> MockMessageBus:
    """
    Mock message bus fixture
    模拟消息总线装置

    Provides a fresh mock message bus for each test
    为每个测试提供一个新的模拟消息总线
    """
    return create_mock_message_bus()


@pytest.fixture
def mock_agent() -> MockAgent:
    """
    Single mock agent fixture
    单个模拟智能体装置

    Provides a fresh mock agent for each test
    为每个测试提供一个新的模拟智能体
    """
    return create_mock_agent()


@pytest.fixture
def mock_agents() -> Dict[str, IAgent]:
    """
    Dictionary of mock agents fixture
    模拟智能体字典装置

    Provides multiple mock agents for testing
    提供多个模拟智能体用于测试
    """
    return {
        'hippocampus': create_mock_agent('hippocampus', 'hippocampus'),
        'temporal_lobe': create_mock_agent('temporal_lobe', 'temporal_lobe'),
        'prefrontal': create_mock_agent('prefrontal', 'prefrontal_cortex'),
        'wernicke': create_mock_agent('wernicke', 'wernicke_area'),
        'broca': create_mock_agent('broca', 'broca_area')
    }


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    """
    Mock embedding service fixture
    模拟嵌入服务装置

    Provides a fresh mock embedding service for each test
    为每个测试提供一个新的模拟嵌入服务
    """
    return create_mock_embedding_service()


@pytest.fixture
def mock_vector_db() -> MockVectorDatabase:
    """
    Mock vector database fixture
    模拟向量数据库装置

    Provides a fresh mock vector database for each test
    为每个测试提供一个新的模拟向量数据库
    """
    return create_mock_vector_database()


# Container Fixtures

@pytest.fixture
def test_container() -> TestContainer:
    """
    Test DI container fixture
    测试DI容器装置

    Provides a pre-configured container with mocks
    提供预配置的包含模拟对象的容器
    """
    container = TestContainer()
    yield container
    container.reset()


@pytest.fixture
def test_container_with_agents() -> TestContainer:
    """
    Test container with registered agents
    带有已注册智能体的测试容器

    Provides a container with mock agents already registered
    提供已注册模拟智能体的容器
    """
    container = TestContainer()
    container.register_agents([
        'hippocampus',
        'temporal_lobe',
        'prefrontal',
        'wernicke',
        'broca'
    ])
    yield container
    container.reset()


@pytest.fixture
def basic_container(test_config) -> Container:
    """
    Basic DI container fixture
    基础DI容器装置

    Provides an empty container with just config registered
    提供仅注册配置的空容器
    """
    container = Container()
    container.register_instance(BMAMConfig, test_config)
    return container


# Scoped Fixtures (for integration tests)

@pytest.fixture(scope="module")
def module_test_container() -> TestContainer:
    """
    Module-scoped test container
    模块作用域的测试容器

    Shared across all tests in a module
    在模块中的所有测试之间共享
    """
    container = TestContainer()
    yield container
    container.reset()


@pytest.fixture(scope="class")
def class_test_container() -> TestContainer:
    """
    Class-scoped test container
    类作用域的测试容器

    Shared across all tests in a class
    在类中的所有测试之间共享
    """
    container = TestContainer()
    yield container
    container.reset()


# Helper Fixtures

@pytest.fixture
def sample_memories() -> List[Dict[str, any]]:
    """
    Sample memory data fixture
    示例记忆数据装置

    Provides test memory data
    提供测试记忆数据
    """
    return [
        {
            'content': 'Paris is the capital of France',
            'metadata': {'type': 'fact', 'subject': 'geography'},
            'importance': 0.8
        },
        {
            'content': 'Python is a programming language',
            'metadata': {'type': 'fact', 'subject': 'technology'},
            'importance': 0.7
        },
        {
            'content': 'Machine learning is a subset of AI',
            'metadata': {'type': 'fact', 'subject': 'technology'},
            'importance': 0.9
        }
    ]


@pytest.fixture
async def populated_memory_system(mock_memory_system, sample_memories):
    """
    Pre-populated mock memory system
    预填充的模拟记忆系统

    Memory system with sample data already stored
    已存储示例数据的记忆系统
    """
    for mem in sample_memories:
        await mock_memory_system.store_memory(
            mem['content'],
            mem.get('metadata'),
            mem.get('importance', 0.5)
        )
    # Reset call tracking after setup
    mock_memory_system.store_calls.clear()
    return mock_memory_system


# Async Fixtures

@pytest.fixture
async def async_mock_memory_system():
    """
    Async mock memory system fixture
    异步模拟记忆系统装置

    For async test functions
    用于异步测试函数
    """
    memory_system = create_mock_memory_system()
    yield memory_system
    memory_system.reset()


# Parametrized Fixtures

@pytest.fixture(params=[1, 5, 10])
def k_values(request):
    """
    Parametrized k values for retrieval testing
    用于检索测试的参数化k值

    Tests will run with k=1, k=5, k=10
    测试将使用k=1, k=5, k=10运行
    """
    return request.param


@pytest.fixture(params=['semantic', 'hybrid', 'keyword'])
def search_types(request):
    """
    Parametrized search types
    参数化搜索类型

    Tests will run with different search types
    测试将使用不同的搜索类型运行
    """
    return request.param


# Cleanup Fixtures

@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Auto-reset singletons between tests
    在测试之间自动重置单例

    Ensures clean state between tests
    确保测试之间的干净状态
    """
    yield
    # Reset any global state here if needed
    from ..config import reset_config
    from ..container import reset_container

    reset_config()
    reset_container()
