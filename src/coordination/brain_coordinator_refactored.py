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
# Removed: agent_buffer_system (early design flaw - removed 2025-11-12)
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
                # 混合触发模式: 后台定时 + AdaptiveShaping事件触发
                # 后台提供兜底机制，AdaptiveShaping提供即时响应
                background_config = BackgroundProcessConfig(
                    test_mode=False,
                    consolidation_interval_seconds=1800,  # 30分钟兜底巩固
                    forgetting_interval_seconds=3600,     # 1小时遗忘检查
                    reconsolidation_interval_seconds=900, # 15分钟重巩固
                    enabled=True,  # ✅ 启用后台定时触发（兜底机制）
                    run_on_startup=True,  # ✅ 启动时立即开始
                    # 降低巩固过滤阈值，让新记忆也能被巩固
                    min_hit_count_for_consolidation=1,    # 从3降到1（访问1次就可以）
                    min_confidence_for_consolidation=0.3,  # 从0.6降到0.3
                    min_coverage_for_consolidation=0.0     # 从0.5降到0.0（不过滤coverage）
                )

            self.background_processes = BackgroundMemoryProcessManager(self, background_config)

            # Initialize adaptive memory shaping manager
            from ..memory.adaptive_memory_shaping import AdaptiveMemoryShapingManager
            self.adaptive_shaping = AdaptiveMemoryShapingManager(self)

            logger.info("✅ [6/10] BackgroundMemoryProcesses + AdaptiveShaping initialized")
        except ImportError as e:
            logger.warning(f"⚠️ Background memory processes module not found: {e}")
            self.background_processes = None
            self.adaptive_shaping = None
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

        # 🔥 FIX: 创建统一的知识图谱实例，供所有脑区共享
        from ..memory.knowledge_graph import LightweightKnowledgeGraph
        self.unified_kg = LightweightKnowledgeGraph()

        # 🔥 FIX: 将统一KG实例传给KnowledgeGraphBuilder
        self.knowledge_graph_builder = KnowledgeGraphBuilder(
            llm_client=None,
            kg_instance=self.unified_kg
        )

        self.temporal_lobe = TemporalLobeAgent(
            capacity=70000,
            embedding_service=embedding_service,
            knowledge_graph_builder=self.knowledge_graph_builder,
            unified_kg=self.unified_kg  # 🔥 FIX: 传递统一KG实例
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
        self.prefrontal_agent = self.prefrontal_storage  # Alias for functional brain regions test
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

    # ============================================================================
    # Memory Archive Management (BMA Format)
    # ============================================================================

    def export_memory_archive(
        self,
        archive_name: str,
        output_dir: Path = Path("archives/"),
        description: str = "",
        tags: Optional[List[str]] = None,
        include_faiss: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export current memory state to BMA (BMAM Memory Archive) format.

        Creates a standardized, portable memory archive that can be:
        - Loaded into any BMAM instance
        - Shared across different environments
        - Used for testing and benchmarking
        - Version controlled and backed up

        Args:
            archive_name: Name for the archive (will create {name}.bma directory)
            output_dir: Directory where archive will be created (default: archives/)
            description: Human-readable description of memory contents
            tags: List of tags for categorization (e.g., ["baseline", "test", "locomo"])
            include_faiss: Whether to include FAISS vector index (default: True)
            metadata: Additional custom metadata to include in manifest

        Returns:
            Dict with export results:
            {
                'success': bool,
                'archive_path': Path,
                'statistics': Dict,
                'size_bytes': int,
                'files_created': List[str]
            }

        Example:
            result = coordinator.export_memory_archive(
                archive_name="memory_baseline",
                description="Memory snapshot after training",
                tags=["baseline", "test"],
                include_faiss=True
            )
        """
        try:
            from ..memory.memory_archive import MemoryArchive

            # Get current memory database path from environment or use default
            import os
            database_url = os.getenv('DATABASE_URL', 'data/brain_memory.db')
            # Remove sqlite:/// prefix if present
            if database_url.startswith('sqlite:///'):
                database_url = database_url.replace('sqlite:///', '')

            db_path = Path(database_url)
            if not db_path.exists():
                return {
                    'success': False,
                    'error': f'Memory database not found: {db_path}',
                    'archive_path': None
                }

            # Get FAISS index path if requested
            faiss_path = None
            if include_faiss:
                faiss_path = Path("data/faiss_index")
                if not faiss_path.exists():
                    logger.warning(f"⚠️  FAISS index not found at {faiss_path}, skipping vector index")
                    faiss_path = None

            # Create archive v2.0.0 with multi-region support
            logger.info(f"📦 Exporting multi-region memory archive: {archive_name}")
            archive = MemoryArchive.create_from_coordinator(
                name=archive_name,
                coordinator=self,
                output_dir=output_dir,
                description=description,
                tags=tags,
                metadata=metadata
            )

            # Get archive info
            info = archive.get_info()

            result = {
                'success': True,
                'archive_path': archive.archive_path,
                'statistics': info['statistics'],
                'info': info
            }

            # Add format-specific fields
            if 'total_size_bytes' in info:
                result['size_bytes'] = info['total_size_bytes']
            if 'files' in info:
                result['files_created'] = info['files']
            if 'brain_regions' in info:
                result['brain_regions'] = info['brain_regions']
                result['total_regions'] = info.get('total_regions', len(info['brain_regions']))

            return result

        except Exception as e:
            logger.error(f"❌ Failed to export memory archive: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'archive_path': None
            }

    def load_memory_archive(
        self,
        archive_path: Path,
        target_dir: Path = Path("data/"),
        validate: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Load memory archive in BMA format to current instance.

        Replaces current memory state with archived memories. This is useful for:
        - Restoring from snapshots
        - Loading test memories
        - Switching between different memory contexts
        - Testing with baseline memories

        WARNING: This will replace current memory database and FAISS index.
                 Make sure to backup current state before loading if needed.

        Args:
            archive_path: Path to .bma archive directory
            target_dir: Target directory for loading (default: data/)
            validate: Whether to validate archive before loading (default: True)
            force: Force loading even if validation fails (default: False)

        Returns:
            Dict with load results:
            {
                'success': bool,
                'loaded_files': List[str],
                'validation': Dict,
                'statistics': Dict
            }

        Example:
            # Load baseline memory
            result = coordinator.load_memory_archive(
                archive_path=Path("archives/memory_baseline.bma"),
                validate=True
            )

            # Force load without validation (not recommended)
            result = coordinator.load_memory_archive(
                archive_path=Path("archives/test.bma"),
                validate=False,
                force=True
            )
        """
        try:
            from ..memory.memory_archive import MemoryArchive

            archive_path = Path(archive_path)

            if not archive_path.exists():
                return {
                    'success': False,
                    'error': f'Archive not found: {archive_path}',
                    'loaded_files': []
                }

            logger.info(f"📥 Loading memory archive: {archive_path}")

            # Create archive instance
            archive = MemoryArchive(archive_path)

            # Load archive
            result = archive.load(
                target_dir=target_dir,
                validate=validate,
                force=force
            )

            # Get archive statistics
            info = archive.get_info()

            result['statistics'] = info.get('statistics', {})
            result['archive_name'] = info.get('name', archive_path.name)

            if result['success']:
                logger.info(f"✅ Successfully loaded memory archive: {info.get('name')}")
                logger.info(f"   Total memories: {info['statistics'].get('total_memories', 0):,}")

                # Load brain region states if v2.0.0
                brain_regions_data = result.get('brain_regions_data', {})
                if brain_regions_data:
                    logger.info(f"🧠 Loading brain region states...")

                    # Load Hippocampus state
                    if 'hippocampus' in brain_regions_data and hasattr(self, 'hippocampus'):
                        try:
                            success = self.hippocampus.load_state(brain_regions_data['hippocampus'])
                            if success:
                                logger.info(f"   ✓ Hippocampus state restored")
                            else:
                                logger.warning(f"   ⚠️ Hippocampus state load failed")
                        except Exception as e:
                            logger.error(f"   ❌ Hippocampus load error: {e}")

                    # Load Prefrontal state
                    prefrontal_agent = getattr(self, 'prefrontal_storage', None) or getattr(self, 'prefrontal_agent', None)
                    if 'prefrontal' in brain_regions_data and prefrontal_agent:
                        try:
                            success = prefrontal_agent.load_state(brain_regions_data['prefrontal'])
                            if success:
                                logger.info(f"   ✓ PrefrontalCortex state restored")
                            else:
                                logger.warning(f"   ⚠️ PrefrontalCortex state load failed")
                        except Exception as e:
                            logger.error(f"   ❌ PrefrontalCortex load error: {e}")

                    # Load Amygdala state
                    if 'amygdala' in brain_regions_data and hasattr(self, 'amygdala'):
                        try:
                            success = self.amygdala.load_state(brain_regions_data['amygdala'])
                            if success:
                                logger.info(f"   ✓ Amygdala state restored")
                            else:
                                logger.warning(f"   ⚠️ Amygdala state load failed")
                        except Exception as e:
                            logger.error(f"   ❌ Amygdala load error: {e}")

                    # Load BasalGanglia state
                    if 'basal_ganglia' in brain_regions_data and hasattr(self, 'basal_ganglia'):
                        try:
                            success = self.basal_ganglia.load_state(brain_regions_data['basal_ganglia'])
                            if success:
                                logger.info(f"   ✓ BasalGanglia state restored")
                            else:
                                logger.warning(f"   ⚠️ BasalGanglia state load failed")
                        except Exception as e:
                            logger.error(f"   ❌ BasalGanglia load error: {e}")

                    logger.info(f"🎉 All brain regions loaded successfully")

                # Reinitialize memory system to pick up new database
                # (Memory system will reconnect on next query)
                logger.info(f"🔄 Memory system will reload on next operation")

            return result

        except Exception as e:
            logger.error(f"❌ Failed to load memory archive: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'loaded_files': []
            }

    def validate_memory_archive(
        self,
        archive_path: Path,
        check_checksums: bool = True
    ) -> Dict[str, Any]:
        """
        Validate memory archive integrity and compatibility.

        Checks:
        - Archive structure (manifest, database, etc.)
        - File integrity via checksums
        - Format version compatibility
        - Required features availability

        Args:
            archive_path: Path to .bma archive directory
            check_checksums: Whether to verify file checksums (slower but thorough)

        Returns:
            Dict with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'manifest_valid': bool,
                'files_valid': bool,
                'checksums_valid': bool,
                'compatibility': Dict
            }

        Example:
            validation = coordinator.validate_memory_archive(
                archive_path=Path("archives/memory_baseline.bma"),
                check_checksums=True
            )

            if validation['valid']:
                print("✅ Archive is valid")
            else:
                print(f"❌ Validation errors: {validation['errors']}")
        """
        try:
            from ..memory.memory_archive import MemoryArchive

            archive_path = Path(archive_path)

            if not archive_path.exists():
                return {
                    'valid': False,
                    'errors': [f'Archive not found: {archive_path}'],
                    'warnings': [],
                    'manifest_valid': False,
                    'files_valid': False,
                    'checksums_valid': False
                }

            archive = MemoryArchive(archive_path)
            validation = archive.validate(check_checksums=check_checksums)

            return validation

        except Exception as e:
            logger.error(f"❌ Failed to validate archive: {e}", exc_info=True)
            return {
                'valid': False,
                'errors': [f'Validation failed: {str(e)}'],
                'warnings': [],
                'manifest_valid': False,
                'files_valid': False,
                'checksums_valid': False
            }

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

        # 🔥 Temporal question patterns - require cross-memory reasoning
        # "When did X..." needs to combine conversation date + relative time
        temporal_patterns = [
            'when did', 'when is', 'when was', 'when will', 'what date',
            'what time', 'how long ago', 'how many days', 'how many years'
        ]
        has_temporal_pattern = any(pattern in query_lower for pattern in temporal_patterns)

        has_high_priority = any(kw in query_lower for kw in high_priority_keywords)
        has_inference_pattern = any(pattern in query_lower for pattern in inference_patterns)

        # Question words requiring reasoning (relaxed - no entity requirement)
        reasoning_questions = ['what', 'who', 'why']
        starts_with_reasoning = any(query_lower.startswith(q) for q in reasoning_questions)

        # Trigger reasoning chain if:
        # 1. Has high-priority inference keywords (e.g., "identity", "likely"), OR
        # 2. Has inference pattern (e.g., "what is"), OR
        # 3. Starts with reasoning question + has proper nouns (names in query), OR
        # 4. 🔥 Has temporal pattern (e.g., "when did") - needs cross-memory date calculation
        has_proper_nouns = any(word[0].isupper() for word in query.split() if len(word) > 1)

        should_use = (
            has_high_priority or
            has_inference_pattern or
            has_temporal_pattern or  # 🔥 NEW: temporal questions need reasoning chain
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

            # 🔥 6. Write to functional brain regions (for Pillar #2 validation)
            # PrefrontalCortex: Store reasoning chain summary in working_memory (使用正确API触发auto-persistence)
            if use_reasoning_chain and reasoning_chain_result and hasattr(self, 'prefrontal_agent'):
                try:
                    # 🔥 使用正确的API调用,触发auto-persistence
                    result = await self.prefrontal_agent.store_item(
                        content=f"Reasoning for: {user_input[:50]}... → {response[:100]}...",
                        task_type='reasoning_chain',
                        priority=8,  # 高优先级
                        metadata={
                            'memory_count': reasoning_chain_result.get('memory_count', 0),
                            'causal_links': reasoning_chain_result.get('causal_links_count', 0),
                            'confidence': reasoning_chain_result.get('confidence', 0.0)
                        }
                    )
                    if result.get('stored'):
                        logger.info(f"🧠 PrefrontalCortex stored reasoning (memory_id={result.get('memory_id')[:8]})")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to store in PrefrontalCortex: {e}")

            # Amygdala: Store emotional tags in emotional_buffer (使用正确API触发auto-persistence)
            if hasattr(self, 'amygdala') and memory_stored:
                try:
                    # Simple emotion detection based on keywords
                    emotion_keywords = {
                        'happy': ['happy', 'joy', 'excited', 'wonderful', 'great', 'love', 'lottery', 'win', 'celebration', 'amazing'],
                        'sad': ['sad', 'heartbroken', 'cry', 'death', 'passed away', 'miss', 'depressed', 'lonely'],
                        'stress': ['stress', 'worried', 'deadline', 'pressure', 'anxious', 'overwhelming', 'busy'],
                        'anger': ['angry', 'frustrated', 'upset', 'mad', 'annoyed', 'irritated'],
                        'fear': ['fear', 'scared', 'afraid', 'worried', 'nervous', 'anxious']
                    }

                    detected_emotions = []
                    emotion_intensity = 0.0
                    input_lower = user_input.lower()

                    for emotion, keywords in emotion_keywords.items():
                        matches = [kw for kw in keywords if kw in input_lower]
                        if matches:
                            detected_emotions.append(emotion)
                            # 降低阈值,捕捉更多情绪
                            emotion_intensity = max(emotion_intensity, 0.3 + 0.05 * len(matches))

                    # 降低触发阈值从0.5到0.3,捕捉更多情绪
                    if detected_emotions and emotion_intensity > 0.3:
                        # 🔥 使用正确的API调用,触发auto-persistence
                        # 修复: memory_stored是bool，需要从hippocampus获取最新memory_id
                        latest_memory_id = 'unknown'
                        if hasattr(self, 'hippocampus') and hasattr(self.hippocampus, 'memories'):
                            if len(self.hippocampus.memories) > 0:
                                latest_memory_id = self.hippocampus.memories[-1].id

                        result = await self.amygdala.tag_emotion(
                            reference_id=latest_memory_id,
                            content_summary=user_input[:100],
                            emotion_tags=detected_emotions,
                            emotion_intensity=min(emotion_intensity, 1.0),
                            metadata={'source': 'user_input', 'auto_tagged': True}
                        )
                        if result.get('tagged'):
                            logger.info(f"🎭 Amygdala tagged emotion: {detected_emotions} (intensity={emotion_intensity:.2f})")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to tag emotion in Amygdala: {e}")

            # BasalGanglia: Store behavioral patterns in strategy_cache (使用正确API触发auto-persistence)
            if hasattr(self, 'basal_ganglia'):
                try:
                    # Simple pattern detection based on keywords
                    action_keywords = {
                        'click': ['clicked', 'click', 'press', 'button'],
                        'open': ['opened', 'open', 'launch', 'start'],
                        'save': ['save', 'saved', 'saving'],
                        'search': ['search', 'searched', 'find', 'query'],
                        'create': ['create', 'created', 'make', 'new']
                    }

                    detected_actions = []
                    input_lower = user_input.lower()

                    for action, keywords in action_keywords.items():
                        if any(kw in input_lower for kw in keywords):
                            detected_actions.append(action)

                    if detected_actions:
                        for action in detected_actions:
                            skill_name = f"{action}_pattern"
                            # Check if skill already exists
                            if skill_name in self.basal_ganglia.skills:
                                # 🔥 使用正确的API调用practice_skill,触发auto-persistence
                                result = await self.basal_ganglia.practice_skill(skill_name)
                                if result.get('practiced'):
                                    logger.info(f"🎯 BasalGanglia practiced: {skill_name} (proficiency={result.get('proficiency_level', 0):.2f})")
                            else:
                                # 🔥 使用正确的API调用store_skill,触发auto-persistence
                                result = await self.basal_ganglia.store_skill(
                                    skill_name=skill_name,
                                    content=f"Pattern: {action} action detected",
                                    steps=[user_input[:100]],
                                    metadata={'source': 'user_input', 'action': action, 'auto_detected': True}
                                )
                                if result.get('stored'):
                                    logger.info(f"🎯 BasalGanglia learned new skill: {skill_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to store in BasalGanglia: {e}")

            # 🔄 Phase 2: Action → Environment Feedback Loop (Pillar #3)
            # Feed action result back to environment to close the loop
            if hasattr(self, 'environment'):
                try:
                    from src.agents.environment.environment_agent.data_models import StateType
                    await self.environment.update_state(
                        state_type=StateType.TASK_EXECUTION,
                        context={
                            'action': 'response_generated',
                            'user_input': user_input[:200],
                            'response': response[:200],
                            'timestamp': datetime.now(),
                            'memories_retrieved': len(memories)
                        }
                    )
                    logger.debug(f"🔄 Action fed back to environment (response length: {len(response)})")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update environment: {e}")

            # 🧠 自适应记忆塑造机制
            # 基于记忆系统状态自动触发巩固/反思/遗忘
            if memory_stored and hasattr(self, 'adaptive_shaping'):
                try:
                    # 获取最新记忆数据
                    memory_data = {}
                    if hasattr(self, 'hippocampus') and len(self.hippocampus.memories) > 0:
                        latest_memory = self.hippocampus.memories[-1]
                        memory_data = {
                            'memory_id': latest_memory.id,
                            'importance': getattr(latest_memory, 'importance', 0.5),
                            'emotion_tags': getattr(latest_memory, 'emotion_tags', []),
                            'entities': getattr(latest_memory, 'entities', [])
                        }

                        # 触发自适应塑造检查
                        await self.adaptive_shaping.on_new_memory_stored(
                            latest_memory.id,
                            memory_data
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Adaptive memory shaping failed: {e}")

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

    async def process_environment_event(
        self,
        event_type: str,  # 'observation', 'reward', 'feedback'
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process environment events and integrate into memory system

        Pillar #3: Environment Memory Flywheel

        This method closes the loop: Environment → Memory → Reasoning → Action → Environment

        Args:
            event_type: Type of event ('observation', 'reward', 'feedback')
            event_data: Event data including 'content', 'source', 'timestamp', etc.

        Returns:
            Dict with status, stored flag, and event processing details
        """
        try:
            from src.agents.environment.environment_agent.data_models import StateType, RewardType

            logger.info(f"🌍 Processing environment event: {event_type}")

            # 1. Update environment state
            if hasattr(self, 'environment'):
                try:
                    # Determine state type based on event
                    state_type = StateType.CONVERSATION  # Default
                    if event_type == 'observation':
                        state_type = StateType.CONVERSATION
                    elif event_type == 'reward':
                        state_type = StateType.TASK_EXECUTION
                    elif event_type == 'feedback':
                        state_type = StateType.LEARNING

                    # Update environment state
                    await self.environment.update_state(
                        state_type=state_type,
                        context={
                            'event_type': event_type,
                            'event_data': event_data,
                            'timestamp': event_data.get('timestamp', datetime.now())
                        }
                    )
                    logger.debug(f"✅ Environment state updated: {state_type.value}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update environment state: {e}")

            # 2. Store observation in Hippocampus (via process_input pipeline)
            if event_type == 'observation':
                content = event_data.get('content', '')
                source = event_data.get('source', 'environment')

                if content:
                    # Use existing process_input to store in Hippocampus
                    # This ensures observation goes through full memory pipeline
                    logger.debug(f"📝 Storing environment observation in memory: {content[:50]}...")
                    await self.process_input(f"[Environment Observation from {source}] {content}")

                    return {
                        'status': 'success',
                        'stored': True,
                        'event_type': event_type,
                        'content_length': len(content),
                        'source': source
                    }
                else:
                    logger.warning("⚠️ Empty observation content, skipping storage")
                    return {'status': 'skipped', 'stored': False, 'reason': 'empty_content'}

            # 3. Issue reward signal if needed
            elif event_type == 'reward':
                if hasattr(self, 'environment'):
                    try:
                        reward_value = event_data.get('reward_value', 0.0)
                        reason = event_data.get('reason', 'environment_reward')
                        reward_type_str = event_data.get('reward_type', 'neutral')

                        # Map string to RewardType enum
                        reward_type = RewardType.NEUTRAL
                        if reward_type_str == 'positive':
                            reward_type = RewardType.POSITIVE
                        elif reward_type_str == 'negative':
                            reward_type = RewardType.NEGATIVE

                        await self.environment.issue_reward(
                            reward_type=reward_type,
                            reward_value=reward_value,
                            reason=reason,
                            associated_memory_id=event_data.get('associated_memory_id')
                        )
                        logger.debug(f"✅ Reward signal issued: {reward_type.value} ({reward_value})")

                        return {
                            'status': 'success',
                            'stored': True,
                            'event_type': event_type,
                            'reward_value': reward_value,
                            'reward_type': reward_type_str
                        }
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to issue reward: {e}")
                        return {'status': 'error', 'stored': False, 'error': str(e)}

            # 4. Provide feedback if needed
            elif event_type == 'feedback':
                if hasattr(self, 'environment'):
                    try:
                        feedback_type = event_data.get('feedback_type', 'info')
                        content = event_data.get('content', '')
                        target_agent = event_data.get('target_agent')
                        severity = event_data.get('severity', 'info')

                        await self.environment.provide_feedback(
                            feedback_type=feedback_type,
                            content=content,
                            target_agent=target_agent,
                            severity=severity
                        )
                        logger.debug(f"✅ Feedback provided: {feedback_type}")

                        return {
                            'status': 'success',
                            'stored': True,
                            'event_type': event_type,
                            'feedback_type': feedback_type
                        }
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to provide feedback: {e}")
                        return {'status': 'error', 'stored': False, 'error': str(e)}

            else:
                logger.warning(f"⚠️ Unknown event type: {event_type}")
                return {'status': 'error', 'stored': False, 'reason': 'unknown_event_type'}

        except Exception as e:
            logger.error(f"❌ Environment event processing failed: {e}", exc_info=True)
            return {'status': 'error', 'stored': False, 'error': str(e)}


# Backward compatibility alias
BrainCoordinator = BrainInspiredCoordinator
