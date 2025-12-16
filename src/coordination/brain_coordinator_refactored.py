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
from ..memory.key_value_stores import KeyValueMemoryStore
from ..memory.storage_coordinator import get_storage_coordinator
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
from ..brain.active_learning import ActiveLearningManager  # 🔥 2025-12-14: 主动学习集成
from ..agents.brain_regions.thalamus_agent import ThalamusAgent, Timescale  # 🔥 2025-12-15: HRM集成
from ..agents.brain_regions.anterior_cingulate_agent import AnteriorCingulateAgent  # 🔥 2025-12-15: ACT集成
from .result_arbiter import ResultArbiter, LearningCaseLogger  # 🔥 2025-12-15: 结果审查集成
from .proactive_inquiry import ProactiveInquiryManager  # 🔥 2025-12-16: 主动询问机制
from .confidence_calibrator import get_confidence_calibrator  # 🔥 2025-12-16: 置信度校准
from ..agents.core.learnable_router import LearnableAgentRouter  # 🔥 2025-12-15: 可学习路由集成
from ..agents.brain_regions.amygdala_hrm_extension import AmygdalaHRMExtension  # 🔥 2025-12-15: HRM扩展
from ..agents.brain_regions.basal_ganglia_hrm_extension import BasalGangliaHRMExtension  # 🔥 2025-12-15: HRM扩展
from .brain_retrieval_integration import (  # 🔥 2025-12-15: 高级脑仿生检索
    BrainInspiredRetrieval,
    BrainRetrievalResult,
    PrefrontalFeedbackSystem
)

logger = get_logger(__name__)


# 🔥 2025-12-15: HRM Enhanced Agents - 组合基础Agent与HRM扩展
class AmygdalaAgentHRM(AmygdalaHRMExtension, AmygdalaAgent):
    """Amygdala Agent with HRM L-module (fast emotional tagging)"""
    pass


