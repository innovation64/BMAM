"""
Testing DI Container
测试依赖注入容器

Pre-configured container with mocks for testing
预配置的包含模拟对象的测试容器
"""

from typing import Dict, Any, Optional
from ..container import Container, Lifecycle
from ..config import BMAMConfig
from ..interfaces import (
    IMemorySystem,
    IMessageBus,
    IAgent,
    IEmbeddingService,
    IVectorDatabase
)
from .mock_factories import (
    create_mock_memory_system,
    create_mock_message_bus,
    create_mock_agent,
    create_mock_embedding_service,
    create_mock_vector_database
)


class TestContainer:
    """
    Testing DI Container
    测试依赖注入容器

    Provides a pre-configured container with mocks for testing
    提供预配置的包含模拟对象的测试容器

    Features:
    - Pre-registered mock implementations
    - Easy registration of test doubles
    - Reset functionality between tests
    - Access to all registered mocks for assertions

    Example:
        test_container = TestContainer()
        coordinator = test_container.build_coordinator()

        # Access mocks for verification
        assert len(test_container.memory_system.store_calls) == 1
    """

    def __init__(self):
        self._container = Container()
        self._mocks: Dict[str, Any] = {}
        self._setup_default_mocks()

    def _setup_default_mocks(self):
        """Setup default mock registrations"""
        # Configuration
        config = BMAMConfig.for_testing()
        self._container.register_instance(BMAMConfig, config)

        # Memory system
        memory_system = create_mock_memory_system()
        self._mocks['memory_system'] = memory_system
        self._container.register_instance(IMemorySystem, memory_system)

        # Message bus
        message_bus = create_mock_message_bus()
        self._mocks['message_bus'] = message_bus
        self._container.register_instance(IMessageBus, message_bus)

        # Embedding service
        embedding_service = create_mock_embedding_service()
        self._mocks['embedding_service'] = embedding_service
        self._container.register_instance(IEmbeddingService, embedding_service)

        # Vector database
        vector_db = create_mock_vector_database()
        self._mocks['vector_db'] = vector_db
        self._container.register_instance(IVectorDatabase, vector_db)

        # Empty agents dict (can be populated by tests)
        self._mocks['agents'] = {}
        self._container.register_instance(Dict[str, IAgent], self._mocks['agents'])

    @property
    def container(self) -> Container:
        """Access underlying DI container"""
        return self._container

    @property
    def memory_system(self):
        """Access mock memory system"""
        return self._mocks['memory_system']

    @property
    def message_bus(self):
        """Access mock message bus"""
        return self._mocks['message_bus']

    @property
    def embedding_service(self):
        """Access mock embedding service"""
        return self._mocks['embedding_service']

    @property
    def vector_db(self):
        """Access mock vector database"""
        return self._mocks['vector_db']

    @property
    def agents(self) -> Dict[str, IAgent]:
        """Access registered agents"""
        return self._mocks['agents']

    def register_agent(self, agent_id: str, agent: Optional[IAgent] = None):
        """
        Register a test agent
        注册测试智能体

        Args:
            agent_id: Agent identifier
            agent: Agent instance (creates mock if None)
        """
        if agent is None:
            agent = create_mock_agent(agent_id=agent_id)

        self._mocks['agents'][agent_id] = agent
        return agent

    def register_agents(self, agent_ids: list):
        """
        Register multiple mock agents
        注册多个模拟智能体

        Args:
            agent_ids: List of agent identifiers
        """
        for agent_id in agent_ids:
            self.register_agent(agent_id)

    def register(self, interface: type, implementation: type, lifecycle: Lifecycle = Lifecycle.SINGLETON):
        """
        Register a custom implementation
        注册自定义实现

        Args:
            interface: Interface type
            implementation: Implementation class
            lifecycle: Lifecycle strategy
        """
        self._container.register(interface, implementation, lifecycle)

    def register_instance(self, interface: type, instance: Any):
        """
        Register a pre-created instance
        注册预创建的实例

        Args:
            interface: Interface type
            instance: Pre-created instance
        """
        self._container.register_instance(interface, instance)
        # Also track in mocks for easy access
        self._mocks[interface.__name__] = instance

    def resolve(self, interface: type):
        """
        Resolve an interface from the container
        从容器解析接口

        Args:
            interface: Interface to resolve

        Returns:
            Registered implementation
        """
        return self._container.resolve(interface)

    def reset(self):
        """
        Reset all mocks and clear container
        重置所有模拟对象并清空容器

        Use this between tests to ensure clean state
        在测试之间使用此方法以确保干净状态
        """
        # Reset all tracked mocks
        for mock in self._mocks.values():
            if hasattr(mock, 'reset'):
                mock.reset()

        # Clear agents
        self._mocks['agents'].clear()

        # Clear container and re-setup
        self._container.clear()
        self._setup_default_mocks()

    def get_config(self) -> BMAMConfig:
        """Get test configuration"""
        return self._container.resolve(BMAMConfig)

    def verify_no_calls(self):
        """
        Verify that no mocks were called
        验证没有调用任何模拟对象

        Useful for negative tests
        对负面测试有用
        """
        assert len(self.memory_system.store_calls) == 0, "Memory system had unexpected store calls"
        assert len(self.memory_system.retrieve_calls) == 0, "Memory system had unexpected retrieve calls"
        assert len(self.message_bus.published_messages) == 0, "Message bus had unexpected publishes"

    def verify_memory_stored(self, expected_count: int = 1):
        """Verify memories were stored"""
        actual = len(self.memory_system.store_calls)
        assert actual == expected_count, f"Expected {expected_count} store calls, got {actual}"

    def verify_messages_published(self, expected_count: int = 1):
        """Verify messages were published"""
        actual = len(self.message_bus.published_messages)
        assert actual == expected_count, f"Expected {expected_count} published messages, got {actual}"

    def get_published_messages(self, message_type: Optional[str] = None):
        """
        Get published messages, optionally filtered by type
        获取已发布的消息，可选按类型过滤

        Args:
            message_type: Filter by message type (None for all)

        Returns:
            List of published messages
        """
        if message_type is None:
            return self.message_bus.published_messages

        return [
            msg for msg in self.message_bus.published_messages
            if msg.message_type == message_type
        ]

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context exit"""
        self.reset()
