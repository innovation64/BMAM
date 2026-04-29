"""
Brain Coordinator Builder with Dependency Injection
大脑协调器构建器：依赖注入

Provides fluent API for building BrainInspiredCoordinator with all dependencies
properly injected, eliminating the massive constructor anti-pattern.
"""

from typing import List, Dict, Any, Optional, Callable
import logging

from src.core.container import Container as DependencyContainer, get_container
from src.core.config import get_config, BMAMConfig
from src.core.interfaces.memory_interface import IMemorySystem
from src.core.interfaces.agent_interface import IAgent
from src.core.interfaces.message_bus_interface import IMessageBus

logger = logging.getLogger(__name__)


class CoordinatorBuilder:
    """
    Fluent Builder for BrainInspiredCoordinator
    大脑协调器的流式构建器

    Eliminates the 200-line constructor anti-pattern by using
    builder pattern with dependency injection.

    Example:
        >>> from src.core.container import get_container
        >>> container = get_container()
        >>>
        >>> coordinator = (CoordinatorBuilder(container)
        ...     .with_memory()
        ...     .with_agents(['hippocampus', 'prefrontal'])
        ...     .with_message_bus()
        ...     .enable_learning()
        ...     .enable_kg_integration()
        ...     .build())
        >>>
        >>> result = await coordinator.process("query")
    """

    def __init__(
        self,
        container: Optional[DependencyContainer] = None,
        config: Optional[BMAMConfig] = None
    ):
        """
        Initialize Coordinator Builder
        初始化协调器构建器

        Args:
            container: DI container (uses global if None)
            config: BMAM configuration (uses global if None)
        """
        self._container = container or get_container()
        self._config = config or get_config()
        self._components: Dict[str, Any] = {}
        self._features: Dict[str, bool] = {
            'learning': False,
            'kg_integration': False,
            'background_memory': False,
            'routing': True  # Enabled by default
        }

        logger.debug("CoordinatorBuilder initialized")

    def with_memory(
        self,
        memory_system: Optional[IMemorySystem] = None
    ) -> 'CoordinatorBuilder':
        """
        Configure Memory System
        配置记忆系统

        Args:
            memory_system: Memory system instance (resolved from container if None)

        Returns:
            Self for chaining
        """
        if memory_system is None:
            # Register memory components if not already registered
            if not self._container.is_registered(IMemorySystem):
                from src.memory.memory_system.registration import register_memory_system_components
                register_memory_system_components(self._container)

            memory_system = self._container.resolve(IMemorySystem)

        self._components['memory_system'] = memory_system
        logger.debug("Memory system configured")
        return self

    def with_agents(
        self,
        agent_names: List[str],
        agent_factory: Optional[Callable[[str], IAgent]] = None
    ) -> 'CoordinatorBuilder':
        """
        Configure Agents
        配置智能体

        Args:
            agent_names: List of agent names to create
            agent_factory: Optional factory function to create agents

        Returns:
            Self for chaining
        """
        agents = {}

        for name in agent_names:
            if agent_factory:
                agent = agent_factory(name)
            else:
                # Use container to resolve or create agent
                agent_key = f"agent_{name}"
                if self._container.is_registered(agent_key):
                    agent = self._container.resolve(agent_key)
                else:
                    # Create agent using legacy method (for now)
                    agent = self._create_legacy_agent(name)

            agents[name] = agent
            logger.debug(f"Agent '{name}' configured")

        self._components['agents'] = agents
        return self

    def with_message_bus(
        self,
        message_bus: Optional[IMessageBus] = None
    ) -> 'CoordinatorBuilder':
        """
        Configure Message Bus
        配置消息总线

        Args:
            message_bus: Message bus instance (resolved from container if None)

        Returns:
            Self for chaining
        """
        if message_bus is None:
            if self._container.is_registered(IMessageBus):
                message_bus = self._container.resolve(IMessageBus)
            else:
                # Default to MessageBusManager. Note this class does not yet
                # implement IMessageBus (see message_bus.py:51 TODO); callers
                # that require the interface should register a real impl.
                from src.coordination.message_bus import MessageBusManager
                message_bus = MessageBusManager()

        self._components['message_bus'] = message_bus
        logger.debug("Message bus configured")
        return self

    def enable_learning(self, enabled: bool = True) -> 'CoordinatorBuilder':
        """
        Enable/Disable Learning System
        启用/禁用学习系统

        Args:
            enabled: Whether to enable learning

        Returns:
            Self for chaining
        """
        self._features['learning'] = enabled
        logger.debug(f"Learning {'enabled' if enabled else 'disabled'}")
        return self

    def enable_kg_integration(self, enabled: bool = True) -> 'CoordinatorBuilder':
        """
        Enable/Disable Knowledge Graph Integration
        启用/禁用知识图谱集成

        Args:
            enabled: Whether to enable KG integration

        Returns:
            Self for chaining
        """
        self._features['kg_integration'] = enabled
        logger.debug(f"KG integration {'enabled' if enabled else 'disabled'}")
        return self

    def enable_background_memory(self, enabled: bool = True) -> 'CoordinatorBuilder':
        """
        Enable/Disable Background Memory Processing
        启用/禁用后台记忆处理

        Args:
            enabled: Whether to enable background processing

        Returns:
            Self for chaining
        """
        self._features['background_memory'] = enabled
        logger.debug(f"Background memory {'enabled' if enabled else 'disabled'}")
        return self

    def enable_routing(self, enabled: bool = True) -> 'CoordinatorBuilder':
        """
        Enable/Disable Intelligent Routing
        启用/禁用智能路由

        Args:
            enabled: Whether to enable routing

        Returns:
            Self for chaining
        """
        self._features['routing'] = enabled
        logger.debug(f"Routing {'enabled' if enabled else 'disabled'}")
        return self

    def build(self) -> 'BrainInspiredCoordinatorV2':
        """
        Build BrainInspiredCoordinator Instance
        构建大脑协调器实例

        Returns:
            Configured BrainInspiredCoordinatorV2 instance

        Raises:
            ValueError: If required components are missing
        """
        logger.info("Building BrainInspiredCoordinator...")

        # Validate required components
        if 'memory_system' not in self._components:
            raise ValueError("Memory system is required. Call with_memory()")

        if 'agents' not in self._components or not self._components['agents']:
            raise ValueError("At least one agent is required. Call with_agents()")

        # Create coordinator
        from .coordinator_v2 import BrainInspiredCoordinatorV2

        coordinator = BrainInspiredCoordinatorV2(
            container=self._container,
            config=self._config,
            components=self._components,
            features=self._features
        )

        logger.info("BrainInspiredCoordinator built successfully")
        return coordinator

    def _create_legacy_agent(self, agent_name: str) -> Any:
        """
        Create agent using legacy method (temporary)
        使用遗留方法创建智能体（临时）

        This will be replaced with proper DI once all agents
        are refactored to use dependency injection.

        Args:
            agent_name: Name of agent to create

        Returns:
            Agent instance
        """
        logger.warning(f"Creating agent '{agent_name}' using legacy method")

        # Import legacy agent classes
        try:
            if agent_name == 'hippocampus':
                from src.agents.brain_regions.hippocampus_agent import HippocampusAgent
                return HippocampusAgent(memory_system=self._components.get('memory_system'))

            elif agent_name == 'prefrontal':
                from src.agents.brain_regions.prefrontal_cortex_agent import PrefrontalCortexAgent
                return PrefrontalCortexAgent()

            elif agent_name == 'amygdala':
                from src.agents.brain_regions.amygdala_agent import AmygdalaAgent
                return AmygdalaAgent()

            elif agent_name == 'basal_ganglia':
                from src.agents.brain_regions.basal_ganglia_agent import BasalGangliaAgent
                return BasalGangliaAgent()

            elif agent_name == 'cerebellum':
                from src.agents.brain_regions.cerebellum_agent import CerebellumAgent
                return CerebellumAgent()

            else:
                raise ValueError(f"Unknown agent: {agent_name}")

        except ImportError as e:
            logger.error(f"Failed to import agent '{agent_name}': {e}")
            raise


# Convenience function for quick coordinator creation
def create_coordinator(
    agent_names: Optional[List[str]] = None,
    enable_learning: bool = False,
    enable_kg: bool = False,
    container: Optional[DependencyContainer] = None,
    config: Optional[BMAMConfig] = None
) -> 'BrainInspiredCoordinatorV2':
    """
    Quick Create Coordinator with Default Settings
    快速创建默认配置的协调器

    Convenience function that uses builder internally.

    Args:
        agent_names: List of agents to create (default: ['hippocampus', 'prefrontal'])
        enable_learning: Whether to enable learning
        enable_kg: Whether to enable KG integration
        container: DI container (uses global if None)
        config: BMAM configuration (uses global if None)

    Returns:
        Configured coordinator instance

    Example:
        >>> coordinator = create_coordinator(
        ...     agent_names=['hippocampus', 'prefrontal'],
        ...     enable_learning=True
        ... )
    """
    agent_names = agent_names or ['hippocampus', 'prefrontal']

    builder = CoordinatorBuilder(container, config)
    builder.with_memory().with_agents(agent_names).with_message_bus()

    if enable_learning:
        builder.enable_learning()

    if enable_kg:
        builder.enable_kg_integration()

    return builder.build()