class BasalGangliaAgentHRM(BasalGangliaHRMExtension, BasalGangliaAgent):
    """Basal Ganglia Agent with HRM fixed-point detection"""
    pass


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
            brain_network=getattr(self, 'brain_network', None),
            routing_manager=self.routing_manager,  # 🔥 FIX: Pass routing_manager for weight updates
            coordinator=None  # 🔥 2025-12-15: 稍后设置，因为此时 coordinator 尚未完全初始化
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

        # 🔥 2025-12-14: Initialize Active Learning Manager
        logger.info("🔧 [11/12] Initializing ActiveLearningManager...")
        try:
            self.active_learning = ActiveLearningManager(config={
                'active_learning_enabled': True,
                'active_learning_threshold': 0.5,  # 低于此置信度时考虑提问
                'curiosity_level': 0.6
            })
            logger.info("✅ [11/12] ActiveLearningManager initialized")
        except Exception as e:
            logger.warning(f"⚠️ ActiveLearningManager not available: {e}")
            self.active_learning = None

        # 🔥 2025-12-15: Initialize HRM (Hierarchical Reasoning Model) components
        logger.info("🔧 [12/12] Initializing HRM (Thalamus + AnteriorCingulate)...")
        try:
            # Thalamus: 多时间尺度协调器
            # 不同脑区以不同频率更新 (τ=1 快速, τ=3 中速, τ=10 慢速)
            brain_regions = {
                'hippocampus': self.hippocampus,
                'temporal_lobe': self.temporal_lobe,
                'prefrontal': self.prefrontal_storage,
                'amygdala': self.amygdala,
                'basal_ganglia': self.basal_ganglia
            }
            thalamus_config = {
                'custom_timescales': {
                    'hippocampus': Timescale.HIPPOCAMPUS,      # τ=1, 每次都更新 (情景记忆)
                    'temporal_lobe': Timescale.HIPPOCAMPUS,    # τ=1, 每次都更新 (语义记忆)
                    'prefrontal': Timescale.PREFRONTAL,        # τ=10, 慢更新 (执行控制)
                    'amygdala': Timescale.AMYGDALA,            # τ=1, 快速响应 (情绪)
                    'basal_ganglia': Timescale.BASAL_GANGLIA   # τ=3, 中速 (习惯/程序记忆)
                },
                'sync_threshold': 0.8  # 脑区间同步阈值
            }
            self.thalamus = ThalamusAgent(brain_regions, thalamus_config)

            # AnteriorCingulate: 自适应计算时间 (ACT)
            # 决定何时停止思考，平衡速度与准确性
            act_config = {
                'min_iterations': 1,
                'max_iterations': 5,
                'confidence_threshold': 0.85,
                'ponder_cost': 0.01  # 每次迭代的计算成本
            }
            self.anterior_cingulate = AnteriorCingulateAgent(act_config)

            logger.info("✅ [12/13] HRM initialized")
            logger.info(f"   🔗 Thalamus managing {len(brain_regions)} brain regions")
            logger.info(f"   🧠 AnteriorCingulate ACT enabled (threshold={act_config['confidence_threshold']})")
        except Exception as e:
            logger.warning(f"⚠️ HRM initialization failed: {e}")
            self.thalamus = None
            self.anterior_cingulate = None

        # 🔥 2025-12-15: Initialize Result Arbiter (结果审查机制)
        logger.info("🔧 [13/14] Initializing ResultArbiter...")
        try:
            self.result_arbiter = ResultArbiter(
                prefrontal_agent=self.prefrontal_storage,
                environment_agent=getattr(self, 'environment', None)
            )
            self.learning_case_logger = LearningCaseLogger()
            logger.info("✅ [13/14] ResultArbiter initialized")
        except Exception as e:
            logger.warning(f"⚠️ ResultArbiter initialization failed: {e}")
            self.result_arbiter = None
            self.learning_case_logger = None

        # 🔥 2025-12-16: Initialize Proactive Inquiry Manager (主动询问机制)
        logger.info("🔧 [13.5/14] Initializing ProactiveInquiryManager...")
        try:
            self.proactive_inquiry = ProactiveInquiryManager(
                prefrontal_agent=self.prefrontal_storage,
                result_arbiter=self.result_arbiter
            )
            logger.info("✅ [13.5/14] ProactiveInquiryManager initialized")
        except Exception as e:
            logger.warning(f"⚠️ ProactiveInquiryManager initialization failed: {e}")
            self.proactive_inquiry = None

        # 🔥 2025-12-15: Initialize Learnable Router (可学习脑区路由)
        logger.info("🔧 [14/15] Initializing LearnableAgentRouter...")
        try:
            brain_region_names = [
                'hippocampus', 'temporal_lobe', 'prefrontal', 'amygdala', 'basal_ganglia',
                'memory_retrieval', 'consolidation', 'reflection', 'reasoning_validator'
            ]
            self.learnable_router = LearnableAgentRouter(
                agent_names=brain_region_names,
                learning_rate=0.05,
                checkpoint_dir="data/checkpoints"
            )
            logger.info(f"✅ [14/15] LearnableAgentRouter initialized ({len(brain_region_names)} agents)")
        except Exception as e:
            logger.warning(f"⚠️ LearnableAgentRouter initialization failed: {e}")
            self.learnable_router = None

        # 🔥 2025-12-15: Initialize Brain-Inspired Retrieval (高级脑仿生检索)
        # 整合: 快慢路径分离 + 前额叶反馈 + 杏仁核注意力 + 脑区协作循环
        logger.info("🔧 [15/15] Initializing BrainInspiredRetrieval...")
        try:
            from ..services.shared_openai_client import shared_client_manager
            self.brain_inspired_retrieval = BrainInspiredRetrieval(
                memory_coordinator=self.memory_coordinator,
                llm_client=shared_client_manager,
                enable_fast_path=False,   # 🔥 关闭快速路径，强制深度检索
                enable_iterative=True,    # 启用迭代检索
                max_iterations=5          # 最多5轮迭代
            )
            # 独立的前额叶反馈系统 (用于策略学习)
            self.prefrontal_feedback = PrefrontalFeedbackSystem()
            logger.info("✅ [15/15] BrainInspiredRetrieval initialized")
            logger.info("   🧠 Features: Prefrontal Feedback + Brain Region Collaboration")
            logger.info("   🔁 Iterative retrieval enabled (max 5 iterations)")
        except Exception as e:
            logger.warning(f"⚠️ BrainInspiredRetrieval initialization failed: {e}")
            import traceback
            logger.warning(f"   Traceback: {traceback.format_exc()}")
            self.brain_inspired_retrieval = None
            self.prefrontal_feedback = None

        # 🔥 2025-12-15: 设置 LearningManager 的 coordinator 引用
        # 此时所有组件已初始化完成，可以安全地传递 self
        if self.learning_manager:
            self.learning_manager._coordinator = self
            logger.debug("  ✅ LearningManager coordinator reference set")

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

        # 🔥 2025-12-13: 创建统一的KV分离存储系统
        # 基于论文 "Key-value memory in the brain" - 键值分离提高检索效率
        self.kv_memory_store = KeyValueMemoryStore(
            value_store_path="data/kv_value_store.db",
            enable_vector_index=True
        )
        logger.info("✅ KV分离存储系统已初始化")

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
            memory_system=self.kv_memory_store,  # 🔥 使用KV分离存储代替碎片化存储
            use_global_storage=True  # 🔥 FIX: Enable global storage delegation
        )

        # 🔥 2025-12-15: 使用HRM增强版Agent (带快速情绪标记)
        self.amygdala = AmygdalaAgentHRM(
            capacity=1000,
            hippocampus_agent=self.hippocampus,
            temporal_lobe_agent=self.temporal_lobe
        )

        self.prefrontal_storage = PrefrontalAgent(capacity=10, brain_coordinator=None)
        self.prefrontal_agent = self.prefrontal_storage  # Alias for functional brain regions test

        # 🔥 2025-12-15: 使用HRM增强版Agent (带不动点检测)
        self.basal_ganglia = BasalGangliaAgentHRM(capacity=500)


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

        # 🔥 NEW: Initialize version manager for persistent memory management
        from ..memory.memory_version_manager import MemoryVersionManager
        self.version_manager = MemoryVersionManager(
            coordinator=self,
            auto_save_enabled=True
        )

        # 🔥 FIX: Auto-load latest memory state on startup (断点续传)
        logger.info("📥 Checking for existing memory state...")
        try:
            loaded = await self.version_manager.auto_load()
            if loaded:
                logger.info("✅ Restored previous memory state (断点续传成功)")
            else:
                logger.info("📝 No previous state found, starting fresh")
        except Exception as e:
            logger.warning(f"⚠️ Auto-load failed: {e}, starting fresh")

        # 🔥 NEW: Sync hippocampus with global storage on startup
        # This ensures local cache reflects the actual global state
        logger.info("🔄 Syncing brain regions with global storage...")
        try:
            sync_result = await self.hippocampus.ensure_global_sync()
            logger.info(f"✅ Hippocampus global sync: {sync_result}")
        except Exception as e:
            logger.warning(f"⚠️ Hippocampus global sync failed: {e}")

        # 🔥 P0 FIX: Sync Hippocampus memories to VectorDB
        # This fixes the issue where historical memories from JSON are not indexed in FAISS
        logger.info("🔄 Syncing Hippocampus memories to VectorDB...")
        try:
            vectordb_sync = await self.hippocampus.sync_to_global_vectordb(
                memory_system=self.memory_system,
                batch_size=50  # Process in batches to avoid memory issues
            )
            logger.info(f"✅ VectorDB sync complete: {vectordb_sync}")
        except Exception as e:
            logger.warning(f"⚠️ VectorDB sync failed: {e}")

        # Start message bus
        await self.message_bus_manager.start()

        # Start background processes
        if self.background_processes and self.background_processes.config.enabled:
            await self.background_processes.start()

        # Start continuous learning loop
        await self.learning_manager.start_continuous_learning_loop()

        logger.info("✅ Brain coordination system started")

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

        # 🔥 NEW: Auto-save memory state before shutdown
        if hasattr(self, 'version_manager') and self.version_manager:
            logger.info("💾 Auto-saving memory state before shutdown...")
            try:
                await self.version_manager.auto_save()
                logger.info("✅ Memory state saved")
            except Exception as e:
                logger.warning(f"⚠️ Failed to auto-save: {e}")

        # Stop learning loop
        await self.learning_manager.stop_continuous_learning_loop()

        # Stop background processes
        if self.background_processes:
            await self.background_processes.stop()

        # Stop message bus
        await self.message_bus_manager.stop()

        logger.info("✅ Brain coordination system stopped")


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
        importance: float = 0.5,
        inherited_event_time: datetime = None  # 🔥 2025-12-16: 继承的事件时间
    ) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator"""
        return await self.memory_coordinator.store_memory_with_timestamp(
            content, timestamp, speaker, importance,
            inherited_event_time=inherited_event_time
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

    async def brain_retrieve(
        self,
        query: str,
        k: int = 10,
        context: Dict[str, Any] = None,
        activation_plan: Optional[Dict[str, bool]] = None,
        force_slow_path: bool = False
    ) -> BrainRetrievalResult:
        """
        🧠 高级脑仿生检索 - 使用完整的脑区协作流程

        特性:
        1. 快慢路径分离 (FastPathDetector) - 简单查询快速返回
        2. 脑区协作循环 - 海马→前额叶→杏仁核→颞叶循环
        3. 前额叶反馈学习 - 根据检索质量调整策略
        4. 杏仁核注意力调节 - 情绪相关记忆优先
        5. 颞叶语义补充 - 概念知识增强

        Args:
            query: 查询文本
            k: 返回结果数量
            context: 上下文信息
            activation_plan: 脑区激活计划 (来自Thalamus)
            force_slow_path: 强制使用深度检索

        Returns:
            BrainRetrievalResult: 包含检索结果、路径类型、迭代次数等
        """
        if not self.brain_inspired_retrieval:
            # Fallback to simple retrieval
            logger.warning("BrainInspiredRetrieval not available, using smart_retrieve fallback")
            memories = await self.smart_retrieve(query, k, 'auto', context)
            return BrainRetrievalResult(
                memories=memories,
                path_type='fallback',
                iterations=1,
                gaps_detected=[],
                confidence=0.5,
                retrieval_time_ms=0,
                debug_info={'fallback': True}
            )

        # 获取 Thalamus 激活计划 (如果可用)
        if activation_plan is None and self.thalamus:
            try:
                thalamus_plan = await self.thalamus.get_activation_plan(query, context or {})
                activation_plan = thalamus_plan.get('regions', {})
            except Exception as e:
                logger.debug(f"Thalamus activation plan failed: {e}")

        # 执行脑仿生检索
        result = await self.brain_inspired_retrieval.retrieve(
            query=query,
            k=k,
            context=context,
            activation_plan=activation_plan,
            force_slow_path=force_slow_path
        )

        # 记录统计信息
        self.processing_stats['retrieval_calls'] = self.processing_stats.get('retrieval_calls', 0) + 1
        if result.path_type == 'fast':
            self.processing_stats['fast_path_hits'] = self.processing_stats.get('fast_path_hits', 0) + 1
        else:
            self.processing_stats['slow_path_calls'] = self.processing_stats.get('slow_path_calls', 0) + 1

        return result

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

            # 🔥 2025-12-15: Learnable Router - 可学习的脑区路由
            learnable_routing_result = None
            if self.learnable_router:
                try:
                    learnable_routing_result = await self.learnable_router.route(user_input, top_k=4)
                    query_features['learnable_selected_agents'] = learnable_routing_result['selected_agents']
                    query_features['learnable_scores'] = learnable_routing_result['scores']
                    logger.debug(f"🧭 LearnableRouter: {learnable_routing_result['selected_agents'][:3]}")
                except Exception as e:
                    logger.debug(f"LearnableRouter routing skipped: {e}")

            # 2. Memory retrieval via BrainInspiredRetrieval (脑仿生检索)
            # 🔥 2025-12-15: 使用完整的脑区协作检索流程
            brain_retrieval_result = None
            if self.brain_inspired_retrieval:
                try:
                    brain_retrieval_result = await self.brain_retrieve(
                        query=user_input,
                        k=10,
                        context=context,
                        force_slow_path=False  # 让系统自动判断快慢路径
                    )
                    memories = brain_retrieval_result.memories
                    logger.info(
                        f"🧠 BrainRetrieval: {len(memories)} memories, "
                        f"path={brain_retrieval_result.path_type}, "
                        f"iterations={brain_retrieval_result.iterations}, "
                        f"confidence={brain_retrieval_result.confidence:.2f}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ BrainInspiredRetrieval failed, using fallback: {e}")
                    memories = await self.smart_retrieve(user_input, k=10, context=context)
            else:
                # Fallback to simple retrieval
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

            # 🎭 3.4 Theory of Mind Pre-check: 对抗性问题检测
            # 2025-12-17: 集成 ToM 模块检测欺骗性问题
            adversarial_result = None
            if self.reasoning_validator and memories:
                try:
                    adversarial_result = await self.reasoning_validator.check_adversarial_before_reasoning(
                        query=user_input,
                        memories=[
                            {'content': m.content if hasattr(m, 'content') else m.get('content', '')}
                            for m in memories[:15]
                        ]
                    )
                    if adversarial_result:
                        logger.info(f"🎭 Adversarial question detected by ToM: {adversarial_result.get('adversarial_type')}")
                except Exception as e:
                    logger.debug(f"ToM check skipped: {e}")

            # 🔥 3.5 Temporal Reasoning for date/duration questions
            # 2025-12-12: 集成temporal推理到主流程
            temporal_reasoning_result = None
            if self.reasoning_validator and memories and not adversarial_result:
                try:
                    # 检测temporal问题 (when, what date, how long等)
                    query_lower = user_input.lower().strip()
                    temporal_keywords = [
                        'when', 'what date', 'what day', 'how long', 'how many days',
                        'how many years', 'how many months', 'how many weeks',
                        'duration', 'before', 'after', 'ago'
                    ]
                    # 排除Who/What person类问题
                    non_temporal_prefixes = ['who ', 'who\'s ', 'what is ', 'what are ']
                    is_non_temporal = any(query_lower.startswith(p) for p in non_temporal_prefixes)
                    is_temporal_query = any(kw in query_lower for kw in temporal_keywords) and not is_non_temporal

                    if is_temporal_query:
                        logger.info("⏰ Activating Temporal Reasoning...")

                        # 🔥 2025-12-13: 提取查询中的实体用于过滤
                        query_entities = []
                        query_words = user_input.lower().split()
                        # 查找可能的实体名（首字母大写的词，或者特定关键词后的词）
                        for word in user_input.split():
                            if word[0].isupper() and word.lower() not in ['when', 'what', 'how', 'where', 'did', 'the', 'a', 'an', 'to']:
                                query_entities.append(word.lower())

                        # 🔥 优先级排序：包含查询实体的记忆优先
                        def relevance_score(mem):
                            content = (mem.content if hasattr(mem, 'content') else mem.get('content', '')).lower()
                            score = 0
                            for entity in query_entities:
                                if entity in content:
                                    score += 10
                            # 如果包含相对时间词，增加分数
                            if any(w in content for w in ['yesterday', 'today', 'last week', 'ago', 'before']):
                                score += 5
                            return score

                        sorted_memories = sorted(memories, key=relevance_score, reverse=True)

                        # 格式化记忆供temporal推理使用
                        memory_dicts = []
                        for mem in sorted_memories[:20]:
                            if hasattr(mem, 'content'):
                                mem_dict = {'content': mem.content}
                                if hasattr(mem, 'timestamp'):
                                    mem_dict['timestamp'] = str(mem.timestamp)
                                if hasattr(mem, 'metadata') and mem.metadata:
                                    mem_dict['metadata'] = mem.metadata
                                    if 'event_time' in mem.metadata:
                                        mem_dict['event_time'] = mem.metadata['event_time']
                                memory_dicts.append(mem_dict)
                            elif isinstance(mem, dict):
                                mem_dict = mem.copy()
                                metadata = mem.get('metadata', {})
                                if metadata and 'event_time' in metadata:
                                    mem_dict['event_time'] = metadata['event_time']
                                memory_dicts.append(mem_dict)

                        # 调用temporal推理
                        temporal_reasoning_result = await self.reasoning_validator._temporal_reasoning(
                            query=user_input,
                            memories=memory_dicts,
                            hippocampus=self.hippocampus if hasattr(self, 'hippocampus') else None
                        )

                        if temporal_reasoning_result and temporal_reasoning_result.get('answer'):
                            confidence = temporal_reasoning_result.get('confidence', 0)
                            logger.info(f"✅ Temporal reasoning: answer='{temporal_reasoning_result['answer']}' (confidence={confidence:.2f})")
                except Exception as e:
                    logger.warning(f"⚠️ Temporal reasoning failed: {e}")

            # 4. Generate response
            # 🎭 优先使用ToM对抗性检测结果（如果检测到欺骗性问题）
            if adversarial_result and adversarial_result.get('answer'):
                response = adversarial_result['answer']
                logger.info(f"🎭 Using ToM Adversarial answer (type={adversarial_result.get('adversarial_type')})")
            # 🔥 然后使用temporal推理结果（如果置信度足够高）
            # 2025-12-13: 降低阈值到0.35，因为temporal reasoning计算相对日期时置信度会被降低
            elif temporal_reasoning_result and temporal_reasoning_result.get('answer') and temporal_reasoning_result.get('confidence', 0) >= 0.35:
                response = temporal_reasoning_result['answer']
                logger.info(f"⏰ Using Temporal Reasoning answer")
            elif use_reasoning_chain and reasoning_chain_result:
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

            # 🔥 NEW: Record retrieval outcome for learning feedback
            if hasattr(self, 'learning_manager') and self.learning_manager:
                try:
                    # Determine retrieval strategy used
                    strategy = query_features.get('recommended_strategy', 'hybrid')
                    # Evaluate success based on: got memories AND reasonable confidence
                    retrieval_success = len(memories) > 0
                    # Use reasoning chain confidence if available, else estimate
                    confidence = 0.5
                    if use_reasoning_chain and reasoning_chain_result:
                        confidence = reasoning_chain_result.get('confidence', 0.5)
                    elif memories:
                        # Simple heuristic: more memories = higher confidence (capped)
                        confidence = min(0.3 + len(memories) * 0.1, 0.9)

                    self.learning_manager.record_retrieval_outcome(
                        strategy=strategy,
                        query=user_input,
                        success=retrieval_success,
                        confidence=confidence,
                        memory_count=len(memories)
                    )
                except Exception as e:
                    logger.debug(f"Failed to record retrieval outcome: {e}")

            # 🔥 2025-12-14: Active Learning - 低置信度时考虑提问
            # 🔥 2025-12-16: 增强不确定性验证机制 (P0)
            active_learning_question = None
            uncertainty_verification = None

            # 不确定性验证阈值 (0.6 = 60% 置信度以下触发验证请求)
            UNCERTAINTY_THRESHOLD = 0.6

            if confidence < UNCERTAINTY_THRESHOLD:
                confidence_pct = int(confidence * 100)

                # 🔥 方案1: 使用 Active Learning 模块生成智能问题
                if self.active_learning:
                    try:
                        generated_question = await self.active_learning.check_and_generate_question(
                            query=user_input,
                            current_response=response,
                            confidence=confidence,
                            context={'memories_count': len(memories), 'strategy': strategy}
                        )
                        if generated_question:
                            active_learning_question = generated_question.content
                            # 格式化不确定性验证请求
                            uncertainty_verification = {
                                'triggered': True,
                                'confidence': confidence,
                                'confidence_pct': confidence_pct,
                                'question': active_learning_question,
                                'reason': 'low_confidence'
                            }
                            response = (
                                f"{response}\n\n"
                                f"💭 **不确定性提示** (置信度: {confidence_pct}%)\n"
                                f"我对这个回答不太确定。{active_learning_question}"
                            )
                            logger.info(f"💭 Uncertainty verification: confidence={confidence_pct}%, question='{active_learning_question[:50]}...'")
                    except Exception as e:
                        logger.debug(f"Active learning check failed: {e}")

                # 🔥 方案2: 如果没有 Active Learning 或生成失败，使用简单的验证请求
                if not active_learning_question:
                    uncertainty_verification = {
                        'triggered': True,
                        'confidence': confidence,
                        'confidence_pct': confidence_pct,
                        'question': None,
                        'reason': 'low_confidence'
                    }
                    response = (
                        f"{response}\n\n"
                        f"💭 **不确定性提示** (置信度: {confidence_pct}%)\n"
                        f"我对这个回答只有 {confidence_pct}% 的把握。如果有误，请告诉我正确的信息。"
                    )
                    logger.info(f"💭 Uncertainty verification (simple): confidence={confidence_pct}%")

            # 🔥 2025-12-15: HRM (Hierarchical Reasoning Model) 协调
            # Thalamus: 按不同时间尺度更新脑区
            hrm_coordination_result = None
            if self.thalamus:
                try:
                    # 执行一次协调步骤
                    hrm_coordination_result = await self.thalamus.coordinate_step(
                        input_data={
                            'query': user_input,
                            'response': response,
                            'memories': memories,
                            'confidence': confidence,
                            'step': getattr(self, '_hrm_step_counter', 0)
                        }
                    )
                    self._hrm_step_counter = getattr(self, '_hrm_step_counter', 0) + 1
                    updated_regions = hrm_coordination_result.get('updated_regions', [])
                    if updated_regions:
                        logger.debug(f"🔗 Thalamus coordinated: {updated_regions}")
                except Exception as e:
                    logger.debug(f"Thalamus coordination skipped: {e}")

            # AnteriorCingulate: 记录处理结果 (用于未来自适应计算)
            if self.anterior_cingulate:
                try:
                    self.anterior_cingulate.record_feedback_result({
                        'query_complexity': query_features.get('complexity', 'simple'),
                        'memory_count': len(memories),
                        'confidence': confidence,
                        'processing_time': processing_time,
                        'success': True
                    })
                except Exception as e:
                    logger.debug(f"AnteriorCingulate recording skipped: {e}")

            # 🔥 2025-12-15: HRM Extension - BasalGanglia 收敛监控 (不动点检测)
            convergence_result = None
            if hasattr(self.basal_ganglia, 'monitor_convergence'):
                try:
                    region_outputs = {
                        'hippocampus': {'converged': len(memories) > 0, 'memories': len(memories)},
                        'temporal_lobe': {'converged': bool(query_features.get('entities')), 'response': response[:100]},
                        'prefrontal': {'converged': confidence > 0.5, 'confidence': confidence},
                        'amygdala': {'converged': True, 'response': 'emotional_check'},
                        'basal_ganglia': {'converged': True, 'response': 'skill_check'}
                    }
                    convergence_result = await self.basal_ganglia.monitor_convergence(
                        step=getattr(self, '_hrm_step_counter', 0),
                        region_outputs=region_outputs
                    )
                    if convergence_result.get('is_fixed_point'):
                        logger.info(f"🎯 BasalGanglia detected fixed point: {convergence_result.get('fixed_point_id')}")
                        # 学习收敛模式
                        query_type = query_features.get('query_type', 'general')
                        await self.basal_ganglia.learn_convergence_pattern(
                            query_type=query_type,
                            convergence_step=convergence_result.get('step', 0)
                        )
                except Exception as e:
                    logger.debug(f"BasalGanglia convergence monitoring skipped: {e}")

            # 🔥 2025-12-15: HRM Extension - Amygdala 快速情绪标记 (每步更新)
            if hasattr(self.amygdala, 'fast_emotional_tagging') and memory_stored:
                try:
                    # 为新存储的记忆执行快速情绪标记
                    latest_memory_id = 'unknown'
                    if hasattr(self, 'hippocampus') and hasattr(self.hippocampus, 'memories') and self.hippocampus.memories:
                        latest_memory_id = self.hippocampus.memories[-1].id

                    emotional_result = await self.amygdala.fast_emotional_tagging({
                        'memory_id': latest_memory_id,
                        'content': user_input,
                        'context': {'confidence': confidence, 'response': response[:100]}
                    })
                    if emotional_result.get('converged'):
                        logger.debug(f"🎭 Amygdala emotional convergence: {emotional_result.get('emotion_tags')}")
                except Exception as e:
                    logger.debug(f"Amygdala fast emotional tagging skipped: {e}")

            # 🔥 2025-12-15: Result Arbiter - 结果质量审查
            review_result = None
            if self.result_arbiter:
                try:
                    review_result = await self.result_arbiter.review_answer(
                        query=user_input,
                        answer=response,
                        memories=[{'content': m.content if hasattr(m, 'content') else m.get('content', ''),
                                   'id': getattr(m, 'id', m.get('id', '')),
                                   'metadata': getattr(m, 'metadata', m.get('metadata', {}))}
                                  for m in memories],
                        confidence=confidence,
                        query_features=query_features
                    )

                    # 如果有质量问题，调整置信度
                    if review_result.has_issues:
                        original_confidence = confidence
                        confidence *= review_result.confidence_adjustment
                        logger.info(f"📊 ResultArbiter: {len(review_result.issues)} issues found, "
                                   f"confidence adjusted {original_confidence:.2f} → {confidence:.2f}")

                        # 如果需要重试且这是第一次尝试
                        if review_result.should_retry and not context.get('_retry_attempt'):
                            logger.info(f"🔄 ResultArbiter recommends retry: {review_result.retry_strategy}")

                            # 🔥 2025-12-16: EnvironmentAgent 外部探索触发
                            # 🔥 2025-12-16 FIX: 评估模式下不修改响应，避免污染答案
                            if review_result.retry_strategy == 'environment_exploration' and hasattr(self, 'environment'):
                                try:
                                    exploration_result = await self.environment.explore_external(
                                        query=user_input,
                                        exploration_type="web_search",
                                        query_type=query_features.get('query_type', 'general'),
                                        max_results=3,
                                        priority="high"
                                    )
                                    if exploration_result.get('exploration_complete'):
                                        external_results = exploration_result.get('results', [])
                                        if external_results:
                                            # 将外部探索结果添加到响应 (非评估模式)
                                            if not context.get('evaluation_mode', False):
                                                external_info = "\n\n📚 **补充信息** (来自外部探索):\n"
                                                for i, result in enumerate(external_results[:2], 1):
                                                    title = result.get('title', result.get('snippet', ''))[:50]
                                                    external_info += f"{i}. {title}...\n"
                                                response = response + external_info
                                            logger.info(f"🌐 EnvironmentAgent exploration: {len(external_results)} results")
                                except Exception as e:
                                    logger.debug(f"Environment exploration failed: {e}")

                            if self.learning_case_logger:
                                await self.learning_case_logger.log_failure_case(
                                    query=user_input,
                                    answer=response,
                                    memories_used=[{'content': m.content if hasattr(m, 'content') else m.get('content', ''),
                                                   'id': getattr(m, 'id', m.get('id', ''))}
                                                  for m in memories[:5]],
                                    review_result=review_result
                                )
                    else:
                        # 成功案例记录
                        if self.learning_case_logger and confidence > 0.7:
                            await self.learning_case_logger.log_success_case(
                                query=user_input,
                                answer=response,
                                memories_used=[{'id': getattr(m, 'id', m.get('id', ''))} for m in memories],
                                confidence=confidence
                            )
                except Exception as e:
                    logger.debug(f"ResultArbiter review skipped: {e}")

            # 🔥 2025-12-15: LearnableRouter Feedback Learning - 从结果学习
            if self.learnable_router and learnable_routing_result:
                try:
                    # 根据review_result和confidence确定success
                    routing_success = confidence > 0.5 and (review_result is None or not review_result.has_issues)
                    # 计算满意度分数
                    satisfaction = min(confidence * 1.2, 1.0) if routing_success else max(0.0, confidence - 0.2)

                    await self.learnable_router.update_from_feedback(
                        query=user_input,
                        selected_agents=learnable_routing_result['selected_agents'],
                        success=routing_success,
                        satisfaction=satisfaction
                    )
                    logger.debug(f"🎓 LearnableRouter feedback: success={routing_success}, satisfaction={satisfaction:.2f}")
                except Exception as e:
                    logger.debug(f"LearnableRouter feedback skipped: {e}")

            # 🔥 2025-12-16: ConfidenceCalibrator Feedback Learning - 跨脑区置信度校准学习
            # 根据响应质量更新各脑区的校准因子
            try:
                calibrator = get_confidence_calibrator()
                retrieval_success = confidence > 0.5 and (review_result is None or not review_result.has_issues)

                # 识别使用的记忆来源（脑区）
                memory_sources = set()
                for mem in memories:
                    # 从记忆的 calibration_info 或 source 字段获取来源
                    calibration_info = mem.get('_calibration', {}) if isinstance(mem, dict) else getattr(mem, '_calibration', {})
                    source = calibration_info.get('region') or mem.get('source', 'hippocampus') if isinstance(mem, dict) else getattr(mem, 'source', 'hippocampus')
                    memory_sources.add(source)

                # 为每个使用的脑区记录反馈
                for region in memory_sources:
                    calibrator.record_outcome(
                        region_name=region,
                        query=user_input,
                        memories_used=[m if isinstance(m, dict) else {'content': getattr(m, 'content', '')} for m in memories],
                        success=retrieval_success,
                        feedback_score=confidence
                    )

                # 定期保存校准状态（每100次查询保存一次）
                total_queries = sum(s.total_queries for s in calibrator.region_states.values())
                if total_queries % 100 == 0:
                    calibrator.save_calibration()
                    logger.info(f"📊 ConfidenceCalibrator saved (total_queries={total_queries})")

                logger.debug(f"📈 ConfidenceCalibrator feedback: regions={list(memory_sources)}, success={retrieval_success}")
            except Exception as e:
                logger.debug(f"ConfidenceCalibrator feedback skipped: {e}")

            # 🔥 2025-12-15: Prefrontal Feedback Learning - 前额叶策略学习
            # 根据结果质量调整检索策略权重
            if self.prefrontal_feedback and brain_retrieval_result:
                try:
                    # 评估检索质量
                    quality_assessment = self.prefrontal_feedback.evaluate_retrieval_quality(
                        query=user_input,
                        memories=memories,
                        query_type=query_features.get('query_type', 'general')
                    )

                    # 根据 ResultArbiter 结果调整奖励信号
                    reward_signal = quality_assessment['reward_signal']
                    if review_result:
                        if review_result.has_issues:
                            reward_signal = min(reward_signal, -0.3)  # 有问题则惩罚
                        elif confidence > 0.7:
                            reward_signal = max(reward_signal, 0.3)   # 高置信度则奖励

                    # 应用反馈学习
                    self.prefrontal_feedback.apply_feedback(
                        query_type=query_features.get('query_type', 'general'),
                        reward_signal=reward_signal
                    )
                    logger.debug(
                        f"🧠 Prefrontal feedback: quality={quality_assessment['quality_score']:.2f}, "
                        f"reward={reward_signal:.2f}, issues={quality_assessment.get('issues', [])}"
                    )
                except Exception as e:
                    logger.debug(f"Prefrontal feedback skipped: {e}")

            # 🔥 2025-12-16: Proactive Inquiry - 主动询问机制 (矛盾检测 + 知识缺口)
            proactive_inquiry_result = None
            if self.proactive_inquiry:
                try:
                    # 格式化记忆供主动询问分析
                    formatted_memories = [
                        {
                            'content': m.content if hasattr(m, 'content') else m.get('content', ''),
                            'entities': getattr(m, 'entities', m.get('entities', [])),
                            'metadata': getattr(m, 'metadata', m.get('metadata', {})),
                            'timestamp': str(getattr(m, 'timestamp', m.get('timestamp', '')))
                        }
                        for m in memories
                    ]

                    proactive_inquiry_result = await self.proactive_inquiry.analyze_for_inquiry(
                        query=user_input,
                        memories=formatted_memories,
                        confidence=confidence,
                        response_draft=response
                    )

                    if proactive_inquiry_result.should_inquire and proactive_inquiry_result.formatted_prompt:
                        # 将主动询问添加到响应 (非评估模式)
                        # 🔥 2025-12-16 FIX: 评估模式下不修改响应，避免污染答案
                        if not context.get('evaluation_mode', False):
                            response = response + proactive_inquiry_result.formatted_prompt
                        logger.info(
                            f"💬 ProactiveInquiry triggered: {len(proactive_inquiry_result.inquiries)} inquiries, "
                            f"types={[inq.inquiry_type.value for inq in proactive_inquiry_result.inquiries]}"
                        )
                except Exception as e:
                    logger.debug(f"ProactiveInquiry analysis skipped: {e}")

            # 🔥 2025-12-16: 构建 insights，包含不确定性验证和主动询问信息
            insights = {}
            if active_learning_question:
                insights['active_learning_question'] = active_learning_question
            if uncertainty_verification:
                insights['uncertainty_verification'] = uncertainty_verification
            if proactive_inquiry_result and proactive_inquiry_result.should_inquire:
                insights['proactive_inquiry'] = {
                    'triggered': True,
                    'inquiry_count': len(proactive_inquiry_result.inquiries),
                    'inquiry_types': [inq.inquiry_type.value for inq in proactive_inquiry_result.inquiries],
                    'bypass_response': proactive_inquiry_result.bypass_response
                }

            # 🔥 2025-12-16: EnvironmentAgent 奖励信号闭环
            # 基于响应质量自动发放奖励，强化学习记忆权重
            if hasattr(self, 'environment') and memory_stored:
                try:
                    from src.agents.environment.environment_agent.data_models import RewardType

                    # 计算奖励值：基于置信度和质量审查结果
                    reward_value = 0.0
                    reward_type = RewardType.NEUTRAL

                    if confidence >= 0.7 and (review_result is None or not review_result.has_issues):
                        # 高质量响应 → 正奖励
                        reward_value = min(confidence, 0.8)
                        reward_type = RewardType.POSITIVE
                        reward_reason = f"High quality response (confidence={confidence:.2f})"
                    elif confidence < 0.4 or (review_result and review_result.has_issues):
                        # 低质量响应 → 负奖励
                        reward_value = -0.3
                        reward_type = RewardType.NEGATIVE
                        reward_reason = f"Low quality response (confidence={confidence:.2f}, issues={review_result.has_issues if review_result else False})"
                    else:
                        # 中等质量 → 小正奖励
                        reward_value = 0.1
                        reward_type = RewardType.NEUTRAL
                        reward_reason = f"Moderate quality response (confidence={confidence:.2f})"

                    # 获取最新记忆ID
                    latest_memory_id = None
                    if hasattr(self, 'hippocampus') and hasattr(self.hippocampus, 'memories') and self.hippocampus.memories:
                        latest_memory_id = self.hippocampus.memories[-1].id

                    await self.environment.issue_reward(
                        reward_type=reward_type,
                        reward_value=reward_value,
                        reason=reward_reason,
                        associated_memory_id=latest_memory_id
                    )
                    logger.debug(f"🎯 EnvironmentAgent reward: {reward_type.value} ({reward_value:.2f})")

                    insights['environment_reward'] = {
                        'reward_type': reward_type.value,
                        'reward_value': reward_value,
                        'reason': reward_reason
                    }
                except Exception as e:
                    logger.debug(f"Environment reward skipped: {e}")

            return ProcessingResult(
                response=response,
                routing_decision=query_features,
                agents_involved=['conversation'],
                memories_retrieved=memories,
                memory_stored=memory_stored,
                processing_time=processing_time,
                agent_logs={},
                insights=insights,
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
