"""
Brain-Inspired 12-Agent Coordinator System (REFACTORED)
12智能体协调器：实现真正的并行处理和智能体通信

REFACTORING SUMMARY:
- Original: 7908 lines, 146 methods (God Class anti-pattern)
- Refactored: ~500 lines, delegates to 7 specialized modules
- Maintains 100% backward compatibility with existing code
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..utils.config import get_logger, get_settings
from ..utils.memory_signal_config import load_memory_signal_config, DEFAULT_MEMORY_SIGNAL_CONFIG
from ..utils.knowledge_graph_builder import KnowledgeGraphBuilder
from ..utils.pattern_config import pattern_config
from ..utils.flexible_date_parser import FlexibleDateParser
from ..utils.i18n_config import get_config as get_i18n_config

from .clean_agent_system import (
    BrainRegion, AgentMessage,
    ShortTermMemoryAgent, LongTermMemoryAgent, MemoryRetrievalAgent,
    ConsolidationAgent, MemoryDistortionAgent, ReflectionAgent,
    ForgettingAgent, StressResponseAgent, PersonalityAgent, PersonaMemoryAgent,
    ConversationAgent, ExecutiveControlAgent,
    PerceptionEncodingAgent, ActionExecutionAgent
)

from ..agents.environment import EnvironmentAgent
from ..agents.core.reasoning_validator import ReasoningValidatorAgent
from ..memory.memory_system import memory_system
from ..agents.agent_buffer_system import agent_buffer_system
# Removed: NeuralPlasticityEngine (Hebbian learning - no longer used)

from ..agents.brain_regions import (
    HippocampusAgent,
    TemporalLobeAgent,
    PrefrontalAgent,
    AmygdalaAgent,
    BasalGangliaAgent
)
from ..agents.brain_regions.temporal_lobe_agent import MemoryType

from ..optimization import (
    get_capacity_manager,
    get_query_cache,
    get_fast_path_detector,
    get_context_limiter
)
from .kg_merge_config import get_default_config as get_kg_merge_config

# Import refactored modules
from .message_bus import MessageBusManager, LearningLogger
from .agent_lifecycle import AgentLifecycleManager
from .routing_manager import RoutingManager
from .learning_manager import LearningManager
from .kg_merge_handler import KGMergeHandler
from .memory_coordinator import MemoryCoordinator
from .metrics_collector import MetricsCollector

logger = get_logger(__name__)


class _LegacyMemoryManagerAdapter:
    """Compatibility layer exposing legacy memory_manager interface."""

    def __init__(self, coordinator: "BrainInspiredCoordinator", memory_system_ref):
        self._coordinator = coordinator
        self._memory_system = memory_system_ref

    async def retrieve_memories(self, query: str, k: int = 5, **kwargs):
        return await self._memory_system.search_memories(query, k=k, **kwargs)

    async def store_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None, **kwargs):
        return await self._memory_system.store_memory(
            content,
            metadata=metadata or {},
            **kwargs
        )

    async def consolidate_memories(self):
        return await self._coordinator.memory_coordinator.trigger_consolidation(
            strategy='batch',
            batch_size=50
        )


@dataclass
class ProcessingResult:
    """Result from brain-inspired processing"""
    response: str
    routing_decision: Dict[str, Any]
    agents_involved: List[str]
    memories_retrieved: List[Dict[str, Any]]
    memory_stored: bool
    processing_time: float
    agent_logs: Dict[str, List[Dict]]
    insights: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    activation_trace: Optional[List[Dict[str, Any]]] = None
    memories_used: Optional[List[str]] = None


class BrainInspiredCoordinator:
    """
    12-Agent Brain-Inspired Coordinator System (REFACTORED)

    Delegates responsibilities to specialized modules:
    - MessageBusManager: Message queue and background tasks
    - AgentLifecycleManager: Agent activation and lifecycle
    - RoutingManager: Intelligent routing and query analysis
    - LearningManager: Continuous learning and plasticity
    - KGMergeHandler: Knowledge graph operations
    - MemoryCoordinator: Memory storage, retrieval, consolidation
    - MetricsCollector: Statistics and performance monitoring
    """

    def __init__(self):

        # Core settings and configuration
        self.settings = get_settings()
        self.memory_signal_config = load_memory_signal_config()
        self.default_language = os.getenv('BMAM_DEFAULT_LANGUAGE', 'en').lower()
        self.pattern_config = pattern_config
        self.i18n_config = get_i18n_config()
        self.date_parser = FlexibleDateParser()
        self.kg_merge_config = get_kg_merge_config()

        # Core memory system reference
        self.memory_system = memory_system
        self.memory_manager = _LegacyMemoryManagerAdapter(self, memory_system)

        # Initialize metrics collector first (needed by other modules)
        self.metrics_collector = MetricsCollector()
        self.processing_stats = self.metrics_collector.processing_stats  # Backward compatibility

        # Initialize message bus
        self.message_bus_manager = MessageBusManager()
        self.message_bus = self.message_bus_manager.message_bus  # Backward compatibility
        self.agent_tasks = self.message_bus_manager.agent_tasks  # Backward compatibility
        self.is_running = False

        # Persistent learning log
        self.learning_logger = LearningLogger(Path('data/learning_log.jsonl'))

        # Initialize all agents
        logger.info("🔧 [1/10] Initializing agents...")
        self._initialize_agents()
        logger.info("✅ [1/10] Agents initialized")

        # Removed: Neural Plasticity Engine (Hebbian learning - no longer used)
        # Previously: self.plasticity_engine = NeuralPlasticityEngine(agent_names)
        self.plasticity_engine = None  # Placeholder for compatibility

        # Initialize agent lifecycle manager
        logger.info("🔧 [2/10] Initializing AgentLifecycleManager...")
        self.agent_lifecycle_manager = AgentLifecycleManager(
            agents=self.agents,
            processing_stats=self.processing_stats,
            pattern_getter_fn=self._get_query_patterns,
            phrases_checker_fn=self._phrases_in_text
        )
        logger.info("✅ [2/10] AgentLifecycleManager initialized")

        # Initialize routing manager
        logger.info("🔧 [3/10] Initializing RoutingManager...")
        self.routing_manager = RoutingManager(
            memory_signal_config=self.memory_signal_config,
            pattern_getter_fn=self._get_query_patterns,
            phrases_checker_fn=self._phrases_in_text,
            task_type_keywords_fn=self._get_task_type_keywords,
            kg_patterns_fn=self._get_kg_patterns
        )
        logger.info("✅ [3/10] RoutingManager initialized")

        # Initialize KG merge handler
        logger.info("🔧 [4/10] Initializing KGMergeHandler...")
        self.kg_handler = KGMergeHandler(
            kg_patterns_fn=self._get_kg_patterns,
            phrases_checker_fn=self._phrases_in_text
        )
        logger.info("✅ [4/10] KGMergeHandler initialized")

        # Initialize memory coordinator
        logger.info("🔧 [5/10] Initializing MemoryCoordinator...")
        self.memory_coordinator = MemoryCoordinator(
            hippocampus=self.hippocampus,
            temporal_lobe=self.temporal_lobe,
            consolidation_agent=self.consolidation,
            forgetting_agent=self.forgetting,
            agent_lifecycle_manager=self.agent_lifecycle_manager,
            memory_system=self.memory_system  # 🔥 CRITICAL FIX: Pass MemorySystem reference
        )
        logger.info("✅ [5/10] MemoryCoordinator initialized")

        # Initialize Memory Reasoning Chain Engine (Brain-inspired cross-storage reasoning)
        # MUST come after MemoryCoordinator
        logger.info("🔧 [5.5/10] Initializing Memory Reasoning Chain Engine...")
        try:
            from ..reasoning.memory_reasoning_chain import MemoryReasoningChain
            from ..services.shared_openai_client import shared_client_manager

            self.memory_reasoning_chain = MemoryReasoningChain(
                hippocampus_agent=self.hippocampus,
                memory_system=self.memory_system,
                kg_builder=self.knowledge_graph_builder,
                temporal_lobe_agent=self.temporal_lobe,
                client_manager=shared_client_manager,
                memory_coordinator=self.memory_coordinator  # Use unified retrieval
            )
            logger.info("✅ [5.5/10] Memory Reasoning Chain Engine initialized")
        except Exception as e:
            logger.warning(f"⚠️ Memory Reasoning Chain not available: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")
            self.memory_reasoning_chain = None

        # Initialize background memory processes
        logger.info("🔧 [6/10] Initializing BackgroundMemoryProcesses...")
        try:
            from ..memory.background_memory_processes import BackgroundMemoryProcessManager, BackgroundProcessConfig

            auto_test_mode = os.getenv('BMAM_TEST_MODE', '').lower() in ('true', '1', 'yes')

            if auto_test_mode:
                background_config = BackgroundProcessConfig(
                    test_mode=True,
                    consolidation_interval_seconds=15,
                    forgetting_interval_seconds=60,
                    reconsolidation_interval_seconds=30,
                    enabled=False,
                    run_on_startup=False
                )
            else:
                background_config = BackgroundProcessConfig(
                    test_mode=False,
                    consolidation_interval_seconds=3600,
                    forgetting_interval_seconds=7200,
                    reconsolidation_interval_seconds=1800,
                    enabled=True,
                    run_on_startup=False
                )

            self.background_processes = BackgroundMemoryProcessManager(self, background_config)
            logger.info("✅ [6/10] BackgroundMemoryProcesses initialized")
        except ImportError:
            logger.warning("⚠️ Background memory processes module not found")
            self.background_processes = None
            logger.info("✅ [6/10] BackgroundMemoryProcesses skipped (not found)")

        # Initialize learning manager
        logger.info("🔧 [7/10] Initializing Metacognition & LearningManager...")
        try:
            logger.debug("  [7.1] Importing metacognition modules...")
            from ..optimization.metacognition import (
                get_continuous_learner,
                get_conflict_detector
            )
            logger.debug("  [7.2] Calling get_continuous_learner()...")
            self.continuous_learner = get_continuous_learner()
            logger.debug("  [7.3] Calling get_conflict_detector()...")
            self.conflict_detector = get_conflict_detector()
            logger.debug("  [7.4] Metacognition modules obtained")
        except ImportError:
            logger.warning("⚠️ Metacognition modules not found")
            self.continuous_learner = None
            self.conflict_detector = None

        logger.debug("  [7.5] Creating LearningManager...")
        self.learning_manager = LearningManager(
            plasticity_engine=self.plasticity_engine,
            continuous_learner=self.continuous_learner,
            conflict_detector=self.conflict_detector,
            brain_network=getattr(self, 'brain_network', None)
        )
        logger.info("✅ [7/10] LearningManager initialized")

        # Initialize optimization modules
        logger.info("🔧 [8/10] Initializing Optimization modules...")
        self.capacity_manager = get_capacity_manager()
        self.query_cache = get_query_cache(embedding_service=memory_system.embedding_service)
        self.fast_path_detector = get_fast_path_detector()
        self.context_limiter = get_context_limiter()
        logger.info("✅ [8/10] Optimization modules initialized")

        # Initialize metacognition modules
        logger.info("🔧 [9/10] Initializing Additional Metacognition modules...")
        try:
            from ..optimization.metacognition import (
                get_preference_extractor,
                get_confidence_evaluator
            )
            self.preference_extractor = get_preference_extractor()
            self.confidence_evaluator = get_confidence_evaluator()
        except ImportError:
            logger.warning("⚠️ Additional metacognition modules not available")
            self.preference_extractor = None
            self.confidence_evaluator = None
        logger.info("✅ [9/10] Metacognition modules ready")

        # Initialize environment stimulus processor
        logger.info("🔧 [10/10] Initializing Environment stimulus processor...")
        try:
            from ..agents.environment.stimulus_processor import (
                get_stimulus_processor,
                get_contextual_integrator
            )
            self.stimulus_processor = get_stimulus_processor()
            self.contextual_integrator = get_contextual_integrator()
        except ImportError:
            logger.warning("⚠️ Environment stimulus processor not available")
            self.stimulus_processor = None
            self.contextual_integrator = None
        logger.info("✅ [10/10] Environment stimulus processor ready")

        logger.info("🎉 BrainInspiredCoordinator initialization COMPLETE!")


    def _resolve_language(
        self,
        context: Optional[Dict[str, Any]] = None,
        query_features: Optional[Dict[str, Any]] = None
    ) -> str:
        """Resolve active language from context or query features."""
        if query_features:
            lang = (query_features.get('language') or '').strip().lower()
            if lang:
                return lang
        if context:
            lang = (context.get('detected_language') or '').strip().lower()
            if lang:
                return lang
        return self.default_language

    def _get_query_patterns(
        self,
        key: str,
        language: Optional[str] = None
    ) -> List[str]:
        """Fetch query pattern list from configuration with graceful fallback."""
        lang = (language or self.default_language) or 'en'
        patterns = self.pattern_config.get_patterns('query_patterns.json', key, lang)
        if patterns:
            return patterns
        if lang != self.default_language:
            fallback = self.pattern_config.get_patterns('query_patterns.json', key, self.default_language)
            if fallback:
                return fallback
        return []

    def _get_task_type_keywords(self, task_type: str, language: Optional[str] = None) -> List[str]:
        """Retrieve task-type specific keywords from configuration."""
        lang = (language or self.default_language) or 'en'
        try:
            config = self.pattern_config.load('query_patterns.json')
        except Exception as err:
            logger.warning(f"Failed to load query_patterns.json: {err}")
            return []

        task_mappings = config.get('task_type_keywords', {})
        task_entry = task_mappings.get(task_type, {})
        if isinstance(task_entry, dict):
            keywords = task_entry.get(lang) or task_entry.get(self.default_language, [])
            return keywords
        return []

    def _get_kg_patterns(
        self,
        key: str,
        language: Optional[str] = None
    ) -> List[str]:
        """Fetch KG-related pattern list from configuration."""
        lang = (language or self.default_language) or 'en'
        patterns = self.pattern_config.get_patterns('kg_query_patterns.json', key, lang)
        if patterns:
            return patterns
        if lang != self.default_language:
            fallback = self.pattern_config.get_patterns('kg_query_patterns.json', key, self.default_language)
            return fallback or []
        return []

    def _phrases_in_text(self, phrases: List[str], text: str) -> bool:
        """Case-insensitive phrase containment helper."""
        lowered = text.lower()
        return any((phrase or '').lower() in lowered for phrase in phrases)

    async def initialize(self):
        """Public initializer kept for backwards compatibility."""
        if not self.is_running:
            await self.start_system()
        return self

    def _initialize_agents(self):
        """Initialize all 12 agents according to design document"""

        from ..memory.memory_system import memory_system
        db = memory_system.db_manager
        vec = memory_system.vector_db
        emb = memory_system.embedding_service


        embedding_service = self.memory_system.embedding_service if self.memory_system else None
        self.knowledge_graph_builder = KnowledgeGraphBuilder(llm_client=None)

        self.temporal_lobe = TemporalLobeAgent(
            capacity=70000,
            embedding_service=embedding_service,
            knowledge_graph_builder=self.knowledge_graph_builder
        )

        self.hippocampus = HippocampusAgent(
            capacity=20000,
            temporal_lobe_agent=self.temporal_lobe,
            embedding_service=embedding_service,
            kg_builder=self.knowledge_graph_builder,
            memory_system=self.memory_system  # 🔥 Pass MemorySystem for consolidation
        )

        self.amygdala = AmygdalaAgent(
            capacity=1000,
            hippocampus_agent=self.hippocampus,
            temporal_lobe_agent=self.temporal_lobe
        )

        self.prefrontal_storage = PrefrontalAgent(capacity=10, brain_coordinator=None)
        self.basal_ganglia = BasalGangliaAgent(capacity=500)


        # 8 Core Memory Processing Agents
        self.short_term_memory = ShortTermMemoryAgent()
        self.long_term_memory = LongTermMemoryAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.memory_retrieval = MemoryRetrievalAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.consolidation = ConsolidationAgent(db_manager=db)
        self.memory_distortion = MemoryDistortionAgent(db_manager=db)
        self.reflection = ReflectionAgent(db_manager=db, embedding_service=emb)
        self.forgetting = ForgettingAgent(db_manager=db)
        self.stress_response = StressResponseAgent(db_manager=db)

        self.reasoning_validator = ReasoningValidatorAgent(
            reflection_agent=self.reflection,
            consolidation_agent=self.consolidation
        )

        # 4 Auxiliary Functional Agents
        self.persona_memory = PersonaMemoryAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.personality = PersonalityAgent(persona_memory_agent=self.persona_memory)
        self.conversation = ConversationAgent()
        self.executive_control = ExecutiveControlAgent()
        self.perception_encoding = PerceptionEncodingAgent()
        self.action_execution = ActionExecutionAgent()

        self.environment = EnvironmentAgent(brain_coordinator=None)

        # Agent registry
        self.agents = {
            'hippocampus': self.hippocampus,
            'temporal_lobe': self.temporal_lobe,
            'prefrontal_storage': self.prefrontal_storage,
            'amygdala': self.amygdala,
            'basal_ganglia': self.basal_ganglia,
            'short_term_memory': self.short_term_memory,
            'long_term_memory': self.long_term_memory,
            'memory_retrieval': self.memory_retrieval,
            'consolidation': self.consolidation,
            'memory_distortion': self.memory_distortion,
            'reflection': self.reflection,
            'forgetting': self.forgetting,
            'stress_response': self.stress_response,
            'reasoning_validator': self.reasoning_validator,
            'persona_memory': self.persona_memory,
            'personality': self.personality,
            'conversation': self.conversation,
            'executive_control': self.executive_control,
            'perception_encoding': self.perception_encoding,
            'action_execution': self.action_execution,
            'environment': self.environment
        }

        # Initialize agent statistics
        for agent_id in self.agents:
            self.processing_stats['agent_activations'][agent_id] = 0

        # Set delayed references
        self.prefrontal_storage.brain_coordinator = self
        self.environment.brain_coordinator = self

        # BrainNetwork initialization
        self.use_brain_network = os.getenv('USE_BRAIN_NETWORK', 'true').lower() == 'true'

        if self.use_brain_network:
            from ..brain.brain_network import BrainNetwork
            self.brain_network = BrainNetwork(agents=self.agents)
        else:
            self.brain_network = None

        # ExternalMemorySystem
        self.use_external_memory = os.getenv('USE_EXTERNAL_MEMORY', 'false').lower() == 'true'

        if self.use_external_memory:
            from ..systems.external_memory_system import ExternalMemorySystem
            self.external_memory = ExternalMemorySystem(
                embedding_service=embedding_service,
                kg_builder=self.knowledge_graph_builder,
                search_api_key=os.getenv('SEARCH_API_KEY')
            )
        else:
            self.external_memory = None

    async def start_system(self):
        """Start the coordination system"""
        if self.is_running:
            return

        self.is_running = True

        # Start message bus
        await self.message_bus_manager.start()

        # Start background processes
        if self.background_processes and self.background_processes.config.enabled:
            await self.background_processes.start()

        # Start continuous learning loop
        await self.learning_manager.start_continuous_learning_loop()

    def configure_test_mode(self, enabled: bool = True):
        """Configure test mode with accelerated timing"""
        if hasattr(self, 'background_processes') and self.background_processes:
            if enabled:
                self.background_processes.config.test_mode = True
                self.background_processes.config.consolidation_interval_seconds = 30
                self.background_processes.config.forgetting_interval_seconds = 60
                self.background_processes.config.reconsolidation_interval_seconds = 45
            else:
                self.background_processes.config.test_mode = False
                self.background_processes.config.consolidation_interval_seconds = 3600
                self.background_processes.config.forgetting_interval_seconds = 7200
                self.background_processes.config.reconsolidation_interval_seconds = 1800

    async def stop_system(self):
        """Stop the coordination system"""
        self.is_running = False

        # Stop learning loop
        await self.learning_manager.stop_continuous_learning_loop()

        # Stop background processes
        if self.background_processes:
            await self.background_processes.stop()

        # Stop message bus
        await self.message_bus_manager.stop()

        # Plasticity engine removed (no longer needed)
        # Previously: await self.plasticity_engine.stop_plasticity_engine()


    async def shutdown(self):
        """Alias for stop_system"""
        await self.stop_system()

    # ============================================================================
    # Delegating Methods - Maintain backward compatibility
    # ============================================================================

    async def _activate_agent(self, agent_id: str, message: AgentMessage) -> Dict[str, Any]:
        """Delegate to AgentLifecycleManager"""
        return await self.agent_lifecycle_manager.activate_agent(agent_id, message)

    def _map_agent_name(self, agent_name: str) -> Optional[str]:
        """Delegate to AgentLifecycleManager"""
        return self.agent_lifecycle_manager.map_agent_name(agent_name)

    def _classify_task_type(self, user_input: str) -> str:
        """Delegate to AgentLifecycleManager"""
        return self.agent_lifecycle_manager.classify_task_type(
            user_input, self.default_language, self._get_task_type_keywords
        )

    async def trigger_consolidation(self, strategy: str = 'batch', batch_size: int = 50) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator"""
        return await self.memory_coordinator.trigger_consolidation(strategy, batch_size)

    async def consolidate_memories(self) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator"""
        return await self.memory_coordinator.consolidate_memories()

    async def trigger_forgetting(self, region: str) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator"""
        return await self.memory_coordinator.trigger_forgetting(region)

    async def store_memory_with_timestamp(
        self,
        content: str,
        timestamp: datetime,
        speaker: str = None,
        importance: float = 0.5
    ) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator"""
        return await self.memory_coordinator.store_memory_with_timestamp(
            content, timestamp, speaker, importance
        )

    async def smart_retrieve(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'auto',
        context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Delegate to MemoryCoordinator"""
        return await self.memory_coordinator.smart_retrieve(query, k, strategy, context)

    def get_system_status(self) -> Dict[str, Any]:
        """Delegate to MetricsCollector"""
        return self.metrics_collector.get_system_status(self.agents, self.is_running)

    async def run_continuous_learning_cycle(self) -> Dict[str, Any]:
        """Delegate to LearningManager"""
        return await self.learning_manager.run_continuous_learning_cycle(self.hippocampus)

    async def _select_optimal_retrieval_strategy(self, query: str, context: Dict[str, Any]) -> str:
        """Delegate to RoutingManager"""
        return await self.routing_manager.select_optimal_retrieval_strategy(query, context)

    async def _analyze_query_features(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to RoutingManager"""
        language = self._resolve_language(context)
        return await self.routing_manager.analyze_query_features(query, context, language)

    def _should_use_reasoning_chain(self, query: str, query_features: Dict[str, Any]) -> bool:
        """
        Determine if Memory Reasoning Chain should be used

        Use reasoning chain for:
        - Inference questions (What/Who/Why questions requiring reasoning)
        - Questions about entity characteristics/identity
        - Questions requiring temporal/causal reasoning
        - Complex multi-hop reasoning

        Args:
            query: User query
            query_features: Analyzed query features

        Returns:
            bool: True if reasoning chain should be used
        """
        query_lower = query.lower()

        # High-priority inference keywords that always trigger reasoning chain
        high_priority_keywords = [
            'identity', 'characteristic', 'likely', 'would pursue',
            'would be', 'seems', 'appears', 'suggests', 'indicates',
            'personality', 'nature', 'type of person'
        ]

        # Inference question patterns
        inference_patterns = [
            'what is', 'who is', 'why did', 'why would', 'what would',
            'what fields', 'what areas', 'what type'
        ]

        has_high_priority = any(kw in query_lower for kw in high_priority_keywords)
        has_inference_pattern = any(pattern in query_lower for pattern in inference_patterns)

        # Question words requiring reasoning (relaxed - no entity requirement)
        reasoning_questions = ['what', 'who', 'why']
        starts_with_reasoning = any(query_lower.startswith(q) for q in reasoning_questions)

        # Trigger reasoning chain if:
        # 1. Has high-priority inference keywords (e.g., "identity", "likely"), OR
        # 2. Has inference pattern (e.g., "what is"), OR
        # 3. Starts with reasoning question + has proper nouns (names in query)
        has_proper_nouns = any(word[0].isupper() for word in query.split() if len(word) > 1)

        should_use = (
            has_high_priority or
            has_inference_pattern or
            (starts_with_reasoning and has_proper_nouns)
        )

        return should_use

    # ============================================================================
    # Main Processing Pipeline (Simplified - delegates to modules)
    # ============================================================================

    async def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """
        Main processing pipeline - orchestrates all modules

        This is the primary entry point that coordinates all specialized modules.
        """
        start_time = datetime.now()

        if context is None:
            context = {}

        try:
            self.metrics_collector.record_request(success=False)  # Will update on success

            # 1. Query analysis via RoutingManager
            query_features = await self._analyze_query_features(user_input, context)

            # 2. Memory retrieval via MemoryCoordinator
            memories = await self.smart_retrieve(user_input, k=10, context=context)

            # 2.5. Enhanced reasoning chain retrieval (for complex inference questions)
            use_reasoning_chain = False
            reasoning_chain_result = None

            if self.memory_reasoning_chain and self._should_use_reasoning_chain(user_input, query_features):
                try:
                    logger.info(f"🧠 Using Memory Reasoning Chain for: '{user_input[:50]}...'")
                    reasoning_chain_result = await self.memory_reasoning_chain.answer_with_reasoning_chain(
                        question=user_input,
                        max_memories=20
                    )
                    use_reasoning_chain = True
                    logger.info(
                        f"✅ Reasoning chain: {reasoning_chain_result['memory_count']} memories, "
                        f"{reasoning_chain_result['causal_links_count']} links, "
                        f"confidence={reasoning_chain_result['confidence']:.2f}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Reasoning chain failed, falling back to standard retrieval: {e}")
                    use_reasoning_chain = False

            # 3. KG enhancement via KGMergeHandler (if needed)
            if self.kg_handler.should_trigger_kg_search(user_input, memories):
                kg_facts = await self.kg_handler.query_kg_for_facts(
                    user_input,
                    entities=query_features.get('entities', [])
                )
                memories = self.kg_handler.merge_kg_memories(memories, kg_facts)

            # 4. Generate response
            if use_reasoning_chain and reasoning_chain_result:
                # Use reasoning chain answer directly
                response = reasoning_chain_result['answer']
                logger.info("📝 Using reasoning chain answer")
            else:
                # Standard agent activation
                response_result = await self._activate_agent(
                    'conversation',
                    AgentMessage(
                        sender='coordinator',
                        receiver='conversation',
                        message_type='request',
                        content={
                            'action': 'generate_response',
                            'user_input': user_input,
                            'memories': memories,
                            'context': context
                        }
                    )
                )
                response = response_result.get('response', 'I understand.')

            # 5. Store memory if needed
            memory_stored = await self.memory_coordinator.store_memory_if_needed(
                user_input, response, context
            )

            processing_time = (datetime.now() - start_time).total_seconds()
            self.metrics_collector.record_request(success=True, processing_time=processing_time)

            return ProcessingResult(
                response=response,
                routing_decision=query_features,
                agents_involved=['conversation'],
                memories_retrieved=memories,
                memory_stored=memory_stored,
                processing_time=processing_time,
                agent_logs={},
                insights={},
                success=True
            )

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}", exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            self.metrics_collector.record_request(success=False, processing_time=processing_time)

            return ProcessingResult(
                response=f"Error: {str(e)}",
                routing_decision={},
                agents_involved=[],
                memories_retrieved=[],
                memory_stored=False,
                processing_time=processing_time,
                agent_logs={},
                insights={},
                success=False,
                error=str(e)
            )

    async def process_input(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Simplified processing interface - returns response string"""
        result = await self.process_user_input(user_input, context)
        return result.response


# Backward compatibility alias
BrainCoordinator = BrainInspiredCoordinator

