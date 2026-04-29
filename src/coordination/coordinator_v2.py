"""
Brain Inspired Coordinator V2 with Dependency Injection
大脑启发式协调器V2：依赖注入版本

Eliminates the massive constructor anti-pattern by accepting
pre-configured components through dependency injection.
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio

from src.core.container import Container as DependencyContainer
from src.core.config import BMAMConfig
from src.core.interfaces.memory_interface import IMemorySystem
from src.core.interfaces.agent_interface import IAgent
from src.core.interfaces.message_bus_interface import IMessageBus

logger = logging.getLogger(__name__)


class BrainInspiredCoordinatorV2:
    """
    Brain Inspired Coordinator V2 with Dependency Injection
    大脑启发式协调器V2（依赖注入版本）

    Key improvements over V1:
    - No 200-line constructor
    - All dependencies injected via constructor
    - No initialization in constructor (lazy initialization)
    - Clean separation of construction and initialization
    - Fully testable with real or mock components

    Architecture:
        - Uses builder pattern for construction
        - Accepts pre-configured components
        - Lazy initialization on first use
        - Feature flags for optional functionality

    Example:
        >>> # Don't use constructor directly - use builder
        >>> from src.coordination.coordinator_builder import CoordinatorBuilder
        >>>
        >>> coordinator = (CoordinatorBuilder()
        ...     .with_memory()
        ...     .with_agents(['hippocampus', 'prefrontal'])
        ...     .enable_learning()
        ...     .build())
        >>>
        >>> result = await coordinator.process("query")
    """

    def __init__(
        self,
        container: DependencyContainer,
        config: BMAMConfig,
        components: Dict[str, Any],
        features: Dict[str, bool]
    ):
        """
        Initialize Coordinator V2 (NO SIDE EFFECTS)
        初始化协调器V2（无副作用）

        Args:
            container: DI container
            config: BMAM configuration
            components: Pre-configured components dict
            features: Feature flags dict

        Note:
            This constructor does NOT initialize any resources.
            All initialization is done lazily on first use.
            Use CoordinatorBuilder to create instances.
        """
        logger.debug("Creating BrainInspiredCoordinatorV2 (no side effects)...")

        self._container = container
        self._config = config
        self._components = components
        self._features = features

        # Extract core components
        self.memory_system: IMemorySystem = components['memory_system']
        self.agents: Dict[str, IAgent] = components['agents']
        self.message_bus: Optional[IMessageBus] = components.get('message_bus')

        # Lazy initialization flags
        self._initialized = False
        self._init_lock = asyncio.Lock()

        # Optional subsystems (initialized lazily if enabled)
        self._learning_system = None
        self._kg_integration = None
        self._routing_manager = None
        self._background_tasks = []

        logger.debug(f"BrainInspiredCoordinatorV2 created with {len(self.agents)} agents")

    async def initialize(self) -> None:
        """
        Initialize Coordinator (Explicit Initialization)
        初始化协调器（显式初始化）

        Must be called before using the coordinator.
        This is where expensive initialization happens.

        Example:
            >>> coordinator = create_coordinator()
            >>> await coordinator.initialize()
            >>> result = await coordinator.process("query")
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:  # Double-check pattern
                return

            logger.info("Initializing BrainInspiredCoordinatorV2...")

            # Initialize optional subsystems based on feature flags
            if self._features.get('learning'):
                await self._initialize_learning_system()

            if self._features.get('kg_integration'):
                await self._initialize_kg_integration()

            if self._features.get('routing'):
                await self._initialize_routing()

            if self._features.get('background_memory'):
                await self._start_background_memory_processing()

            self._initialized = True
            logger.info("BrainInspiredCoordinatorV2 initialized successfully")

    async def _initialize_learning_system(self) -> None:
        """Initialize learning system (if enabled)"""
        logger.debug("Initializing learning system...")
        try:
            from src.optimization.learning_optimizer import LearningOptimizer
            self._learning_system = LearningOptimizer(
                memory_system=self.memory_system
            )
            logger.info("Learning system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize learning system: {e}")

    async def _initialize_kg_integration(self) -> None:
        """Initialize knowledge graph integration (if enabled)"""
        logger.debug("Initializing KG integration...")
        try:
            from src.memory.knowledge_graph import KnowledgeGraph
            self._kg_integration = KnowledgeGraph()
            logger.info("KG integration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize KG integration: {e}")

    async def _initialize_routing(self) -> None:
        """Initialize intelligent routing (if enabled).

        RoutingManager's real signature requires memory_signal_config plus four
        callbacks owned by the V1 coordinator (_get_query_patterns,
        _phrases_in_text, _get_task_type_keywords, _get_kg_patterns). V2 has
        not yet ported those, so we accept them via the components dict if
        present and otherwise install no-op defaults.
        """
        logger.debug("Initializing routing manager...")
        try:
            from src.coordination.routing_manager import RoutingManager

            comp = self._components or {}
            mem_signal_cfg = comp.get('memory_signal_config', {}) or {}

            def _empty_list(*_args, **_kwargs):
                return []

            def _phrases_in_text(_phrases, _text):
                return False

            self._routing_manager = RoutingManager(
                memory_signal_config=mem_signal_cfg,
                pattern_getter_fn=comp.get('pattern_getter_fn', _empty_list),
                phrases_checker_fn=comp.get('phrases_checker_fn', _phrases_in_text),
                task_type_keywords_fn=comp.get('task_type_keywords_fn', _empty_list),
                kg_patterns_fn=comp.get('kg_patterns_fn', _empty_list),
            )
            logger.info("Routing manager initialized (V2 fallback callbacks)")
        except Exception as e:
            logger.error(f"Failed to initialize routing manager: {e}")

    async def _start_background_memory_processing(self) -> None:
        """Start background memory processing (if enabled)"""
        logger.debug("Starting background memory processing...")
        try:
            task = asyncio.create_task(self._background_memory_loop())
            self._background_tasks.append(task)
            logger.info("Background memory processing started")
        except Exception as e:
            logger.error(f"Failed to start background processing: {e}")

    async def _background_memory_loop(self) -> None:
        """Background loop for memory consolidation"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                logger.debug("Running background memory consolidation...")
                # Call consolidation here
                if hasattr(self.memory_system, 'compact_index'):
                    await self.memory_system.compact_index()
            except asyncio.CancelledError:
                logger.info("Background memory loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background memory loop: {e}")

    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process User Input
        处理用户输入

        Args:
            user_input: User query or command
            context: Optional context information

        Returns:
            Response string

        Example:
            >>> result = await coordinator.process("What is AI?")
        """
        await self.initialize()  # Ensure initialized

        logger.info(f"Processing input: {user_input[:50]}...")

        try:
            # Route to appropriate agents
            if self._routing_manager:
                agent_names = await self._routing_manager.route(user_input)
            else:
                # Default: use all agents
                agent_names = list(self.agents.keys())

            # Process with selected agents
            results = []
            for name in agent_names:
                agent = self.agents.get(name)
                if agent:
                    try:
                        result = await agent.process(user_input)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Agent '{name}' failed: {e}")

            # Combine results
            response = self._combine_results(results)

            # Optional: Update learning
            if self._learning_system:
                await self._learning_system.learn_from_interaction(
                    user_input, response
                )

            return response

        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return f"Error: {str(e)}"

    def _combine_results(self, results: List[Any]) -> str:
        """Combine agent results into final response"""
        if not results:
            return "No response generated"

        # Simple combination for now
        return str(results[0]) if results else "No response"

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get System Status
        获取系统状态

        Returns:
            Dictionary with system status
        """
        return {
            'initialized': self._initialized,
            'agents': list(self.agents.keys()),
            'features': self._features,
            'memory_stats': self.memory_system.get_system_stats() if self._initialized else {},
        }

    async def stop_system(self) -> None:
        """
        Stop Coordinator and Cleanup
        停止协调器并清理

        Cancels background tasks and closes resources.
        """
        logger.info("Stopping BrainInspiredCoordinatorV2...")

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._initialized = False
        logger.info("BrainInspiredCoordinatorV2 stopped")

    def __repr__(self) -> str:
        """String representation"""
        status = "initialized" if self._initialized else "not initialized"
        return f"BrainInspiredCoordinatorV2({status}, {len(self.agents)} agents)"
