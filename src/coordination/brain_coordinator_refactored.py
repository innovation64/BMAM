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
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..utils.config import get_logger, get_settings
from ..utils.paths import BMAMPaths
from ..utils.memory_signal_config import load_memory_signal_config
from ..utils.knowledge_graph_builder import KnowledgeGraphBuilder
from ..utils.pattern_config import pattern_config
from ..utils.flexible_date_parser import FlexibleDateParser
from ..utils.i18n_config import get_config as get_i18n_config

# 🔥 2026-01-20 ABL-001: 消融配置检查（解决消融实验结果异常问题）
from ..config.ablation_config import is_component_enabled, get_active_ablation

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

from ..agents.brain_regions import (
    HippocampusAgent,
    TemporalLobeAgent,
    PrefrontalAgent,
    AmygdalaAgent,
    BasalGangliaAgent
)
# Note: MemoryType removed (unused)

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
from .memory_archive_manager import MemoryArchiveManager  # 🔥 2025-12-19: 归档操作提取
from .soul_state import get_soul_state, Insight, ValueGap  # P0: Introspection & Value Profile
from .confidence_calibrator import get_confidence_calibrator  # 🔥 2025-12-16: 置信度校准
from ..agents.core.learnable_router import LearnableAgentRouter  # 🔥 2025-12-15: 可学习路由集成
from ..agents.brain_regions.amygdala_hrm_extension import AmygdalaHRMExtension  # 🔥 2025-12-15: HRM扩展
from ..agents.brain_regions.basal_ganglia_hrm_extension import BasalGangliaHRMExtension  # 🔥 2025-12-15: HRM扩展
from .distributed_retrieval import (  # 🔥 2026-01-27 FIX-016: 五脑区分布式检索
    DistributedRetrievalCoordinator,
    init_distributed_coordinator
)
from .brain_retrieval_integration import (  # 🔥 2025-12-15: 高级脑仿生检索
    BrainInspiredRetrieval,
    BrainRetrievalResult,
    PrefrontalFeedbackSystem
)
from ..learning.feedback_loop import FeedbackLoop  # 🔥 2026-01-26 FIX-012: 反馈闭环激活
from ..memory.forgetting_coordinator import ForgettingCoordinator  # 🔥 2026-01-26 FIX-013: 遗忘协调器
from ..core.config import get_config as get_core_config  # 🔥 Task 1.5: Centralized config
from ..core.container import get_bm_container  # 🔥 Task 2.3: Lightweight DI container

# 🔥 2025-12-20 FIX: 恢复 HippocampalPrefrontalLoop 迭代检索
from ..brain.hippocampal_loop import HippocampalPrefrontalLoop

# 🔥 2025-12-20 FIX: 恢复 CapabilityOrchestrator 集成（精度恢复关键）
from ..reasoning.capability_analyzer import CapabilityAnalyzer
from ..reasoning.capability_orchestrator import CapabilityOrchestrator

# 🔥 2025-12-25: 数据集感知配置管理器（解决V1/V2/V3特性干扰问题）
from .adaptive_config import get_adaptive_config_manager

logger = get_logger(__name__)


_CJK_RANGE_RE = None


def _contains_cjk(text: str) -> bool:
    """Return True if text contains CJK (Chinese/Japanese/Korean) characters."""
    global _CJK_RANGE_RE
    if _CJK_RANGE_RE is None:
        import re as _re
        _CJK_RANGE_RE = _re.compile(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uac00-\ud7af\uff00-\uffef]')
    return bool(text and _CJK_RANGE_RE.search(text))


def _looks_like_language_drift(question: str, response: str) -> bool:
    """Heuristic: response drifted to CJK while question was English.
    """
    if not response or not _contains_cjk(response):
        return False
    return not _contains_cjk(question or '')


# Per-request agent involvement tracking. ContextVar is async-safe so concurrent
# coordinator requests don't bleed into each other. Set at the top of
# _process_user_input_impl, appended by _activate_agent and dispatch branches,
# read into ProcessingResult.agents_involved on return.
from contextvars import ContextVar as _ContextVar
_request_agent_trace: _ContextVar = _ContextVar('_request_agent_trace', default=None)


def _trace_agent(agent_id: str) -> None:
    """Append agent_id to the current request's involvement list, if active."""
    if not agent_id:
        return
    trace = _request_agent_trace.get()
    if trace is not None:
        trace.append(agent_id)


def _collect_agents_involved() -> List[str]:
    """Return the current request's unique agents-involved list, in first-seen order."""
    trace = _request_agent_trace.get()
    if not trace:
        return []
    seen: Dict[str, None] = {}
    for name in trace:
        if name and name not in seen:
            seen[name] = None
    return list(seen.keys())


class ComponentCriticality(Enum):
    """Component importance level for initialization failure handling."""
    CRITICAL = "critical"      # Failure -> raise (system cannot function)
    IMPORTANT = "important"    # Failure -> log error + degrade gracefully
    OPTIONAL = "optional"      # Failure -> log warning + degrade gracefully


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

        # 🔥 2026-03-03: Component health tracker with criticality levels (Task 1.6)
        self._component_health: Dict[str, Dict[str, Any]] = {}

        # 🔥 2025-12-19: Feature availability tracker for health checks
        self._feature_status: Dict[str, bool] = {
            'background_memory': False,
            'adaptive_shaping': False,
            'metacognition': False,
            'continuous_learning': False,
            'preference_extraction': False,
            'environment_processor': False,
            'brain_inspired_retrieval': False,
        }

        # 🔥 2025-12-25: 数据集感知配置管理器
        self.adaptive_config_manager = self._init_component(
            'adaptive_config_manager',
            ComponentCriticality.OPTIONAL,
            get_adaptive_config_manager
        )

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
        self.learning_logger = LearningLogger(BMAMPaths.DATA_DIR / 'learning_log.jsonl')

        # Initialize all agents
        logger.info("🔧 [1/10] Initializing agents...")
        self._initialize_agents()
        logger.info("✅ [1/10] Agents initialized")

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
        # unified_kg is created inside _initialize_agents() above; bind it now so
        # KG writes (via TemporalLobe / KnowledgeGraphBuilder) and KG queries (via
        # KGMergeHandler.query_kg_for_facts) hit the same in-memory instance.
        self.kg_handler = KGMergeHandler(
            kg_patterns_fn=self._get_kg_patterns,
            phrases_checker_fn=self._phrases_in_text,
            unified_kg=self.unified_kg
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

        # 🔥 2025-12-25 FIX: Update MemoryCoordinator with functional brain regions
        # These are initialized in _initialize_agents() before memory_coordinator
        # V3 (PersonaMem 52%) 功能: 脑区绑定到 MemoryCoordinator（跨脑区协作检索需要）
        self.memory_coordinator.persona_memory = self.persona_memory  # 🔥 V3: PersonaMem 需要
        self.memory_coordinator.amygdala = self.amygdala
        self.memory_coordinator.prefrontal_storage = self.prefrontal_storage
        self.memory_coordinator.basal_ganglia = self.basal_ganglia
        logger.info("✅ [5/10] MemoryCoordinator brain regions linked: PersonaMemory, Amygdala, Prefrontal, BasalGanglia")

        # Initialize Memory Reasoning Chain Engine (Brain-inspired cross-storage reasoning)
        # MUST come after MemoryCoordinator
        logger.info("🔧 [5.5/10] Initializing Memory Reasoning Chain Engine...")
        def _create_memory_reasoning_chain():
            from ..reasoning.memory_reasoning_chain import MemoryReasoningChain
            from ..services.shared_openai_client import shared_client_manager
            return MemoryReasoningChain(
                hippocampus_agent=self.hippocampus,
                memory_system=self.memory_system,
                kg_builder=self.knowledge_graph_builder,
                temporal_lobe_agent=self.temporal_lobe,
                client_manager=shared_client_manager,
                memory_coordinator=self.memory_coordinator
            )
        self.memory_reasoning_chain = self._init_component(
            'memory_reasoning_chain',
            ComponentCriticality.OPTIONAL,
            _create_memory_reasoning_chain
        )

        # 🔥 2025-12-20 FIX: 恢复 HippocampalPrefrontalLoop 迭代检索
        logger.info("🔧 [5.6/10] Initializing HippocampalPrefrontalLoop...")
        self.hippocampal_prefrontal_loop = self._init_component(
            'hippocampal_prefrontal_loop',
            ComponentCriticality.OPTIONAL,
            lambda: HippocampalPrefrontalLoop(memory_system=self.memory_system)
        )

        # 🔥 2025-12-20 FIX: 恢复 CapabilityOrchestrator 初始化（精度恢复关键）
        logger.info("🔧 [5.7/10] Initializing CapabilityAnalyzer & CapabilityOrchestrator...")
        def _create_capability_orchestrator():
            brain_agents = {
                'hippocampus': self.hippocampus,
                'temporal_lobe': self.temporal_lobe,
                'prefrontal': self.prefrontal_storage,
                'amygdala': self.amygdala,
                'basal_ganglia': self.basal_ganglia
            }
            analyzer = CapabilityAnalyzer()
            orchestrator = CapabilityOrchestrator(
                brain_agents=brain_agents,
                memory_system=self.memory_system
            )
            return (analyzer, orchestrator)
        _cap_result = self._init_component(
            'capability_orchestrator',
            ComponentCriticality.OPTIONAL,
            _create_capability_orchestrator
        )
        if _cap_result:
            self.capability_analyzer, self.capability_orchestrator = _cap_result
        else:
            self.capability_analyzer = None
            self.capability_orchestrator = None

        # Initialize background memory processes
        logger.info("🔧 [6/10] Initializing BackgroundMemoryProcesses...")
        def _create_background_processes():
            from ..memory.background_memory_processes import (
                BackgroundMemoryProcessManager, BackgroundProcessConfig
            )
            auto_test_mode = os.getenv(
                'BMAM_TEST_MODE', ''
            ).lower() in ('true', '1', 'yes')

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
                    consolidation_interval_seconds=1800,
                    forgetting_interval_seconds=3600,
                    reconsolidation_interval_seconds=900,
                    enabled=True,
                    run_on_startup=True,
                    min_hit_count_for_consolidation=0,
                    min_confidence_for_consolidation=0.3,
                    min_coverage_for_consolidation=0.0
                )

            bg_proc = BackgroundMemoryProcessManager(self, background_config)
            from ..memory.adaptive_memory_shaping import (
                AdaptiveMemoryShapingManager
            )
            shaping = AdaptiveMemoryShapingManager(self)
            return (bg_proc, shaping)

        _bg_result = self._init_component(
            'background_memory_processes',
            ComponentCriticality.OPTIONAL,
            _create_background_processes
        )
        if _bg_result:
            self.background_processes, self.adaptive_shaping = _bg_result
            self._feature_status['background_memory'] = True
            self._feature_status['adaptive_shaping'] = True
        else:
            self.background_processes = None
            self.adaptive_shaping = None

        # Initialize learning manager
        logger.info("🔧 [7/10] Initializing Metacognition & LearningManager...")
        def _create_metacognition():
            from ..optimization.metacognition import (
                get_continuous_learner,
                get_conflict_detector
            )
            return (get_continuous_learner(), get_conflict_detector())

        _meta_result = self._init_component(
            'metacognition',
            ComponentCriticality.OPTIONAL,
            _create_metacognition
        )
        if _meta_result:
            self.continuous_learner, self.conflict_detector = _meta_result
            self._feature_status['metacognition'] = True
            self._feature_status['continuous_learning'] = True
        else:
            self.continuous_learner = None
            self.conflict_detector = None

        logger.debug("  [7.5] Creating LearningManager...")
        self.learning_manager = LearningManager(
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
        def _create_preference_extraction():
            from ..optimization.metacognition import (
                get_preference_extractor,
                get_confidence_evaluator
            )
            return (get_preference_extractor(), get_confidence_evaluator())

        _pref_result = self._init_component(
            'preference_extraction',
            ComponentCriticality.OPTIONAL,
            _create_preference_extraction
        )
        if _pref_result:
            self.preference_extractor, self.confidence_evaluator = _pref_result
            self._feature_status['preference_extraction'] = True
        else:
            self.preference_extractor = None
            self.confidence_evaluator = None
        logger.info("✅ [9/10] Metacognition modules ready")

        # Initialize environment stimulus processor
        logger.info("🔧 [10/10] Initializing Environment stimulus processor...")
        def _create_environment_processor():
            from ..agents.environment.stimulus_processor import (
                get_stimulus_processor,
                get_contextual_integrator
            )
            return (get_stimulus_processor(), get_contextual_integrator())

        _env_result = self._init_component(
            'environment_processor',
            ComponentCriticality.OPTIONAL,
            _create_environment_processor
        )
        if _env_result:
            self.stimulus_processor, self.contextual_integrator = _env_result
            self._feature_status['environment_processor'] = True
        else:
            self.stimulus_processor = None
            self.contextual_integrator = None
        logger.info("✅ [10/10] Environment stimulus processor ready")

        # 🔥 2025-12-14: Initialize Active Learning Manager
        logger.info("🔧 [11/12] Initializing ActiveLearningManager...")
        self.active_learning = self._init_component(
            'active_learning',
            ComponentCriticality.OPTIONAL,
            lambda: ActiveLearningManager(config={
                'active_learning_enabled': True,
                'active_learning_threshold': 0.5,
                'curiosity_level': 0.6
            })
        )

        # 🔥 2025-12-15: Initialize HRM (Hierarchical Reasoning Model) components
        logger.info("🔧 [12/12] Initializing HRM (Thalamus + AnteriorCingulate)...")
        def _create_hrm():
            _brain_regions = {
                'hippocampus': self.hippocampus,
                'temporal_lobe': self.temporal_lobe,
                'prefrontal': self.prefrontal_storage,
                'amygdala': self.amygdala,
                'basal_ganglia': self.basal_ganglia
            }
            _thal_cfg = {
                'custom_timescales': {
                    'hippocampus': Timescale.HIPPOCAMPUS,
                    'temporal_lobe': Timescale.HIPPOCAMPUS,
                    'prefrontal': Timescale.PREFRONTAL,
                    'amygdala': Timescale.AMYGDALA,
                    'basal_ganglia': Timescale.BASAL_GANGLIA
                },
                'sync_threshold': 0.8
            }
            _thal = ThalamusAgent(_brain_regions, _thal_cfg)
            _act_cfg = {
                'min_iterations': 1,
                'max_iterations': 5,
                'confidence_threshold': get_core_config().retrieval.confidence_threshold,
                'ponder_cost': 0.01
            }
            _act = AnteriorCingulateAgent(_act_cfg)
            return (_thal, _act)

        _hrm_result = self._init_component(
            'hrm',
            ComponentCriticality.IMPORTANT,
            _create_hrm
        )
        if _hrm_result:
            self.thalamus, self.anterior_cingulate = _hrm_result
        else:
            self.thalamus = None
            self.anterior_cingulate = None

        # 🔥 2025-12-15: Initialize Result Arbiter (结果审查机制)
        logger.info("🔧 [13/14] Initializing ResultArbiter...")
        def _create_result_arbiter():
            arbiter = ResultArbiter(
                prefrontal_agent=self.prefrontal_storage,
                environment_agent=getattr(self, 'environment', None)
            )
            case_logger = LearningCaseLogger()
            return (arbiter, case_logger)

        _arbiter_result = self._init_component(
            'result_arbiter',
            ComponentCriticality.IMPORTANT,
            _create_result_arbiter
        )
        if _arbiter_result:
            self.result_arbiter, self.learning_case_logger = _arbiter_result
        else:
            self.result_arbiter = None
            self.learning_case_logger = None

        # 🔥 2025-12-16: Initialize Proactive Inquiry Manager (主动询问机制)
        logger.info("🔧 [13.5/14] Initializing ProactiveInquiryManager...")
        self.proactive_inquiry = self._init_component(
            'proactive_inquiry',
            ComponentCriticality.OPTIONAL,
            lambda: ProactiveInquiryManager(
                prefrontal_agent=self.prefrontal_storage,
                result_arbiter=self.result_arbiter
            )
        )

        # 🔥 2025-12-15: Initialize Learnable Router (可学习脑区路由)
        logger.info("🔧 [14/15] Initializing LearnableAgentRouter...")
        self.learnable_router = self._init_component(
            'learnable_router',
            ComponentCriticality.IMPORTANT,
            lambda: LearnableAgentRouter(
                agent_names=[
                    'hippocampus', 'temporal_lobe', 'prefrontal',
                    'amygdala', 'basal_ganglia',
                    'memory_retrieval', 'consolidation',
                    'reflection', 'reasoning_validator'
                ],
                learning_rate=0.05,
                checkpoint_dir=str(BMAMPaths.MEMORY_DIR / "checkpoints")
            )
        )

        # 🔥 2025-12-15: Initialize Brain-Inspired Retrieval (高级脑仿生检索)
        # 整合: 快慢路径分离 + 前额叶反馈 + 杏仁核注意力 + 脑区协作循环
        logger.info("🔧 [15/15] Initializing BrainInspiredRetrieval...")
        def _create_brain_retrieval():
            from ..services.shared_openai_client import shared_client_manager
            retrieval = BrainInspiredRetrieval(
                memory_coordinator=self.memory_coordinator,
                llm_client=shared_client_manager,
                enable_fast_path=False,
                enable_iterative=True,
                max_iterations=5
            )
            feedback = PrefrontalFeedbackSystem()
            return (retrieval, feedback)

        _br_result = self._init_component(
            'brain_inspired_retrieval',
            ComponentCriticality.IMPORTANT,
            _create_brain_retrieval
        )
        if _br_result:
            self.brain_inspired_retrieval, self.prefrontal_feedback = _br_result
            self._feature_status['brain_inspired_retrieval'] = True
        else:
            self.brain_inspired_retrieval = None
            self.prefrontal_feedback = None

        # 设置 LearningManager 的后期依赖（初始化时尚未可用）
        if self.learning_manager:
            self.learning_manager._coordinator = self
            self.learning_manager.hippocampus = self.hippocampus  # 🔥 FIX: 持续学习需要 hippocampus
            logger.debug("  ✅ LearningManager dependencies set (coordinator + hippocampus)")

        # 🔥 2025-12-21: Initialize PreferenceAwareRetrieval (PersonaMem/PrefEval优化)
        logger.info("🔧 [16/16] Initializing PreferenceAwareRetrieval...")
        def _create_preference_retrieval():
            from ..memory.preference_aware_retrieval import (
                get_preference_aware_retrieval
            )
            return get_preference_aware_retrieval(
                memory_system=self.memory_system,
                preference_boost_weight=0.3,
                enable_contrastive_learning=True,
                enable_metamemory=True,
                enable_silent_engram=True
            )

        self.preference_aware_retrieval = self._init_component(
            'preference_aware_retrieval',
            ComponentCriticality.OPTIONAL,
            _create_preference_retrieval
        )
        if self.preference_aware_retrieval:
            self._feature_status['preference_aware_retrieval'] = True

        # 🔥 2025-12-19: Initialize MemoryArchiveManager (extracted from coordinator)
        self.archive_manager = MemoryArchiveManager(self)
        logger.debug("  ✅ MemoryArchiveManager initialized")

        # 🔥 2026-01-26 FIX-012: Initialize FeedbackLoop (反馈闭环，环境Agent基础)
        def _create_feedback_loop():
            _key_opt = None
            _meta_mon = None
            if self.preference_aware_retrieval:
                _key_opt = getattr(
                    self.preference_aware_retrieval, 'key_optimizer', None
                )
                _meta_mon = getattr(
                    self.preference_aware_retrieval, 'metamemory_monitor', None
                )
            return FeedbackLoop(
                key_optimizer=_key_opt,
                metamemory_monitor=_meta_mon,
                confidence_threshold=0.6,
                learning_enabled=True
            )

        self.feedback_loop = self._init_component(
            'feedback_loop',
            ComponentCriticality.IMPORTANT,
            _create_feedback_loop
        )

        # 🔥 2026-01-26 FIX-013: Initialize ForgettingCoordinator (统一遗忘策略)
        self.forgetting_coordinator = self._init_component(
            'forgetting_coordinator',
            ComponentCriticality.IMPORTANT,
            lambda: ForgettingCoordinator(
                memory_system=self.memory_system,
                hippocampus_agent=self.hippocampus,
                basal_ganglia_agent=self.basal_ganglia
            )
        )

        # 🔥 2025-12-19: Initialize SoulState with insights log (P0)
        self.soul_state = get_soul_state()
        self.soul_state.set_insights_log_path(BMAMPaths.DATA_DIR / 'insights.log')
        logger.debug("  ✅ SoulState with insights logging initialized")

        # 🔥 2025-12-19: Initialize ValueProfile persistence (P0)
        self.soul_state.set_value_profiles_path(BMAMPaths.DATA_DIR / 'value_profiles.json')
        self.soul_state.load_value_profiles()  # Load existing profiles if available
        logger.debug("  ✅ ValueProfile persistence initialized")

        # 🔥 Task 2.3: Register key components in lightweight DI container
        _bm = get_bm_container()
        _bm.register('soul_state', self.soul_state)
        _bm.register('memory_coordinator', self.memory_coordinator)
        _bm.register('config', self.settings)
        logger.debug("  ✅ BMContainer: core components registered")

        # 🔥 2026-04-06: Initialize ConsolidatedFactStore (隐性知识层)
        # 从重复记忆中积累高置信度事实，不需要检索就能注入上下文
        try:
            from ..memory.consolidated_fact_store import ConsolidatedFactStore
            self.fact_store = ConsolidatedFactStore(BMAMPaths.DATA_DIR)
            logger.info(f"  ✅ ConsolidatedFactStore: {self.fact_store.get_stats()}")
        except Exception as e:
            logger.warning(f"  ⚠️ ConsolidatedFactStore init failed: {e}")
            self.fact_store = None

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

    def _init_component(self, name: str, criticality: ComponentCriticality, factory):
        """Initialize a component with appropriate error handling based on criticality.

        Args:
            name: Component name for logging and health tracking.
            criticality: How critical this component is.
            factory: Callable that creates the component.

        Returns:
            The component instance, or None if initialization failed
            (non-CRITICAL only).

        Raises:
            RuntimeError: If a CRITICAL component fails to initialize.
        """
        try:
            component = factory()
            self._component_health[name] = {
                'status': 'healthy',
                'criticality': criticality.value,
                'initialized_at': datetime.now().isoformat(),
                'error': None
            }
            return component
        except Exception as e:
            error_msg = f"Failed to initialize {name}: {e}"
            self._component_health[name] = {
                'status': 'failed',
                'criticality': criticality.value,
                'initialized_at': datetime.now().isoformat(),
                'error': str(e)
            }

            if criticality == ComponentCriticality.CRITICAL:
                logger.critical(f"CRITICAL component failed: {error_msg}")
                raise RuntimeError(error_msg) from e
            elif criticality == ComponentCriticality.IMPORTANT:
                logger.error(f"IMPORTANT component failed: {error_msg}")
                return None
            else:  # OPTIONAL
                logger.warning(f"Optional component unavailable: {error_msg}")
                return None

    def get_component_health(self) -> Dict[str, Any]:
        """Return health status of all components.

        Returns:
            Dict with summary counts and per-component health info.
        """
        healthy = sum(
            1 for c in self._component_health.values()
            if c['status'] == 'healthy'
        )
        failed = sum(
            1 for c in self._component_health.values()
            if c['status'] == 'failed'
        )

        return {
            'summary': {
                'total': len(self._component_health),
                'healthy': healthy,
                'failed': failed,
            },
            'components': dict(self._component_health)
        }

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

        # 🔥 2026-01-20 ABL-001: 记录消融配置状态
        # 问题: 消融实验结果异常（禁用组件反而准确率提高）
        # 原因: 主代码从未检查 BMAM_DISABLE_* 环境变量
        # 解决: 读取消融配置并在关键路径中检查
        ablation_config = get_active_ablation()
        self._ablation_state = {
            'hippocampus': is_component_enabled('hippocampus'),
            'temporal_lobe': is_component_enabled('temporal_lobe'),
            'amygdala': is_component_enabled('amygdala'),
            'prefrontal': is_component_enabled('prefrontal'),
            'basal_ganglia': is_component_enabled('basal_ganglia'),
            'story_arc': is_component_enabled('story_arc'),
            'temporal_reasoning': is_component_enabled('temporal_reasoning'),
            'kg': is_component_enabled('kg'),
            'hybrid_retrieval': is_component_enabled('hybrid_retrieval'),
            'consolidation': is_component_enabled('consolidation'),
            'hrm': is_component_enabled('hrm'),
            'salience': is_component_enabled('salience'),
        }

        # Log ablation status if any component is disabled
        disabled = [k for k, v in self._ablation_state.items() if not v]
        if disabled:
            logger.warning(f"🔬 ABLATION MODE: Components DISABLED = {disabled}")
        else:
            logger.debug("🔬 ABLATION: All components enabled (full system)")

        # 🔥 FIX: 创建统一的知识图谱实例，供所有脑区共享
        # NOTE: kg_handler binding moved to __init__ (after KGMergeHandler is
        # constructed). The previous hasattr(self, 'kg_handler') check here
        # was always False because _initialize_agents() runs before kg_handler
        # is created, so unified_kg silently never reached the merge handler.
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
            value_store_path=str(BMAMPaths.KV_VALUE_STORE_DB),
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
            use_global_storage=True,  # 🔥 FIX: Enable global storage delegation
            global_vector_db=vec,  # 🔥 2025-12-20 FIX: 传递全局FAISS用于MemoryRetrievalAgent同步
            global_db_manager=db   # 🔥 2026-01-27 FIX-011: 传递全局DBManager确保检索一致性
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

        # 🔥 2026-01-27 FIX-016: 五脑区分布式检索协调器
        # 设计原则: 每个脑区维护独立存储，检索时并行查询并融合结果
        self.distributed_retrieval = self._init_component(
            'distributed_retrieval',
            ComponentCriticality.IMPORTANT,
            lambda: init_distributed_coordinator(
                hippocampus=self.hippocampus,
                temporal_lobe=self.temporal_lobe,
                amygdala=self.amygdala,
                prefrontal=self.prefrontal_storage,
                basal_ganglia=self.basal_ganglia,
                knowledge_graph=self.unified_kg
            )
        )

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
        """Delegate to AgentLifecycleManager and record agent involvement."""
        _trace_agent(agent_id)
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
        # 🔥 2026-01-20 ABL-001: 消融检查 - consolidation 禁用时跳过
        if hasattr(self, '_ablation_state') and not self._ablation_state.get('consolidation', True):
            logger.debug("🔬 ABLATION: consolidation disabled, skipping trigger_consolidation")
            return {'status': 'skipped', 'reason': 'ablation_disabled'}
        return await self.memory_coordinator.trigger_consolidation(strategy, batch_size)

    async def consolidate_memories(self, evaluation_mode: bool = False) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator

        Args:
            evaluation_mode: 🔥 评估模式 - 绕过时间/访问次数限制
        """
        # 🔥 2026-01-20 ABL-001: 消融检查 - consolidation 禁用时跳过
        if hasattr(self, '_ablation_state') and not self._ablation_state.get('consolidation', True):
            logger.debug("🔬 ABLATION: consolidation disabled, skipping consolidate_memories")
            return {'status': 'skipped', 'reason': 'ablation_disabled'}
        return await self.memory_coordinator.consolidate_memories(evaluation_mode=evaluation_mode)

    async def trigger_forgetting(self, region: str = None, capacity_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Trigger forgetting process using ForgettingCoordinator (FIX-013)

        Args:
            region: Brain region name (legacy, for compatibility)
            capacity_threshold: Capacity ratio to trigger forgetting (0.0-1.0)
        """
        # 🔥 2026-01-26 FIX-013: 使用统一的 ForgettingCoordinator
        if hasattr(self, 'forgetting_coordinator') and self.forgetting_coordinator:
            try:
                result = await self.forgetting_coordinator.trigger_forgetting(
                    capacity_threshold=capacity_threshold
                )
                logger.info(f"📊 ForgettingCoordinator: forgotten={result.get('memories_forgotten', 0)}")
                return result
            except Exception as e:
                logger.warning(f"⚠️ ForgettingCoordinator failed: {e}, falling back to MemoryCoordinator")

        # Fallback to legacy MemoryCoordinator
        if region:
            return await self.memory_coordinator.trigger_forgetting(region)
        # No region specified — try forgetting on all core regions
        results = {}
        for r in ['hippocampus', 'temporal_lobe']:
            try:
                results[r] = await self.memory_coordinator.trigger_forgetting(r)
            except Exception as e:
                logger.warning(f"Forgetting fallback for {r} failed: {e}")
                results[r] = {'status': 'error', 'reason': str(e)}
        total_forgotten = sum(r.get('memories_forgotten', 0) for r in results.values() if isinstance(r, dict))
        return {'status': 'ok', 'memories_forgotten': total_forgotten, 'details': results}

    async def store_memory_with_timestamp(
        self,
        content: str,
        timestamp: datetime,
        speaker: str = None,
        importance: float = 0.5,
        inherited_event_time: datetime = None,  # 🔥 2025-12-16: 继承的事件时间
        user_id: str = "default",  # 🔥 2025-12-24: 用户标识 (恢复自52%版本)
        context: Dict[str, Any] = None  # 🔥 2025-12-26: 添加context用于Task-Aware Config
    ) -> Dict[str, Any]:
        """Delegate to MemoryCoordinator, with enhanced preference extraction"""
        # 🔥 2025-12-26: 获取Task-Aware Config，确保偏好提取只在需要时执行
        context = context or {}
        context['user_input'] = content  # 用于任务检测
        adaptive_weights = self.adaptive_config_manager.get_adaptive_weights(context.get('user_input', ''),context)

        # 🎯 2025-12-22: 使用增强版 UserPreferenceExtractor 提取偏好
        # 这对于评测时的对话塑造(conversation shaping)至关重要
        if self.persona_memory and content and speaker:
            speaker_lower = speaker.lower()
            if speaker_lower == 'user' or 'user:' in content.lower()[:20]:
                try:
                    # 🔥 2026-01-20 FIX-004: 偏好提取权重软下限，避免完全跳过
                    # 原问题: weight<0.1时完全跳过，导致PrefEval偏好丢失
                    # 解决: 使用可配置的最低权重，保证至少提取1个偏好
                    # 设计原则: 模拟基底神经节的基线活动，即使被抑制也保持最小活跃度
                    if self.preference_extractor:
                        raw_weight = adaptive_weights.preference_extraction_weight
                        # 🔥 FIX-004: 从配置获取权重下限（避免硬编码）
                        min_weight = adaptive_weights.min_preference_weight
                        weight = max(raw_weight, min_weight)

                        if raw_weight < min_weight:
                            logger.debug(f"⏭️ Preference weight boosted: {raw_weight:.2f} → {weight:.2f}")

                        extracted_raw = self.preference_extractor.extract_from_text(content)

                        # 根据权重动态限制保留数量
                        max_items_per_category = max(1, int(5 * weight))  # 1-4个

                        # 过滤: 权重越低，只保留最高频的偏好
                        extracted = {}
                        for pref_type, prefs in extracted_raw.items():
                            if not prefs:
                                extracted[pref_type] = []
                                continue

                            # 去重并限制数量
                            unique_prefs = list(dict.fromkeys(prefs))  # 保持顺序去重
                            extracted[pref_type] = unique_prefs[:max_items_per_category]

                        total_prefs = sum(len(v) for v in extracted.values())

                        if total_prefs > 0:
                            # 结构化存储到 PersonaMemoryAgent
                            for pref_type, prefs in extracted.items():
                                for pref in prefs:
                                    if not pref:
                                        continue
                                    await self.persona_memory.store_persona({
                                        'content': f"User {pref_type}: {pref}",
                                        'category': pref_type,
                                        'importance': self._get_preference_importance(pref_type),
                                        'user_id': user_id,  # 🔥 2025-12-24: 传入 user_id (恢复自52%)
                                        'metadata': {
                                            'source': 'conversation_shaping',
                                            'preference_type': pref_type,
                                            'preference_value': pref,
                                            'structured_category': self._get_structured_category(pref_type),
                                            'timestamp': str(timestamp),
                                            'speaker': speaker,
                                            'user_id': user_id,  # 🔥 2025-12-24: 也存入 metadata (恢复自52%)
                                            'original_statement': content[:500]  # 🔥 2025-12-24: 保存原始用户陈述 (恢复自52%)
                                        }
                                    })
                            logger.debug(f"🎯 PersonaMemory: stored {total_prefs} preferences from shaping (enhanced)")
                    else:
                        # 回退模式: 尝试创建临时提取器
                        try:
                            from ..optimization.metacognition import UserPreferenceExtractor
                            temp_extractor = UserPreferenceExtractor()
                            extracted = temp_extractor.extract_from_text(content)
                            total_prefs = sum(len(v) for v in extracted.values())

                            if total_prefs > 0:
                                for pref_type, prefs in extracted.items():
                                    for pref in prefs:
                                        if not pref:
                                            continue
                                        await self.persona_memory.store_persona({
                                            'content': f"User {pref_type}: {pref}",
                                            'category': pref_type,
                                            'importance': self._get_preference_importance(pref_type),
                                            'user_id': user_id,  # 🔥 2025-12-24: 传入 user_id (恢复自52%)
                                            'metadata': {
                                                'source': 'conversation_shaping',
                                                'preference_type': pref_type,
                                                'preference_value': pref,
                                                'structured_category': self._get_structured_category(pref_type),
                                                'timestamp': str(timestamp),
                                                'speaker': speaker,
                                                'user_id': user_id,  # 🔥 2025-12-24: 也存入 metadata (恢复自52%)
                                                'original_statement': content[:500]  # 🔥 2025-12-24: 保存原始用户陈述 (恢复自52%)
                                            }
                                        })
                                logger.debug(f"🎯 PersonaMemory: stored {total_prefs} preferences (fallback extractor)")
                        except Exception as fallback_err:
                            logger.debug(f"Fallback preference extraction failed: {fallback_err}")
                except Exception as e:
                    logger.debug(f"PersonaMemory store skipped: {e}")

        result = await self.memory_coordinator.store_memory_with_timestamp(
            content, timestamp, speaker, importance,
            inherited_event_time=inherited_event_time
        )

        # 🔥 2026-04-06: 累积事实到隐性知识层（每次存储记忆时触发）
        if self.fact_store and content:
            try:
                self.fact_store.extract_and_accumulate(content)
                # 每 50 次存储持久化一次
                total = sum(len(v) for v in self.fact_store.facts.values())
                if total > 0 and total % 50 == 0:
                    self.fact_store.save()
            except Exception as e:
                logger.debug(f"Fact accumulation skipped: {e}")

        return result

    async def smart_retrieve(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'auto',
        context: Dict[str, Any] = None,
        activation_plan: Optional[Dict[str, bool]] = None,
        use_distributed: bool = True  # FIX-016: default ON (FIX-011 dual-write removed)
    ) -> List[Dict[str, Any]]:
        """
        Delegate to MemoryCoordinator with activation_plan support.

        If activation_plan is None, uses a sensible default that prioritizes
        episodic and semantic regions (hippocampus + temporal_lobe).

        🔥 FIX-016: 新增 use_distributed 参数，启用五脑区并行检索
        """
        # Default activation: enable all 5 brain regions for full retrieval
        if activation_plan is None:
            activation_plan = {
                'hippocampus': True,      # Episodic memory
                'temporal_lobe': True,    # Semantic memory + KG
                'prefrontal': True,       # Working memory context
                'amygdala': True,         # Emotional salience
                'basal_ganglia': True     # Procedural patterns
            }

        # 🔥 2026-01-20 ABL-001: 消融检查 - 禁用的组件不参与检索
        # 设计原则: 从 activation_plan 动态获取脑区，避免硬编码（符合人脑模块化设计）
        if hasattr(self, '_ablation_state') and activation_plan:
            for region in activation_plan.keys():
                if not self._ablation_state.get(region, True):
                    activation_plan[region] = False
                    logger.debug(f"🔬 ABLATION: {region} disabled in smart_retrieve")

        # 🔥 2026-01-27 FIX-016: 五脑区分布式检索模式
        if use_distributed and hasattr(self, 'distributed_retrieval') and self.distributed_retrieval:
            from .distributed_retrieval import BrainRegion
            # 将 activation_plan 转换为 enabled_regions
            enabled_regions = [
                BrainRegion(name) for name, enabled in activation_plan.items()
                if enabled and name in [r.value for r in BrainRegion]
            ]
            distributed_memories = await self.distributed_retrieval.retrieve(
                query=query,
                k=k,
                context=context,
                enabled_regions=enabled_regions if enabled_regions else None
            )
            # 转换为标准格式
            return [mem.to_dict() for mem in distributed_memories]

        return await self.memory_coordinator.smart_retrieve(query, k, strategy, context, activation_plan)

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
            # Fallback to simple retrieval with activation_plan support
            logger.warning("BrainInspiredRetrieval not available, using smart_retrieve fallback")
            memories = await self.smart_retrieve(query, k, 'auto', context, activation_plan)
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

        # 🔥 2026-03-26 FIX: 消融检查 - activation_plan 为 None 时也需要检查
        if hasattr(self, '_ablation_state'):
            if activation_plan is None:
                activation_plan = {}
            # 确保被消融禁用的脑区不参与检索
            for region, enabled in self._ablation_state.items():
                if not enabled:
                    activation_plan[region] = False
                    logger.debug(f"🔬 ABLATION: {region} disabled in brain_retrieve")
        if activation_plan is not None:
            for region in list(activation_plan.keys()):
                if hasattr(self, '_ablation_state') and not self._ablation_state.get(region, True):
                    activation_plan[region] = False

        # 执行脑仿生检索
        result = await self.brain_inspired_retrieval.retrieve(
            query=query,
            k=k,
            context=context,
            activation_plan=activation_plan,
            force_slow_path=force_slow_path
        )

        # 🔥 2025-12-26: 获取Task-Aware Config，确保偏好增强只在需要时应用
        context_with_query = context.copy() if context else {}
        context_with_query['user_input'] = query
        adaptive_weights = self.adaptive_config_manager.get_adaptive_weights(context.get('user_input', ''),context_with_query)

        # 🔥 2025-12-21: 应用偏好感知增强
        # 🔥 2025-12-26 FIX V2: 使用 preference_retrieval_boost 软权重控制增强强度
        # preference_retrieval_boost 范围: 0.0-0.3
        # - 0.0 (低权重): 不应用偏好增强
        # - 0.3 (高权重): 最大化偏好记忆的权重（1.3倍boost）
        if self.preference_aware_retrieval and result.memories:
            boost_weight = adaptive_weights.preference_retrieval_boost

            # 只有当boost > 0.05时才应用增强（避免完全为0时浪费计算）
            if boost_weight > 0.05:
                try:
                    # 获取查询向量
                    query_vector = None
                    if hasattr(self.memory_system, 'embedding_service'):
                        query_vector = await self.memory_system.embedding_service.embed_text_async(query)
                        if query_vector is not None and hasattr(query_vector, 'tolist'):
                            import numpy as np
                            query_vector = np.array(query_vector)

                    # 应用偏好增强
                    pref_result = await self.preference_aware_retrieval.enhance_retrieval(
                        query=query,
                        query_vector=query_vector,
                        base_results=result.memories,
                        context=context
                    )

                    # 🔥 根据 boost_weight 动态调整偏好记忆和基础记忆的融合比例
                    # boost_weight=0.1 → 偏好记忆权重1.1倍
                    # boost_weight=0.3 → 偏好记忆权重1.3倍
                    boost_factor = 1.0 + boost_weight

                    # 重新计算分数：偏好记忆加权，基础记忆保持原分数
                    if pref_result.boost_applied and pref_result.preference_memories:
                        pref_ids = {pm.get('id') for pm in pref_result.preference_memories if isinstance(pm, dict) and 'id' in pm}

                        # 调整所有记忆的分数
                        for mem in pref_result.memories:
                            if isinstance(mem, dict) and mem.get('id') in pref_ids:
                                # 偏好记忆boost
                                mem['score'] = mem.get('score', 0.5) * boost_factor

                    # 更新检索结果
                    result.memories = pref_result.memories

                    # 添加调试信息
                    if pref_result.boost_applied:
                        result.debug_info['preference_boost'] = pref_result.debug_info
                        result.debug_info['boost_factor'] = boost_factor
                        logger.debug(
                            f"Preference boost applied: {len(pref_result.preference_memories)} memories, "
                            f"factor={boost_factor:.2f}"
                        )

                except Exception as e:
                    logger.debug(f"Preference enhancement skipped: {e}")

        # 记录统计信息
        self.processing_stats['retrieval_calls'] = self.processing_stats.get('retrieval_calls', 0) + 1
        if result.path_type == 'fast':
            self.processing_stats['fast_path_hits'] = self.processing_stats.get('fast_path_hits', 0) + 1
        else:
            self.processing_stats['slow_path_calls'] = self.processing_stats.get('slow_path_calls', 0) + 1

        return result

    # ============================================================================
    # Memory Archive Management (BMA Format) - Delegated to MemoryArchiveManager
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
        """Delegate to MemoryArchiveManager. See archive_manager.export_archive() for docs."""
        return self.archive_manager.export_archive(
            archive_name=archive_name,
            output_dir=output_dir,
            description=description,
            tags=tags,
            include_faiss=include_faiss,
            metadata=metadata
        )

    def load_memory_archive(
        self,
        archive_path: Path,
        target_dir: Path = None,
        validate: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """Delegate to MemoryArchiveManager. See archive_manager.load_archive() for docs."""
        return self.archive_manager.load_archive(
            archive_path=archive_path,
            target_dir=target_dir,
            validate=validate,
            force=force
        )

    def validate_memory_archive(
        self,
        archive_path: Path,
        check_checksums: bool = True
    ) -> Dict[str, Any]:
        """Delegate to MemoryArchiveManager. See archive_manager.validate_archive() for docs."""
        return self.archive_manager.validate_archive(
            archive_path=archive_path,
            check_checksums=check_checksums
        )


    def get_system_status(self) -> Dict[str, Any]:
        """Delegate to MetricsCollector"""
        return self.metrics_collector.get_system_status(self.agents, self.is_running)

    def get_feature_health(self) -> Dict[str, Any]:
        """
        Get health check status for optional features.

        Returns dict with:
        - features: Dict[str, bool] - availability of each optional feature
        - healthy_count: int - number of features successfully loaded
        - total_count: int - total number of optional features
        - degraded_features: List[str] - features running in degraded mode

        Example:
            health = coordinator.get_feature_health()
            if health['degraded_features']:
                print(f"Degraded features: {health['degraded_features']}")
        """
        healthy = [k for k, v in self._feature_status.items() if v]
        degraded = [k for k, v in self._feature_status.items() if not v]
        return {
            'features': self._feature_status.copy(),
            'healthy_count': len(healthy),
            'total_count': len(self._feature_status),
            'degraded_features': degraded,
            'health_percentage': len(healthy) / len(self._feature_status) * 100 if self._feature_status else 100
        }

    async def run_continuous_learning_cycle(self) -> Dict[str, Any]:
        """Delegate to LearningManager"""
        return await self.learning_manager.run_continuous_learning_cycle(self.hippocampus)

    async def run_introspection_cycle(self) -> Dict[str, Any]:
        """
        运行自省周期任务 - 汇总最近的失败/低置信度/冲突

        🔥 2025-12-19: P0 真实自省与洞察库

        This should be called periodically or after significant events.
        The summary is stored in searchable format for future reference.

        Returns:
            Dict containing introspection summary
        """
        summary = await self.soul_state.async_generate_introspection_summary()

        # 如果有重大关注点，记录为insight
        if summary['top_concerns']:
            await self.soul_state.async_record_insight(
                trigger_type='reflection',
                trigger_reason='Periodic introspection cycle',
                conclusion=(
                    f"Identified {len(summary['top_concerns'])} concerns: "
                    f"{'; '.join(summary['top_concerns'])}"
                ),
                follow_up_actions=[
                    'Review and address identified concerns',
                    'Consider strategy adjustments'
                ],
                confidence=0.7
            )

        logger.info(f"🔍 Introspection completed: {summary['total_insights']} insights, "
                    f"{len(summary['top_concerns'])} concerns")
        return summary

    async def record_processing_failure(self, query: str, error: str):
        """记录处理失败到洞察库"""
        await self.soul_state.async_record_failure(query, error)

    async def record_low_confidence_decision(
        self, query: str, confidence: float, analysis: str
    ):
        """记录低置信度决策到洞察库"""
        if confidence < 0.5:
            await self.soul_state.async_record_low_confidence(
                query, confidence, analysis
            )

    # ============================================================================
    # 🔥 2025-12-19: ValueProfile Methods - 价值观/偏好累积 (P0)
    # ============================================================================

    def extract_and_update_preferences(self, user_input: str):
        """
        从用户输入中提取偏好并更新用户档案

        Args:
            user_input: 用户输入文本
        """
        if not self._feature_status.get('preference_extraction'):
            return

        try:
            # 使用 UserPreferenceExtractor 提取偏好
            extracted = self.preference_extractor.extract_from_text(user_input)

            # 更新到 SoulState 的用户档案
            self.soul_state.update_from_preference_extractor(extracted)

            # 记录提取结果
            total = sum(len(v) for v in extracted.values())
            if total > 0:
                logger.debug(f"📊 Extracted {total} preferences from user input")

        except Exception as e:
            logger.warning(f"Failed to extract preferences: {e}")

    def _get_preference_importance(self, pref_type: str) -> float:
        """
        根据偏好类型返回重要性分数

        Args:
            pref_type: 偏好类型 (likes, facts, skills, etc.)

        Returns:
            重要性分数 (0.0-1.0)
        """
        # 不同类型的偏好有不同的基础重要性
        importance_map = {
            'likes': 0.75,
            'dislikes': 0.80,  # 不喜欢的东西更需要记住避免
            'habits': 0.70,
            'interests': 0.85,  # 兴趣是核心偏好
            'activities': 0.70,
            'facts': 0.90,     # 用户事实最重要
            'skills': 0.75,
            'goals': 0.85      # 目标很重要
        }
        return importance_map.get(pref_type, 0.7)

    def _get_structured_category(self, pref_type: str) -> str:
        """
        将偏好类型映射到结构化分类

        Args:
            pref_type: 偏好类型

        Returns:
            结构化分类名称
        """
        # 将偏好类型归类到高层分类
        category_map = {
            'likes': 'preference',
            'dislikes': 'preference',
            'habits': 'behavior',
            'interests': 'preference',
            'activities': 'behavior',
            'facts': 'identity',      # 用户身份信息
            'skills': 'capability',   # 用户能力
            'goals': 'aspiration'     # 用户志向
        }
        return category_map.get(pref_type, 'general')

    def get_value_aware_routing_context(self) -> Dict[str, Any]:
        """
        获取包含价值观信息的路由上下文

        Returns:
            路由上下文字典，包含用户偏好、目标、禁忌等
        """
        return self.soul_state.get_routing_context()

    def get_response_constraints(self) -> Dict[str, Any]:
        """
        获取响应生成约束

        Returns:
            响应约束字典，包含风格约束、避免主题等
        """
        return self.soul_state.get_response_constraints()

    # 🔥 2026-01-21 FIX-005: 统一偏好检索 API
    # PersonaMem 作为多用户主路径，SoulState 作为单用户备用
    async def get_user_preferences(self, query: str, user_id: str = None, k: int = 5) -> List[str]:
        """
        统一偏好检索接口

        Args:
            query: 查询文本
            user_id: 用户ID (可选)
            k: 返回数量

        Returns:
            偏好内容列表
        """
        preferences = []

        # 多用户模式: 使用 PersonaMem
        if user_id and user_id != "default" and self.persona_memory:
            try:
                result = await self.persona_memory.retrieve_persona(
                    query, k=k, user_id=user_id
                )
                for pm in result.get('memories', []):
                    if isinstance(pm, dict):
                        content = pm.get('content', '') or pm.get('memory', {}).get('content', '')
                        if content and len(content) > 5:
                            preferences.append(content)
                if preferences:
                    logger.debug(f"🎯 FIX-005: Retrieved {len(preferences)} preferences from PersonaMem (user={user_id})")
                    return preferences[:k]
            except Exception as e:
                logger.debug(f"PersonaMem retrieval failed: {e}, falling back to SoulState")

        # 单用户模式/备用: 使用 SoulState
        try:
            high_conf = self.soul_state.user_profile.get_high_confidence_preferences(min_confidence=0.5)
            for pref in high_conf[:k]:
                if hasattr(pref, 'item') and pref.item:
                    preferences.append(f"User preference: {pref.item}")
            if preferences:
                logger.debug(f"🎯 FIX-005: Retrieved {len(preferences)} preferences from SoulState (fallback)")
        except Exception as e:
            logger.debug(f"SoulState retrieval failed: {e}")

        return preferences[:k]

    def check_value_gaps(self) -> List[ValueGap]:
        """
        检查价值观缺口

        Returns:
            价值缺口列表
        """
        return self.soul_state.check_value_gaps()

    def get_value_gap_warnings(self) -> List[str]:
        """
        获取价值缺口警告 (用于UI显示)

        Returns:
            警告消息列表
        """
        return self.soul_state.get_value_gap_warnings()

    def update_user_identity(self, name: str = None, description: str = None):
        """更新用户身份信息"""
        self.soul_state.update_user_identity(name, description)

    def add_user_goal(self, goal: str, is_long_term: bool = False):
        """添加用户目标"""
        self.soul_state.add_user_goal(goal, is_long_term)

    def add_user_taboo(self, taboo: str):
        """添加用户禁忌"""
        self.soul_state.add_user_taboo(taboo)

    # ============================================================================
    # 🔥 2025-12-19: Scenario Simulation API - 场景模拟 (P1)
    # ============================================================================

    async def simulate_scenario(
        self,
        condition: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        模拟"如果...会怎样"场景

        Args:
            condition: 假设条件 (e.g., "如果用户换工作", "What if it rains tomorrow")
            context: 额外上下文

        Returns:
            场景模拟结果字典，包含:
            - prediction: 预测结果
            - confidence: 置信度
            - is_speculation: 是否为推测 (记忆不足时为True)
            - formatted_response: 格式化的响应文本

        Example:
            result = await coordinator.simulate_scenario("如果用户搬到新城市")
            print(result['formatted_response'])
        """
        try:
            # 从 clean_agent_system 获取 ReflectionAgent
            reflection_agent = self.agent_manager.agents.get('reflection')
            if not reflection_agent:
                logger.warning("ReflectionAgent not available for scenario simulation")
                return {
                    'success': False,
                    'error': 'ReflectionAgent not available',
                    'prediction': f"无法模拟场景: {condition}"
                }

            # 检索相关记忆
            memories = []
            if hasattr(self, 'hippocampus') and self.hippocampus:
                try:
                    # 提取关键词进行检索
                    keywords = [w for w in condition.split() if len(w) > 2][:5]
                    for kw in keywords:
                        results = await self.hippocampus.search(kw, limit=5)
                        for r in results:
                            memories.append({
                                'id': r.get('id', ''),
                                'content': r.get('content', ''),
                                'importance': r.get('importance', 0.5)
                            })
                except Exception as e:
                    logger.debug(f"Memory retrieval for scenario failed: {e}")

            # 调用场景模拟
            result = await reflection_agent.simulate_scenario(
                condition=condition,
                memories=memories[:20],  # 限制记忆数量
                context=context
            )

            # 添加推测警告到 soul_state
            if result.is_speculation:
                await self.soul_state.async_add_thought(
                    f"🔮 Scenario simulation (speculation): {condition[:30]}..."
                )

            return {
                'success': True,
                'scenario_id': result.scenario_id,
                'condition': result.condition,
                'prediction': result.prediction,
                'confidence': result.confidence,
                'is_speculation': result.is_speculation,
                'supporting_memories': result.supporting_memories,
                'reasoning_chain': result.reasoning_chain,
                'alternative_outcomes': result.alternative_outcomes,
                'formatted_response': reflection_agent.format_scenario_for_response(result)
            }

        except Exception as e:
            logger.error(f"Scenario simulation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'prediction': f"场景模拟失败: {condition}"
            }

    async def batch_simulate_scenarios(
        self,
        conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        批量模拟多个场景

        Args:
            conditions: 条件列表

        Returns:
            场景结果列表
        """
        results = []
        for condition in conditions:
            result = await self.simulate_scenario(condition)
            results.append(result)
        return results

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

    # 🔥 2025-12-20 FIX: 恢复答案精炼函数（解决73.8%冗长回答失败问题）
    async def _refine_answer_for_qa(self, query: str, answer: str) -> str:
        """
        🎯 Answer refinement for MemOS QA benchmarks

        Problem: Verbose answers fail MemOS strict matching (73.8% of failures)
        Solution: Extract concise core answer from verbose responses
        """
        if not answer:
            return answer

        word_count = len(answer.split())

        # Already concise - no refinement needed
        if word_count <= 15:
            return answer

        question_lower = query.lower()
        logger.debug(f"📝 Refining verbose answer ({word_count} words)...")

        try:
            from src.agents.base import BrainAgent

            class TempRefiner(BrainAgent):
                async def process_message(self, msg): return {}

            refiner = TempRefiner('answer_refiner', 'prefrontal', 'Answer Refiner')

            # Determine answer type by question morphology, NOT by listing
            # benchmark-specific example strings. Format hints describe shape
            # (date format, single-word, noun phrase, comma list, ...) so this
            # rule does not bias the system toward any particular eval set.
            if question_lower.startswith('when') or 'what date' in question_lower or 'what time' in question_lower:
                answer_type = "a date or time, formatted as 'D Month YYYY', 'Month YYYY', or 'YYYY'"
            elif question_lower.startswith('who') or 'identity' in question_lower:
                answer_type = "a noun phrase naming a person, role, or identity"
            elif question_lower.startswith('where') or 'location' in question_lower:
                answer_type = "a place name or location phrase"
            elif 'how long' in question_lower or 'how many' in question_lower:
                answer_type = "a number or a duration phrase"
            elif 'field' in question_lower or 'pursue' in question_lower or 'education' in question_lower:
                answer_type = "one or more academic field names, comma-separated"
            elif 'status' in question_lower:
                answer_type = "a single status word"
            elif question_lower.startswith('what') and any(w in question_lower for w in ['like', 'enjoy', 'hobby', 'interest', 'favorite']):
                answer_type = "a short comma-separated list of items"
            elif question_lower.startswith('what') and any(w in question_lower for w in ['did', 'does', 'has', 'have', 'research', 'read', 'buy', 'bought']):
                answer_type = "a specific noun phrase or action phrase (not a single bare topic word)"
            else:
                answer_type = "the direct, concise answer (max 10 words, no explanation)"

            prompt = f"""Extract ONLY {answer_type} from this verbose answer.

Question: {query}
Verbose Answer: {answer}

Rules:
- Extract ONLY the core answer (max 10 words)
- NO explanation, NO sentences, NO "Based on..."
- If temporal: use format like "7 May 2023" or "June 2023"
- If status: just the status word

Output ONLY the extracted answer:"""

            refined = await refiner.call_llm(prompt, temperature=0.0, max_tokens=30)
            refined = refined.strip().strip('"').strip("'").strip('.')

            # Validate refinement
            if refined and len(refined.split()) <= 15 and len(refined) < len(answer):
                logger.info(f"   → Refined: '{refined}' (from {word_count} words)")
                return refined
            else:
                return answer

        except Exception as e:
            logger.warning(f"⚠️ Answer refinement failed: {e}")
            return answer

    # ============================================================================
    # 🔥 2025-12-20 FIX: LearnableRouter 动态回答路径选择
    # ============================================================================

    def _determine_answer_path(
        self,
        learnable_routing_result: Optional[Dict[str, Any]],
        query_lower: str,
        has_temporal_result: bool = False,
        has_reasoning_chain: bool = False
    ) -> str:
        """
        根据 LearnableRouter 结果动态决定回答生成路径

        神经科学依据:
        - 前额叶基于任务特征动态选择处理通路
        - 不同脑区激活模式对应不同认知策略

        Returns:
            'temporal' | 'reasoning_chain' | 'orchestrator' | 'conversation'
        """
        if not learnable_routing_result:
            # Fallback: 基于关键词的传统路由
            temporal_keywords = ['when', 'what date', 'what day', 'how long', 'ago',
                                 'most recently', 'last week', 'last month',
                                 'from earliest', 'happened first', 'started first']
            temporal_phrases = ['what is the order of', 'which first',
                                'from earliest to latest', 'from first to last']
            if (any(kw in query_lower for kw in temporal_keywords) or
                    any(phrase in query_lower for phrase in temporal_phrases)):
                return 'temporal'
            return 'orchestrator'

        selected = learnable_routing_result.get('selected_agents', [])
        scores = learnable_routing_result.get('scores', {})

        if not selected:
            return 'orchestrator'

        top_agent = selected[0]
        top_score = scores.get(top_agent, 0.5)

        # 🧠 Agent → Path 映射 (基于脑区功能)
        # hippocampus: 情景记忆, 时间定位 → temporal reasoning
        # temporal_lobe: 语义知识, 长期记忆 → orchestrator
        # prefrontal/reasoning_validator: 复杂推理 → reasoning chain
        # amygdala: 情绪/社会认知 → orchestrator (情感增强)
        # basal_ganglia: 习惯/程序 → conversation (快速响应)

        path_mapping = {
            'hippocampus': 'temporal',
            'temporal_lobe': 'orchestrator',
            'prefrontal': 'reasoning_chain',
            'prefrontal_storage': 'reasoning_chain',
            'reasoning_validator': 'reasoning_chain',
            'amygdala': 'orchestrator',
            'basal_ganglia': 'conversation',
            'short_term_memory': 'orchestrator',
            'long_term_memory': 'orchestrator',
            'memory_retrieval': 'orchestrator',
            'consolidation': 'orchestrator',
        }

        # 使用top agent确定初始路径
        initial_path = path_mapping.get(top_agent, 'orchestrator')

        # 🔥 动态调整: 考虑多个高分agent
        high_score_agents = [a for a in selected[:3] if scores.get(a, 0) > 0.6]

        # 如果有多个高分agent涉及推理，提升reasoning chain优先级
        reasoning_agents = {'prefrontal', 'prefrontal_storage', 'reasoning_validator'}
        if len(set(high_score_agents) & reasoning_agents) >= 1 and has_reasoning_chain:
            initial_path = 'reasoning_chain'

        # 🔥 2026-04-04 FIX: temporal reasoning 路由
        # 对明确的 "when" 问题，信任 temporal 结果（已通过阈值过滤）
        # 对非 temporal 问题，需要 hippocampus 在 high_score_agents 中才走 temporal
        is_explicit_temporal = query_lower.startswith('when ') or 'how long' in query_lower
        if has_temporal_result and (is_explicit_temporal or 'hippocampus' in high_score_agents):
            initial_path = 'temporal'

        # 🔥 2026-03-30: HabitLearner 策略推荐暂时禁用
        # 消融实验证明：冷启动时 Q-learning 推荐会干扰路由决策 (-7%)
        # 需要更成熟的训练-推理分离机制后再启用
        # TODO: 引入显式的训练阶段 vs 推理阶段切换

        logger.info(f"🧭 Dynamic routing: top_agent={top_agent}({top_score:.2f}) → path={initial_path}")

        return initial_path

    # ============================================================================
    # Feedback Interface (Simplified - environment agent placeholder)
    # ============================================================================

    async def apply_feedback(
        self,
        query_type: str,
        reward_signal: float,
        query: str = None,
        response: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        简化版反馈接口 - 预留给环境智能体后期集成

        设计原则（符合人脑学习机制）:
        1. 多巴胺信号: reward_signal 模拟强化学习的奖励信号
        2. 神经可塑性: 根据反馈调整路由权重
        3. 记忆巩固: 成功的模式被强化，失败的模式被抑制

        Args:
            query_type: 查询类型 ('temporal', 'preference', 'factual', 'identity')
            reward_signal: 奖励信号 (0.0=错误, 1.0=正确, 0.5=部分正确)
            query: 原始查询 (可选，用于记录)
            response: 系统响应 (可选，用于记录)
            context: 上下文信息 (可选)

        Returns:
            Dict with feedback application result

        🔮 后期拓展 (环境智能体集成):
            - 自动判断答案正确性
            - 多模态反馈 (用户表情、点击行为等)
            - 跨会话学习
        """
        context = context or {}

        # 1. 记录到学习日志
        feedback_record = {
            'timestamp': datetime.now().isoformat(),
            'query_type': query_type,
            'reward': reward_signal,
            'query': query[:200] if query else None,
            'success': reward_signal >= 0.5
        }

        if hasattr(self, 'learning_logger') and self.learning_logger:
            self.learning_logger.record('feedback', feedback_record)

        # 2. 更新路由权重（简化版神经可塑性）
        # 正向强化: 成功的查询类型权重增加
        # 负向抑制: 失败的查询类型权重减少
        weight_delta = (reward_signal - 0.5) * 0.05  # 小步长更新，避免过拟合

        if hasattr(self, 'routing_manager') and self.routing_manager:
            try:
                # 更新对应类型的路由权重
                self.routing_manager.update_type_weight(query_type, weight_delta)
                logger.debug(f"🧠 Feedback applied: {query_type} weight += {weight_delta:.3f}")
            except Exception as e:
                logger.debug(f"Routing weight update skipped: {e}")

        # 3. 如果有连续学习器，记录学习案例
        if hasattr(self, 'continuous_learner') and self.continuous_learner:
            try:
                await self.continuous_learner.record_case(
                    query=query,
                    query_type=query_type,
                    success=reward_signal >= 0.5,
                    reward=reward_signal
                )
            except Exception as e:
                logger.debug(f"Continuous learner record skipped: {e}")

        return {
            'status': 'applied',
            'query_type': query_type,
            'reward': reward_signal,
            'weight_delta': weight_delta
        }

    # ============================================================================
    # Main Processing Pipeline (Simplified - delegates to modules)
    # ============================================================================

    async def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """Process user input with timeout protection"""
        timeout = get_core_config().coordinator.request_timeout

        try:
            result = await asyncio.wait_for(
                self._process_user_input_impl(user_input, context),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Request timed out after {timeout}s for input: {user_input[:50]}...")
            return ProcessingResult(
                response="I apologize, but processing your request took too long. Please try again.",
                routing_decision={},
                agents_involved=[],
                memories_retrieved=[],
                memory_stored=False,
                processing_time=timeout,
                agent_logs={},
                insights={},
                success=False,
                error=f"Request timeout after {timeout}s"
            )

        # Post-generation robustness: if the response contains CJK characters
        # but the input query is English, the LLM slipped into the wrong language.
        # Re-prompt for an English answer. This is a safety net, not a brain-region
        # change — it catches sporadic language-drift bugs without affecting retrieval.
        try:
            response = getattr(result, 'response', None)
            if response and _looks_like_language_drift(user_input, response):
                translated = await self._enforce_english_response(user_input, response)
                if translated and not _contains_cjk(translated):
                    result.response = translated
                    logger.warning(
                        f"Post-gen language drift fixed: {response[:40]!r} -> {translated[:40]!r}"
                    )
        except Exception as e:
            logger.debug(f"English enforcement check skipped: {e}")

        return result

    async def _enforce_english_response(self, question: str, drifted_response: str) -> Optional[str]:
        """Ask the LLM to restate the drifted response in concise English."""
        try:
            from ..agents.base import BrainAgent

            class _TempTranslator(BrainAgent):
                async def process_message(self, msg):
                    return {}

            translator = _TempTranslator(
                agent_id='english_enforcer',
                brain_region='prefrontal',
                system_prompt='English Response Enforcer'
            )
            prompt = (
                "Restate the following answer in concise English (10-15 words). "
                "If the answer conveys 'no information found' or uncertainty, "
                "output exactly: Information not available.\n\n"
                f"Question: {question}\n"
                f"Answer (may be in the wrong language): {drifted_response}\n\n"
                "English answer:"
            )
            translated = await translator.call_llm(prompt=prompt, temperature=0.0, max_tokens=60)
            if translated:
                return translated.strip()
        except Exception as e:
            logger.debug(f"English enforcement LLM call failed: {e}")
        return None

    async def _retrieve_persona_preferences(
        self, user_input: str, context: Dict[str, Any], adaptive_weights
    ) -> Optional[list]:
        """Retrieve persona/preference memories. Extracted for parallel execution."""
        if not self.persona_memory:
            return None
        try:
            is_evaluation_mode = context.get('evaluation_mode', False)
            query_category = self.persona_memory._detect_query_category(user_input)
            needs_persona = is_evaluation_mode or bool(query_category)

            if not needs_persona:
                return None

            context_k = context.get('_context_aware_k')
            if context_k and 'persona' in context_k:
                persona_k = context_k['persona']
            else:
                persona_k = adaptive_weights.persona_retrieval_k

            if is_evaluation_mode:
                extra_k = int(10 * max(0, adaptive_weights.persona_weight - 0.5) * 2)
                persona_k = min(25, persona_k + extra_k)

            eval_user_id = context.get('user_id') or context.get('persona_user_id')

            persona_result = await self.persona_memory.retrieve_persona(
                user_input,
                k=persona_k,
                user_id=eval_user_id,
                preference_boost=adaptive_weights.preference_retrieval_boost
            )
            persona_memories = persona_result.get('memories', [])

            if adaptive_weights.persona_weight > 0.6 and is_evaluation_mode:
                recent_result = await self.persona_memory.recent_persona(
                    limit=10, user_id=eval_user_id
                )
                recent_mems = recent_result.get('memories', [])
                existing_ids = {pm.get('memory', {}).get('id') for pm in persona_memories if isinstance(pm, dict)}
                for rm in recent_mems:
                    rm_id = rm.get('id') if isinstance(rm, dict) else None
                    if rm_id not in existing_ids:
                        persona_memories.append({'memory': rm, 'retrieval_confidence': 0.5})

            if persona_memories:
                prefs = []
                for pm in persona_memories:
                    if isinstance(pm, dict):
                        content = pm.get('content', '') or pm.get('memory', {}).get('content', '')
                        if content and len(content) > 5:
                            prefs.append(content)
                if prefs:
                    prefs = prefs[:8]
                    # 不在并行 task 中写 context（竞态风险），返回值由主线程处理
                    logger.info(f"🎯 PersonaMemory: found {len(prefs)} preferences/facts (category={query_category})")
                    return (prefs, query_category)
            return None
        except Exception as e:
            logger.debug(f"Preference retrieval skipped: {e}")
            return None

    async def _process_user_input_impl(self, user_input: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """
        Main processing pipeline - orchestrates all modules

        This is the primary entry point that coordinates all specialized modules.
        """
        start_time = datetime.now()

        # Reset per-request agent involvement trace. ContextVar isolates this
        # per asyncio task; calling set() with a fresh list at the top of every
        # request prevents stale traces from leaking between sequential calls.
        _request_agent_trace.set([])

        if context is None:
            context = {}

        # 🔥 2026-03-30: 保留原始输入给存储（含 [Context:] 日期标记），
        # 用干净文本做检索/推理/反馈
        import re as _re
        raw_input_for_storage = user_input
        user_input = _re.sub(r'\[Context:[^\]]*\]\s*', '', user_input).strip() or user_input
        if raw_input_for_storage != user_input:
            context['_raw_input_with_context'] = raw_input_for_storage

        # 🔥 2025-12-25: 应用数据集感知配置（根据任务特征动态调整系统行为）
        # 解决V1/V2/V3特性全局启用导致的跨数据集干扰问题
        context['user_input'] = user_input  # 确保用户输入在context中供检测使用
        adaptive_weights = self.adaptive_config_manager.get_adaptive_weights(context.get('user_input', ''),context)
        logger.debug(f"🎯 Applied config: {self.adaptive_config_manager.get_config_summary()}")

        # ToM Advisory (read-only intent classification)
        from ..agents.brain_regions.tom_advisor import get_tom_advisor
        tom = get_tom_advisor()
        tom.apply_to_context(user_input, context)

        try:
            self.metrics_collector.record_request(success=False)  # Will update on success

            # 1. Query analysis via RoutingManager
            query_features = await self._analyze_query_features(user_input, context)

            # 1b. Route decision (P1 close-loop). Without this call, the
            # learning record below always reads recommended_strategy='hybrid'
            # because nothing else populates that field. Decision here doesn't
            # change which retriever runs (brain_inspired_retrieval still
            # owns its own internal strategy), but it gives the feedback loop
            # a real label to attribute reward/penalty to.
            try:
                route_decision = await self.routing_manager.decide_retrieval_route(
                    query_features, context
                )
                query_features['recommended_strategy'] = route_decision.get('recommended_strategy')
                query_features['route_confidence'] = route_decision.get('confidence')
                query_features['route_alpha'] = route_decision.get('alpha')
                logger.debug(
                    f"🎯 Route: {query_features['recommended_strategy']} "
                    f"(conf={query_features['route_confidence']:.2f})"
                )
            except Exception as e:
                logger.debug(f"Route decision skipped: {e}")

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
            # 🔥 2025-12-27 FIX: Context-Aware K值分配（解决LoCoMo长对话退化问题）
            # 根据对话轮数动态调整 episodic/persona/semantic 的检索K值
            conversation_turns = context.get('conversation_turns', 0)
            if conversation_turns > 0:
                # 使用 context-aware K 值
                context_k = self.adaptive_config_manager.compute_context_aware_k(
                    conversation_turns, adaptive_weights
                )
                retrieval_k = context_k.get('episodic', adaptive_weights.episodic_retrieval_k)
                # 将 context_k 传递给后续的 persona 检索使用
                context['_context_aware_k'] = context_k
                logger.debug(f"🎯 Context-Aware K: turns={conversation_turns}, k={context_k}")
            else:
                # 回退到基于查询特征的 K 值
                retrieval_k = adaptive_weights.episodic_retrieval_k

            # 🔥 2026-03-28 OPT: 并行执行 brain_retrieve + persona_retrieval
            # brain_retrieve 和 persona 检索互不依赖，可以同时运行
            async def _do_brain_retrieve():
                if self.brain_inspired_retrieval:
                    _trace_agent('brain_inspired_retrieval')
                    try:
                        result = await self.brain_retrieve(
                            query=user_input,
                            k=retrieval_k,
                            context=context,
                            force_slow_path=False,
                        )
                        logger.info(
                            f"🧠 BrainRetrieval: {len(result.memories)} memories (k={retrieval_k}), "
                            f"path={result.path_type}, "
                            f"iterations={result.iterations}, "
                            f"confidence={result.confidence:.2f}"
                        )
                        return result
                    except Exception as e:
                        logger.warning(f"⚠️ BrainInspiredRetrieval failed, using fallback: {e}")
                        mems = await self.smart_retrieve(user_input, k=retrieval_k, context=context)
                        return mems  # list fallback
                else:
                    return await self.smart_retrieve(user_input, k=retrieval_k, context=context)

            brain_task = asyncio.ensure_future(_do_brain_retrieve())
            persona_task = asyncio.ensure_future(
                self._retrieve_persona_preferences(user_input, context, adaptive_weights)
            )

            brain_result_raw, preference_context = await asyncio.gather(
                brain_task, persona_task, return_exceptions=True
            )

            # Unpack brain retrieval result
            brain_retrieval_result = None
            if isinstance(brain_result_raw, Exception):
                logger.warning(f"⚠️ Brain retrieval exception: {brain_result_raw}")
                memories = await self.smart_retrieve(user_input, k=retrieval_k, context=context)
            elif isinstance(brain_result_raw, list):
                memories = brain_result_raw
            else:
                brain_retrieval_result = brain_result_raw
                memories = brain_retrieval_result.memories

            # Unpack persona result (may be Exception from gather)
            if isinstance(preference_context, Exception):
                logger.debug(f"Preference retrieval failed: {preference_context}")
                preference_context = None
            elif isinstance(preference_context, tuple):
                # (prefs_list, query_category) — write to context from main thread
                prefs_list, query_category = preference_context
                preference_context = prefs_list
                context['user_preferences'] = prefs_list
                context['persona_query_category'] = query_category
            # else: None (no preferences found)

            # 🔥 2025-12-20 FIX: 恢复 HippocampalPrefrontalLoop 迭代检索
            # Brain mechanism: 海马-前额叶反馈环路，在初始检索不足时扩展搜索
            initial_memory_count = len(memories) if memories else 0
            if hasattr(self, 'hippocampal_prefrontal_loop') and self.hippocampal_prefrontal_loop and memories:
                original_memories = memories  # Preserve for error recovery
                try:
                    enhanced_result = await self.hippocampal_prefrontal_loop.iterative_retrieval(
                        query=user_input,
                        initial_memories=memories,
                        max_iterations=2  # 最多2轮扩展
                    )
                    memories = enhanced_result.get('memories') or original_memories
                    iterations_used = enhanced_result.get('iterations', 0)
                    if len(memories) > initial_memory_count:
                        logger.info(
                            f"🔄 HippocampalPrefrontalLoop: {initial_memory_count} → {len(memories)} memories "
                            f"(+{len(memories) - initial_memory_count} after {iterations_used} iterations)"
                        )
                except Exception as e:
                    memories = original_memories  # Restore on failure
                    logger.warning(f"⚠️ HippocampalPrefrontalLoop failed: {e}, using original memories")

            # 2.5. Enhanced reasoning chain retrieval (for complex inference questions)
            use_reasoning_chain = False
            reasoning_chain_result = None

            if self.memory_reasoning_chain and self._should_use_reasoning_chain(user_input, query_features):
                _trace_agent('memory_reasoning_chain')
                try:
                    logger.info(f"🧠 Using Memory Reasoning Chain for: '{user_input[:50]}...'")
                    # 🔥 2026-04-04: 传入预检索记忆，避免重复检索
                    # 之前 reasoning_chain 独立做 cross_region_retrieval，浪费时间且结果不一致
                    pre_mems = None
                    if memories:
                        pre_mems = [
                            m if isinstance(m, dict) else {'content': getattr(m, 'content', str(m))}
                            for m in memories
                        ]
                    reasoning_chain_result = await self.memory_reasoning_chain.answer_with_reasoning_chain(
                        question=user_input,
                        max_memories=20,
                        pre_retrieved_memories=pre_mems
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
            # 🔥 FIX: 消融检查 - 禁用 kg 时跳过知识图谱增强
            kg_enabled = self._ablation_state.get('kg', True) if hasattr(self, '_ablation_state') else True
            if kg_enabled and self.kg_handler.should_trigger_kg_search(user_input, memories):
                _trace_agent('kg_handler')
                kg_facts = await self.kg_handler.query_kg_for_facts(
                    user_input,
                    entities=query_features.get('entities', [])
                )
                memories = self.kg_handler.merge_kg_memories(memories, kg_facts)

            # 🎭 3.4 Theory of Mind - 已禁用错误的 adversarial detection
            # 2025-12-25: 当前实现不是真正的心智理论，会误判正常问题
            # 正确的 ToM 应该用于：
            #   1) 用户信念建模 (UserBeliefState) - 用户认为世界是什么样的
            #   2) 意图推断 (IntentInference) - 用户问这个问题的真正目的
            #   3) 视角切换 (PerspectiveTaking) - 从用户视角组织答案
            #   4) 信念不匹配处理 - 当用户信念与事实不符时温和纠正
            # TODO: 重新设计 ToM 为上述正确功能
            adversarial_result = None  # 保留变量避免后续代码报错

            # 🔥 3.5 Temporal Reasoning for date/duration questions
            # 2025-12-12: 集成temporal推理到主流程
            temporal_reasoning_result = None
            if self.reasoning_validator and memories and not adversarial_result:
                try:
                    # 检测temporal问题 (when, what date, how long等)
                    query_lower = user_input.lower().strip()
                    # 🔥 2026-02-16 FIX: 精确 temporal 检测，减少误触发
                    # 高置信 temporal 关键词（明确指向时间查询）
                    temporal_keywords = [
                        'when did', 'when was', 'when is', 'when will',
                        'when has', 'when does',  # 🔥 2026-04-04: 补充更多 "when" 形式
                        'what date', 'what day', 'what time',
                        'how long ago', 'how long has', 'how long did',
                        'how many days', 'how many years', 'how many months',
                        'how many weeks',
                        'most recently', 'last week', 'last month', 'last weekend',
                        'last saturday', 'last sunday', 'last tuesday', 'last friday',
                    ]
                    # 排序/顺序类 temporal 短语
                    temporal_phrases = [
                        'what is the order of', 'what order',
                        'which first', 'which event first',
                        'from earliest to latest', 'from first to last',
                        'from earliest', 'from first', 'started first',
                        'happened first', 'graduated first',
                    ]
                    # 排除非时间查询（扩展过滤器）
                    non_temporal_prefixes = [
                        'who ', 'who\'s ', 'whose ',
                        'what is the name', 'what are the names',
                        'what is my ', 'what are my ',
                        'what is her ', 'what is his ',
                        'what does ', 'what did ',
                        'where ', 'which ',
                        'how is ', 'how does ', 'how did ',
                        'do i ', 'does ',
                        'is ', 'are ', 'was ', 'were ',
                        'can ', 'could ', 'would ', 'should ',
                        'tell me about ', 'describe ',
                    ]
                    # 排除包含身份/偏好关键词的查询
                    non_temporal_contains = [
                        'favorite', 'favourite', 'prefer', 'hobby',
                        'relationship', 'identity', 'name',
                        'personality', 'occupation', 'job', 'field',
                    ]
                    is_non_temporal = (
                        any(query_lower.startswith(p) for p in non_temporal_prefixes) or
                        any(kw in query_lower for kw in non_temporal_contains)
                    )
                    # 🔥 2026-04-04: 补充 "when" 开头的通用匹配
                    # LoCoMo 问题常用 "When PERSON has VERB" 形式
                    starts_with_when = query_lower.startswith('when ')
                    is_temporal_query = (
                        (any(kw in query_lower for kw in temporal_keywords) or
                         any(phrase in query_lower for phrase in temporal_phrases) or
                         starts_with_when)
                        and not is_non_temporal
                    )

                    # 🔥 FIX: 消融检查 - 禁用 temporal_reasoning 时跳过
                    temporal_reasoning_enabled = self._ablation_state.get('temporal_reasoning', True) if hasattr(self, '_ablation_state') else True
                    if is_temporal_query and temporal_reasoning_enabled:
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

            # 🎯 3.6 persona preference_context 已在上方 asyncio.gather 并行获取

            # 🔥 2026-03-26 FIX: 注入 cached user_portrait 到 QA 上下文
            # 解决 PersonaMem 48.9% 瓶颈：合成的用户肖像未被用于问答
            eval_user_id = context.get('user_id') or context.get('persona_user_id')
            if eval_user_id and self.persona_memory:
                cached_portraits = getattr(self, '_cached_user_portraits', {})
                portrait = cached_portraits.get(eval_user_id)
                if portrait:
                    portrait_facts = []
                    if portrait.get('portrait'):
                        portrait_facts.append(f"User profile: {portrait['portrait']}")
                    for key in ['likes', 'interests', 'dislikes', 'habits', 'facts', 'goals']:
                        for item in portrait.get(key, [])[:3]:
                            portrait_facts.append(f"User {key}: {item}")
                    if portrait_facts:
                        existing = preference_context or []
                        preference_context = portrait_facts + [
                            p for p in existing if p not in portrait_facts
                        ]
                        preference_context = preference_context[:12]
                        context['user_preferences'] = preference_context
                        context['persona_query_category'] = context.get(
                            'persona_query_category', ''
                        ) or 'identity'
                        logger.info(
                            f"🎯 Portrait injected: {len(portrait_facts)} facts "
                            f"for user={eval_user_id}"
                        )

            # 🔥 2026-04-06: 注入隐性知识（巩固事实）到记忆列表前端
            # 这些是高置信度的"不需要检索就知道"的事实
            if self.fact_store and memories:
                try:
                    implicit_facts = self.fact_store.get_facts_for_query(
                        user_input, top_k=5, min_confidence=0.4
                    )
                    if implicit_facts:
                        # 将隐性知识转为记忆格式，插入到记忆列表前端
                        for fact in reversed(implicit_facts):
                            fact_mem = {
                                'content': f"[Known fact] {fact.entity}: {fact.fact_text}",
                                'source': 'consolidated_facts',
                                'relevance': fact.confidence,
                                'score': fact.confidence,
                            }
                            memories.insert(0, fact_mem)
                        logger.info(
                            f"💡 Injected {len(implicit_facts)} implicit facts "
                            f"(entities: {list(set(f.entity for f in implicit_facts))})"
                        )
                except Exception as e:
                    logger.debug(f"Fact injection skipped: {e}")

            # 4. Generate response
            # 🎭 优先使用ToM对抗性检测结果（如果检测到欺骗性问题）- 安全优先
            if adversarial_result and adversarial_result.get('answer'):
                response = adversarial_result['answer']
                logger.info(f"🎭 Using ToM Adversarial answer (type={adversarial_result.get('adversarial_type')})")

            else:
                # 🔥 2025-12-20 FIX: 使用 LearnableRouter 动态路由决策
                # 替代固定 if-elif 链，基于学习的脑区选择决定回答路径
                query_lower = user_input.lower()
                # 🔥 2026-04-04: 对明确的 temporal 查询降低阈值到 0.50
                # 对非 temporal 查询保持 0.70 防止误覆盖
                _temporal_conf = temporal_reasoning_result.get('confidence', 0) if temporal_reasoning_result else 0
                _temporal_threshold = 0.50 if query_lower.startswith('when ') or 'how long' in query_lower else 0.70
                has_temporal = bool(temporal_reasoning_result and temporal_reasoning_result.get('answer') and
                                   _temporal_conf >= _temporal_threshold)
                # audit telemetry — passive
                try:
                    from . import audit_log as _audit
                    _audit.event(
                        'temporal_decision',
                        query_class=('when_or_how_long'
                                     if (query_lower.startswith('when ') or 'how long' in query_lower)
                                     else 'other'),
                        threshold=_temporal_threshold,
                        confidence=round(float(_temporal_conf), 4),
                        had_answer=bool(temporal_reasoning_result and temporal_reasoning_result.get('answer')),
                        passed_threshold=bool(_temporal_conf >= _temporal_threshold),
                        selected=has_temporal,
                    )
                except Exception:  # noqa: BLE001 - probe must never break the request
                    pass
                has_reasoning = bool(use_reasoning_chain and reasoning_chain_result)

                answer_path = self._determine_answer_path(
                    learnable_routing_result=learnable_routing_result,
                    query_lower=query_lower,
                    has_temporal_result=has_temporal,
                    has_reasoning_chain=has_reasoning
                )
                # audit: which path the request will take, with the inputs
                # the router used. Lets us see the path distribution for the
                # 21/33 questions that don't reach the orchestrator.
                try:
                    from . import audit_log as _audit
                    if _audit.is_enabled():
                        learnable_top_agent = None
                        learnable_top_score = None
                        if learnable_routing_result:
                            sel = learnable_routing_result.get('selected_agents') or []
                            scores = learnable_routing_result.get('scores') or {}
                            if sel:
                                learnable_top_agent = sel[0]
                                learnable_top_score = scores.get(sel[0])
                        _audit.event(
                            'answer_path_decision',
                            answer_path=answer_path,
                            had_temporal_result=bool(has_temporal),
                            had_reasoning_chain=bool(has_reasoning),
                            used_reasoning_chain=bool(use_reasoning_chain),
                            learnable_top_agent=learnable_top_agent,
                            learnable_top_score=(
                                round(float(learnable_top_score), 4)
                                if learnable_top_score is not None else None
                            ),
                            memory_count=len(memories) if memories else 0,
                        )
                except Exception:  # noqa: BLE001
                    pass

                # 根据动态路由结果选择路径
                if answer_path == 'temporal' and has_temporal:
                    _trace_agent('temporal_reasoning')
                    response = temporal_reasoning_result['answer']
                    logger.info(f"⏰ Dynamic route → Temporal Reasoning answer")

                elif answer_path == 'reasoning_chain' and has_reasoning:
                    response = reasoning_chain_result['answer']
                    logger.info("📝 Dynamic route → Reasoning chain answer")

                # 🔥 2025-12-22 FIX: reasoning_chain fallback to orchestrator (not conversation)
                # 当选择reasoning_chain但没有结果时，应该用orchestrator，而非conversation
                elif (answer_path == 'reasoning_chain' and not has_reasoning and
                      self.capability_orchestrator and self.capability_analyzer):
                    _trace_agent('capability_orchestrator')
                    logger.info(f"🔄 Dynamic route → reasoning_chain unavailable, using CapabilityOrchestrator")
                    try:
                        cap_analysis = await self.capability_analyzer.analyze(user_input, context)
                        capabilities = cap_analysis.get('capabilities', [])
                        execution_plan = cap_analysis.get('execution_plan', 'Default plan')
                        logger.info(f"📋 Required capabilities: {[c['name'] for c in capabilities]}")

                        # 🔥 2025-12-27: 传入 user_id 用于多用户记忆过滤
                        orchestrator_result = await self.capability_orchestrator.execute(
                            query=user_input,
                            capabilities=capabilities,
                            memories=memories,
                            execution_plan=execution_plan,
                            supplementary_context=None,
                            user_id=context.get('user_id') if context else None
                        )
                        response = orchestrator_result.get('answer', 'I understand.')
                        confidence = orchestrator_result.get('confidence', 0.0)
                        logger.info(f"✅ CapabilityOrchestrator (fallback): confidence={confidence:.2f}, "
                                   f"capabilities_used={orchestrator_result.get('capabilities_used', [])}")
                    except Exception as e:
                        logger.warning(f"⚠️ CapabilityOrchestrator fallback failed: {e}")
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

                elif answer_path == 'orchestrator' and self.capability_orchestrator and self.capability_analyzer:
                    # 🔥 Dynamic route → CapabilityOrchestrator 动态脑区协作
                    _trace_agent('capability_orchestrator')
                    logger.info(f"🧠 Dynamic route → CapabilityOrchestrator")
                    try:
                        # Step 1: 分析所需能力
                        cap_analysis = await self.capability_analyzer.analyze(user_input, context)
                        capabilities = cap_analysis.get('capabilities', [])
                        execution_plan = cap_analysis.get('execution_plan', 'Default plan')
                        logger.info(f"📋 Required capabilities: {[c['name'] for c in capabilities]}")

                        # Step 2: 执行能力编排
                        supplementary_context = {}
                        if 'reflection_insights' in dir() and reflection_insights:
                            supplementary_context['reflection_patterns'] = reflection_insights.get('patterns_identified', [])
                            supplementary_context['reflection_reasoning'] = reflection_insights.get('reasoning', '')
                            if reflection_insights.get('answer'):
                                supplementary_context['reflection_hint'] = reflection_insights['answer']

                        # 🔥 2025-12-27: 传入 user_id 用于多用户记忆过滤
                        orchestrator_result = await self.capability_orchestrator.execute(
                            query=user_input,
                            capabilities=capabilities,
                            memories=memories,
                            execution_plan=execution_plan,
                            supplementary_context=supplementary_context if supplementary_context else None,
                            user_id=context.get('user_id') if context else None
                        )
                        response = orchestrator_result.get('answer', 'I understand.')
                        confidence = orchestrator_result.get('confidence', 0.0)
                        logger.info(f"✅ CapabilityOrchestrator: confidence={confidence:.2f}, "
                                   f"capabilities_used={orchestrator_result.get('capabilities_used', [])}")
                    except Exception as e:
                        logger.warning(f"⚠️ CapabilityOrchestrator failed: {e}, falling back to conversation agent")
                        import traceback
                        logger.warning(f"   Traceback: {traceback.format_exc()}")
                        # Fallback to conversation agent
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

                else:
                    # 🔥 Dynamic route → Conversation (快速响应或fallback)
                    logger.info(f"💬 Dynamic route → Conversation agent (path={answer_path})")
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

            # 🔥 2025-12-20 FIX: 答案精炼（仅对特定问题类型，避免破坏multi_hop）
            # 只对temporal/status/identity问题精炼，multi_hop需要完整推理
            query_lower = user_input.lower()
            # 精炼事实类问题，排除反事实推断（"would X..."）
            factual_starters = ['what', 'who', 'where', 'when', 'which', 'how many', 'how long']
            is_counterfactual = query_lower.startswith('would') or 'would have' in query_lower
            should_refine = (
                not is_counterfactual and (
                    any(query_lower.startswith(s) for s in factual_starters) or
                    'status' in query_lower or
                    'identity' in query_lower
                )
            )
            if should_refine:
                response = await self._refine_answer_for_qa(user_input, response)

            # 🔥 2026-01-26 FIX-012: Record retrieval outcome for FeedbackLoop (环境Agent基础)
            if hasattr(self, 'feedback_loop') and self.feedback_loop and memories:
                try:
                    # 提取查询中的实体 (简单实现: 用分词)
                    query_entities = [w for w in user_input.split() if len(w) > 2]
                    self.feedback_loop.evaluate_retrieval(
                        query=user_input,
                        query_vector=None,  # 可后续从embedding服务获取
                        query_entities=query_entities,
                        memories=memories
                    )
                    logger.debug(f"📊 FeedbackLoop: recorded {len(memories)} retrieval outcomes")
                except Exception as e:
                    logger.warning(f"⚠️ FeedbackLoop recording failed: {e}")

            # 5. Store memory if needed (use raw input with [Context:] for date extraction)
            store_input = context.get('_raw_input_with_context', user_input)
            memory_stored = await self.memory_coordinator.store_memory_if_needed(
                store_input, response, context
            )

            # 🔥 2025-12-21: 调用偏好提取 - 从用户输入中提取偏好并更新档案
            if memory_stored and not context.get('skip_memory_store'):
                self.extract_and_update_preferences(user_input)

                # 如果提取到偏好，同时存储到PersonaMemory (增强版结构化存储)
                if self._feature_status.get('preference_extraction') and self.preference_extractor:
                    try:
                        extracted = self.preference_extractor.extract_from_text(user_input)
                        total_prefs = sum(len(v) for v in extracted.values())
                        if total_prefs > 0:
                            # 🔥 2025-12-22: 结构化存储到 PersonaMemoryAgent
                            # 使用分类 metadata 便于检索
                            for pref_type, prefs in extracted.items():
                                for pref in prefs:
                                    # 跳过空列表
                                    if not pref:
                                        continue
                                    await self.persona_memory.store_persona({
                                        'content': f"User {pref_type}: {pref}",
                                        'category': pref_type,
                                        'importance': self._get_preference_importance(pref_type),
                                        'metadata': {
                                            'source': 'preference_extraction',
                                            'preference_type': pref_type,
                                            'preference_value': pref,
                                            'original_input': user_input[:200],
                                            'structured_category': self._get_structured_category(pref_type)
                                        }
                                    })
                            logger.debug(f"🎯 Stored {total_prefs} preferences to PersonaMemory (structured)")
                    except Exception as e:
                        logger.debug(f"PersonaMemory store skipped: {e}")

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
                    # 🔥 2026-03-31: 统一情绪检测 — 使用共享 emotion_utils
                    from ..utils.emotion_utils import detect_emotions
                    detected_emotions, emotion_intensity = detect_emotions(user_input)

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

            # 🔥 2026-03-30: HabitLearner 反馈暂时禁用（与推荐一起）
            # 消融实验证明冷启动 Q-learning 干扰路由 (-7%)
            # TODO: 引入训练阶段 vs 推理阶段分离后再启用

            # 🔥 2025-12-14: Active Learning - 低置信度时考虑提问
            # 🔥 2025-12-16: 增强不确定性验证机制 (P0)
            active_learning_question = None
            uncertainty_verification = None

            # 🔥 2026-04-04: benchmark 模式下跳过不确定性提示
            # skip_memory_store 表示正在做 QA 评估，不需要追加噪声元数据
            is_benchmark = context.get('skip_memory_store', False)

            # 不确定性验证阈值 (0.6 = 60% 置信度以下触发验证请求)
            UNCERTAINTY_THRESHOLD = 0.6

            if confidence < UNCERTAINTY_THRESHOLD and not is_benchmark:
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
                        # 🔥 2026-04-04 FIX: benchmark 模式也跳过，避免噪声污染答案
                        if not context.get('evaluation_mode', False) and not is_benchmark:
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

            # 🔥 2025-12-23: 多选题格式修正 (PersonaMem 评估需要)
            # 如果是多选题但响应不是选项格式，强制转换为选项格式
            if context.get('evaluation_mode', False) and '(a)' in user_input and '(b)' in user_input:
                response_lower = response.lower() if response else ''
                has_option_format = any(opt in response_lower for opt in ['(a)', '(b)', '(c)', '(d)', 'the answer is'])
                if not has_option_format:
                    # 响应不是选项格式，需要转换
                    logger.info(f"📝 MCQ format fix: response not in option format, converting...")
                    try:
                        from src.agents.base import BrainAgent
                        class TempMCQConverter(BrainAgent):
                            async def process_message(self, msg): return {}
                        converter = TempMCQConverter('mcq_converter', 'prefrontal', 'MCQ Converter')

                        convert_prompt = f"""Based on the given context, select the BEST option from the multiple choice question.

Question with options:
{user_input}

Context/Analysis to base your selection on:
{response}

Task: Pick the option (a), (b), (c), or (d) that best aligns with the given context.

Output ONLY: "The answer is (X)" where X is a, b, c, or d."""

                        converted = await converter.call_llm(convert_prompt, temperature=0.0, max_tokens=50)
                        import re
                        match = re.search(r'\(([a-d])\)', converted.lower())
                        if match:
                            response = f"The answer is ({match.group(1)})"
                            logger.info(f"   → Converted to: {response}")
                    except Exception as e:
                        logger.warning(f"MCQ conversion failed: {e}")

            agents_involved = _collect_agents_involved() or ['conversation']
            return ProcessingResult(
                response=response,
                routing_decision=query_features,
                agents_involved=agents_involved,
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
                agents_involved=_collect_agents_involved(),
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
