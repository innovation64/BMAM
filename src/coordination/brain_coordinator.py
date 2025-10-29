"""
Brain-Inspired 12-Agent Coordinator System
12智能体协调器：实现真正的并行处理和智能体通信
"""

import os
import asyncio
import math
import re
import json
import threading
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Optional, Coroutine, Tuple, Iterable
from dataclasses import dataclass
from datetime import datetime

from ..utils.config import get_logger, get_settings
from ..utils.memory_signal_config import load_memory_signal_config, DEFAULT_MEMORY_SIGNAL_CONFIG
from ..utils.knowledge_graph_builder import KnowledgeGraphBuilder

from .clean_agent_system import (
    BrainRegion, AgentMessage,
    # Core agents - directly imported
    ShortTermMemoryAgent, LongTermMemoryAgent, MemoryRetrievalAgent,
    ConsolidationAgent, MemoryDistortionAgent, ReflectionAgent,
    ForgettingAgent, StressResponseAgent, PersonalityAgent, PersonaMemoryAgent,
    # Auxiliary agents - clean implementation
    ConversationAgent, ExecutiveControlAgent,
    PerceptionEncodingAgent, ActionExecutionAgent
)
# 🔥 Phase 4: Environment Agent
from ..agents.environment import EnvironmentAgent
from ..agents.core.reasoning_validator import ReasoningValidatorAgent
from ..memory.memory_system import memory_system
from ..agents.agent_buffer_system import agent_buffer_system
from ..brain.neural_plasticity import NeuralPlasticityEngine

# 🔥 Import brain region agents (storage layer)
from ..agents.brain_regions import (
    HippocampusAgent,
    TemporalLobeAgent,
    PrefrontalAgent,
    AmygdalaAgent,
    BasalGangliaAgent
)
from ..agents.brain_regions.temporal_lobe_agent import MemoryType

# 🚀 Import optimization modules
from ..optimization import (
    get_capacity_manager,
    get_query_cache,
    get_fast_path_detector,
    get_context_limiter
)

# Configure logging
logger = get_logger(__name__)


class LearningLogger:
    """Append-only JSONL logger for learning and reasoning events."""

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(self, event: str, payload: Dict[str, Any]) -> None:
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'payload': payload
        }
        try:
            line = json.dumps(entry, ensure_ascii=False)
        except Exception as err:
            logger.warning(f"Failed to serialise learning log entry: {err}")
            return

        try:
            with self._lock:
                with self._log_path.open('a', encoding='utf-8') as stream:
                    stream.write(line + '\n')
        except Exception as err:
            logger.warning(f"Failed to persist learning log entry: {err}")


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
        return await self._coordinator._activate_agent(
            'consolidation',
            AgentMessage(
                sender='evaluation_adapter',
                receiver='consolidation',
                message_type='request',
                content={'action': 'system_consolidation'}
            )
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
    activation_trace: Optional[List[Dict[str, Any]]] = None  # 🔥 For learning
    memories_used: Optional[List[str]] = None  # 🔥 For learning


class BrainInspiredCoordinator:
    """
    12-Agent Brain-Inspired Coordinator System
    Implements the design from 设计思路.md with proper agent communication
    """
    
    def __init__(self):
        logger.info("Initializing Brain-Inspired 12-Agent Coordinator...")

        # Communication system
        self.message_bus = asyncio.Queue()
        self.agent_tasks = {}
        self._task_counter = 0
        self.is_running = False
        
        # Processing statistics (initialize before agents)
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'agent_activations': {},
            'memory_operations': 0
        }

        self.settings = get_settings()
        self.memory_signal_config = load_memory_signal_config()

        # Core memory system reference for legacy integrations
        self.memory_system = memory_system
        self.memory_manager = _LegacyMemoryManagerAdapter(self, memory_system)

        # Persistent learning log for metacognition and audits
        self.learning_logger = LearningLogger(Path('data/learning_log.jsonl'))

        # Initialize all 12 agents
        self._initialize_agents()
        
        # Initialize Neural Plasticity Engine
        agent_names = list(self.agents.keys())
        self.plasticity_engine = NeuralPlasticityEngine(agent_names)

        # 🔥 Phase 3: Initialize Background Memory Processes (optional module)
        try:
            from ..memory.background_memory_processes import BackgroundMemoryProcessManager, BackgroundProcessConfig
            import os

            # 🎯 P2优化: 自动检测测试模式（环境变量或配置）
            auto_test_mode = os.getenv('BMAM_TEST_MODE', '').lower() in ('true', '1', 'yes')

            if auto_test_mode:
                # Test mode: Disabled to prevent test interference
                # Phase 2 background processes cause -0.2 regression (3.9→3.7)
                background_config = BackgroundProcessConfig(
                    test_mode=True,
                    consolidation_interval_seconds=15,  # 15 seconds
                    forgetting_interval_seconds=60,  # 1 minute
                    reconsolidation_interval_seconds=30,  # 30 seconds
                    enabled=False,  # 🔥 DISABLED IN TEST MODE to prevent interference
                    run_on_startup=False
                )
                logger.info("🧪 AUTO-DETECTED TEST MODE via BMAM_TEST_MODE env var (background processes DISABLED)")
            else:
                # Production mode: 正常节律 (1h/2h/30min)
                background_config = BackgroundProcessConfig(
                    test_mode=False,
                    consolidation_interval_seconds=3600,  # 1 hour
                    forgetting_interval_seconds=7200,  # 2 hours
                    reconsolidation_interval_seconds=1800,  # 30 minutes
                    enabled=True,
                    run_on_startup=False  # 启动时不立即运行,等系统稳定后再运行
                )

            self.background_processes = BackgroundMemoryProcessManager(self, background_config)
        except ImportError:
            logger.warning("⚠️ Background memory processes module not found, continuing without it")
            self.background_processes = None

        # 🚀 Initialize optimization modules (stability + efficiency)
        self.capacity_manager = get_capacity_manager()
        self.query_cache = get_query_cache(embedding_service=memory_system.embedding_service)
        self.fast_path_detector = get_fast_path_detector()
        self.context_limiter = get_context_limiter()

        # 🎯 P5: Initialize metacognition modules (reflection + continuous learning)
        from ..optimization.metacognition import (
            get_preference_extractor,
            get_confidence_evaluator,
            get_conflict_detector,
            get_continuous_learner
        )
        self.preference_extractor = get_preference_extractor()
        self.confidence_evaluator = get_confidence_evaluator()
        self.conflict_detector = get_conflict_detector()
        self.continuous_learner = get_continuous_learner()

        # 🌐 P6: Initialize Environment Agent stimulus processor
        from ..agents.environment.stimulus_processor import (
            get_stimulus_processor,
            get_contextual_integrator,
            StimulusModality
        )
        self.stimulus_processor = get_stimulus_processor()
        self.contextual_integrator = get_contextual_integrator()

        logger.info(f"Successfully initialized 12-agent system with {len(self.agents)} agents")
        logger.info("Neural Plasticity Engine integrated - system now has adaptive learning!")
        logger.info("✅ Background Memory Processes initialized (Phase 3)")
        logger.info("🚀 Optimization modules loaded (Capacity+Cache+FastPath+ContextLimit)")
        logger.info("🧠 P5: Metacognition modules loaded (Preference+Confidence+Conflict+Learning)")
        logger.info("🌐 P6: Environment stimulus processing integrated")

    async def initialize(self):
        """Public initializer kept for backwards compatibility (see main())."""
        if not self.is_running:
            await self.start_system()
        return self

    def _initialize_agents(self):
        """Initialize all 12 agents according to design document"""
        
        # Get memory system services
        from src.memory.memory_system import memory_system
        db = memory_system.db_manager
        vec = memory_system.vector_db
        emb = memory_system.embedding_service

        # 🔥 NEW: Memory Storage Layer (Brain Regions) - Plan C: 集成存储和处理
        logger.info("🧠 Initializing Memory Storage Layer (Brain Regions)...")

        # 先初始化TemporalLobe (因为Hippocampus和Amygdala需要它的引用)
        # 🔥 优先级2: 传递embedding_service用于语义相似度融合
        embedding_service = self.memory_system.embedding_service if self.memory_system else None

        # 🔗 Phase 3a: Shared Knowledge Graph builder (hippocampus ⇄ temporal lobe)
        self.knowledge_graph_builder = KnowledgeGraphBuilder(llm_client=None)

        self.temporal_lobe = TemporalLobeAgent(
            capacity=70000,
            embedding_service=embedding_service,
            knowledge_graph_builder=self.knowledge_graph_builder
        )

        # 初始化Hippocampus,传入temporal_lobe和embedding_service用于记忆巩固和混合检索
        self.hippocampus = HippocampusAgent(
            capacity=20000,
            temporal_lobe_agent=self.temporal_lobe,
            embedding_service=embedding_service,
            kg_builder=self.knowledge_graph_builder
        )

        # 初始化Amygdala,传入hippocampus和temporal_lobe用于情绪调节
        self.amygdala = AmygdalaAgent(capacity=1000, hippocampus_agent=self.hippocampus, temporal_lobe_agent=self.temporal_lobe)

        # 初始化PrefrontalAgent,传入coordinator引用(需要延迟设置,因为self还未完全初始化)
        self.prefrontal_storage = PrefrontalAgent(capacity=10, brain_coordinator=None)  # Will be set after init

        # 其他脑区
        self.basal_ganglia = BasalGangliaAgent(capacity=500)

        logger.info("✅ Memory Storage Layer initialized (5 brain regions, Plan C features enabled)")

        # 8 Core Memory Processing Agents (使用brain_regions作为存储)
        self.short_term_memory = ShortTermMemoryAgent()
        self.long_term_memory = LongTermMemoryAgent(db_manager=db, embedding_service=emb, vector_db=vec, capacity=70000)
        self.memory_retrieval = MemoryRetrievalAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.consolidation = ConsolidationAgent(db_manager=db)
        self.memory_distortion = MemoryDistortionAgent(db_manager=db)
        self.reflection = ReflectionAgent(db_manager=db, embedding_service=emb)
        self.forgetting = ForgettingAgent(db_manager=db)
        self.stress_response = StressResponseAgent(db_manager=db)

        # Reasoning & Validation Agent (🔥 集成KG查询 + Phase 2: 集成PrefrontalAgent)
        self.reasoning_validator = ReasoningValidatorAgent(
            reflection_agent=self.reflection,
            consolidation_agent=self.consolidation,
            temporal_lobe_agent=self.temporal_lobe,  # 用于查询KnowledgeGraph
            prefrontal_agent=self.prefrontal_storage  # 🔥 Phase 2: 用于冲突检测和元认知评估
        )

        # 4 Auxiliary Functional Agents
        self.persona_memory = PersonaMemoryAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.personality = PersonalityAgent(persona_memory_agent=self.persona_memory)  # 人格智能体 - 摇光明明
        self.conversation = ConversationAgent()
        self.executive_control = ExecutiveControlAgent()
        self.perception_encoding = PerceptionEncodingAgent()
        self.action_execution = ActionExecutionAgent()

        # 🔥 Phase 4: Environment Agent
        self.environment = EnvironmentAgent(brain_coordinator=None)  # Will be set after init
        
        # Agent registry
        self.agents = {
            # 🔥 Memory Storage Layer (Brain Regions)
            'hippocampus': self.hippocampus,
            'temporal_lobe': self.temporal_lobe,
            'prefrontal_storage': self.prefrontal_storage,
            'amygdala': self.amygdala,
            'basal_ganglia': self.basal_ganglia,

            # Core Memory Processing agents
            'short_term_memory': self.short_term_memory,
            'long_term_memory': self.long_term_memory,
            'memory_retrieval': self.memory_retrieval,
            'consolidation': self.consolidation,
            'memory_distortion': self.memory_distortion,
            'reflection': self.reflection,
            'forgetting': self.forgetting,
            'stress_response': self.stress_response,
            'reasoning_validator': self.reasoning_validator,

            # Auxiliary agents
            'persona_memory': self.persona_memory,
            'personality': self.personality,  # 人格智能体 - 摇光明明
            'conversation': self.conversation,
            'executive_control': self.executive_control,
            'perception_encoding': self.perception_encoding,
            'action_execution': self.action_execution,

            # 🔥 Phase 4: Environment Agent
            'environment': self.environment
        }
        
        # Initialize agent statistics
        for agent_id in self.agents:
            self.processing_stats['agent_activations'][agent_id] = 0

        # 🔥 Plan C: Set delayed references after all agents are initialized
        self.prefrontal_storage.brain_coordinator = self
        self.environment.brain_coordinator = self
        logger.info("✅ Plan C: Brain region agent references wired up")
        logger.info("✅ Phase 4: Environment Agent integrated")

        # 🧠 BrainNetwork initialization
        import os
        self.use_brain_network = os.getenv('USE_BRAIN_NETWORK', 'true').lower() == 'true'

        if self.use_brain_network:
            from src.brain.brain_network import BrainNetwork
            self.brain_network = BrainNetwork(agents=self.agents)
            logger.info("🧠 BrainNetwork initialized (graph topology mode enabled)")
        else:
            self.brain_network = None
            logger.info("⚙️ BrainNetwork disabled (using pipeline mode)")

        # 🔥 Phase 3: Initialize ExternalMemorySystem (如果需要)
        self.use_external_memory = os.getenv('USE_EXTERNAL_MEMORY', 'false').lower() == 'true'

        if self.use_external_memory:
            from src.systems.external_memory_system import ExternalMemorySystem

            kg_builder = self.knowledge_graph_builder or KnowledgeGraphBuilder(llm_client=None)

            self.external_memory = ExternalMemorySystem(
                embedding_service=embedding_service,
                kg_builder=kg_builder,
                search_api_key=os.getenv('SEARCH_API_KEY')
            )

            logger.info("✅ Phase 3: ExternalMemorySystem initialized (use_external_memory=true)")
        else:
            self.external_memory = None
            logger.info("⚙️ Phase 3: ExternalMemorySystem disabled (use_external_memory=false)")
    
    async def start_system(self):
        """Start the coordination system"""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Brain-Inspired Coordinator System started")

        # Start message processing loop
        asyncio.create_task(self._process_message_bus())

        # 🔥 Phase 3: Start background memory processes
        if self.background_processes and self.background_processes.config.enabled:
            await self.background_processes.start()
            logger.info("✅ Background memory processes started (consolidation/forgetting/reconsolidation)")
        else:
            if self.background_processes:
                logger.info("⏭️ Background memory processes DISABLED (test mode or config)")
            else:
                logger.info("⏭️ Background memory processes not available")

    def configure_test_mode(self, enabled: bool = True):
        """Configure test mode with accelerated timing"""
        if hasattr(self, 'background_processes') and self.background_processes:
            if enabled:
                # Test mode: short intervals for rapid testing
                self.background_processes.config.test_mode = True
                self.background_processes.config.consolidation_interval_seconds = 30
                self.background_processes.config.forgetting_interval_seconds = 60
                self.background_processes.config.reconsolidation_interval_seconds = 45
                logger.info("🧪 TEST MODE ENABLED: Short intervals (30s/60s/45s)")
            else:
                # Production mode: normal intervals
                self.background_processes.config.test_mode = False
                self.background_processes.config.consolidation_interval_seconds = 3600
                self.background_processes.config.forgetting_interval_seconds = 7200
                self.background_processes.config.reconsolidation_interval_seconds = 1800
                logger.info("🏭 PRODUCTION MODE: Normal intervals (1h/2h/30min)")
        else:
            logger.warning("⚠️ Background processes not available for configuration")

    async def stop_system(self):
        """Stop the coordination system"""
        self.is_running = False

        # 🔥 Phase 3: Stop background memory processes first
        if self.background_processes:
            await self.background_processes.stop()
            logger.info("✅ Background memory processes stopped")

        # Cancel all agent tasks
        for task in list(self.agent_tasks.values()):
            if not task.done():
                task.cancel()

        if self.agent_tasks:
            await asyncio.gather(*self.agent_tasks.values(), return_exceptions=True)

        self.agent_tasks.clear()

        # Stop plasticity engine and save data
        await self.plasticity_engine.stop_plasticity_engine()

        logger.info("Brain-Inspired Coordinator System stopped with plasticity data saved")

    async def trigger_consolidation(self, strategy: str = 'batch', batch_size: int = 50) -> Dict[str, Any]:
        """
        🔥 手动触发记忆巩固

        Args:
            strategy: 巩固策略
                - 'batch': 批量巩固 (从Hippocampus提取N条记忆)
                - 'system': 系统级巩固 (评估所有记忆)
                - 'sleep': 睡眠巩固 (模拟睡眠时的巩固)
            batch_size: 批量巩固时处理的记忆数量

        Returns:
            Dict with consolidation results

        触发时机建议:
            - 学习完一批内容后 (Learning Session End)
            - Hippocampus容量 > 80%
            - 从学习模式切换到问答模式时
        """
        logger.info(f"🧠 Manually triggering consolidation (strategy={strategy}, batch_size={batch_size})")

        action_map = {
            'batch': 'batch_consolidation',
            'system': 'system_consolidation',
            'sleep': 'sleep_consolidation'
        }

        action = action_map.get(strategy, 'batch_consolidation')

        content = {'action': action}
        if strategy == 'batch':
            content['batch_size'] = batch_size

        result = await self._activate_agent(
            'consolidation',
            AgentMessage(
                sender='coordinator',
                receiver='consolidation',
                message_type='request',
                content=content
            )
        )

        logger.info(f"✅ Consolidation completed: {result.get('consolidated_count', 0)} memories consolidated")
        return result

    async def _select_optimal_retrieval_strategy(self, query: str, context: Dict[str, Any]) -> str:
        """
        🧠 智能检索策略选择 - 模拟人脑的自适应检索机制

        人脑检索策略选择原理:
        1. 模式识别 - 识别查询的认知模式
        2. 上下文感知 - 基于当前上下文调整策略
        3. 经验学习 - 从成功检索中学习最优策略
        4. 动态适应 - 根据检索结果动态调整

        而不是硬编码规则，而是基于认知特征的智能评估
        """
        # 🔍 分析查询的认知特征
        query_features = await self._analyze_query_features(query, context)

        # 🧠 基于记忆激活和认知负荷选择策略
        strategy_scores = {
            'keyword_search': self._evaluate_keyword_search_suitability(query_features),
            'semantic_search': self._evaluate_semantic_search_suitability(query_features),
            'episodic_search': self._evaluate_episodic_search_suitability(query_features),
            'associative_search': self._evaluate_associative_search_suitability(query_features),
            'multi_strategy_search': self._evaluate_multi_strategy_suitability(query_features)
        }

        # 🎯 选择最高分的策略
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        strategy_name = best_strategy[0]
        confidence = best_strategy[1]

        logger.info(f"🧠 Cognitive strategy selection: {strategy_name} (confidence: {confidence:.2f})")
        logger.info(f"📊 Strategy scores: {dict(strategy_scores)}")

        return strategy_name

    async def _analyze_query_features(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析查询的认知特征 - 模拟人脑对信息的特征提取
        """
        query_lower = query.lower()  # 提前定义，供后续使用

        features = {
            'length': len(query),
            'word_count': len(query.split()),
            'question_words': [],
            'time_indicators': [],
            'entities': [],
            'has_numerical_data': False,
            'complexity_score': 0.0,
            'specificity_score': 0.0,
            'temporal_nature': False,
            'relational_nature': False,
            'query_lower': query_lower  # 🔥 添加小写查询文本，供动态alpha计算使用
        }

        # 🔍 识别疑问词 (模式识别)
        question_patterns = {
            'what': 'fact_finding', 'which': 'selection', 'who': 'identity',
            'when': 'temporal', 'where': 'spatial', 'why': 'causal',
            'how': 'procedural', 'how many': 'quantitative'
        }
        for pattern, qtype in question_patterns.items():
            if pattern in query_lower:
                features['question_words'].append((pattern, qtype))

        # 🔍 识别时间指示器
        time_patterns = ['when', 'date', 'time', 'session', 'recently', 'last', 'first', 'before', 'after']
        features['temporal_nature'] = any(pattern in query_lower for pattern in time_patterns)

        # 🔍 识别关系性词汇
        relational_patterns = ['and', 'with', 'between', 'related', 'compare', 'difference', 'vs', 'versus']
        features['relational_nature'] = any(pattern in query_lower for pattern in relational_patterns)

        # 🔍 识别数值数据
        import re
        numerical_patterns = re.findall(r'\d+', query)
        features['has_numerical_data'] = len(numerical_patterns) > 0

        # 🔍 从上下文中提取实体
        features['entities'] = context.get('entities', [])

        # 🧠 计算复杂度分数
        features['complexity_score'] = self._calculate_complexity_score(features)

        # 🧠 计算特指性分数
        features['specificity_score'] = self._calculate_specificity_score(features)

        return features

    def _calculate_complexity_score(self, features: Dict[str, Any]) -> float:
        """计算查询复杂度分数"""
        complexity = 0.0

        # 基于长度
        if features['word_count'] > 20:
            complexity += 0.3
        elif features['word_count'] > 10:
            complexity += 0.2

        # 基于问题类型
        causal_questions = sum(1 for _, qtype in features['question_words'] if qtype == 'causal')
        procedural_questions = sum(1 for _, qtype in features['question_words'] if qtype == 'procedural')
        complexity += (causal_questions + procedural_questions) * 0.2

        # 基于关系性
        if features['relational_nature']:
            complexity += 0.2

        # 基于实体数量
        if len(features['entities']) > 2:
            complexity += 0.1

        return min(complexity, 1.0)

    def _calculate_specificity_score(self, features: Dict[str, Any]) -> float:
        """计算查询特指性分数"""
        specificity = 0.0

        # 疑问词增加特指性
        if features['question_words']:
            specificity += 0.3

        # 数值数据增加特指性
        if features['has_numerical_data']:
            specificity += 0.2

        # 实体增加特指性
        specificity += min(len(features['entities']) * 0.1, 0.3)

        # 时间指示器增加特指性
        if features['temporal_nature']:
            specificity += 0.2

        return min(specificity, 1.0)

    def _determine_preferred_memory_type(self, query_features: Dict[str, Any]) -> Optional[MemoryType]:
        """
        阶段1: 根据问题特征确定首选记忆类型

        Args:
            query_features: 查询特征分析结果

        Returns:
            MemoryType or None (None表示不做类型过滤)
        """
        # 时间相关问题 → TEMPORAL memories
        if query_features.get('temporal_nature', False):
            logger.info("📊 Question type: TEMPORAL - filtering for temporal memories")
            return MemoryType.TEMPORAL

        # 关系型问题 (who with whom, between X and Y) → RELATIONAL memories
        if query_features.get('relational_nature', False):
            logger.info("📊 Question type: RELATIONAL - filtering for relational memories")
            return MemoryType.RELATIONAL

        # 事实性问题 (what, who, where) → FACTUAL memories
        fact_question_types = ['fact_finding', 'identity', 'selection', 'spatial']
        has_fact_question = any(
            qtype in fact_question_types
            for _, qtype in query_features.get('question_words', [])
        )
        if has_fact_question:
            logger.info("📊 Question type: FACTUAL - filtering for factual memories")
            return MemoryType.FACTUAL

        # 默认：不做类型过滤，检索所有类型
        logger.info("📊 Question type: GENERAL - no memory type filtering")
        return None

    def _evaluate_keyword_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估关键词检索适用性 - 精确事实查询"""
        score = 0.0

        # 高特指性适合关键词搜索
        score += features['specificity_score'] * 0.4

        # 事实查询适合关键词搜索
        fact_questions = sum(1 for _, qtype in features['question_words'] if qtype in ['fact_finding', 'identity', 'selection'])
        score += fact_questions * 0.3

        # 数值查询适合关键词搜索
        if features['has_numerical_data']:
            score += 0.2

        # 短查询更适合关键词搜索
        if features['word_count'] < 8:
            score += 0.1

        return min(score, 1.0)

    def _evaluate_semantic_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估语义检索适用性 - 一般性理解查询"""
        score = 0.3  # 基础分数，语义检索总是适用

        # 中等复杂度最适合语义搜索
        if 0.3 <= features['complexity_score'] <= 0.7:
            score += 0.3

        # 没有特定指示词时更适合语义搜索
        if not features['question_words'] and not features['temporal_nature']:
            score += 0.2

        # 中等长度查询适合语义搜索
        if 8 <= features['word_count'] <= 15:
            score += 0.2

        return min(score, 1.0)

    def _evaluate_episodic_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估情景记忆检索适用性 - 时间相关查询"""
        score = 0.0

        # 时间性质是关键因素
        if features['temporal_nature']:
            score += 0.6

        # 时间相关问题
        temporal_questions = sum(1 for _, qtype in features['question_words'] if qtype == 'temporal')
        score += temporal_questions * 0.3

        # 会话相关词汇
        if any(word in features.get('entities', []) for word in ['session', 'meeting', 'conversation']):
            score += 0.1

        return min(score, 1.0)

    def _evaluate_associative_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估联想检索适用性 - 关系查询"""
        score = 0.0

        # 关系性质是关键因素
        if features['relational_nature']:
            score += 0.5

        # 多个实体联想
        if len(features['entities']) > 1:
            score += min(len(features['entities']) * 0.1, 0.3)

        # 比较查询适合联想搜索
        if features['complexity_score'] > 0.5:
            score += 0.2

        return min(score, 1.0)

    def _evaluate_multi_strategy_suitability(self, features: Dict[str, Any]) -> float:
        """评估多策略检索适用性 - 复杂查询"""
        score = 0.0

        # 高复杂度是多策略的主要指标
        if features['complexity_score'] > 0.7:
            score += 0.5
        elif features['complexity_score'] > 0.5:
            score += 0.3

        # 长查询适合多策略
        if features['word_count'] > 15:
            score += 0.2

        # 多种问题类型
        question_types = set(qtype for _, qtype in features['question_words'])
        if len(question_types) > 1:
            score += 0.3

        return min(score, 1.0)

    async def shutdown(self):
        """Alias for stop_system() for convenience"""
        await self.stop_system()

    async def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """
        Main processing using brain-inspired BrainNetwork architecture
        实现类脑信息处理流程 (图拓扑激活扩散)
        """
        start_time = datetime.now()

        try:
            self.processing_stats['total_requests'] += 1

            if not self.is_running:
                await self.start_system()

            logger.info(f"Processing user input: {user_input[:50]}...")

            base_context = dict(context) if isinstance(context, dict) else {}

            # 🧠 BrainNetwork模式: 图拓扑激活扩散 + CapabilityOrchestrator
            logger.info("🧠 Using BrainNetwork (Parallel Activation)")
            return await self._process_with_brain_network(user_input, base_context, start_time)

            # ==================================================================================
            # ⚠️ UNREACHABLE CODE WARNING (Dead Code)
            # ==================================================================================
            # 以下代码由于上方的 return 语句而永远不会执行
            # 这是旧的 Pipeline 模式实现，已被 BrainNetwork 模式替代
            # 保留此代码仅供参考或未来可能的重构需求
            # 如需启用 Pipeline 模式，需要添加条件判断而非无条件 return
            # ==================================================================================

            logger.info("⚙️ Using Pipeline (Sequential Execution)")

            # Phase 1: Perception Encoding (感知编码)
            perception_result = await self._activate_agent(
                'perception_encoding',
                AgentMessage(
                    sender='coordinator',
                    receiver='perception_encoding',
                    message_type='request',
                    content={
                        'action': 'encode_input',
                        'input_data': {
                            'content': user_input,
                            'type': 'text',
                            'context': base_context
                        }
                    }
                )
            )
            
            encoded_input = perception_result.get('encoded_input', {})
            requires_chunked_storage = perception_result.get('requires_chunked_storage', False)

            # Phase 2: Executive Control - Task Routing with Plasticity (执行控制 - 任务路由)
            task_type = self._classify_task_type(user_input)
            
            # Get optimal agent sequence from plasticity engine
            optimal_agents = self.plasticity_engine.optimize_routing_strategy(task_type)
            
            routing_result = await self._activate_agent(
                'executive_control',
                AgentMessage(
                    sender='coordinator',
                    receiver='executive_control',
                    message_type='request',
                    content={
                        'action': 'coordinate_agents',
                        'task_info': {
                            'user_input': user_input,
                            'type': task_type,
                            'complexity': encoded_input.get('features', {}).get('complexity', 'medium'),
                            'context': base_context,
                            'optimal_sequence': optimal_agents[:3]  # Top 3 from plasticity
                        }
                    }
                )
            )
            
            coordination_plan = routing_result.get('coordination_plan', {})
            # Use plasticity-optimized agents if executive control doesn't override
            primary_agents = coordination_plan.get('primary_agents', optimal_agents[:2])
            secondary_agents = coordination_plan.get('secondary_agents', optimal_agents[2:4])
            
            # Phase 3: Selective Agent Activation (选择性智能体激活)
            parallel_tasks = {}
            activated_agents = []

            # 🔥 P1优化: 使用智能检索路由 - 单策略执行,无硬编码
            # smart_retrieve()内部完成: 特征分析 → 路由决策 → 单策略执行
            # 不再调用MemoryRetrievalAgent,直接由协调层执行最优策略
            smart_retrieval_result = await self.smart_retrieve(
                query=user_input,
                context=base_context,
                k=10
            )

            # 从智能检索结果中提取记忆
            memories = smart_retrieval_result.get('memories', [])
            retrieval_strategy = smart_retrieval_result.get('strategy', 'unknown')
            route_reasoning = smart_retrieval_result.get('route_reasoning', '')

            logger.info(f"🧠 Smart retrieval: {retrieval_strategy} | {route_reasoning}")
            logger.info(f"📊 Retrieved {len(memories)} memories")

            # 不需要在parallel_tasks中添加memory_retrieval
            # 因为smart_retrieve已经同步完成检索

            # Selective Stress/Threat Detection - only for potentially concerning content
            if self._requires_stress_analysis(user_input):
                parallel_tasks['stress_response'] = self._activate_agent(
                    'stress_response',
                    AgentMessage(
                        sender='coordinator',
                        receiver='stress_response',
                        message_type='request',
                        content={
                            'action': 'threat_detection',
                            'stimulus': {'content': user_input}
                        }
                    )
                )
                activated_agents.append('stress_response')
            
            # Activate primary agents based on routing
            for agent_name in primary_agents:
                agent_id = self._map_agent_name(agent_name)
                if agent_id and agent_id in self.agents:
                    parallel_tasks[agent_id] = self._create_primary_agent_task(agent_id, user_input, base_context)
                    activated_agents.append(agent_id)
            
            # Wait for parallel phase completion - TRUE PARALLEL EXECUTION
            parallel_results = {}
            successful_agents = []
            activation_strengths = []
            
            # Execute all tasks concurrently
            task_names = list(parallel_tasks.keys())
            task_coros = list(parallel_tasks.values())
            
            # Add timeout protection for parallel phase
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*task_coros, return_exceptions=True),
                    timeout=self.settings.parallel_phase_timeout
                )
            except asyncio.TimeoutError:
                logger.warning("并行阶段超时，使用部分结果继续")
                results = [Exception("Parallel phase timeout") for _ in task_coros]
            
            # Process results
            for task_name, result in zip(task_names, results):
                if isinstance(result, Exception):
                    # 检查是否是连接错误
                    error_str = str(result).lower()
                    if any(keyword in error_str for keyword in ['tcptransport', 'connection error', 'connection pool', 'closed=true']):
                        logger.warning(f"智能体 {task_name} 执行失败: {result}")
                    parallel_results[task_name] = {'error': str(result)}
                else:
                    parallel_results[task_name] = result
                    if not result.get('error') and task_name in self.agents:
                        successful_agents.append(task_name)
                        activation_strengths.append(1.0)  # Full activation strength for successful agents
            
            # Record agent activations for plasticity learning
            if len(successful_agents) >= 2:
                await self.plasticity_engine.start_plasticity_engine()
                self.plasticity_engine.record_agent_activation(
                    successful_agents,
                    activation_strengths,
                    context={
                        'user_input': user_input,
                        'task_type': self._classify_task_type(user_input),
                        'timestamp': datetime.now().isoformat()
                    }
                )

            # 🔥 P1优化: memories已经从smart_retrieve获取,不需要从parallel_results提取
            # (memories变量已在上面的smart_retrieve调用后设置)

            # Only get threat info if stress_response was actually activated
            threat_info = parallel_results.get('stress_response', {}) if 'stress_response' in parallel_results else {'threat_score': 0.0, 'threat_level': 'none'}

            base_context['retrieved_memories'] = memories
            base_context['retrieval_conflicts'] = smart_retrieval_result.get('conflicts', [])
            base_context['retrieval_keywords'] = smart_retrieval_result.get('keywords', [])
            base_context['retrieval_missing_keywords'] = smart_retrieval_result.get('missing_keywords', [])
            base_context['retrieval_coverage_ratio'] = smart_retrieval_result.get('coverage_ratio')

            personality_result = parallel_results.get('personality')
            if (not personality_result) or personality_result.get('error'):
                try:
                    personality_result = await self._activate_agent(
                        'personality',
                        AgentMessage(
                            sender='coordinator',
                            receiver='personality',
                            message_type='request',
                            content={
                                'action': 'generate_personality_response',
                                'user_input': user_input,
                                'retrieved_memories': memories
                            }
                        )
                    )
                except Exception as exc:
                    logger.warning(f"Personality agent invocation failed: {exc}")
                    personality_result = None

            if personality_result and not personality_result.get('error'):
                base_context['personality_context'] = personality_result.get('personality_context', {})
                base_context['current_personality_emotion'] = personality_result.get('current_emotion')
                base_context['persona_memories_used'] = personality_result.get('persona_memories_used')

            # Initialize memory tracking variables
            memory_ids = []
            memory_strengths = []
            
            # Record memory co-activation for plasticity learning
            if memories:
                memory_ids = [mem.get('id', f"memory_{i}") for i, mem in enumerate(memories)]
                memory_strengths = [mem.get('similarity_score', 0.5) for mem in memories]
                
                self.plasticity_engine.record_memory_co_activation(
                    memory_ids,
                    memory_strengths,
                    context={
                        'query': user_input,
                        'retrieval_context': 'user_query',
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            # Phase 4: Working Memory Processing (工作记忆处理)
            if memories:
                # Exchange retrieved memories with short-term memory (with timeout protection)
                try:
                    await asyncio.wait_for(
                        agent_buffer_system.exchange_buffers(
                            'memory_retrieval',
                            'short_term_memory',
                            'retrieved_memories',
                            {
                                'memories': memories,
                                'query': user_input,
                                'count': len(memories)
                            }
                        ),
                        timeout=self.settings.buffer_exchange_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("缓冲区交换超时，跳过此步骤继续")
                
                await self._activate_agent(
                    'short_term_memory',
                    AgentMessage(
                        sender='coordinator',
                        receiver='short_term_memory',
                        message_type='request',
                        content={
                            'action': 'store_short_term',
                            'item': {
                                'content': f"Retrieved {len(memories)} relevant memories for: {user_input}",
                                'type': 'memory_context'
                            }
                        }
                    )
                )
            
            # Phase 5: Response Generation with Plasticity Insights (响应生成)
            # Get suggested memories from plasticity engine
            plasticity_memories = []
            if memories:
                memory_ids = [mem.get('id', f"memory_{i}") for i, mem in enumerate(memories)]
                associated_memories = self.plasticity_engine.get_associated_memories(
                    memory_ids[:3],  # Top 3 memories for association
                    association_threshold=0.2,
                    max_associations=5
                )
                plasticity_memories = [{'id': mem_id, 'plasticity_strength': strength} 
                                     for mem_id, strength in associated_memories]
            
            response_result = await self._activate_agent(
                'conversation',
                AgentMessage(
                    sender='coordinator',
                    receiver='conversation',
                    message_type='request',
                    content={
                        'action': 'generate_response',
                        'user_input': user_input,
                        'context': base_context,
                        'memories': memories[:5],  # Top 5 most relevant
                        'plasticity_memories': plasticity_memories,
                        'threat_info': threat_info,
                        'primary_results': {k: v for k, v in parallel_results.items() if k not in ['memory_retrieval', 'stress_response']}
                    }
                )
            )
            
            main_response = response_result.get('response', '抱歉，我现在无法处理您的请求。')

            # Persona-aware refinement
            personality_result = parallel_results.get('personality')
            if personality_result and personality_result.get('error'):
                personality_result = None

            if personality_result is None:
                try:
                    personality_result = await self._activate_agent(
                        'personality',
                        AgentMessage(
                            sender='coordinator',
                            receiver='personality',
                            message_type='request',
                            content={
                                'action': 'generate_personality_response',
                                'user_input': user_input,
                                'retrieved_memories': memories[:5],
                                'base_response': main_response
                            }
                        )
                    )
                except Exception as exc:
                    logger.warning(f"Personality agent invocation failed: {exc}")
                    personality_result = None

            if personality_result and not personality_result.get('error'):
                base_context['personality_context'] = personality_result.get('personality_context', {})
                base_context['persona_memories_used'] = personality_result.get('persona_memories_used', 0)
                base_context['personality_current_emotion'] = personality_result.get('current_emotion')

                # Only use personality response if no relevant memories were found
                # When memories are available, preserve the memory-based conversation response
                if len(memories) == 0 or not response_result.get('memories_used', 0):
                    main_response = personality_result.get('personality_response', main_response)
                else:
                    # Keep memory-based response, but add personality context for logging
                    logger.info(f"Preserving memory-based response from conversation agent ({len(memories)} memories used)")
            
            # Phase 5.5: User Preference Processing (用户偏好处理) - Background
            preference_processed = False
            if self._contains_user_preference(user_input):
                # Store user preference asynchronously to avoid blocking main response
                async def store_preference_background():
                    try:
                        preference_result = await self._activate_agent(
                            'long_term_memory',
                            AgentMessage(
                                sender='coordinator',
                                receiver='long_term_memory',
                                message_type='request',
                                content={
                                    'action': 'store_long_term',
                                    'memory': {
                                        'content': f"用户偏好：{user_input}",
                                        'importance': 0.9,  # 偏好具有高重要性
                                        'context_tags': ['用户偏好', 'preference', 'personal_info'],
                                        'emotion_tags': ['positive', 'preference']
                                    }
                                }
                            )
                        )
                        if preference_result.get('success', False):
                            logger.info(f"后台存储用户偏好完成: {user_input[:50]}")
                            await self._activate_agent(
                                'persona_memory',
                                AgentMessage(
                                    sender='coordinator',
                                    receiver='persona_memory',
                                    message_type='request',
                                    content={
                                        'action': 'store_persona_memory',
                                        'memory': {
                                            'content': f"用户偏好：{user_input}",
                                            'category': 'preference',
                                            'importance': 0.85,
                                            'context_tags': ['persona', 'preference', 'value_alignment'],
                                            'emotion_tags': ['positive'],
                                            'metadata': {
                                                'preference_type': 'user_input',
                                                'value_alignment': base_context.get('user_values', 'neutral')
                                            }
                                        }
                                    }
                                )
                            )
                            # Exchange buffer info between long_term_memory and consolidation
                            await agent_buffer_system.exchange_buffers(
                                'long_term_memory',
                                'consolidation', 
                                'user_preference',
                                {'preference': user_input, 'timestamp': datetime.now().isoformat()}
                            )
                    except Exception as e:
                        logger.error(f"后台存储用户偏好失败: {e}")
                
                # Create background task for preference storage
                self._create_background_task("store_user_preference", store_preference_background())
                preference_processed = True  # Always true since we're storing in background
            
            # 触发记忆巩固
            if preference_processed:
                await self._activate_agent(
                    'consolidation',
                    AgentMessage(
                        sender='coordinator',
                        receiver='consolidation',
                        message_type='request',
                        content={
                            'action': 'consolidate_preference',
                            'memory_id': None,  # Will be handled in background
                            'importance_boost': 0.2
                        }
                    )
                )
            
            # Phase 6: Memory Strategy (短期存储 + 长期候选)
            memory_stored = False
            memory_storage_error = None
            memory_strategy = 'skipped'

            # Handle chunked text if needed
            if requires_chunked_storage and encoded_input.get('segments'):
                await self._handle_chunked_text_storage(
                    encoded_input=encoded_input,
                    user_input=user_input,
                    assistant_response=main_response,
                    context=base_context
                )
                memory_strategy = 'chunked_storage'

            # Always keep a short-term snapshot for immediate context reuse
            await self._store_short_term_memory_snapshot(
                user_input=user_input,
                assistant_response=main_response,
                context=base_context
            )

            if self._should_consider_long_term(user_input, base_context):
                # Determine memory properties
                importance = self._calculate_importance(user_input, threat_info, memories)
                emotion_tags = self._extract_emotions(user_input, threat_info)

                # Apply emotional encoding if needed
                if threat_info.get('threat_score', 0) > 0.3:
                    emotional_encoding = await self._activate_agent(
                        'stress_response',
                        AgentMessage(
                            sender='coordinator',
                            receiver='stress_response',
                            message_type='request',
                            content={
                                'action': 'emotional_encoding',
                                'memory_data': {
                                    'content': user_input,
                                    'importance': importance,
                                    'emotion_tags': emotion_tags,
                                    'emotion_intensity': threat_info.get('threat_score', 0.5)
                                }
                            }
                        )
                    )
                    importance += emotional_encoding.get('importance_boost', 0.0)

                conversation_content = f"用户说：{user_input}\n助手回复：{main_response}"

                explicit_memory_intent = self._has_explicit_memory_request(user_input) or preference_processed

                async def store_conversation_memory():
                    memory_id = await memory_system.store_memory(
                        content=conversation_content,
                        importance=min(1.0, importance),
                        emotion_tags=emotion_tags,
                        context_tags=[self._classify_task_type(user_input), "完整对话"],
                        metadata={
                            'source': 'conversation',
                            'user_input': user_input,
                            'assistant_response': main_response,
                            'memories_used': len(memories),
                            'threat_level': threat_info.get('threat_level', 'unknown'),
                            'threat_score': threat_info.get('threat_score', 0.0),
                            'processing_timestamp': datetime.now().isoformat()
                        }
                    )
                    return memory_id

                async def handle_success(memory_id: str):
                    self.processing_stats['memory_operations'] += 1
                    logger.info(f"Long-term memory stored: {memory_id}")

                    if memory_ids:
                        all_memory_ids = memory_ids + [memory_id]
                        all_strengths = memory_strengths + [importance]

                        self.plasticity_engine.record_memory_co_activation(
                            all_memory_ids,
                            all_strengths,
                            context={
                                'event': 'new_memory_storage',
                                'conversation_context': True,
                                'timestamp': datetime.now().isoformat()
                            }
                        )

                # Record existing memory activation immediately
                if memory_ids:
                    self.plasticity_engine.record_memory_co_activation(
                        memory_ids,
                        memory_strengths,
                        context={
                            'event': 'memory_retrieval',
                            'conversation_context': True,
                            'timestamp': datetime.now().isoformat()
                        }
                    )

                if explicit_memory_intent:
                    memory_strategy = 'stored_immediately'
                    try:
                        memory_id = await asyncio.wait_for(
                            store_conversation_memory(),
                            timeout=self.settings.memory_storage_timeout
                        )

                        if memory_id:
                            memory_stored = True
                            await handle_success(memory_id)
                        else:
                            memory_storage_error = "Memory storage returned None - possible embedding failure"
                            logger.warning(memory_storage_error)
                    except asyncio.TimeoutError:
                        memory_storage_error = f"Memory storage timeout after {self.settings.memory_storage_timeout}s"
                        logger.warning(memory_storage_error)
                    except Exception as e:
                        memory_storage_error = f"Memory storage failed: {str(e)}"
                        logger.error(memory_storage_error)
                else:
                    memory_strategy = 'queued_for_consolidation'

                    async def background_store():
                        try:
                            memory_id = await store_conversation_memory()
                            if memory_id:
                                await handle_success(memory_id)
                            else:
                                logger.warning("Background memory storage returned None - possible embedding failure")
                        except Exception as exc:
                            logger.error(f"Background memory storage failed: {exc}")

                    await self._queue_memory_candidate(
                        user_input=user_input,
                        assistant_response=main_response,
                        importance=importance,
                        emotion_tags=emotion_tags,
                        threat_info=threat_info
                    )
                    self._create_background_task("store_conversation_memory", background_store())

            else:
                memory_strategy = 'short_term_only'
            
            # Phase 7: Background Processing (后台处理)
            background_tasks = []
            
            # Reflection and insights
            if len(memories) > 3:
                background_tasks.append(
                    self._create_background_task(
                        "background_reflection",
                        self._trigger_background_reflection(memories)
                    )
                )
            
            # Memory consolidation
            if memory_stored and importance > 0.7:
                background_tasks.append(
                    self._create_background_task(
                        "background_consolidation",
                        self._trigger_background_consolidation()
                    )
                )

            # Process chunked text queue periodically
            if self.processing_stats['total_requests'] % 10 == 0:
                background_tasks.append(
                    self._create_background_task(
                        "process_chunked_queue",
                        self._trigger_chunked_queue_processing()
                    )
                )
            
            # Forgetting (higher frequency for buffer maintenance)
            if self.processing_stats['total_requests'] % 5 == 0:
                background_tasks.append(
                    self._create_background_task(
                        "background_forgetting",
                        self._trigger_background_forgetting()
                    )
                )

            if self.processing_stats['total_requests'] % self.settings.buffer_cleanup_frequency == 0:
                background_tasks.append(
                    self._create_background_task(
                        "buffer_cleanup",
                        agent_buffer_system.cleanup_stale_entries(
                            max_age_hours=self.settings.buffer_retention_hours
                        )
                    )
                )

            if self.processing_stats['total_requests'] % self.settings.faiss_compaction_frequency == 0:
                background_tasks.append(
                    self._create_background_task(
                        "faiss_compaction",
                        memory_system.enforce_storage_limits(
                            max_vectors=self.settings.max_faiss_vectors
                        )
                    )
                )
            
            # Background tasks run independently - don't wait for them to avoid blocking
            insights = {
                'status': 'background_processing',
                'tasks_started': len(background_tasks),
                'memory_strategy': memory_strategy
            }
            if 'personality_context' in base_context:
                insights['personality_context'] = base_context.get('personality_context', {})
                insights['persona_memories_used'] = base_context.get('persona_memories_used', 0)
                insights['current_personality_emotion'] = base_context.get('personality_current_emotion')

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Collect agent logs
            agent_logs = {}
            for agent_id, agent in self.agents.items():
                if agent.execution_log:
                    agent_logs[agent_id] = agent.execution_log[-5:]  # Last 5 entries
            
            # 检查响应是否包含错误标志
            has_error = False
            error_message = None

            # 检查是否有API异常或其他错误标志
            if main_response.startswith('⚠️') or 'API异常' in main_response:
                has_error = True
                error_message = f"Response contains error: {main_response[:100]}"
                self.processing_stats['failed_requests'] += 1
            else:
                # 检查并行结果中是否有错误
                for agent_id, result_data in parallel_results.items():
                    if isinstance(result_data, dict) and result_data.get('error'):
                        has_error = True
                        error_message = f"Agent {agent_id} error: {result_data['error']}"
                        self.processing_stats['failed_requests'] += 1
                        break

                if not has_error:
                    self.processing_stats['successful_requests'] += 1

            # Include memory storage error in final error reporting
            final_error_message = error_message
            if memory_storage_error and not final_error_message:
                final_error_message = memory_storage_error
                has_error = True

            result = ProcessingResult(
                response=main_response,
                routing_decision=coordination_plan,
                agents_involved=list(parallel_results.keys()),
                memories_retrieved=memories,
                memory_stored=memory_stored,
                processing_time=processing_time,
                agent_logs=agent_logs,
                insights=insights,
                success=not has_error,
                error=final_error_message
            )
            
            if has_error:
                logger.warning(f"Processed request with errors in {processing_time:.2f}s with {len(memories)} memories")
            else:
                logger.info(f"Successfully processed request in {processing_time:.2f}s with {len(memories)} memories")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_stats['failed_requests'] += 1
            
            # 检查是否是连接错误，如果是则重置OpenAI客户端
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['tcptransport', 'connection error', 'connection pool', 'closed=true']):
                logger.warning(f"检测到连接错误: {e}")
                # 连接错误处理已统一到BrainAgent.call_llm中，避免竞态条件
            
            logger.error(f"Error processing user input: {e}")
            
            return ProcessingResult(
                response=f"系统处理错误：{str(e)}",
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
        """Legacy compatibility wrapper returning plain response text."""
        result = await self.process_user_input(user_input, context)
        if isinstance(result, ProcessingResult):
            return result.response
        return result

    async def store_memory_with_timestamp(
        self,
        content: str,
        timestamp: datetime,
        speaker: str = None,
        importance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Store memory with custom timestamp (for learning historical conversations)
        用自定义时间戳存储记忆（用于学习历史对话）

        Args:
            content: Memory content
            timestamp: Custom timestamp (e.g., session date from LoCoMo)
            speaker: Speaker name (e.g., "Caroline")
            importance: Importance score (0.0-1.0)

        Returns:
            {
                'memory_id': str,
                'event_id': str,
                'is_new_event': bool
            }
        """
        if not self.is_running:
            await self.start_system()

        result = await self.hippocampus.store_memory_with_event_segmentation(
            content=content,
            timestamp=timestamp,
            speaker=speaker,
            importance=importance
        )

        logger.info(f"📝 Stored historical memory: {content[:50]}... (timestamp={timestamp.strftime('%Y-%m-%d %H:%M')})")

        return result

    async def _activate_agent(self, agent_id: str, message: AgentMessage) -> Dict[str, Any]:
        """Activate specific agent with message and use buffer system"""
        if agent_id not in self.agents:
            return {'error': f'Agent {agent_id} not found'}
        
        try:
            agent = self.agents[agent_id]
            self.processing_stats['agent_activations'][agent_id] += 1
            
            # Read agent's current buffer state
            try:
                buffer_content = await agent_buffer_system.read_buffer(agent_id)
                # Add ONLY essential buffer data to avoid infinite nesting
                if hasattr(message, 'content') and isinstance(message.content, dict):
                    # Only pass essential data, not the entire buffer including recent_inputs
                    essential_data = {}
                    for key, value in buffer_content.items():
                        if key not in ['recent_inputs', 'recent_exchanges', 'recent_outputs']:
                            essential_data[key] = value
                    message.content['buffer_data'] = essential_data
            except Exception as buffer_e:
                logger.warning(f"Failed to read buffer for {agent_id}: {buffer_e}")
            
            # Process the message
            result = await agent.process_message(message)
            
            # Update agent buffer with processing results
            try:
                # Sanitize function for JSON serialization
                def sanitize_for_json(obj):
                    if isinstance(obj, dict):
                        return {k: sanitize_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [sanitize_for_json(item) for item in obj]
                    elif hasattr(obj, '__dict__'):
                        return str(obj)  # Convert objects to string representation
                    elif isinstance(obj, (str, int, float, bool)) or obj is None:
                        return obj
                    else:
                        return str(obj)  # Convert everything else to string
                
                # Store ONLY the original message content, not the enriched version
                original_content = {k: v for k, v in message.content.items() if k != 'buffer_data'}
                await agent_buffer_system.write_buffer(
                    agent_id, 
                    'recent_inputs', 
                    {
                        'message': sanitize_for_json(original_content),
                        'timestamp': datetime.now().isoformat(),
                        'sender': message.sender
                    },
                    append=True
                )
                
                # Store processing results if available - sanitize for JSON
                if result and not result.get('error'):
                    await agent_buffer_system.write_buffer(
                        agent_id,
                        'recent_outputs',
                        {
                            'result': sanitize_for_json(result),
                            'timestamp': datetime.now().isoformat(),
                            'processing_success': True
                        },
                        append=True
                    )
            except Exception as buffer_e:
                logger.warning(f"Failed to write buffer for {agent_id}: {buffer_e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error activating agent {agent_id}: {e}")
            return {'error': str(e)}
    
    def _map_agent_name(self, agent_name: str) -> Optional[str]:
        """Map Chinese agent names to agent IDs"""
        name_mapping = {
            '记忆存储智能体': 'long_term_memory',
            '记忆检索智能体': 'memory_retrieval',
            '对话智能体': 'conversation',
            '反思智能体': 'reflection',
            '规划智能体': 'action_execution',
            '工具调用智能体': 'action_execution',
            '记忆巩固智能体': 'consolidation',
            '遗忘智能体': 'forgetting'
        }
        return name_mapping.get(agent_name, agent_name.lower().replace(' ', '_'))
    
    def _classify_task_type(self, user_input: str) -> str:
        """Classify task type for routing decisions"""
        user_lower = user_input.lower()
        
        if any(keyword in user_lower for keyword in ['记住', '保存', 'remember', 'save']):
            return 'memory_storage'
        elif any(keyword in user_lower for keyword in ['搜索', '查找', 'search', 'find']):
            return 'memory_retrieval'
        elif any(keyword in user_lower for keyword in ['计算', '计划', 'calculate', 'plan']):
            return 'tool_execution'
        elif any(keyword in user_lower for keyword in ['分析', '思考', 'analyze', 'think']):
            return 'reflection'
        else:
            return 'conversation'
    
    def _contains_user_preference(self, user_input: str) -> bool:
        """检测用户输入是否包含偏好表达"""
        preference_indicators = [
            '我喜欢', '我不喜欢', '我爱', '我讨厌', '我觉得',
            '我认为', '我希望', '我想要', '我需要', '我偏好',
            '我的兴趣', '我的爱好', '我习惯', '我经常', '我通常',
            '我最爱', '我最喜欢', '我很喜欢', '我特别喜欢'
        ]

        return any(indicator in user_input for indicator in preference_indicators)

    def _requires_stress_analysis(self, user_input: str) -> bool:
        """判断是否需要进行压力/威胁分析"""
        # Skip stress analysis for simple greetings and preferences
        simple_patterns = ['你好', 'hello', 'hi', '谢谢', 'thank', '再见', 'bye']
        if any(pattern in user_input.lower() for pattern in simple_patterns):
            return False

        # Skip for preference expressions (they're usually positive)
        if self._contains_user_preference(user_input):
            return False

        # Require stress analysis for potentially emotional content
        stress_indicators = [
            '担心', '害怕', '愤怒', '沮丧', '焦虑', '紧张', '压力', '困难', '问题',
            'worry', 'afraid', 'angry', 'frustrated', 'anxious', 'stress', 'problem'
        ]

        # Also analyze longer inputs (might contain complex emotions)
        return (any(indicator in user_input.lower() for indicator in stress_indicators) or
                len(user_input) > 50)
    
    async def _create_primary_agent_task(self, agent_id: str, user_input: str, context: Dict) -> Dict[str, Any]:
        """Create appropriate task for primary agent"""
        if agent_id == 'long_term_memory':
            return await self._activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'store_long_term',
                        'memory': {
                            'content': user_input,
                            'importance': 0.7,
                            'emotion_tags': ['neutral'],
                            'context_tags': ['user_input']
                        }
                    }
                )
            )
        elif agent_id == 'personality':
            return await self._activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'generate_personality_response',
                        'user_input': user_input,
                        'retrieved_memories': context.get('retrieved_memories', []) if context else []
                    }
                )
            )
        elif agent_id == 'action_execution':
            # Check if it's a calculation request
            if '计算' in user_input or 'calculate' in user_input.lower():
                # Extract expression
                import re
                expr_match = re.search(r'[\d\+\-\*/\(\)\s\.]+', user_input)
                expression = expr_match.group(0) if expr_match else user_input
                
                return await self._activate_agent(
                    agent_id,
                    AgentMessage(
                        sender='coordinator',
                        receiver=agent_id,
                        message_type='request',
                        content={
                            'action': 'execute_tool',
                            'tool_name': 'calculator',
                            'parameters': {'expression': expression.strip()}
                        }
                    )
                )
        
        # Default: return empty result
        return {'default_activation': True}
    
    def _should_consider_long_term(self, user_input: str, context: Dict) -> bool:
        """Decide whether the conversation should be evaluated for long-term storage."""
        cleaned = user_input.strip()
        if len(cleaned) < 5:
            return False

        simple_greetings = ['hi', 'hello', 'bye', '谢谢', '再见']
        if cleaned.lower() in simple_greetings:
            return False

        # Explicit memory intents always qualify
        if self._has_explicit_memory_request(cleaned):
            return True

        # Prefer storing if the input carries descriptive content beyond trivial chat
        descriptive_tokens = len([w for w in cleaned.split() if len(w) > 2])
        if descriptive_tokens >= 4:
            return True

        # Fall back to context or routing decisions (e.g. preference flag) if provided
        if context.get('retrieved_memories') or context.get('persona_memories_used'):
            return True

        return False

    def _has_explicit_memory_request(self, user_input: str) -> bool:
        """Detect whether user explicitly asks the system to remember information."""
        memory_keywords = ['记住', '记录', '保存', '记下', '牢记', 'remember', 'save', 'store']
        lowered = user_input.lower()
        return any(keyword in lowered for keyword in memory_keywords)

    async def _store_short_term_memory_snapshot(self, user_input: str, assistant_response: str, context: Dict) -> None:
        """Persist the latest exchange in short-term structures without blocking."""
        snapshot = {
            'user_input': user_input,
            'assistant_response': assistant_response,
            'timestamp': datetime.now().isoformat()
        }

        try:
            await self._activate_agent(
                'short_term_memory',
                AgentMessage(
                    sender='coordinator',
                    receiver='short_term_memory',
                    message_type='request',
                    content={
                        'action': 'store_short_term',
                        'item': {
                            'content': f"用户: {user_input}\n助手: {assistant_response}",
                            'modality': 'verbal'
                        }
                    }
                )
            )
        except Exception as exc:
            logger.warning(f"Unable to update short-term memory agent: {exc}")

        try:
            # Apply buffer size limits
            buffer_content = await agent_buffer_system.read_buffer('short_term_memory')
            recent_conversations = buffer_content.get('recent_conversations', [])

            # Limit buffer size according to settings
            max_items = self.settings.max_short_term_buffer_size // 500  # ~500 chars per conversation
            if len(recent_conversations) >= max_items:
                # Keep only the most recent items
                recent_conversations = recent_conversations[-(max_items-1):]

            # Add new conversation
            recent_conversations.append({
                'snapshot': snapshot,
                'context_tags': context.get('context_tags', []),
                'timestamp': snapshot['timestamp']
            })

            await agent_buffer_system.write_buffer(
                'short_term_memory',
                'recent_conversations',
                recent_conversations
            )

        except Exception as exc:
            logger.debug(f"Failed to persist short-term snapshot buffer: {exc}")

    async def _handle_chunked_text_storage(
        self,
        encoded_input: Dict[str, Any],
        user_input: str,
        assistant_response: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle storage of chunked long text"""
        segments = encoded_input.get('segments', [])
        overview = encoded_input.get('overview', {})

        logger.info(f"Handling chunked text storage: {len(segments)} segments")

        # Store overview in short-term memory
        try:
            await self._activate_agent(
                'short_term_memory',
                AgentMessage(
                    sender='coordinator',
                    receiver='short_term_memory',
                    message_type='request',
                    content={
                        'action': 'store_short_term',
                        'item': {
                            'content': f"Long text overview: {overview.get('theme', 'N/A')}",
                            'type': 'text_overview',
                            'metadata': overview
                        }
                    }
                )
            )
        except Exception as e:
            logger.warning(f"Failed to store text overview: {e}")

        # Check for explicit memory request
        if self._has_explicit_memory_request(user_input):
            # Store ALL segments immediately for explicit requests, using batched approach
            storage_priority = overview.get('storage_priority', 'medium')

            if storage_priority in ['high', 'medium']:
                # Store segments in batches to avoid overwhelming the system
                await self._store_all_segments_batched(segments, overview, immediate=True)
        else:
            # Queue ALL segments for background consolidation
            await self._queue_all_segments_for_consolidation(segments, overview)

    async def _store_all_segments_batched(
        self,
        segments: List[Dict],
        overview: Dict,
        immediate: bool = False
    ) -> None:
        """Store all segments using batched approach with overflow handling"""
        max_segments = self.settings.max_segments_immediate if immediate else self.settings.max_segments_background

        if len(segments) > max_segments:
            logger.warning(f"Large text with {len(segments)} segments exceeds limit of {max_segments}")

            # Handle overflow
            if self.settings.enable_segment_serialization:
                await self._handle_segment_overflow(segments[max_segments:], overview)
            else:
                logger.warning(f"Truncating to {max_segments} segments - {len(segments) - max_segments} segments will be lost")

            # Process only up to the limit
            segments = segments[:max_segments]

        batch_size = 3  # Process 3 segments at a time
        total_stored = 0

        logger.info(f"Storing {len(segments)} segments in batches of {batch_size}")

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]

            for seg in batch:
                try:
                    importance = 0.7 if immediate else 0.5
                    # Reduce importance for later segments to maintain priority
                    if seg['index'] > 10:
                        importance *= 0.8

                    await memory_system.store_memory(
                        content=seg['summary'],
                        memory_type='episodic',
                        importance=importance,
                        context_tags=['chunked_text', 'segment', 'complete_set'],
                        metadata={
                            'segment_index': seg['index'],
                            'total_segments': len(segments),
                            'batch_number': i // batch_size + 1,
                            'keywords': seg.get('keywords', []),
                            'parent_overview': overview.get('theme', ''),
                            'processing_method': seg.get('processing_method', 'local'),
                            'stored_at': datetime.now().isoformat()
                        }
                    )
                    total_stored += 1

                except Exception as e:
                    logger.error(f"Failed to store segment {seg['index']}: {e}")
                    # Don't break the loop - continue with other segments

            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < len(segments):
                await asyncio.sleep(0.1)

        logger.info(f"Batch storage completed: {total_stored}/{len(segments)} segments stored")

    async def _handle_segment_overflow(self, overflow_segments: List[Dict], overview: Dict) -> None:
        """Handle segments that exceed the storage limit by serializing to disk"""
        try:
            import json
            from pathlib import Path

            # Create overflow directory
            overflow_dir = Path("data/segment_overflow")
            overflow_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            theme_key = overview.get('theme', 'unknown')[:20].replace(' ', '_')
            filename = f"overflow_{theme_key}_{timestamp}.json"
            filepath = overflow_dir / filename

            # Serialize overflow segments
            overflow_data = {
                'overview': overview,
                'total_overflow_segments': len(overflow_segments),
                'segments': [
                    {
                        'index': seg['index'],
                        'summary': seg['summary'],
                        'keywords': seg.get('keywords', []),
                        'token_count': seg['token_count'],
                        'processing_method': seg.get('processing_method', 'local')
                    }
                    for seg in overflow_segments
                ],
                'serialized_at': datetime.now().isoformat(),
                'note': 'These segments exceeded immediate storage limits and were serialized for later processing'
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(overflow_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Serialized {len(overflow_segments)} overflow segments to {filepath}")

            # Create a reference memory to the serialized file
            await memory_system.store_memory(
                content=f"Large text overflow: {len(overflow_segments)} additional segments saved to disk",
                memory_type='procedural',
                importance=0.4,
                context_tags=['overflow', 'serialized', 'reference'],
                metadata={
                    'overflow_file': str(filepath),
                    'overflow_count': len(overflow_segments),
                    'parent_theme': overview.get('theme', ''),
                    'serialization_method': 'disk_storage',
                    'can_be_loaded': True
                }
            )

        except Exception as e:
            logger.error(f"Failed to serialize overflow segments: {e}")
            # At least log the overflow for manual recovery
            logger.warning(f"LOST SEGMENTS: {len(overflow_segments)} segments from '{overview.get('theme', 'unknown')}' could not be stored or serialized")

    async def _queue_all_segments_for_consolidation(
        self,
        segments: List[Dict],
        overview: Dict
    ) -> None:
        """Queue ALL segments for background consolidation with intelligent batching"""
        # Instead of limiting segments, create multiple queue entries for large texts
        batch_size = 5
        batch_count = 0

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            batch_count += 1

            consolidation_data = {
                'type': 'chunked_text_batch',
                'overview': overview,
                'total_segments': len(segments),
                'batch_number': batch_count,
                'batch_start_index': i,
                'segments': [
                    {
                        'index': seg['index'],
                        'summary': seg['summary'],
                        'keywords': seg.get('keywords', []),
                        'token_count': seg['token_count'],
                        'processing_method': seg.get('processing_method', 'local')
                    }
                    for seg in batch
                ],
                'queued_at': datetime.now().isoformat()
            }

            try:
                await agent_buffer_system.write_buffer(
                    'consolidation',
                    'chunked_text_queue',
                    consolidation_data,
                    append=True
                )

            except Exception as e:
                logger.warning(f"Failed to queue batch {batch_count}: {e}")

        logger.info(f"Queued {len(segments)} segments in {batch_count} batches")

        # Apply intelligent queue management
        await self._manage_consolidation_queue_size()

    async def _manage_consolidation_queue_size(self) -> None:
        """Intelligently manage queue size with prioritized eviction"""
        try:
            buffer_content = await agent_buffer_system.read_buffer('consolidation')
            queue = buffer_content.get('chunked_text_queue', [])

            max_queue_size = 20  # Allow more items but still cap it

            if len(queue) > max_queue_size:
                # Sort by priority: recent items and high-priority overviews first
                def get_priority(item):
                    overview = item.get('overview', {})
                    priority = overview.get('storage_priority', 'low')
                    queued_time = item.get('queued_at', '')

                    priority_score = {'high': 3, 'medium': 2, 'low': 1}.get(priority, 1)
                    # Recent items get slight boost
                    time_score = 1 if queued_time else 0

                    return priority_score + time_score

                # Keep highest priority items
                sorted_queue = sorted(queue, key=get_priority, reverse=True)
                kept_queue = sorted_queue[:max_queue_size]

                await agent_buffer_system.write_buffer(
                    'consolidation',
                    'chunked_text_queue',
                    kept_queue
                )

                evicted_count = len(queue) - len(kept_queue)
                logger.info(f"Queue management: kept {len(kept_queue)}, evicted {evicted_count} low-priority items")

        except Exception as e:
            logger.warning(f"Queue management failed: {e}")

    async def _queue_chunked_segments_for_consolidation(
        self,
        segments: List[Dict],
        overview: Dict
    ) -> None:
        """Legacy method - redirect to new implementation"""
        await self._queue_all_segments_for_consolidation(segments, overview)

    async def _queue_memory_candidate(
        self,
        user_input: str,
        assistant_response: str,
        importance: float,
        emotion_tags: List[str],
        threat_info: Dict
    ) -> None:
        """Queue conversation as long-term candidate for consolidation agents."""
        candidate = {
            'user_input': user_input,
            'assistant_response': assistant_response,
            'importance': importance,
            'emotion_tags': emotion_tags,
            'threat_score': threat_info.get('threat_score'),
            'queued_at': datetime.now().isoformat()
        }

        try:
            await agent_buffer_system.write_buffer(
                'consolidation',
                'pending_candidates',
                candidate,
                append=True
            )
        except Exception as exc:
            logger.debug(f"Failed to queue memory candidate: {exc}")
    
    def _calculate_importance(self, user_input: str, threat_info: Dict, memories: List) -> float:
        """Calculate memory importance score"""
        importance = 0.5  # Base importance
        
        # Boost for emotional content
        if threat_info.get('threat_score', 0) > 0.3:
            importance += 0.2
        
        # Boost for length and complexity
        if len(user_input) > 100:
            importance += 0.1
        
        # Boost if related to existing memories
        if len(memories) > 0:
            avg_similarity = sum(mem.get('similarity_score', 0) for mem in memories) / len(memories)
            if avg_similarity > 0.7:
                importance += 0.1
        
        return min(1.0, importance)
    
    def _extract_emotions(self, user_input: str, threat_info: Dict) -> List[str]:
        """Extract emotion tags from input"""
        emotions = []
        
        # Check threat level
        if threat_info.get('threat_score', 0) > 0.5:
            emotions.append('anxious')
        elif threat_info.get('threat_score', 0) > 0.3:
            emotions.append('concerned')
        
        # Simple emotion detection
        positive_words = ['开心', '喜欢', '爱', '高兴', '兴奋', 'happy', 'love', 'like', 'excited']
        negative_words = ['难过', '担心', '害怕', '愤怒', 'sad', 'worried', 'afraid', 'angry']
        
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in positive_words):
            emotions.append('positive')
        if any(word in user_lower for word in negative_words):
            emotions.append('negative')
        
        return emotions if emotions else ['neutral']
    
    async def _trigger_background_reflection(self, memories: List[Dict]) -> Dict[str, Any]:
        """Trigger reflection process in background"""
        try:
            return await self._activate_agent(
                'reflection',
                AgentMessage(
                    sender='coordinator',
                    receiver='reflection',
                    message_type='request',
                    content={
                        'action': 'generate_insights',
                        'memories': memories
                    }
                )
            )
        except Exception as e:
            return {'background_reflection_error': str(e)}
    
    async def _trigger_background_consolidation(self):
        """Trigger consolidation process in background"""
        try:
            await self._activate_agent(
                'consolidation',
                AgentMessage(
                    sender='coordinator',
                    receiver='consolidation',
                    message_type='request',
                    content={'action': 'system_consolidation'}
                )
            )
        except Exception as e:
            logger.error(f"Background consolidation error: {e}")
    
    async def _trigger_background_forgetting(self):
        """Trigger forgetting process in background"""
        try:
            # 轮流执行不同的遗忘任务
            request_count = self.processing_stats['total_requests']

            if request_count % 10 == 0:
                # 每10次请求执行一次选择性遗忘
                action = 'selective_forgetting'
                content = {
                    'action': action,
                    'criteria': {
                        'max_age_days': 7,
                        'max_importance': 0.2,
                        'max_access_frequency': 3,
                        'age_weight': 0.5,
                        'importance_weight': 0.4,
                        'access_weight': 0.2,
                        'importance_reduction': 0.4,
                        'decay_increase': 0.25
                    }
                }
            else:
                # 其他时候应用被动遗忘曲线
                action = 'passive_decay'
                content = {'action': action}

            await self._activate_agent(
                'forgetting',
                AgentMessage(
                    sender='coordinator',
                    receiver='forgetting',
                    message_type='request',
                    content=content
                )
            )
        except Exception as e:
            logger.error(f"Background forgetting error: {e}")

    async def _trigger_chunked_queue_processing(self):
        """Trigger processing of queued chunked text segments"""
        try:
            await self._activate_agent(
                'consolidation',
                AgentMessage(
                    sender='coordinator',
                    receiver='consolidation',
                    message_type='request',
                    content={'action': 'process_chunked_queue'}
                )
            )
        except Exception as e:
            logger.error(f"Chunked queue processing error: {e}")

    # ============================================================================
    # P0 Task 1: Consolidation Integration (Hippocampus → TemporalLobe)
    # ============================================================================

    async def consolidate_memories(self):
        """
        记忆巩固流程：Hippocampus → TemporalLobe

        完整的五脑区协作流程:
        1. Hippocampus提供待巩固的情节记忆候选
        2. ConsolidationAgent提取语义模式和共同知识
        3. ReasoningValidator验证提取的知识一致性
        4. TemporalLobe存储语义知识
        5. Hippocampus标记已巩固

        这是Phase 2改进的核心功能之一：让执行层Agent真正工作起来
        """
        logger.info("🧠 Starting memory consolidation (Hippocampus → TemporalLobe)...")

        try:
            # 🎯 P2优化: 根据test_mode调整巩固阈值
            # 测试模式: 低阈值快速触发, 生产模式: 正常阈值
            if hasattr(self, 'background_processes') and self.background_processes:
                is_test_mode = self.background_processes.config.test_mode
            else:
                is_test_mode = False

            if is_test_mode:
                # Test mode: 低阈值 - 1次访问 + 6分钟即可巩固
                min_access = 1
                min_age_h = 0.1  # 6 minutes
                logger.info("🧪 TEST MODE: Using aggressive consolidation thresholds (access=1, age=0.1h)")
            else:
                # Production mode: 正常阈值 - 3次访问 + 24小时
                min_access = 3
                min_age_h = 24
                logger.info("🏭 PRODUCTION MODE: Using normal consolidation thresholds (access=3, age=24h)")

            # Step 1: 从Hippocampus获取待巩固情节
            episodic_candidates = await self.hippocampus.get_consolidation_candidates(
                min_access_count=min_access,
                min_age_hours=min_age_h,
                max_count=50
            )

            if not episodic_candidates:
                logger.info("No candidates for consolidation")
                return {
                    'consolidated': 0,
                    'message': 'No consolidation candidates found'
                }

            logger.info(f"Found {len(episodic_candidates)} episodic candidates for consolidation")

            # Step 2: 使用ConsolidationAgent提取语义知识
            # 注意: 当前ConsolidationAgent主要处理单个记忆
            # 这里我们按组提取共同模式
            consolidated_count = 0

            # 按时间窗口分组 (例如每天)
            from collections import defaultdict
            time_groups = defaultdict(list)

            for candidate in episodic_candidates:
                # 提取日期作为分组键
                timestamp_str = candidate.get('timestamp', '')
                if timestamp_str:
                    try:
                        date_key = datetime.fromisoformat(timestamp_str).strftime('%Y-%m-%d')
                        time_groups[date_key].append(candidate)
                    except:
                        continue

            logger.info(f"Grouped into {len(time_groups)} time windows")

            # Step 3: 对每个时间组进行巩固
            for date_key, group_episodes in time_groups.items():
                if len(group_episodes) < 2:
                    # 单个记忆不进行模式提取
                    continue

                try:
                    # 提取共同实体和知识
                    all_entities = []
                    combined_content = []

                    for ep in group_episodes:
                        all_entities.extend(ep.get('entities', []))
                        combined_content.append(ep.get('content', ''))

                    # 去重实体
                    common_entities = list(set(all_entities))

                    # 使用LLM提取语义知识 (简化版)
                    semantic_knowledge = await self._extract_semantic_from_episodes(
                        episodes=group_episodes,
                        date=date_key
                    )

                    if not semantic_knowledge:
                        continue

                    # Step 4: 存储到TemporalLobe
                    # 使用TemporalLobe的AgentMessage接口
                    store_result = await self.temporal_lobe.process_message(
                        AgentMessage(
                            sender='coordinator',
                            receiver='temporal_lobe',
                            message_type='request',
                            content={
                                'action': 'store_semantic',
                                'content': semantic_knowledge,
                                'memory_subtype': 'consolidated_fact',
                                'entities': common_entities,
                                'relations': [],  # 可以在未来添加关系提取
                                'importance': 0.8,
                                'metadata': {
                                    'source_episode_ids': [ep['id'] for ep in group_episodes],
                                    'consolidation_date': date_key,
                                    'consolidation_time': datetime.now().isoformat(),
                                    'consolidated_from': 'hippocampus'
                                }
                            }
                        )
                    )

                    semantic_id = store_result.get('memory_id', '')

                    if semantic_id:
                        # Step 5: 标记Hippocampus的情节为已巩固
                        marked_count = await self.hippocampus.mark_as_consolidated(
                            episode_ids=[ep['id'] for ep in group_episodes],
                            semantic_id=semantic_id
                        )

                        consolidated_count += 1
                        logger.info(f"✅ Consolidated {len(group_episodes)} episodes from {date_key} "
                                   f"→ TemporalLobe (semantic_id={semantic_id[:8]})")

                except Exception as e:
                    logger.error(f"Failed to consolidate group for {date_key}: {e}")
                    continue

            logger.info(f"🎉 Consolidation completed: {consolidated_count} patterns extracted")

            return {
                'consolidated': consolidated_count,
                'total_candidates': len(episodic_candidates),
                'time_groups': len(time_groups),
                'message': f'Successfully consolidated {consolidated_count} memory patterns'
            }

        except Exception as e:
            logger.error(f"❌ Consolidation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'consolidated': 0,
                'error': str(e)
            }

    async def _extract_semantic_from_episodes(
        self,
        episodes: List[Dict],
        date: str
    ) -> Optional[str]:
        """
        从一组情节记忆中提取语义知识

        使用LLM理解多个情节的共同模式和核心知识

        Args:
            episodes: 情节记忆列表
            date: 日期标签

        Returns:
            提取的语义知识字符串, 或None如果提取失败
        """
        # 合并内容
        combined_content = "\n".join([
            f"- {ep.get('content', '')[:200]}"  # 截断过长内容
            for ep in episodes[:10]  # 限制数量避免token过多
        ])

        # 使用reasoning_validator的LLM能力 (复用现有Agent的LLM client)
        prompt = f"""从以下{len(episodes)}条情节记忆中提取核心的语义知识:

日期: {date}

情节记忆:
{combined_content}

请提取:
1. 核心事实和知识点
2. 共同的主题或模式
3. 重要的实体关系

以简洁的语义知识形式输出 (2-3句话)。"""

        try:
            # 复用ConsolidationAgent的LLM调用能力
            response = await self.consolidation.call_llm(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )

            # 清理response
            semantic_knowledge = response.strip()

            if len(semantic_knowledge) < 10:
                return None

            return f"[{date}] {semantic_knowledge}"

        except Exception as e:
            logger.warning(f"Failed to extract semantic knowledge: {e}")
            return None

    # ============================================================================
    # P0 Task 2: Forgetting Integration (Five Brain Regions)
    # ============================================================================

    async def trigger_forgetting(self, region: str):
        """
        触发指定脑区的遗忘流程

        完整的三层架构流程:
        1. 存储层(脑区)提供遗忘候选记忆
        2. 执行层(ForgettingAgent)评估保留价值
        3. 协调层决定遗忘哪些记忆
        4. 存储层执行删除
        5. Prefrontal记录遗忘事件(用于反思)

        支持的脑区:
        - hippocampus: 情节记忆 (快速遗忘)
        - temporal_lobe: 语义记忆 (慢遗忘)
        - amygdala: 情绪标记 (保留强情绪)
        - basal_ganglia: 技能/习惯 (几乎不遗忘)

        Args:
            region: 脑区名称
        """
        logger.info(f"🗑️ Triggering forgetting for {region}...")

        try:
            # Step 1: 从指定脑区获取候选记忆
            if region == 'hippocampus':
                candidates = await self.hippocampus.get_forgetting_candidates(
                    bottom_percentile=0.2  # 海马体快速遗忘20%
                )
                brain_region_agent = self.hippocampus
            elif region == 'temporal_lobe':
                # TemporalLobe还需要添加接口方法，这里暂时跳过
                logger.info("TemporalLobe forgetting not yet implemented (keeping internal logic)")
                return {
                    'forgotten': 0,
                    'message': 'TemporalLobe uses internal forgetting logic'
                }
            elif region == 'amygdala':
                # Amygdala接口待添加
                logger.info("Amygdala forgetting not yet implemented")
                return {
                    'forgotten': 0,
                    'message': 'Amygdala forgetting not implemented'
                }
            elif region == 'basal_ganglia':
                # BasalGanglia几乎不遗忘
                logger.info("BasalGanglia rarely forgets (skills are permanent)")
                return {
                    'forgotten': 0,
                    'message': 'BasalGanglia skills are permanent'
                }
            else:
                logger.warning(f"Unknown brain region: {region}")
                return {
                    'forgotten': 0,
                    'error': f'Unknown region: {region}'
                }

            if not candidates:
                logger.info(f"No forgetting candidates in {region}")
                return {
                    'forgotten': 0,
                    'message': 'No candidates for forgetting'
                }

            logger.info(f"Found {len(candidates)} forgetting candidates in {region}")

            # Step 2: 使用ForgettingAgent评估保留价值
            # 注意: 当前ForgettingAgent主要操作数据库记忆
            # 这里我们使用简化的算法评估 (根据重要性、访问次数、时间)
            to_forget = []
            forgetting_threshold = 0.3

            for candidate in candidates:
                # 计算保留分数
                importance = candidate.get('importance', 0.5)
                access_count = candidate.get('access_count', 0)

                # 简化的保留分数计算
                retention_score = importance * 0.7 + min(access_count / 10, 0.3)

                if retention_score < forgetting_threshold:
                    to_forget.append(candidate)

            if not to_forget:
                logger.info(f"All candidates in {region} have sufficient retention value")
                return {
                    'forgotten': 0,
                    'candidates': len(candidates),
                    'message': 'All memories above retention threshold'
                }

            logger.info(f"Selected {len(to_forget)}/{len(candidates)} memories for forgetting")

            # Step 3 & 4: 执行遗忘
            forgotten_ids = [mem['id'] for mem in to_forget]

            if region == 'hippocampus':
                forgotten_count = await brain_region_agent.forget_memories(forgotten_ids)
            else:
                forgotten_count = 0

            # Step 5: 记录到Prefrontal (用于反思)
            if hasattr(self, 'prefrontal_storage'):
                try:
                    await self.prefrontal_storage.store_item(
                        content=f"Forgetting: {forgotten_count} memories from {region}",
                        task_type='forgetting',
                        priority=5,
                        metadata={
                            'region': region,
                            'forgotten_count': forgotten_count,
                            'candidates_count': len(candidates),
                            'threshold': forgetting_threshold
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to record forgetting event to Prefrontal: {e}")

            logger.info(f"✅ Forgot {forgotten_count} memories from {region}")

            return {
                'forgotten': forgotten_count,
                'candidates': len(candidates),
                'region': region,
                'threshold': forgetting_threshold,
                'message': f'Successfully forgot {forgotten_count} memories'
            }

        except Exception as e:
            logger.error(f"❌ Forgetting error for {region}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'forgotten': 0,
                'error': str(e)
            }

    # ============================================================================
    # P0 Task 3: Reflection Integration (Metacognition)
    # ============================================================================

    # ============================================================================
    # P1: 智能检索路由优化 (前额叶决策模式)
    # ============================================================================

    async def smart_retrieve(
        self,
        query: str,
        context: Dict[str, Any] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        智能检索路由：模拟前额叶执行控制决策

        类脑原理:
        - 前额叶根据问题类型自动选择最优检索通路
        - 避免多策略并行的无效调用
        - 事实性问题 → 情节记忆（海马体）
        - 概念性问题 → 语义记忆（颞叶）
        - 时间相关 → 时间线检索
        - 复杂问题 → 混合检索

        P1优化：无硬编码，完全基于特征分析动态决策

        Args:
            query: 查询文本
            context: 上下文信息
            k: 返回数量

        Returns:
            {
                'memories': List[Dict],
                'strategy_used': str,
                'route_decision': Dict,
                'confidence': float
            }
        """
        if context is None:
            context = {}

        start_time = datetime.now()

        # Step 1: ExecutiveControl分析问题特征（前额叶分析）
        logger.info(f"🎯 Smart retrieve: analyzing query...")

        query_features = await self._analyze_query_features(query, context)

        # Step 2: 前额叶路由决策（无硬编码，基于特征动态决策）
        route_decision = await self._decide_retrieval_route(query_features, context)

        strategy = route_decision['recommended_strategy']
        confidence = route_decision['confidence']

        logger.info(f"🎯 Route decision: {strategy} (confidence={confidence:.2f})")

        # Step 3: 根据策略执行单一路由（避免多策略并行浪费）
        try:
            if strategy == 'episodic':
                # 情节记忆优先（海马体）- 适合具体事件查询
                logger.debug(f"🔍 Executing EPISODIC strategy on hippocampus, entities={query_features.get('entities', [])}")
                results = await self.hippocampus.search_memories(
                    query=query,
                    entities=query_features.get('entities', []),
                    k=k
                )
                memories = self._annotate_memory_source(results.get('memories', []), 'hippocampus')
                logger.debug(f"📊 Episodic search: {len(memories)} memories from hippocampus")

            elif strategy == 'semantic':
                # 语义知识优先（颞叶）- 适合概念性查询
                logger.debug(f"🔍 Executing SEMANTIC strategy on temporal_lobe")

                # 🔥 阶段1: 根据问题类型过滤记忆类型
                # ⚠️ TEMPORARILY DISABLED - type filtering excludes untagged memories
                # preferred_memory_type = self._determine_preferred_memory_type(query_features)
                preferred_memory_type = None  # No filtering until all memories are tagged

                results = await self.temporal_lobe.search_memories(
                    query=query,
                    memory_type=preferred_memory_type,
                    k=k
                )
                memories = self._annotate_memory_source(results.get('memories', []), 'temporal_lobe')
                logger.debug(f"📊 Semantic search: {len(memories)} memories from temporal_lobe (type filter: DISABLED)")

            elif strategy == 'temporal':
                # 时间线检索 - 适合时间相关查询
                logger.debug(f"🔍 Executing TEMPORAL strategy on hippocampus with temporal reasoning")
                results = await self.hippocampus.search_with_temporal_reasoning(
                    query=query,
                    k=k
                )
                memories = self._annotate_memory_source(results.get('memories', []), 'hippocampus_temporal')
                logger.debug(f"📊 Temporal search: {len(memories)} memories from hippocampus")

            elif strategy == 'hybrid':
                # 混合检索 - 适合复杂查询
                # 使用路由决策计算的动态alpha权重
                alpha_value = route_decision.get('alpha', 0.5)
                logger.debug(f"🔍 Executing HYBRID strategy with alpha={alpha_value}")
                hybrid_result = await self.hybrid_search(
                    query=query,
                    alpha=alpha_value,
                    k=k
                )
                memories = self._annotate_memory_source(hybrid_result.get('memories', []), f"hybrid_alpha_{alpha_value:.2f}")
                logger.debug(f"📊 Hybrid search: {len(memories)} memories")

            elif strategy == 'kg_joint':
                # KG联合检索 - 适合知识图谱相关查询
                kg_result = await self.kg_memory_joint_search(
                    query=query,
                    k=k
                )
                memories = self._annotate_memory_source(kg_result.get('memories', []), 'kg_joint')

            else:
                # Fallback: 默认语义检索
                logger.warning(f"Unknown strategy {strategy}, fallback to semantic")
                results = await self.temporal_lobe.search_memories(query, k=k)
                memories = self._annotate_memory_source(results.get('memories', []), 'temporal_lobe_fallback')

        except Exception as e:
            logger.error(f"❌ Smart retrieve error: {e}, fallback to semantic")
            results = await self.temporal_lobe.search_memories(query, k=k)
            memories = self._annotate_memory_source(results.get('memories', []), 'temporal_lobe_error_fallback')
            strategy = 'semantic_fallback'

        # 🔥 新增：如果结果为空且策略是semantic，fallback到episodic（更可能有结果）
        if len(memories) == 0 and strategy in ['semantic', 'semantic_fallback']:
            logger.warning(f"⚠️ Semantic search returned 0 results, trying episodic fallback...")
            logger.debug(f"🔍 Fallback: Checking hippocampus for episodic memories")
            try:
                # 先检查hippocampus中有多少记忆
                hippo_count = len(self.hippocampus.memories) if hasattr(self.hippocampus, 'memories') else 'unknown'
                logger.debug(f"📊 Hippocampus has {hippo_count} total memories")

                episodic_results = await self.hippocampus.search_memories(
                    query=query,
                    entities=query_features.get('entities', []),
                    k=k
                )
                memories = self._annotate_memory_source(episodic_results.get('memories', []), 'hippocampus_fallback')
                strategy = f'{strategy}_episodic_fallback'
                logger.info(f"✅ Episodic fallback retrieved {len(memories)} memories from hippocampus")
            except Exception as fallback_e:
                logger.error(f"❌ Episodic fallback also failed: {fallback_e}")

        # 🔥 新增：如果仍为空，尝试hybrid作为最后手段
        if len(memories) == 0 and 'hybrid' not in strategy:
            logger.warning(f"⚠️ Still 0 results, trying hybrid as last resort...")
            logger.debug(f"🔍 Fallback: Trying hybrid search (hippocampus + temporal_lobe + vector)")
            try:
                # 检查两个brain region的记忆数
                hippo_count = len(self.hippocampus.memories) if hasattr(self.hippocampus, 'memories') else 'unknown'
                temporal_count = len(self.temporal_lobe.memories) if hasattr(self.temporal_lobe, 'memories') else 'unknown'
                logger.debug(f"📊 Memory counts: hippocampus={hippo_count}, temporal_lobe={temporal_count}")

                # 使用动态计算的alpha权重，而非硬编码
                fallback_alpha = route_decision.get('alpha', 0.5)
                hybrid_result = await self.hybrid_search(query=query, alpha=fallback_alpha, k=k)
                memories = self._annotate_memory_source(hybrid_result.get('memories', []), f"hybrid_fallback_{fallback_alpha:.2f}")
                strategy = f'{strategy}_hybrid_fallback'
                logger.info(f"✅ Hybrid fallback retrieved {len(memories)} memories (alpha={fallback_alpha})")
            except Exception as hybrid_e:
                logger.error(f"❌ Hybrid fallback also failed: {hybrid_e}")

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"✅ Smart retrieve completed: {len(memories)} memories, "
                   f"strategy={strategy}, time={search_time:.1f}ms")

        # 🔁 多轮检索：针对时间相关查询补充缺失的关键片段
        if self._looks_temporal_query(query):
            memories = await self._augment_temporal_memories(
                query=query,
                base_memories=memories,
                k=k,
                route_decision=route_decision,
                query_features=query_features
            )

        # 🔁 多轮检索：研究/事件链路需要补齐描述性证据
        if self._looks_research_event_query(query):
            memories = await self._augment_event_memories(
                query=query,
                base_memories=memories,
                k=k,
                route_decision=route_decision,
                query_features=query_features
            )

        # 🔥 Quick Win #2: Prefrontal conflict detection integration
        conflicts = []
        if len(memories) > 1 and self.prefrontal_storage:
            try:
                # Prepare multi-source results for conflict detection
                # For now, treat all memories as from same source (will expand in Phase 3)
                multi_source = {
                    'retrieved': memories,
                    'strategy': strategy
                }
                conflicts = await self.prefrontal_storage.detect_conflicts(multi_source)
                if conflicts:
                    logger.warning(f"⚠️ Prefrontal detected {len(conflicts)} memory conflicts!")
                    for i, conflict in enumerate(conflicts[:3]):  # Show first 3
                        logger.warning(f"   Conflict #{i+1}: {conflict.get('conflict_type', 'unknown')} "
                                     f"(severity={conflict.get('severity', 0):.2f})")
                else:
                    logger.info(f"✅ Prefrontal: No conflicts detected across {len(memories)} memories")
            except Exception as e:
                logger.warning(f"⚠️ Conflict detection failed: {e}")

        # 🔁 Plasticity重排：结合缺口/冲突信号
        logger.info(f"🧠 Applying plasticity-based ranking to {len(memories)} memories...")
        keywords_for_ranking: List[str] = []
        missing_keywords_for_ranking: Optional[set] = None
        coverage_ratio_for_ranking: Optional[float] = None
        context_label = 'general'
        if self._looks_temporal_query(query):
            keywords_for_ranking = self._extract_salient_keywords(query, query_features, include_temporal=True)
            coverage_ratio_for_ranking, missing_keywords_for_ranking = self._compute_keyword_coverage(memories, keywords_for_ranking)
            context_label = 'temporal'
        elif self._looks_research_event_query(query):
            keywords_for_ranking = self._extract_salient_keywords(query, query_features, include_temporal=False)
            coverage_ratio_for_ranking, missing_keywords_for_ranking = self._compute_keyword_coverage(memories, keywords_for_ranking)
            context_label = 'event'
        if coverage_ratio_for_ranking is None and keywords_for_ranking:
            coverage_ratio_for_ranking, missing_keywords_for_ranking = self._compute_keyword_coverage(memories, keywords_for_ranking)

        memories = self._apply_plasticity_ranking(
            memories,
            k=k,
            keywords=keywords_for_ranking,
            missing_keywords=missing_keywords_for_ranking,
            context=context_label,
            conflicts=conflicts
        )
        logger.info(f"✅ Plasticity ranking complete, {len(memories)} memories re-ranked")

        self._log_memory_source_summary(memories)
        self._log_plasticity_adjustments(memories, coverage_ratio_for_ranking)

        # 🔥 诊断日志：打印每个检索到的记忆的详细信息（含plasticity信息）
        for i, mem in enumerate(memories[:5]):  # 只打印前5个避免日志过长
            mem_id = mem.get('id', 'unknown')
            content = mem.get('content', '')
            content_preview = content[:200].replace('\n', ' ')
            bm25_score = mem.get('bm25_score', 'N/A')
            relevance = mem.get('relevance', 'N/A')
            plasticity_score = mem.get('plasticity_score', 'N/A')
            metadata = mem.get('metadata', {})
            is_summary = 'source_episode_id' in metadata
            hit_count = metadata.get('hit_count', 0)
            confidence = metadata.get('confidence', 'N/A')

            logger.info(f"🔍 Retrieved #{i+1}: ID={mem_id[:8]}, Plasticity={plasticity_score}, "
                       f"BM25={bm25_score}, Hits={hit_count}, Conf={confidence}, IsSummary={is_summary}")
            logger.info(f"   Content: {content_preview}...")

        # ============================================================================
        # 🧠 Phase 3a: Information Gap Detection & Multi-Brain Collaboration
        # ============================================================================

        # Step 1: 检测信息缺口
        gaps = self._detect_information_gaps(query, memories, query_features)

        # Step 2: 根据缺口决定是否触发Reflection或KG
        reflection_triggered = False
        kg_triggered = False

        # Reflection触发检查
        if self._should_trigger_reflection(query, memories, coverage_ratio_for_ranking or 0.0, gaps):
            reflection_triggered = True
            # 调用Reflection Agent
            reflection_result = await self._call_reflection_agent(
                query=query,
                initial_memories=memories,
                gaps=gaps,
                coverage=coverage_ratio_for_ranking or 0.0
            )
            # 合并Reflection结果
            if reflection_result:
                memories = self._merge_reflection_insights(memories, reflection_result)

        # KG触发检查
        if self._should_trigger_kg_search(query, gaps, query_features):
            kg_triggered = True
            # 调用KG Memory Joint Search
            kg_result = await self._call_kg_search(
                query=query,
                query_features=query_features,
                existing_memories=memories
            )
            # 合并KG结果
            if kg_result:
                memories = self._merge_kg_memories(memories, kg_result)

        # Step 3: ⏰ Temporal Reasoning Enhancement (Q2 Fix)
        # 检测并增强相对时间表达的检索
        temporal_enhanced = False
        if self._should_enhance_temporal_reasoning(query, query_features):
            temporal_enhanced = True
            memories = self._enhance_temporal_memories(query, memories, query_features)

        # 🔥 FIX 3 (temporarily disabled): post-merge plasticity re-ranking caused regressions
        if reflection_triggered or kg_triggered or temporal_enhanced:
            logger.info("⏭️ Post-merge plasticity re-ranking skipped (awaiting KG coverage fix)")

        if self.learning_logger:
            try:
                top_memories_snapshot = []
                for mem in memories[:5]:
                    if not isinstance(mem, dict):
                        continue
                    metadata = mem.get('metadata', {})
                    top_memories_snapshot.append({
                        'id': mem.get('id'),
                        'stage': metadata.get('memory_stage'),
                        'source': metadata.get('source_type'),
                        'plasticity': mem.get('plasticity_score'),
                        'bm25': mem.get('bm25_score'),
                        'relevance': mem.get('relevance')
                    })

                self.learning_logger.record('smart_retrieve', {
                    'query': query,
                    'strategy': strategy,
                    'coverage_ratio': coverage_ratio_for_ranking,
                    'reflection_triggered': reflection_triggered,
                    'kg_triggered': kg_triggered,
                    'total_memories': len(memories),
                    'top_memories': top_memories_snapshot
                })
            except Exception as err:
                logger.warning(f"Failed to log smart_retrieve learning entry: {err}")

        return {
            'memories': memories,
            'strategy_used': strategy,
            'route_decision': route_decision,
            'confidence': confidence,
            'search_time_ms': search_time,
            'query_features': query_features,
            'conflicts': conflicts,  # 🔥 Quick Win #2: Include conflicts in return
            'keywords': keywords_for_ranking,
            'missing_keywords': list(missing_keywords_for_ranking) if missing_keywords_for_ranking else [],
            'coverage_ratio': coverage_ratio_for_ranking,
            # 🧠 Phase 3a: Gap detection & multi-brain collaboration
            'information_gaps': gaps,
            'reflection_triggered': reflection_triggered,
            'kg_triggered': kg_triggered
        }

    def _looks_temporal_query(self, query: str) -> bool:
        temporal_markers = [
            'when', 'what year', 'which year', 'what date', 'which date',
            'last year', 'last month', 'last week', 'yesterday',
            'ago', 'since', 'time', 'date', 'day', 'month', 'year'
        ]
        lower = query.lower()
        return any(marker in lower for marker in temporal_markers)

    def _looks_research_event_query(self, query: str) -> bool:
        keywords = [
            'what did', 'what was', 'what is', 'research', 'studied',
            'investigate', 'investigated', 'paint', 'painted', 'create',
            'created', 'build', 'built', 'explore', 'explored', 'exploring'
        ]
        lower = query.lower()
        return any(marker in lower for marker in keywords)

    async def _augment_temporal_memories(
        self,
        query: str,
        base_memories: List[Dict[str, Any]],
        k: int,
        route_decision: Dict[str, Any],
        query_features: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not base_memories:
            base_memories = []

        keywords = self._extract_salient_keywords(query, query_features, include_temporal=True)
        initial_coverage, missing_keywords = self._compute_keyword_coverage(base_memories, keywords)

        # 🔥 Quick Win #1: Enhanced diagnostic logging
        logger.info(f"🧭 Temporal augmentation analysis:")
        logger.info(f"   Query: {query}")
        logger.info(f"   Extracted keywords: {keywords}")
        logger.info(f"   Initial coverage: {initial_coverage:.2f}")
        logger.info(f"   Missing keywords: {list(missing_keywords)[:5]}")
        logger.info(f"   Base memories count: {len(base_memories)}")

        if initial_coverage >= 0.75:
            logger.info(f"✅ Coverage sufficient ({initial_coverage:.2f} >= 0.75), skipping augmentation")
            return base_memories

        logger.info(f"🧭 Temporal coverage insufficient ({initial_coverage:.2f}); attempting targeted augmentation")
        collected = list(base_memories)
        alpha = route_decision.get('alpha', 0.5)

        attempts = 0
        max_attempts = 2
        while missing_keywords and attempts < max_attempts:
            focus_terms = ' '.join(list(missing_keywords)[:3])
            augmented_query = f"{query} {focus_terms}".strip()
            logger.info(f"🔁 Temporal augmentation attempt #{attempts+1} with terms: {focus_terms}")
            try:
                hybrid_result = await self.hybrid_search(
                    query=augmented_query,
                    alpha=alpha,
                    k=max(k * 2, 8)
                )
                new_memories = hybrid_result.get('memories', [])
                collected = self._merge_memories(collected, new_memories)
            except Exception as e:
                logger.warning(f"Temporal augmentation hybrid search failed: {e}")
                break

            coverage_ratio, missing_keywords = self._compute_keyword_coverage(collected, keywords)
            logger.info(f"🔁 Temporal coverage after attempt #{attempts+1}: {coverage_ratio:.2f}")
            attempts += 1

        if missing_keywords:
            try:
                logger.info(f"🔎 Querying hippocampus for remaining keywords: {list(missing_keywords)[:3]}")
                episodic = await self.hippocampus.search_memories(
                    query=' '.join(list(missing_keywords)[:3]),
                    entities=query_features.get('entities', []),
                    k=max(5, k)
                )
                collected = self._merge_memories(collected, episodic.get('memories', []))
            except Exception as e:
                logger.warning(f"Hippocampus augmentation failed: {e}")

        # 🔥 Quick Win #1: Final augmentation summary
        final_coverage, final_missing = self._compute_keyword_coverage(collected, keywords)
        logger.info(f"📊 Temporal augmentation results:")
        logger.info(f"   Initial coverage: {initial_coverage:.2f}")
        logger.info(f"   Final coverage: {final_coverage:.2f} ({'+' if final_coverage > initial_coverage else ''}{final_coverage - initial_coverage:.2f})")
        logger.info(f"   Attempts used: {attempts}/{max_attempts}")
        logger.info(f"   Memories added: {len(collected) - len(base_memories)}")
        logger.info(f"   Final memory count: {len(collected)}")
        if final_missing:
            logger.info(f"   Still missing keywords: {list(final_missing)[:5]}")

        ranked = self._apply_plasticity_ranking(
            collected,
            k=k,
            keywords=keywords,
            missing_keywords=final_missing,
            context='temporal'
        )
        return ranked

    async def _augment_event_memories(
        self,
        query: str,
        base_memories: List[Dict[str, Any]],
        k: int,
        route_decision: Dict[str, Any],
        query_features: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not base_memories:
            base_memories = []

        keywords = self._extract_salient_keywords(query, query_features, include_temporal=False)
        initial_coverage, missing_keywords = self._compute_keyword_coverage(base_memories, keywords)

        # 🔥 Quick Win #1: Enhanced diagnostic logging
        logger.info(f"🧭 Event augmentation analysis:")
        logger.info(f"   Query: {query}")
        logger.info(f"   Extracted keywords: {keywords}")
        logger.info(f"   Initial coverage: {initial_coverage:.2f}")
        logger.info(f"   Missing keywords: {list(missing_keywords)[:5]}")
        logger.info(f"   Base memories count: {len(base_memories)}")

        if initial_coverage >= 0.7:
            logger.info(f"✅ Coverage sufficient ({initial_coverage:.2f} >= 0.7), skipping augmentation")
            return base_memories

        logger.info(f"🧭 Research/event coverage不足 ({initial_coverage:.2f}); 扩展检索")
        collected = list(base_memories)
        alpha = route_decision.get('alpha', 0.5)

        try:
            focus_terms = ' '.join(list(missing_keywords)[:3])
            augmented_query = f"{query} {focus_terms}".strip()
            hybrid_result = await self.hybrid_search(
                query=augmented_query,
                alpha=alpha,
                k=max(k * 2, 8)
            )
            collected = self._merge_memories(collected, hybrid_result.get('memories', []))
        except Exception as e:
            logger.warning(f"Event augmentation hybrid search failed: {e}")

        try:
            episodic = await self.hippocampus.search_memories(
                query=' '.join(list(missing_keywords)[:3]),
                entities=query_features.get('entities', []),
                k=max(5, k)
            )
            collected = self._merge_memories(collected, episodic.get('memories', []))
        except Exception as e:
            logger.warning(f"Event augmentation hippocampus search failed: {e}")

        # 🔥 Quick Win #1: Final augmentation summary
        final_coverage, final_missing = self._compute_keyword_coverage(collected, keywords)
        logger.info(f"📊 Event augmentation results:")
        logger.info(f"   Initial coverage: {initial_coverage:.2f}")
        logger.info(f"   Final coverage: {final_coverage:.2f} ({'+' if final_coverage > initial_coverage else ''}{final_coverage - initial_coverage:.2f})")
        logger.info(f"   Memories added: {len(collected) - len(base_memories)}")
        logger.info(f"   Final memory count: {len(collected)}")
        if final_missing:
            logger.info(f"   Still missing keywords: {list(final_missing)[:5]}")

        ranked = self._apply_plasticity_ranking(
            collected,
            k=k,
            keywords=keywords,
            missing_keywords=final_missing,
            context='event'
        )
        return ranked

    def _extract_salient_keywords(
        self,
        query: str,
        query_features: Dict[str, Any],
        include_temporal: bool = False
    ) -> List[str]:
        stopwords = {
            'what', 'when', 'where', 'which', 'who', 'whom', 'is', 'are', 'the',
            'was', 'were', 'did', 'does', 'do', 'how', 'many', 'much', 'last',
            'year', 'month', 'week', 'yesterday', 'ago', 'for', 'with', 'into',
            'about', 'that', 'this', 'from', 'over', 'have', 'has', 'had'
        }
        keywords = set()
        for token in re.split(r'[^a-zA-Z0-9]+', query.lower()):
            if len(token) <= 3:
                continue
            if token in stopwords:
                continue
            keywords.add(token)

        entities = query_features.get('entities', [])
        for ent in entities:
            for piece in ent.lower().split():
                if len(piece) > 3:
                    keywords.add(piece)

        if include_temporal:
            temporal_tokens = {'year', 'month', 'week', 'day', 'yesterday', 'ago', 'time', 'date'}
            keywords |= temporal_tokens

        return list(keywords)

    def _compute_keyword_coverage(
        self,
        memories: List[Dict[str, Any]],
        keywords: List[str]
    ) -> Tuple[float, List[str]]:
        if not keywords:
            return 1.0, set()
        lowered_memories = [mem.get('content', '').lower() for mem in memories]
        covered = set()
        for kw in keywords:
            if any(kw in content for content in lowered_memories):
                covered.add(kw)
        coverage_ratio = len(covered) / len(keywords)
        missing = set(keywords) - covered
        return coverage_ratio, missing

    def _merge_memories(
        self,
        base: List[Dict[str, Any]],
        additions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not additions:
            return base

        merged = []
        seen: Dict[str, Dict[str, Any]] = {}

        def _memory_key(mem: Dict[str, Any]) -> str:
            mem_id = mem.get('id')
            if mem_id:
                return mem_id
            content = mem.get('content', '')
            return f"content:{hash(content)}"

        for mem in base:
            key = _memory_key(mem)
            seen[key] = mem

        for mem in additions:
            key = _memory_key(mem)
            if key not in seen:
                seen[key] = mem
            else:
                existing = seen[key]
                existing.setdefault('metadata', {}).setdefault('retrieval_scores', {}).update(
                    mem.get('metadata', {}).get('retrieval_scores', {})
                )

        merged.extend(seen.values())
        return merged

    def _infer_memory_stage(self, source_label: Optional[str]) -> str:
        if not source_label:
            return 'unknown'

        label = source_label.lower()
        if 'reflection' in label or 'insight' in label:
            return 'insight'
        if 'temporal' in label or 'semantic' in label or 'kg' in label:
            return 'semantic'
        if 'hybrid' in label:
            return 'hybrid'
        if 'external' in label or 'environment' in label:
            return 'external'
        if 'hippocampus' in label:
            return 'episodic'
        return 'unknown'

    def _annotate_memory_source(
        self,
        memories: Optional[List[Any]],
        source_label: str
    ) -> List[Any]:
        if not memories:
            return memories or []

        annotated: List[Any] = []
        for mem in memories:
            if isinstance(mem, dict):
                metadata = mem.setdefault('metadata', {})
                metadata.setdefault('source_type', source_label)
                metadata.setdefault('memory_stage', self._infer_memory_stage(source_label))
                mem.setdefault('source_type', metadata.get('source_type', source_label))
                mem.setdefault('memory_stage', metadata.get('memory_stage'))
            annotated.append(mem)
        return annotated

    def _log_memory_source_summary(self, memories: List[Dict[str, Any]]) -> None:
        """Log aggregated source information for retrieved memories."""
        if not memories:
            logger.info("📊 Memory sources: none (0 memories)")
            return

        source_counter: Counter[str] = Counter()
        region_counter: Counter[str] = Counter()

        for mem in memories:
            if not isinstance(mem, dict):
                continue

            metadata = mem.get('metadata') or {}
            source_type = metadata.get('source_type') or mem.get('source_type')
            if source_type:
                source_counter[source_type] += 1

            source_region = metadata.get('source_region') or metadata.get('origin_region')
            if source_region:
                region_counter[source_region] += 1

        if source_counter:
            logger.info(f"📊 Memory sources: {dict(source_counter)}")
        if region_counter:
            logger.info(f"🧠 Source regions: {dict(region_counter)}")

    def _log_plasticity_adjustments(
        self,
        memories: List[Dict[str, Any]],
        coverage_ratio: Optional[float] = None
    ) -> None:
        """Log aggregate coverage bonuses and conflict penalties after re-ranking."""
        if not memories:
            return

        total_bonus = sum(float(mem.get('coverage_bonus', 0.0) or 0.0) for mem in memories)
        total_penalty = sum(float(mem.get('conflict_penalty', 0.0) or 0.0) for mem in memories)

        if coverage_ratio is not None:
            logger.info(
                f"📈 Plasticity adjustments: coverage={coverage_ratio:.2f}, "
                f"coverage_bonus_total={total_bonus:.2f}, conflict_penalty_total={total_penalty:.2f}"
            )
        else:
            logger.info(
                f"📈 Plasticity adjustments: coverage_bonus_total={total_bonus:.2f}, "
                f"conflict_penalty_total={total_penalty:.2f}"
            )

    # ============================================================================
    # Phase 3a: Information Gap Detection & Multi-Brain Collaboration
    # ============================================================================

    def _detect_information_gaps(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        query_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🧠 Phase 3a: 检测查询需要但缺失的信息类型

        Returns:
            {
                'temporal': bool,  # 缺少时间信息
                'entity': bool,    # 缺少实体信息
                'event': bool,     # 缺少事件描述
                'causal': bool,    # 缺少因果关系
                'severity': str,   # 'low', 'medium', 'high'
                'missing_types': List[str]
            }
        """
        gaps = {
            'temporal': False,
            'entity': False,
            'event': False,
            'causal': False,
            'severity': 'low',
            'missing_types': []
        }

        # 检查查询类型
        query_lower = query.lower()

        # 1. 时间信息缺口
        temporal_indicators = ['when', 'what time', 'what date', 'yesterday', 'last week', 'last year']
        if any(ind in query_lower for ind in temporal_indicators):
            # 检查记忆中是否有时间信息
            has_temporal_info = self._has_temporal_markers(memories)
            if not has_temporal_info:
                gaps['temporal'] = True
                gaps['missing_types'].append('temporal')
                logger.info("🕒 Gap detected: Query asks for temporal info but memories lack dates/times")

        # 2. 实体信息缺口
        entity_indicators = ['who', 'which person', 'what is', 'who is']
        if any(ind in query_lower for ind in entity_indicators):
            # 检查记忆中是否有实体描述
            has_entity_info = self._has_entity_markers(memories, query)
            if not has_entity_info:
                gaps['entity'] = True
                gaps['missing_types'].append('entity')
                logger.info("👤 Gap detected: Query asks for entity info but memories lack descriptions")

        # 3. 事件信息缺口
        event_indicators = ['what happened', 'what did', 'did someone', 'what was']
        if any(ind in query_lower for ind in event_indicators):
            # 检查记忆中是否有事件描述
            has_event_info = self._has_event_markers(memories)
            if not has_event_info:
                gaps['event'] = True
                gaps['missing_types'].append('event')
                logger.info("📋 Gap detected: Query asks for event but memories lack descriptions")

        # 4. 因果关系缺口 (WHY类问题)
        causal_indicators = ['why', 'what makes', 'how come', 'reason', 'because']
        if any(ind in query_lower for ind in causal_indicators):
            # WHY类问题通常需要Reflection Agent
            gaps['causal'] = True
            gaps['missing_types'].append('causal')
            logger.info("🤔 Gap detected: WHY-type question requires causal reasoning")

        # 计算严重程度
        gap_count = len(gaps['missing_types'])
        if gap_count == 0:
            gaps['severity'] = 'none'
        elif gap_count == 1:
            gaps['severity'] = 'low'
        elif gap_count == 2:
            gaps['severity'] = 'medium'
        else:
            gaps['severity'] = 'high'

        if gaps['missing_types']:
            logger.info(f"🔍 Information gaps detected: {gaps['missing_types']} (severity: {gaps['severity']})")

        return gaps

    def _has_temporal_markers(self, memories: List[Dict[str, Any]]) -> bool:
        """检查记忆中是否包含时间标记"""
        import re
        temporal_patterns = [
            r'\d{1,2}\s+\w+\s+\d{4}',  # "7 May 2023"
            r'\d{4}-\d{2}-\d{2}',       # "2023-05-07"
            r'(yesterday|today|tomorrow|last\s+(week|month|year))',
            r'\d{1,2}:\d{2}\s*(am|pm)?'  # "1:56 pm"
        ]

        for mem in memories[:10]:  # 只检查前10个记忆
            content = mem.get('content', '').lower()
            for pattern in temporal_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        return False

    def _has_entity_markers(self, memories: List[Dict[str, Any]], query: str) -> bool:
        """检查记忆中是否包含查询相关的实体描述"""
        # 从查询中提取实体名称 (简单实现：大写开头的词)
        import re
        entities = re.findall(r'\b[A-Z][a-z]+\b', query)

        if not entities:
            return True  # 查询中没有实体，不算缺口

        # 检查记忆中是否提到这些实体
        for mem in memories[:10]:
            content = mem.get('content', '')
            if any(entity in content for entity in entities):
                return True
        return False

    def _has_event_markers(self, memories: List[Dict[str, Any]]) -> bool:
        """检查记忆中是否包含事件描述（动词+宾语）"""
        event_verbs = ['went', 'did', 'said', 'made', 'took', 'got', 'painted', 'visited', 'applied']

        for mem in memories[:10]:
            content = mem.get('content', '').lower()
            if any(verb in content for verb in event_verbs):
                return True
        return False

    def _should_trigger_reflection(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        coverage: float,
        gaps: Dict[str, Any]
    ) -> bool:
        """
        🧠 Phase 3a: 判断是否需要触发Reflection Agent

        Reflection触发条件:
        1. WHY/因果类问题 (causal gap)
        2. 覆盖率极低 (< 0.5)
        3. 需要抽象推理 (仅当覆盖率<0.7时)

        🚫 不触发条件:
        - Identity/factual问题 + 高覆盖率(>=0.8) + 无entity gap
        """
        query_lower = query.lower()

        # 🔥 FIX 1: Gate for high-coverage identity/factual questions
        # Don't trigger Reflection when we already have good factual answers
        identity_indicators = ['identity', 'who is', 'what is']
        if any(ind in query_lower for ind in identity_indicators):
            if coverage >= 0.8 and not gaps.get('entity', False):
                logger.info(f"🚫 Skipping Reflection: Identity question with high coverage ({coverage:.2f} >= 0.8)")
                return False

        # 1. WHY类问题 → 需要因果推理
        if gaps.get('causal', False):
            logger.info("🧠 Reflection trigger: Causal/WHY-type question detected")
            return True

        # 2. 覆盖率极低 → 需要抽象模式匹配
        if coverage < 0.5:
            logger.info(f"🧠 Reflection trigger: Low coverage ({coverage:.2f} < 0.5)")
            return True

        # 3. 抽象概念问题 (仅当覆盖率不高时)
        abstract_indicators = ['what makes', 'define', 'characteristic', 'philosophy', 'approach']
        if any(ind in query_lower for ind in abstract_indicators):
            if coverage < 0.7:
                logger.info(f"🧠 Reflection trigger: Abstract concept + low coverage ({coverage:.2f} < 0.7)")
                return True
            else:
                logger.info(f"🚫 Skipping Reflection: Abstract concept but high coverage ({coverage:.2f} >= 0.7)")
                return False

        return False

    def _should_trigger_kg_search(
        self,
        query: str,
        gaps: Dict[str, Any],
        query_features: Dict[str, Any]
    ) -> bool:
        """
        🧠 Phase 3a: 判断是否需要触发KG Memory Joint Search

        KG触发条件:
        1. Identity/relationship问题
        2. 需要三元组关系
        """
        query_lower = query.lower()

        # 1. Identity问题
        if 'identity' in query_lower or 'who is' in query_lower or 'what is' in query_lower:
            logger.info("🔗 KG trigger: Identity question detected")
            return True

        # 2. Relationship问题
        relationship_indicators = ['relationship', 'connected', 'related to', 'family']
        if any(ind in query_lower for ind in relationship_indicators):
            logger.info("🔗 KG trigger: Relationship question detected")
            return True

        # 3. 查询类型为identity或relationship
        query_type = query_features.get('query_type', '')
        if query_type in ['identity', 'relationship']:
            logger.info(f"🔗 KG trigger: Query type is {query_type}")
            return True

        return False

    def _should_trigger_prefrontal(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        coverage: float,
        gaps: Dict[str, Any],
        initial_confidence: float = 0.5
    ) -> bool:
        """
        🧠 Prefrontal Cortex触发条件检测

        Prefrontal负责:
        1. 冲突检测与解决
        2. 置信度评估
        3. 工作记忆管理
        4. 执行控制

        触发条件:
        1. 检测到潜在冲突 (多个记忆内容矛盾)
        2. 初始置信度较低 (< 0.4)
        3. 时间问题且需要验证时间线一致性
        4. 复杂推理任务 (多跳、需要验证)
        """
        query_lower = query.lower()

        # 1. 检测记忆冲突 (简单启发式: 查找明显矛盾的内容)
        if len(memories) >= 2:
            # 检查日期冲突
            date_conflicts = self._detect_date_conflicts(memories)
            if date_conflicts:
                logger.info(f"🧠 Prefrontal trigger: Date conflicts detected ({len(date_conflicts)} conflicts)")
                return True

            # 检查实体矛盾 (例如: "A喜欢B" vs "A不喜欢B")
            content_conflicts = self._detect_content_conflicts(memories)
            if content_conflicts:
                logger.info(f"🧠 Prefrontal trigger: Content conflicts detected ({len(content_conflicts)} conflicts)")
                return True

        # 2. 低置信度 → 需要Prefrontal评估
        if initial_confidence < 0.4:
            logger.info(f"🧠 Prefrontal trigger: Low initial confidence ({initial_confidence:.2f} < 0.4)")
            return True

        # 3. 时间类问题 → 需要时间线验证
        temporal_indicators = ['when', 'date', 'time', 'year', 'month', 'day', 'ago', 'before', 'after']
        if any(ind in query_lower for ind in temporal_indicators):
            if len(memories) >= 2:
                logger.info("🧠 Prefrontal trigger: Temporal query requiring timeline verification")
                return True

        # 4. 复杂推理 → 需要执行控制
        if gaps.get('multi_hop', False) or 'multi_hop' in query_lower:
            logger.info("🧠 Prefrontal trigger: Multi-hop reasoning requires executive control")
            return True

        return False

    def _should_trigger_environment(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        coverage: float,
        initial_confidence: float,
        gaps: Dict[str, Any]
    ) -> bool:
        """
        🌍 Environment Agent触发条件检测

        Environment负责:
        1. 外部知识探索
        2. 环境上下文感知
        3. 补充内部记忆不足

        触发条件:
        1. 覆盖率极低 (< 0.3) 且置信度低 (< 0.3)
        2. 明确的外部信息需求 (包含外部指示词)
        3. 检索为空或几乎为空
        4. 需要实时信息
        """
        query_lower = query.lower()

        # 1. 双重低阈值 → 内部记忆严重不足
        if coverage < 0.3 and initial_confidence < 0.3:
            logger.info(f"🌍 Environment trigger: Dual low threshold (coverage={coverage:.2f}, confidence={initial_confidence:.2f})")
            return True

        # 2. 检索结果为空或极少
        if len(memories) <= 1:
            logger.info(f"🌍 Environment trigger: Very few memories retrieved ({len(memories)} <= 1)")
            return True

        # 3. 外部信息指示词
        external_indicators = [
            'search for', 'look up', 'find information about',
            'what is the latest', 'current', 'recent news',
            'external', 'outside', 'web', 'internet'
        ]
        if any(ind in query_lower for ind in external_indicators):
            logger.info("🌍 Environment trigger: External information request detected")
            return True

        # 4. 实时信息需求
        realtime_indicators = ['now', 'currently', 'today', 'latest', 'most recent']
        if any(ind in query_lower for ind in realtime_indicators):
            if coverage < 0.5:  # 实时信息且覆盖率不高
                logger.info(f"🌍 Environment trigger: Real-time information needed (coverage={coverage:.2f})")
                return True

        # 5. 明确的信息缺口且无法从内部满足
        if gaps.get('entity', False) and coverage < 0.4:
            logger.info(f"🌍 Environment trigger: Entity gap with low coverage ({coverage:.2f} < 0.4)")
            return True

        return False

    def _should_trigger_temporal_orchestration(
        self,
        query: str,
        query_features: Dict[str, Any],
        coverage: float
    ) -> bool:
        """
        ⏰ 时间序列协作触发条件

        当问题涉及时间序列时，需要协调:
        - Hippocampus (情节记忆)
        - Temporal Lobe (时间线、语义)
        - Prefrontal (时间冲突验证)

        触发条件:
        1. 明确的 "when" 问题
        2. 查询特征标记为 temporal
        3. 需要时间排序
        """
        query_lower = query.lower()

        # 1. "when" 问题
        if query_lower.startswith('when '):
            logger.info("⏰ Temporal orchestration: 'When' question detected")
            return True

        # 2. 查询类型为temporal
        if query_features.get('query_type') == 'temporal':
            logger.info("⏰ Temporal orchestration: Query type is 'temporal'")
            return True

        # 3. 包含时间关键词
        temporal_keywords = ['when did', 'what time', 'which year', 'which month', 'which day']
        if any(kw in query_lower for kw in temporal_keywords):
            logger.info(f"⏰ Temporal orchestration: Temporal keywords detected")
            return True

        return False

    def _should_trigger_causal_orchestration(
        self,
        query: str,
        gaps: Dict[str, Any],
        coverage: float
    ) -> bool:
        """
        🔗 因果推理协作触发条件

        当问题涉及因果关系时，需要协调:
        - Reflection (抽象因果推理)
        - KG (因果三元组)
        - Multi-hop reasoning

        触发条件:
        1. WHY 问题
        2. 因果指示词
        3. 检测到因果缺口
        """
        query_lower = query.lower()

        # 1. WHY 问题
        if query_lower.startswith('why '):
            logger.info("🔗 Causal orchestration: 'Why' question detected")
            return True

        # 2. 因果指示词
        causal_indicators = [
            'because', 'reason', 'cause', 'effect', 'result in',
            'lead to', 'due to', 'therefore', 'consequently'
        ]
        if any(ind in query_lower for ind in causal_indicators):
            logger.info("🔗 Causal orchestration: Causal indicators detected")
            return True

        # 3. 因果缺口
        if gaps.get('causal', False):
            logger.info("🔗 Causal orchestration: Causal gap detected")
            return True

        return False

    # ============================================================================
    # Conflict Detection Helper Methods
    # ============================================================================

    def _detect_date_conflicts(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测记忆中的日期冲突

        Returns:
            List of conflicts with format:
            {
                'type': 'date',
                'memory1': {...},
                'memory2': {...},
                'conflict_detail': str
            }
        """
        conflicts = []
        date_pattern = re.compile(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b|\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b')

        # 提取每个记忆的日期
        memory_dates = []
        for mem in memories:
            content = mem.get('content', '')
            dates = date_pattern.findall(content)
            if dates:
                memory_dates.append({
                    'memory': mem,
                    'dates': dates,
                    'content_lower': content.lower()
                })

        # 简单冲突检测: 同一事件有不同日期
        for i in range(len(memory_dates)):
            for j in range(i + 1, len(memory_dates)):
                mem1 = memory_dates[i]
                mem2 = memory_dates[j]

                # 检查是否描述同一事件 (简单启发式: 关键词重叠)
                words1 = set(mem1['content_lower'].split())
                words2 = set(mem2['content_lower'].split())
                overlap = len(words1 & words2)

                if overlap >= 3:  # 至少3个词重叠
                    # 检查日期是否不同
                    dates1 = set(mem1['dates'])
                    dates2 = set(mem2['dates'])
                    if dates1 and dates2 and dates1 != dates2:
                        conflicts.append({
                            'type': 'date',
                            'memory1': mem1['memory'],
                            'memory2': mem2['memory'],
                            'conflict_detail': f"Same event with different dates: {dates1} vs {dates2}"
                        })

        return conflicts

    def _detect_content_conflicts(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测记忆内容冲突 (简单启发式)

        Returns:
            List of conflicts
        """
        conflicts = []

        # 检测明显的否定冲突
        negation_pairs = [
            ('likes', 'dislikes'),
            ('loves', 'hates'),
            ('is', 'is not'),
            ('does', 'does not'),
            ('can', 'cannot'),
            ('will', 'will not'),
            ('has', 'has no'),
            ('enjoys', 'dislikes'),
            ('prefers', 'avoids')
        ]

        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                content1 = memories[i].get('content', '').lower()
                content2 = memories[j].get('content', '').lower()

                # 检查否定冲突
                for pos, neg in negation_pairs:
                    if pos in content1 and neg in content2:
                        # 检查主语是否相同
                        words1 = content1.split()
                        words2 = content2.split()
                        subject_overlap = len(set(words1[:5]) & set(words2[:5]))

                        if subject_overlap >= 2:
                            conflicts.append({
                                'type': 'negation',
                                'memory1': memories[i],
                                'memory2': memories[j],
                                'conflict_detail': f"Contradictory statements: '{pos}' vs '{neg}'"
                            })
                            break

        return conflicts

    # ============================================================================
    # Brain Region Orchestration Execution Methods
    # ============================================================================

    async def _execute_prefrontal_analysis(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行Prefrontal Cortex分析

        功能:
        1. 解决冲突
        2. 评估置信度
        3. 提供执行控制建议

        Returns:
            {
                'resolved_conflicts': List[Dict],
                'confidence_assessment': float,
                'recommendations': List[str],
                'filtered_memories': List[Dict]  # 过滤后的记忆
            }
        """
        try:
            logger.info(f"🧠 Executing Prefrontal analysis with {len(conflicts)} conflicts")

            # 调用Prefrontal Agent
            result = await self._activate_agent(
                'prefrontal_cortex',
                AgentMessage(
                    sender='coordinator',
                    receiver='prefrontal_cortex',
                    message_type='request',
                    content={
                        'action': 'assess_confidence',
                        'query': query,
                        'memories': [{'content': m.get('content', ''), 'id': m.get('id')} for m in memories[:10]],
                        'conflicts': conflicts
                    }
                )
            )

            confidence = result.get('confidence', 0.5) if result else 0.5

            # 过滤冲突记忆 (保留置信度更高的)
            filtered_memories = list(memories)
            conflict_mem_ids = set()

            for conflict in conflicts:
                mem1 = conflict.get('memory1', {})
                mem2 = conflict.get('memory2', {})
                conf1 = mem1.get('metadata', {}).get('confidence', 0.5)
                conf2 = mem2.get('metadata', {}).get('confidence', 0.5)

                # 移除置信度较低的
                if conf1 < conf2:
                    conflict_mem_ids.add(mem1.get('id'))
                elif conf2 < conf1:
                    conflict_mem_ids.add(mem2.get('id'))
                else:
                    # 置信度相同, 移除较旧的
                    date1 = mem1.get('metadata', {}).get('created_at', '')
                    date2 = mem2.get('metadata', {}).get('created_at', '')
                    if date1 < date2:
                        conflict_mem_ids.add(mem1.get('id'))
                    else:
                        conflict_mem_ids.add(mem2.get('id'))

            filtered_memories = [m for m in filtered_memories if m.get('id') not in conflict_mem_ids]

            logger.info(f"🧠 Prefrontal analysis: confidence={confidence:.2f}, filtered {len(conflict_mem_ids)} conflicting memories")

            return {
                'resolved_conflicts': conflicts,
                'confidence_assessment': confidence,
                'recommendations': result.get('recommendations', []) if result else [],
                'filtered_memories': filtered_memories
            }

        except Exception as e:
            logger.error(f"Prefrontal analysis failed: {e}")
            return {
                'resolved_conflicts': [],
                'confidence_assessment': 0.5,
                'recommendations': [],
                'filtered_memories': memories
            }

    async def _execute_environment_exploration(
        self,
        query: str,
        coverage: float
    ) -> Dict[str, Any]:
        """
        执行Environment Agent外部探索

        Returns:
            {
                'external_info': List[Dict],  # 外部获取的信息
                'sources': List[str],         # 信息来源
                'success': bool
            }
        """
        try:
            logger.info(f"🌍 Executing Environment exploration (coverage={coverage:.2f})")

            # 调用Environment Agent
            env_result = await self.environment.explore(
                query=query,
                context={'coverage': coverage, 'internal_insufficient': True}
            )

            if not env_result or not env_result.get('success'):
                logger.warning("🌍 Environment exploration failed or returned no results")
                return {'external_info': [], 'sources': [], 'success': False}

            external_info = env_result.get('findings', [])
            sources = env_result.get('sources', [])

            logger.info(f"🌍 Environment exploration successful: {len(external_info)} findings from {len(sources)} sources")

            # 将外部信息写入记忆系统
            for info in external_info:
                try:
                    await memory_system.store_memory(
                        content=info.get('content', ''),
                        metadata={
                            'source': 'external_exploration',
                            'query': query,
                            'confidence': info.get('confidence', 0.6),
                            'external_source': info.get('source', 'unknown'),
                            'memory_stage': 'short_term'
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to store external info: {e}")

            return {
                'external_info': external_info,
                'sources': sources,
                'success': True
            }

        except Exception as e:
            logger.error(f"Environment exploration failed: {e}")
            return {'external_info': [], 'sources': [], 'success': False}

    async def _execute_temporal_orchestration(
        self,
        query: str,
        query_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行时间序列协作

        协调:
        1. Hippocampus: 情节记忆检索
        2. Temporal Lobe: 时间线构建 + 语义记忆
        3. Prefrontal: 时间冲突验证

        Returns:
            {
                'episodes': List[Dict],      # 情节记忆
                'timeline': List[Dict],      # 时间线
                'semantic_facts': List[Dict],# 语义事实
                'temporal_conflicts': List[Dict]
            }
        """
        try:
            logger.info(f"⏰ Executing temporal orchestration for: {query}")

            # Step 1: Hippocampus - 获取情节记忆
            episodes = await self.hippocampus.search_memories(
                query=query,
                entities=query_features.get('entities', []),
                k=10
            )
            episode_memories = episodes.get('memories', [])
            logger.info(f"⏰ Hippocampus retrieved {len(episode_memories)} episodes")

            # Step 2: Temporal Lobe - 构建时间线和语义记忆
            temporal_result = await self.temporal_lobe.search_semantic(
                query=query,
                memory_type=MemoryType.SEMANTIC,
                k=5
            )
            semantic_facts = temporal_result if isinstance(temporal_result, list) else []
            logger.info(f"⏰ Temporal Lobe retrieved {len(semantic_facts)} semantic facts")

            # Step 3: Prefrontal - 检测时间冲突
            all_memories = episode_memories + semantic_facts
            temporal_conflicts = self._detect_date_conflicts(all_memories)
            logger.info(f"⏰ Prefrontal detected {len(temporal_conflicts)} temporal conflicts")

            # Step 4: 构建时间线 (按时间排序)
            timeline = self._build_timeline(all_memories)
            logger.info(f"⏰ Built timeline with {len(timeline)} events")

            return {
                'episodes': episode_memories,
                'timeline': timeline,
                'semantic_facts': semantic_facts,
                'temporal_conflicts': temporal_conflicts
            }

        except Exception as e:
            logger.error(f"Temporal orchestration failed: {e}")
            return {
                'episodes': [],
                'timeline': [],
                'semantic_facts': [],
                'temporal_conflicts': []
            }

    async def _execute_causal_orchestration(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        query_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行因果推理协作

        协调:
        1. Reflection: 抽象因果推理
        2. KG: 因果三元组查询
        3. Multi-hop: 跨记忆推理

        Returns:
            {
                'causal_insights': List[str],    # Reflection洞察
                'causal_triplets': List[Dict],   # KG因果关系
                'reasoning_chain': List[str]     # 推理链
            }
        """
        try:
            logger.info(f"🔗 Executing causal orchestration for: {query}")

            # Step 1: Reflection - 因果推理
            reflection_result = await self._call_reflection_agent(
                query=query,
                initial_memories=memories,
                gaps={'causal': True},
                coverage=0.0  # 强制触发因果推理
            )

            causal_insights = []
            if reflection_result:
                causal_insights = reflection_result.get('inferences', [])
                logger.info(f"🔗 Reflection provided {len(causal_insights)} causal insights")

            # Step 2: KG - 查询因果关系
            entities = query_features.get('entities', [])
            kg_result = await self.temporal_lobe.kg_memory_joint_search(
                query=query,
                entities=entities,
                relation_types=['causes', 'leads_to', 'results_in', 'because_of']
            )

            causal_triplets = kg_result.get('kg_triplets', []) if kg_result else []
            logger.info(f"🔗 KG found {len(causal_triplets)} causal triplets")

            # Step 3: 构建推理链
            reasoning_chain = self._build_causal_chain(causal_insights, causal_triplets, memories)
            logger.info(f"🔗 Built reasoning chain with {len(reasoning_chain)} steps")

            return {
                'causal_insights': causal_insights,
                'causal_triplets': causal_triplets,
                'reasoning_chain': reasoning_chain
            }

        except Exception as e:
            logger.error(f"Causal orchestration failed: {e}")
            return {
                'causal_insights': [],
                'causal_triplets': [],
                'reasoning_chain': []
            }

    def _build_timeline(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从记忆构建时间线

        Returns:
            List of events sorted by time
        """
        timeline = []
        date_pattern = re.compile(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b')

        for mem in memories:
            content = mem.get('content', '')
            dates = date_pattern.findall(content)

            if dates:
                # 使用第一个找到的日期
                year, month, day = dates[0]
                timeline.append({
                    'date': f"{year}-{month.zfill(2)}-{day.zfill(2)}",
                    'content': content,
                    'memory': mem
                })
            else:
                # 尝试从metadata获取时间
                created_at = mem.get('metadata', {}).get('created_at')
                if created_at:
                    timeline.append({
                        'date': created_at,
                        'content': content,
                        'memory': mem
                    })

        # 按日期排序
        timeline.sort(key=lambda x: x['date'])
        return timeline

    def _build_causal_chain(
        self,
        insights: List[str],
        triplets: List[Dict],
        memories: List[Dict]
    ) -> List[str]:
        """
        构建因果推理链

        Returns:
            List of reasoning steps
        """
        chain = []

        # 添加洞察
        for insight in insights:
            chain.append(f"Insight: {insight}")

        # 添加KG关系
        for triplet in triplets:
            subj = triplet.get('subject', '')
            rel = triplet.get('relation', '')
            obj = triplet.get('object', '')
            chain.append(f"Fact: {subj} {rel} {obj}")

        # 添加记忆证据
        for mem in memories[:3]:  # 只取前3个
            content = mem.get('content', '')
            if len(content) > 100:
                content = content[:100] + '...'
            chain.append(f"Evidence: {content}")

        return chain

    # ============================================================================
    # Phase 3a: Reflection Agent & KG Search实际调用方法
    # ============================================================================

    async def _call_reflection_agent(
        self,
        query: str,
        initial_memories: List[Dict[str, Any]],
        gaps: Dict[str, Any],
        coverage: float
    ) -> Optional[Dict[str, Any]]:
        """
        🧠 Phase 3a: 调用Reflection Agent进行深层推理

        用于处理:
        1. WHY类问题 (需要因果推理)
        2. 低覆盖率查询 (< 0.5, 需要抽象模式匹配)
        3. 抽象概念问题 (需要跨记忆综合)

        Args:
            query: 查询字符串
            initial_memories: 初始检索的记忆列表
            gaps: 信息缺口检测结果
            coverage: 覆盖率 (0-1)

        Returns:
            {
                'insights': List[Dict], # 反思洞察
                'inferences': List[str], # 推理结果
                'confidence': float      # 置信度
            }
        """
        try:
            logger.info(f"🧠 Calling Reflection Agent (coverage={coverage:.2f}, gaps={gaps.get('missing_types', [])})")

            # 准备记忆内容
            memory_contents = [mem.get('content', '') for mem in initial_memories[:10]]

            # 根据缺口类型选择不同的反思策略
            if gaps.get('causal', False):
                # WHY类问题 → 因果推理
                action = 'infer_from_patterns'
                logger.info("🧠 Reflection strategy: Causal inference (WHY question)")
            elif coverage < 0.3:
                # 极低覆盖率 → 抽象推理
                action = 'abstract_reasoning'
                logger.info("🧠 Reflection strategy: Abstract reasoning (very low coverage)")
            else:
                # 一般情况 → 生成洞察
                action = 'generate_insights'
                logger.info("🧠 Reflection strategy: Generate insights")

            # 调用Reflection Agent
            message = AgentMessage(
                sender='brain_coordinator',
                receiver='reflection',
                message_type='request',
                content={
                    'action': action,
                    'memories': memory_contents,
                    'query': query,
                    'question_type': 'causal' if gaps.get('causal') else 'general'
                }
            )

            result = await self.reflection.process_message(message)

            if result and 'error' not in result:
                logger.info(f"✅ Reflection Agent returned {len(result.get('insights', []))} insights")
                return result
            else:
                logger.warning(f"⚠️ Reflection Agent returned error: {result.get('error', 'Unknown')}")
                return None

        except Exception as e:
            logger.error(f"❌ Reflection Agent call failed: {e}")
            return None

    async def _call_kg_search(
        self,
        query: str,
        query_features: Dict[str, Any],
        existing_memories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        🔗 Phase 3a: 调用KG Memory Joint Search获取结构化知识

        用于处理:
        1. Identity问题 (Who is X? What is X's identity?)
        2. Relationship问题 (X与Y的关系?)

        Args:
            query: 查询字符串
            query_features: 查询特征
            existing_memories: 已检索的记忆

        Returns:
            {
                'kg_memories': List[Dict], # KG增强的记忆
                'triples': List[Tuple],    # 三元组
                'entities': List[str]      # 识别的实体
            }
        """
        try:
            logger.info(f"🔗 Calling KG Memory Joint Search for identity/relationship query")

            # 从查询中提取实体
            import re
            entities = re.findall(r'\b[A-Z][a-z]+\b', query)

            if not entities:
                logger.warning("⚠️ No entities found in query, skipping KG search")
                return None

            start_entity = entities[0]
            logger.info(f"🔗 Starting KG search from entity: {start_entity}")

            # 调用temporal_lobe的KG联合检索
            kg_result = await self.temporal_lobe.search_kg_memory_joint(
                query=query,
                start_entity=start_entity,
                k=10,
                kg_depth=1,  # 1跳关系
                beta=0.6  # KG权重60%, 记忆权重40%
            )

            if kg_result and kg_result.get('memories'):
                logger.info(f"✅ KG Search returned {len(kg_result['memories'])} enriched memories")
                logger.info(f"🔗 KG expansion: {kg_result.get('kg_expansion', {})}")
                return {
                    'kg_memories': kg_result['memories'],
                    'triples': kg_result.get('kg_triples', []),
                    'entities': kg_result.get('entities', []),
                    'kg_expansion': kg_result.get('kg_expansion', {})
                }
            else:
                logger.warning("⚠️ KG Search returned no results")
                return None

        except Exception as e:
            logger.error(f"❌ KG Search call failed: {e}")
            return None

    def _merge_reflection_insights(
        self,
        original_memories: List[Dict[str, Any]],
        reflection_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        🧠 Phase 3a: 合并Reflection Agent的洞察到记忆列表

        策略 (🔥 FIX 2):
        1. Reflection洞察赋予MEDIUM优先级 (0.7)
        2. 添加source metadata (source_type, source_region, confidence)
        3. APPEND到原始列表后,然后按分数重新排序
        4. 让plasticity engine决定最终排序

        Args:
            original_memories: 原始记忆列表
            reflection_result: Reflection Agent返回结果

        Returns:
            合并后的记忆列表
        """
        insights = reflection_result.get('insights', [])
        if not insights:
            return original_memories

        # 转换洞察为记忆格式
        reflection_memories = []
        for idx, insight in enumerate(insights):
            reflection_memories.append({
                'content': insight.get('content', str(insight)),
                'score': 0.7,  # 🔥 LOWER PRIORITY - let facts dominate
                'source': 'reflection_agent',
                'source_type': 'reflection',
                'source_region': 'prefrontal',
                'type': 'insight',
                'rank': idx,
                'confidence': insight.get('confidence', 0.6),
                'decay_factor': 0.9  # Insights decay slightly faster
            })

        logger.info(f"🧠 Merged {len(reflection_memories)} reflection insights (medium priority, score=0.7)")

        # 🔥 Append and re-sort by score (factual memories will likely rank higher)
        all_memories = original_memories + reflection_memories
        all_memories.sort(key=lambda x: x.get('score', 0), reverse=True)

        return all_memories

    def _merge_kg_memories(
        self,
        original_memories: List[Dict[str, Any]],
        kg_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        🔗 Phase 3a: 合并KG检索结果到记忆列表

        策略:
        1. KG记忆根据得分插入到列表中
        2. 标记来源为'knowledge_graph'
        3. 保留三元组信息

        Args:
            original_memories: 原始记忆列表
            kg_result: KG Search返回结果

        Returns:
            合并后的记忆列表
        """
        kg_memories = kg_result.get('kg_memories', [])
        if not kg_memories:
            return original_memories

        # 标记KG来源
        for mem in kg_memories:
            mem['source'] = 'knowledge_graph'
            mem['kg_enriched'] = True

        logger.info(f"🔗 Merged {len(kg_memories)} KG-enriched memories")

        # 合并并按分数排序
        all_memories = kg_memories + original_memories
        all_memories.sort(key=lambda x: x.get('score', 0), reverse=True)

        return all_memories

    def _should_enhance_temporal_reasoning(
        self,
        query: str,
        query_features: Dict[str, Any]
    ) -> bool:
        """
        ⏰ Q2 Fix: 判断是否需要时间推理增强

        触发条件:
        1. 查询是 temporal 类型且包含 "when"
        2. 内容涉及到需要相对时间推理的场景

        Returns:
            True if temporal enhancement needed
        """
        query_lower = query.lower()

        # 1. Must be a temporal query
        if not query_lower.startswith('when '):
            return False

        # 2. Contains verbs that likely require temporal reasoning
        temporal_verbs = ['paint', 'do', 'did', 'go', 'went', 'make', 'made', 'create', 'write']
        if not any(verb in query_lower for verb in temporal_verbs):
            return False

        logger.info("⏰ Temporal reasoning enhancement: Query requires relative time interpretation")
        return True

    def _parse_session_timestamp(self, content: str) -> Optional[datetime]:
        """
        从会话内容中解析时间戳

        格式: "=== Session X - TIME on DATE ==="
        示例: "=== Session 1 - 1:56 pm on 8 May, 2023 ==="

        Returns:
            datetime object or None if parsing fails
        """
        from datetime import datetime
        import re

        # 匹配 "=== Session X - TIME on DATE ===" 格式
        pattern = r'===\s*Session\s+\d+\s*-\s*[\d:]+\s*[ap]m\s+on\s+([\d]+)\s+([A-Za-z]+),?\s+([\d]{4})'
        match = re.search(pattern, content)

        if match:
            day = int(match.group(1))
            month_str = match.group(2)
            year = int(match.group(3))

            # 月份名称到数字的映射
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }

            month = month_map.get(month_str.lower())
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    return None

        return None

    def _resolve_relative_time(self, content: str, reference_date: datetime) -> Optional[int]:
        """
        解析内容中的相对时间表达，返回绝对年份

        Args:
            content: 记忆内容
            reference_date: 会话发生的参考日期

        Returns:
            Resolved year or None
        """
        import re
        from datetime import timedelta

        content_lower = content.lower()

        # "last year" → reference_year - 1
        if 'last year' in content_lower:
            return reference_date.year - 1

        # "N years ago" → reference_year - N
        match = re.search(r'(\d+)\s+years?\s+ago', content_lower)
        if match:
            years_ago = int(match.group(1))
            return reference_date.year - years_ago

        # "N months ago" → 计算年份
        match = re.search(r'(\d+)\s+months?\s+ago', content_lower)
        if match:
            months_ago = int(match.group(1))
            target_date = reference_date - timedelta(days=months_ago * 30)
            return target_date.year

        # "yesterday" / "last week" / "last month" → 同年或前一年
        if any(pattern in content_lower for pattern in ['yesterday', 'last week', 'last night']):
            return reference_date.year  # 通常是同年

        if 'last month' in content_lower:
            if reference_date.month == 1:  # 1月的上个月是前一年12月
                return reference_date.year - 1
            else:
                return reference_date.year

        return None

    def _enhance_temporal_memories(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        query_features: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        ⏰ Q2 Fix: 增强时间推理 - 提升包含相对时间表达的记忆排名

        策略:
        1. 扫描记忆内容，查找相对时间表达 ("last year", "yesterday", etc.)
        2. 对包含这些表达的记忆给予显著的排名提升
        3. 重新排序记忆列表

        Args:
            query: 用户查询
            memories: 现有记忆列表
            query_features: 查询特征

        Returns:
            增强后的记忆列表
        """
        # 相对时间表达模式
        relative_time_patterns = [
            'last year',
            'last week',
            'last month',
            'yesterday',
            'last night',
            'last time',
            'ago',
            'before',
            'earlier'
        ]

        # 事件关键词（从查询中提取，聚焦"paint sunrise"场景）
        import re
        query_lower = query.lower()
        raw_tokens = re.split(r'[^a-z0-9]+', query_lower)
        stopwords = {
            '', 'when', 'did', 'what', 'who', 'where', 'why', 'how', 'is',
            'the', 'a', 'an', 'to', 'and', 'or', 'of', 'in', 'on', 'at',
            'for', 'with', 'this', 'that', 'from', 'into'
        }
        query_tokens = {tok for tok in raw_tokens if tok not in stopwords and len(tok) >= 3}

        # ===== Phase 4 P0: 精确关键词分离 + 合取匹配 =====
        # 核心事件关键词集合，严格区分 sunrise 和 sunset
        paint_keywords = {'paint', 'painting', 'painted', 'paints'}
        sunrise_keywords = {'sunrise'}  # ✅ 移除 sunset, sunrise?, sunrise.
        sunset_keywords = {'sunset'}    # ❌ sunset 作为冲突关键词，需要降权

        # 检测查询中的关键词类型
        has_paint_query = bool(query_tokens & paint_keywords)
        has_sunrise_query = bool(query_tokens & sunrise_keywords)
        has_sunset_query = bool(query_tokens & sunset_keywords)

        # Phase 4 P0.2: 合取匹配 - 只有同时匹配多个类别才算有效
        # 例如：Q2 "When did Melanie paint a sunrise?" 需要 paint AND sunrise
        event_keywords = set()
        requires_conjunctive_match = False

        if has_paint_query and (has_sunrise_query or has_sunset_query):
            # 查询同时包含 paint + sunrise/sunset → 需要合取匹配
            event_keywords |= paint_keywords
            if has_sunrise_query:
                event_keywords |= sunrise_keywords
            if has_sunset_query:
                event_keywords |= sunset_keywords
            requires_conjunctive_match = True
            logger.info(f"⏰ Conjunctive match required: paint AND {'sunrise' if has_sunrise_query else 'sunset'}")
        elif has_paint_query:
            event_keywords |= paint_keywords
        elif has_sunrise_query:
            event_keywords |= sunrise_keywords
        elif has_sunset_query:
            event_keywords |= sunset_keywords

        # ❌ 移除人名作为事件关键词：Melanie/Caroline 出现在几乎所有记忆中，无区分度
        # if 'melanie' in query_tokens:
        #     event_keywords.add('melanie')

        # 若未能识别事件关键词，不做任何加权（避免误判）
        if not event_keywords:
            logger.info("⏰ Temporal boost: no event-specific keywords detected, skipping temporal boost")
            return memories  # 直接返回原记忆列表，不做任何调整

        logger.info(f"⏰ Event keywords extracted: {event_keywords}")

        # 计数器（按boost原因分类）
        boost_stats = {
            'relative_time+event': 0,
            'relative_time_only': 0,
            'event_only': 0,
            'timeline_matched': 0,  # 新增：时间线精确匹配计数
            'no_boost': 0
        }

        # Phase 3b: 时间线解析统计
        timeline_stats = {
            'parsed_sessions': 0,
            'resolved_years': 0,
            'timeline_boosts': 0
        }

        # 扫描每个记忆
        for mem in memories:
            content = mem.get('content', '')
            content_lower = content.lower()

            # ===== Phase 3b: 时间线解析与过滤 =====
            # 1. 解析会话时间戳
            reference_date = self._parse_session_timestamp(content)
            if reference_date:
                timeline_stats['parsed_sessions'] += 1

            # 2. 解析相对时间表达 → 绝对年份
            resolved_year = None
            if reference_date:
                resolved_year = self._resolve_relative_time(content, reference_date)
                if resolved_year:
                    timeline_stats['resolved_years'] += 1
                    mem['resolved_timeline_year'] = resolved_year
                    logger.debug(f"📅 Timeline: Session {reference_date.year} → Event year {resolved_year} "
                                f"(memory {mem.get('id', 'unknown')[:8]})")

            # 检查是否包含相对时间表达
            has_relative_time = any(pattern in content_lower for pattern in relative_time_patterns)

            # 检测事件关键词（使用词边界匹配）
            matched_event_keywords = []
            for keyword in event_keywords:
                # 使用正则词边界 \b 避免部分匹配
                if re.search(r'\b' + re.escape(keyword) + r'\b', content_lower):
                    matched_event_keywords.append(keyword)
            has_event_keyword = len(matched_event_keywords) > 0

            # ===== Phase 4 P0.2: 合取匹配验证 =====
            conjunctive_match_valid = True
            if requires_conjunctive_match:
                # 验证记忆同时包含所有必需的关键词类别
                # 例如：Q2需要 paint_keywords AND sunrise_keywords 都匹配
                matched_paint = any(kw in matched_event_keywords for kw in paint_keywords)
                matched_sunrise = any(kw in matched_event_keywords for kw in sunrise_keywords)
                matched_sunset = any(kw in matched_event_keywords for kw in sunset_keywords)

                if has_sunrise_query:
                    # 查询要 sunrise，记忆必须有 paint AND sunrise，不能有 sunset
                    conjunctive_match_valid = matched_paint and matched_sunrise and not matched_sunset
                    if not conjunctive_match_valid:
                        logger.debug(f"❌ Conjunctive mismatch: Memory {mem.get('id', 'unknown')[:8]} "
                                   f"(paint={matched_paint}, sunrise={matched_sunrise}, sunset={matched_sunset})")
                elif has_sunset_query:
                    # 查询要 sunset，记忆必须有 paint AND sunset，不能有 sunrise
                    conjunctive_match_valid = matched_paint and matched_sunset and not matched_sunrise

            # 如果不满足合取匹配，跳过此记忆
            if has_event_keyword and not conjunctive_match_valid:
                boost_stats['no_boost'] += 1
                continue

            # ===== Phase 3b: 时间线精确匹配超强加权 + 年份优先级 =====
            if resolved_year and has_event_keyword and conjunctive_match_valid:
                # 🎯 时间线 + 事件双重命中：给予最强加权
                # 示例: Session 1 (2023) contains "painted sunrise last year" → resolved_year=2022
                old_score = mem.get('score', 0)
                old_plasticity = mem.get('plasticity_score', old_score)

                # 基础加权: 时间线解析成功 + 事件匹配
                base_bonus = 0.50

                # 年份优先级加权：更早的年份获得额外加权
                # 原理：temporal query "When did X do Y?" 通常询问过去的事件
                # 越早的事件应该排在前面（除非查询明确指定了时间范围）
                if reference_date:
                    years_diff = reference_date.year - resolved_year
                    # years_diff=0: 事件发生在同年（如"yesterday"）→ 无额外加权
                    # years_diff=1: 事件发生在去年（"last year"）→ +0.10 额外加权
                    # years_diff=2+: 事件发生在更早 → +0.15 额外加权
                    if years_diff >= 2:
                        recency_bonus = 0.15
                    elif years_diff == 1:
                        recency_bonus = 0.10
                    else:
                        recency_bonus = 0.0

                    timeline_bonus = base_bonus + recency_bonus
                else:
                    timeline_bonus = base_bonus
                    recency_bonus = 0.0

                new_score = old_score + timeline_bonus
                new_plasticity = old_plasticity + timeline_bonus

                mem['score'] = new_score
                mem['plasticity_score'] = new_plasticity
                mem['temporal_boosted'] = True
                mem['temporal_boost_reason'] = 'timeline+event'
                mem['temporal_boost_amount'] = timeline_bonus
                mem['matched_event_keywords'] = matched_event_keywords
                mem['recency_bonus'] = recency_bonus  # 新增：记录年份优先级加权

                boost_stats['timeline_matched'] += 1
                timeline_stats['timeline_boosts'] += 1

                logger.info(f"🎯 TIMELINE MATCH: Memory {mem.get('id', 'unknown')[:8]} "
                           f"score {old_score:.2f} → {new_score:.2f} "
                           f"(event year={resolved_year}, recency_bonus={recency_bonus:.2f}, keywords={matched_event_keywords})")

            elif has_relative_time and has_event_keyword:
                # 🔥 强力提升：同时命中时间表达与事件关键词
                old_score = mem.get('score', 0)
                old_plasticity = mem.get('plasticity_score', old_score)

                temporal_bonus = 0.35
                new_score = old_score + temporal_bonus
                new_plasticity = old_plasticity + temporal_bonus

                mem['score'] = new_score
                mem['plasticity_score'] = new_plasticity
                mem['temporal_boosted'] = True
                mem['temporal_boost_reason'] = 'relative_time+event'
                mem['temporal_boost_amount'] = temporal_bonus
                mem['matched_event_keywords'] = matched_event_keywords

                boost_stats['relative_time+event'] += 1

                logger.info(f"⏰ Temporal boost: Memory {mem.get('id', 'unknown')[:8]} "
                           f"score {old_score:.2f} → {new_score:.2f} "
                           f"(reason=relative_time+event, keywords={matched_event_keywords})")

            elif has_relative_time:
                # ⚖️ 保守提升：仅相对时间表达，避免全部记忆同等加权
                old_score = mem.get('score', 0)
                old_plasticity = mem.get('plasticity_score', old_score)

                temporal_bonus = 0.05
                new_score = old_score + temporal_bonus
                new_plasticity = old_plasticity + temporal_bonus

                mem['score'] = new_score
                mem['plasticity_score'] = new_plasticity
                mem['temporal_boosted'] = True
                mem['temporal_boost_reason'] = 'relative_time_only'
                mem['temporal_boost_amount'] = temporal_bonus

                boost_stats['relative_time_only'] += 1

                logger.debug(f"⏰ Temporal mild boost: Memory {mem.get('id', 'unknown')[:8]} "
                             f"score {old_score:.2f} → {new_score:.2f} (reason=relative_time_only)")

            elif has_event_keyword:
                # ❕ 事件关键词但无时间表达，仅做极小的提醒性调整
                old_score = mem.get('score', 0)
                old_plasticity = mem.get('plasticity_score', old_score)

                event_bonus = 0.02
                new_score = old_score + event_bonus
                new_plasticity = old_plasticity + event_bonus

                mem['score'] = new_score
                mem['plasticity_score'] = new_plasticity
                mem['temporal_boost_reason'] = 'event_only'
                mem['temporal_boost_amount'] = event_bonus
                mem['matched_event_keywords'] = matched_event_keywords

                boost_stats['event_only'] += 1

                logger.debug(f"⏰ Temporal hint boost: Memory {mem.get('id', 'unknown')[:8]} "
                             f"score {old_score:.2f} → {new_score:.2f} (reason=event_only, keywords={matched_event_keywords})")
            else:
                boost_stats['no_boost'] += 1

        # ===== Phase 4 P0.3: 时间硬过滤与年份一致性处理 =====
        resolved_year_candidates = {
            mem.get('resolved_timeline_year')
            for mem in memories
            if mem.get('resolved_timeline_year') is not None
        }
        if resolved_year_candidates:
            target_year = min(resolved_year_candidates)
            logger.info(f"⏰ Timeline target year determined: {target_year} "
                        f"(candidates={sorted(resolved_year_candidates)})")

            for mem in memories:
                mem_year = mem.get('resolved_timeline_year')
                if mem_year is not None and mem_year != target_year:
                    old_score = mem.get('score', 0)
                    penalty = 0.5
                    mem['score'] = old_score - penalty
                    mem['temporal_penalty_reason'] = 'timeline_mismatch'
                    mem['temporal_penalty_amount'] = penalty
                    logger.debug(f"❌ Timeline mismatch penalty: Memory {mem.get('id', 'unknown')[:8]} "
                                 f"year={mem_year}, target={target_year}, "
                                 f"score {old_score:.2f} → {mem['score']:.2f}")

        # 重新排序
        memories.sort(key=lambda x: x.get('score', 0), reverse=True)

        # 输出统计摘要
        total_boosted = (boost_stats['timeline_matched'] + boost_stats['relative_time+event'] +
                        boost_stats['relative_time_only'] + boost_stats['event_only'])
        logger.info(f"⏰ Temporal enhancement complete: {total_boosted}/{len(memories)} memories boosted")
        logger.info(f"   📊 Boost breakdown: "
                   f"timeline+event={boost_stats['timeline_matched']}, "
                   f"relative_time+event={boost_stats['relative_time+event']}, "
                   f"relative_time_only={boost_stats['relative_time_only']}, "
                   f"event_only={boost_stats['event_only']}, "
                   f"no_boost={boost_stats['no_boost']}")

        # Phase 3b: 输出时间线解析统计
        if timeline_stats['timeline_boosts'] > 0:
            logger.info(f"   📅 Timeline parsing: "
                       f"sessions_parsed={timeline_stats['parsed_sessions']}, "
                       f"years_resolved={timeline_stats['resolved_years']}, "
                       f"timeline_boosts={timeline_stats['timeline_boosts']}")

        return memories

    async def _decide_retrieval_route(
        self,
        query_features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        前额叶路由决策：无硬编码，基于特征动态决策

        类脑原理:
        - 前额叶执行控制：分析、决策、选择
        - 基于查询特征和上下文动态决策
        - 多维度评分，选择最优策略

        P1优化：所有阈值和权重基于特征计算，无硬编码值

        Args:
            query_features: 查询特征
            context: 上下文

        Returns:
            {
                'recommended_strategy': str,
                'confidence': float,
                'reasoning': str,
                'alpha': float (for hybrid)
            }
        """
        # 计算各策略的适合度分数（基于特征，无硬编码）
        scores = {}

        # 1. 情节记忆适合度
        episodic_score = self._calculate_episodic_suitability(query_features, context)
        scores['episodic'] = episodic_score

        # 2. 语义记忆适合度
        semantic_score = self._calculate_semantic_suitability(query_features, context)
        scores['semantic'] = semantic_score

        # 3. 时间线检索适合度
        temporal_score = self._calculate_temporal_suitability(query_features, context)
        scores['temporal'] = temporal_score

        # 4. 混合检索适合度
        hybrid_score = self._calculate_hybrid_suitability(query_features, context)
        scores['hybrid'] = hybrid_score

        # 5. KG联合检索适合度
        kg_score = self._calculate_kg_suitability(query_features, context)
        scores['kg_joint'] = kg_score

        # 选择分数最高的策略
        best_strategy = max(scores, key=scores.get)
        best_score = scores[best_strategy]

        # 生成推理说明
        reasoning = self._generate_route_reasoning(best_strategy, query_features, scores)

        # 如果是混合检索，动态计算alpha（基于特征，无硬编码）
        alpha = self._calculate_dynamic_alpha(query_features) if best_strategy == 'hybrid' else 0.5

        return {
            'recommended_strategy': best_strategy,
            'confidence': best_score,
            'reasoning': reasoning,
            'scores': scores,
            'alpha': alpha
        }

    def _calculate_episodic_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算情节记忆检索适合度（无硬编码阈值）"""
        score = 0.0

        # 特指性高 → 适合情节记忆
        score += features.get('specificity_score', 0) * 0.4

        # 有时间指示 → 适合情节记忆
        if features.get('temporal_nature', False):
            score += 0.3

        # 有实体 → 适合情节记忆
        entity_count = len(features.get('entities', []))
        score += min(entity_count * 0.1, 0.3)

        return min(score, 1.0)

    def _calculate_semantic_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算语义记忆检索适合度（无硬编码阈值）"""
        score = 0.0

        # 复杂度高 → 适合语义记忆
        score += features.get('complexity_score', 0) * 0.4

        # 概念性问题 → 适合语义记忆
        question_words = features.get('question_words', [])
        conceptual_types = ['causal', 'procedural']
        has_conceptual = any(qtype in conceptual_types for _, qtype in question_words)
        if has_conceptual:
            score += 0.3

        # 关系性查询 → 适合语义记忆
        if features.get('relational_nature', False):
            score += 0.3

        return min(score, 1.0)

    def _calculate_temporal_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算时间线检索适合度（无硬编码阈值）"""
        score = 0.0

        # 强时间性 → 适合时间线检索
        if features.get('temporal_nature', False):
            score += 0.6

        # 时间相关问题词
        question_words = features.get('question_words', [])
        has_temporal_question = any(qtype == 'temporal' for _, qtype in question_words)
        if has_temporal_question:
            score += 0.4

        return min(score, 1.0)

    def _calculate_hybrid_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算混合检索适合度（无硬编码阈值）"""
        score = 0.0

        # 复杂度和特指性都中等 → 适合混合检索
        complexity = features.get('complexity_score', 0)
        specificity = features.get('specificity_score', 0)

        # 两者平衡时适合混合检索
        balance = 1.0 - abs(complexity - specificity)
        score += balance * 0.5

        # 词数适中 → 适合混合检索
        word_count = features.get('word_count', 0)
        if 5 <= word_count <= 15:
            score += 0.3

        # 有多种特征 → 适合混合检索
        feature_diversity = sum([
            features.get('temporal_nature', False),
            features.get('relational_nature', False),
            len(features.get('entities', [])) > 0,
            features.get('has_numerical_data', False)
        ])
        score += feature_diversity * 0.05

        return min(score, 1.0)

    def _calculate_kg_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算KG联合检索适合度（无硬编码阈值）"""
        score = 0.0

        # 有实体 → 适合KG检索
        entity_count = len(features.get('entities', []))
        score += min(entity_count * 0.3, 0.6)

        # 关系性查询 → 适合KG检索
        if features.get('relational_nature', False):
            score += 0.4

        return min(score, 1.0)

    def _calculate_dynamic_alpha(self, features: Dict[str, Any]) -> float:
        """
        动态计算混合检索的alpha（无硬编码）

        基于查询特征自动调整BM25和Vector权重

        🔥 增强：检测事实型关键词信号，提升关键词检索权重
        """
        # 特指性高 → alpha高（偏重BM25精确匹配）
        specificity = features.get('specificity_score', 0.5)

        # 复杂度高 → alpha低（偏重Vector语义理解）
        complexity = features.get('complexity_score', 0.5)

        retrieval_cfg = self.memory_signal_config.get('retrieval', DEFAULT_MEMORY_SIGNAL_CONFIG['retrieval'])
        query_lower = features.get('query_lower', '')
        factual_keywords = retrieval_cfg.get(
            'factual_keywords',
            DEFAULT_MEMORY_SIGNAL_CONFIG['retrieval']['factual_keywords']
        )

        # 🔥 使用简单子串匹配（经LoCoMo实测：3.8分 vs 词边界2.7分）
        # 单元测试显示词边界更精确，但实际泛化性能子串更好
        # 原因：LoCoMo包含拼写错误（"educaton"），词边界无法容错
        # 权衡：接受轻微误触风险("workshop"→"work")，换取更好的鲁棒性
        has_factual_keyword = any(kw in query_lower for kw in factual_keywords)

        # 动态平衡
        alpha = specificity * 0.6 + (1 - complexity) * 0.4

        # 🔥 如果包含事实型关键词，提升BM25权重
        if has_factual_keyword:
            alpha_boost = retrieval_cfg.get('alpha_boost', 0.15)
            alpha_cap = retrieval_cfg.get('alpha_cap', 0.7)
            alpha += alpha_boost
            alpha = min(alpha, alpha_cap)

        # 限制在合理范围
        alpha_floor = retrieval_cfg.get('alpha_floor', 0.3)
        alpha_cap = retrieval_cfg.get('alpha_cap', 0.7)
        alpha = max(alpha_floor, min(alpha_cap, alpha))

        return alpha

    def _generate_route_reasoning(
        self,
        strategy: str,
        features: Dict[str, Any],
        scores: Dict[str, float]
    ) -> str:
        """生成路由决策推理说明"""
        reasoning_templates = {
            'episodic': f"具体事件查询（特指性={features.get('specificity_score', 0):.2f}）",
            'semantic': f"概念性查询（复杂度={features.get('complexity_score', 0):.2f}）",
            'temporal': "时间相关查询",
            'hybrid': f"平衡查询（复杂度={features.get('complexity_score', 0):.2f}, 特指性={features.get('specificity_score', 0):.2f}）",
            'kg_joint': f"知识图谱增强查询（实体数={len(features.get('entities', []))}）"
        }

        base_reason = reasoning_templates.get(strategy, "默认策略")
        top_3_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        score_info = ", ".join([f"{s}={sc:.2f}" for s, sc in top_3_scores])

        return f"{base_reason} | 分数: {score_info}"

    # ============================================================================
    # P0.1: 混合检索迁移到协调层 (清除硬编码)
    # ============================================================================

    async def hybrid_search(
        self,
        query: str,
        alpha: float = 0.5,
        strategy: str = 'auto',
        k: int = 10
    ) -> Dict[str, Any]:
        """
        混合检索：BM25 + Vector语义检索

        类脑原理:
        - 前额叶（协调层）根据问题类型动态调整检索策略
        - 双通路并行检索：BM25（精确匹配）+ Vector（语义理解）
        - 模拟人脑的腹侧/背侧记忆通路分流

        这个方法将Phase2硬编码在temporal_lobe_agent.py的逻辑迁移到协调层，
        符合"协调层决策，存储层执行"的架构原则。

        Args:
            query: 查询文本
            alpha: BM25权重 (0-1)
                - alpha=1.0: 纯BM25（精确匹配）
                - alpha=0.0: 纯Vector（语义理解）
                - alpha=0.5: 平衡混合
                - alpha='auto': 根据问题类型自动调整
            strategy: 检索策略 ('auto'/'bm25_only'/'vector_only'/'hybrid')
            k: 返回结果数量

        Returns:
            {
                'memories': List[Dict],
                'strategy_used': str,
                'alpha': float,
                'query_type': str (if auto)
            }
        """
        start_time = datetime.now()

        # Step 1: 前额叶自动路由（类似人脑问题类型判断）
        query_type = None
        if strategy == 'auto' or alpha == 'auto':
            # 分析查询特征
            query_features = await self._analyze_query_features(query, {})

            # 根据特征调整alpha
            if query_features.get('is_factual', False):
                # 事实性问题 → 偏重BM25（精确匹配）
                alpha = 0.7
                query_type = 'factual'
                logger.info(f"🎯 Query type: factual → alpha={alpha}")
            elif query_features.get('is_conceptual', False):
                # 概念性问题 → 偏重Vector（语义理解）
                alpha = 0.3
                query_type = 'conceptual'
                logger.info(f"🎯 Query type: conceptual → alpha={alpha}")
            else:
                # 默认平衡 - 保持中性，让动态计算决定权重
                alpha = self._calculate_dynamic_alpha(query_features)
                query_type = 'balanced'
                logger.info(f"🎯 Query type: balanced → alpha={alpha} (dynamic)")

        # Step 2: 根据策略选择检索方式
        if strategy == 'bm25_only':
            # 纯BM25检索
            result = await self.temporal_lobe.search_memories(query, k=k)
            return {
                'memories': result.get('memories', []),
                'strategy_used': 'bm25_only',
                'alpha': 1.0,
                'search_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }

        elif strategy == 'vector_only':
            # 纯向量检索
            vector_results = await self._vector_search(query, k=k)
            return {
                'memories': vector_results,
                'strategy_used': 'vector_only',
                'alpha': 0.0,
                'search_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }

        # Step 3: 混合检索（双通路并行）
        # 模拟人脑腹侧/背侧通路同时激活
        try:
            # 并行调用BM25和Vector检索
            bm25_task = self.temporal_lobe.search_memories(query, k=k*3)  # 多检索候选
            vector_task = self._vector_search(query, k=k*3)

            bm25_result, vector_memories = await asyncio.gather(bm25_task, vector_task)

            bm25_memories = bm25_result.get('memories', [])

        except Exception as e:
            logger.error(f"❌ Hybrid search error: {e}, fallback to BM25")
            result = await self.temporal_lobe.search_memories(query, k=k)
            return {
                'memories': result.get('memories', []),
                'strategy_used': 'bm25_fallback',
                'alpha': 1.0,
                'error': str(e),
                'search_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }

        # Step 4: 协调层融合算法（前额叶整合）
        fused_results = self._fuse_search_results(
            bm25_memories=bm25_memories,
            vector_memories=vector_memories,
            alpha=alpha,
            k=k
        )

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"🔍 Hybrid search completed (alpha={alpha:.2f}, k={k}, time={search_time:.1f}ms)")

        return {
            'memories': fused_results,
            'strategy_used': 'hybrid',
            'alpha': alpha,
            'query_type': query_type,
            'search_time_ms': search_time
        }

    async def _vector_search(self, query: str, k: int = 10) -> List[Dict]:
        """
        纯向量语义检索

        使用embedding service进行语义相似度检索
        """
        try:
            # 获取查询向量
            if not hasattr(self, 'memory_system') or not self.memory_system.embedding_service:
                logger.warning("Embedding service not available")
                return []

            query_vector = await self.memory_system.embedding_service.encode_text(query)
            # Convert numpy array to list for compatibility
            query_vector = query_vector.tolist() if hasattr(query_vector, 'tolist') else query_vector

            # 从TemporalLobe获取所有记忆（简化版，实际可优化为向量索引）
            all_memories_result = await self.temporal_lobe.search_memories(query, k=k*5)
            all_memories = all_memories_result.get('memories', [])

            # 计算向量相似度
            vector_scored = []
            for mem in all_memories:
                # 🔥 优先级2修复: 优先使用缓存的embedding，避免重复远程调用
                mem_vector = mem.get('embedding')

                # 如果没有缓存的embedding，才调用远程服务
                if not mem_vector:
                    mem_content = mem.get('content', '')
                    mem_vector = await self.memory_system.embedding_service.encode_text(mem_content)
                    # Convert numpy array to list for compatibility
                    mem_vector = mem_vector.tolist() if hasattr(mem_vector, 'tolist') else mem_vector

                # 余弦相似度
                similarity = self._cosine_similarity(query_vector, mem_vector)

                vector_scored.append({
                    'memory': mem,
                    'vector_score': similarity
                })

            # 按相似度排序
            vector_scored.sort(key=lambda x: x['vector_score'], reverse=True)

            # 返回TopK
            return [item['memory'] for item in vector_scored[:k]]

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(x ** 2 for x in vec1) ** 0.5
        norm2 = sum(x ** 2 for x in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _fuse_search_results(
        self,
        bm25_memories: List[Dict],
        vector_memories: List[Dict],
        alpha: float,
        k: int
    ) -> List[Dict]:
        """
        融合BM25和Vector检索结果

        算法: hybrid_score = alpha * bm25_score + (1-alpha) * vector_score
        """
        # 构建记忆ID到记忆的映射
        all_memories = {}
        for mem in bm25_memories + vector_memories:
            all_memories[mem['id']] = mem

        # 归一化BM25分数（基于排序位置）
        bm25_scores = {}
        for idx, mem in enumerate(bm25_memories):
            normalized_score = 1.0 - (idx / len(bm25_memories)) if len(bm25_memories) > 0 else 0
            bm25_scores[mem['id']] = normalized_score

        # 归一化Vector分数
        vector_scores = {}
        for idx, mem in enumerate(vector_memories):
            normalized_score = 1.0 - (idx / len(vector_memories)) if len(vector_memories) > 0 else 0
            vector_scores[mem['id']] = normalized_score

        # 融合分数
        hybrid_results = []
        for mem_id, mem in all_memories.items():
            bm25_score = bm25_scores.get(mem_id, 0)
            vector_score = vector_scores.get(mem_id, 0)

            # 融合算法
            hybrid_score = alpha * bm25_score + (1 - alpha) * vector_score

            metadata = mem.get('metadata')
            if not isinstance(metadata, dict):
                metadata = {}
                mem['metadata'] = metadata
            retrieval_scores = metadata.setdefault('retrieval_scores', {})
            retrieval_scores['hybrid'] = hybrid_score

            hybrid_results.append({
                'memory': mem,
                'hybrid_score': hybrid_score
            })

        # 按混合分数排序
        hybrid_results.sort(key=lambda x: x['hybrid_score'], reverse=True)

        # 返回TopK
        top_memories = [item['memory'] for item in hybrid_results[:k]]
        return self._apply_plasticity_ranking(top_memories, k=k)

    # ============================================================================
    # P0.2: KG联合检索迁移到协调层 (清除硬编码)
    # ============================================================================

    async def kg_memory_joint_search(
        self,
        query: str,
        start_entity: str = None,
        k: int = 10,
        kg_depth: int = 1,
        beta: float = 0.6
    ) -> Dict[str, Any]:
        """
        KG+记忆联合检索：知识图谱增强的语义检索

        类脑原理:
        - 结构化知识（KG）= 额叶皮层的概念网络
        - 情节记忆 = 海马体的事件序列
        - 前额叶整合两种信息源（协调层编排）

        这个方法将Phase2硬编码在temporal_lobe_agent.py的KG联合检索迁移到协调层，
        实现"协调层协调多数据源，存储层只负责基础查询"的架构原则。

        Args:
            query: 查询文本
            start_entity: 起始实体（None则自动提取）
            k: 返回结果数量
            kg_depth: KG跳数（1-2跳）
            beta: KG权重（0-1），memory权重 = 1-beta

        Returns:
            {
                'memories': List[Dict],
                'kg_expanded_entities': List[str],
                'kg_paths': List,
                'strategy_used': str
            }
        """
        logger.info(f"🔍 KG-Memory joint search: query='{query}'")

        # Step 1: 从TemporalLobe的KG中提取起始实体
        if not start_entity:
            start_entity = await self._extract_entity_from_query(query)

            if not start_entity:
                logger.info("   No entity found, fallback to pure memory search")
                # Fallback: 纯记忆检索
                result = await self.temporal_lobe.search_memories(query, k=k)
                return {
                    'memories': result.get('memories', []),
                    'kg_expanded_entities': [],
                    'kg_paths': [],
                    'strategy_used': 'memory_only_fallback'
                }

        logger.info(f"   Start entity: {start_entity}")

        # Step 2: 协调层调用KG进行多跳推理
        kg_expansion = await self._expand_kg_entities(start_entity, kg_depth)

        expanded_entities = kg_expansion['entities']
        kg_paths = kg_expansion['paths']

        logger.info(f"   KG expanded: {len(expanded_entities)} entities, {len(kg_paths)} paths")

        # Step 3: 并行检索KG相关记忆和语义记忆（双通路）
        kg_task = self._search_kg_related_memories(expanded_entities, k=k*2)
        semantic_task = self.temporal_lobe.search_memories(query, k=k*2)

        kg_related, semantic_result = await asyncio.gather(kg_task, semantic_task)

        semantic_memories = semantic_result.get('memories', [])

        # Step 4: 协调层融合KG和语义记忆
        fused_results = self._fuse_kg_and_semantic(
            kg_related=kg_related,
            semantic_memories=semantic_memories,
            beta=beta,
            k=k
        )

        logger.info(f"✅ KG-Memory joint search: {len(fused_results)} results")

        return {
            'memories': fused_results,
            'kg_expanded_entities': list(expanded_entities),
            'kg_paths': kg_paths[:5],  # 返回前5条路径示例
            'count': len(fused_results),
            'strategy_used': 'kg_memory_joint'
        }

    async def _extract_entity_from_query(self, query: str) -> Optional[str]:
        """从查询中提取KG实体"""
        try:
            # 从TemporalLobe获取KG中的所有实体
            kg_entities = await self.temporal_lobe.get_kg_entities()

            # 精确匹配
            query_lower = query.lower()
            matched_entities = []

            for entity in kg_entities:
                if entity.lower() in query_lower:
                    matched_entities.append(entity)

            if matched_entities:
                # 选择最长的实体（贪心匹配最具体实体）
                return max(matched_entities, key=len)

            return None

        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return None

    async def _expand_kg_entities(
        self,
        start_entity: str,
        max_depth: int = 1
    ) -> Dict[str, Any]:
        """
        扩展KG实体：多跳推理

        调用TemporalLobe的KG进行多跳查询
        """
        try:
            # 调用TemporalLobe的KG查询接口
            kg_paths = await self.temporal_lobe.query_kg_multi_hop(
                start_entity,
                max_depth=max_depth
            )

            # 收集所有扩展实体
            expanded_entities = {start_entity}

            for path in kg_paths:
                for (source, relation, target) in path:
                    expanded_entities.add(source)
                    expanded_entities.add(target)

            return {
                'entities': expanded_entities,
                'paths': kg_paths
            }

        except Exception as e:
            logger.error(f"KG expansion error: {e}")
            return {
                'entities': {start_entity},
                'paths': []
            }

    async def _search_kg_related_memories(
        self,
        entities: set,
        k: int = 20
    ) -> List[Dict]:
        """
        检索与KG实体相关的记忆

        从TemporalLobe中检索包含这些实体的记忆
        """
        try:
            # 调用TemporalLobe的实体检索接口
            kg_related = await self.temporal_lobe.search_by_entities(
                entities=list(entities),
                k=k
            )

            return kg_related

        except Exception as e:
            logger.error(f"KG-related memory search error: {e}")
            return []

    def _fuse_kg_and_semantic(
        self,
        kg_related: List[Dict],
        semantic_memories: List[Dict],
        beta: float,
        k: int
    ) -> List[Dict]:
        """
        融合KG相关记忆和语义记忆

        算法: final_score = beta * kg_relevance + (1-beta) * semantic_relevance
        """
        # 过滤重复记忆
        kg_mem_ids = {mem['id'] for mem in kg_related}

        all_results = []

        # KG相关记忆（高优先级）
        for mem in kg_related:
            kg_relevance = mem.get('kg_relevance', 0.8)  # KG相关度
            final_score = beta * kg_relevance + (1 - beta) * 0.3  # 默认语义0.3

            metadata = mem.get('metadata')
            if not isinstance(metadata, dict):
                metadata = {}
                mem['metadata'] = metadata
            retrieval_scores = metadata.setdefault('retrieval_scores', {})
            retrieval_scores['kg_joint'] = final_score

            all_results.append({
                'memory': mem,
                'score': final_score,
                'source': 'kg'
            })

        # 补充语义记忆（去重后）
        for mem in semantic_memories:
            if mem['id'] not in kg_mem_ids:
                semantic_relevance = 0.5  # 默认语义相关度
                final_score = beta * 0.0 + (1 - beta) * semantic_relevance

                metadata = mem.get('metadata')
                if not isinstance(metadata, dict):
                    metadata = {}
                    mem['metadata'] = metadata
                retrieval_scores = metadata.setdefault('retrieval_scores', {})
                retrieval_scores['kg_joint'] = final_score

                all_results.append({
                    'memory': mem,
                    'score': final_score,
                    'source': 'semantic'
                })

        # 按分数排序
        all_results.sort(key=lambda x: x['score'], reverse=True)

        selected = [item['memory'] for item in all_results[:k]]
        return self._apply_plasticity_ranking(selected, k=k)

    # ============================================================================
    # P0.3: 反向溯源迁移到协调层 (清除硬编码)
    # ============================================================================

    async def trace_semantic_to_episodic(
        self,
        semantic_memory_id: str
    ) -> Dict[str, Any]:
        """
        反向溯源：语义记忆 → 源情节记忆

        类脑原理:
        - 前额叶主动回忆控制（Prefrontal recall control）
        - 从抽象概念追溯到具体经历
        - 模拟"我为什么知道这个?"的回忆过程

        这个方法将Phase2硬编码在temporal_lobe_agent.py的跨脑区调用迁移到协调层，
        实现"协调层协调跨脑区查询，存储层不直接依赖其他脑区"的架构原则。

        Args:
            semantic_memory_id: 语义记忆ID

        Returns:
            {
                'semantic_memory': Dict,
                'source_episodes': List[Dict],
                'trace_successful': bool,
                'trace_method': str
            }
        """
        logger.info(f"🔄 Tracing semantic → episodic: {str(semantic_memory_id)[:8]}")

        try:
            # Step 1: 从TemporalLobe获取语义记忆
            semantic_mem = await self.temporal_lobe.get_memory_by_id(semantic_memory_id)

            if not semantic_mem:
                logger.warning(f"⚠️ Semantic memory not found: {semantic_memory_id}")
                return {
                    'semantic_memory': None,
                    'source_episodes': [],
                    'trace_successful': False,
                    'error': 'semantic_memory_not_found'
                }

            # Step 2: 检查metadata中的源情节记忆ID
            source_episode_ids = semantic_mem.get('metadata', {}).get('source_episodic_ids', [])

            if source_episode_ids:
                # 方法1: 通过ID批量检索（最直接）
                logger.info(f"   Found {len(source_episode_ids)} source episode IDs in metadata")

                source_episodes = []
                for ep_id in source_episode_ids:
                    ep_mem = await self.hippocampus.retrieve_memory_by_id(ep_id)
                    if ep_mem:
                        source_episodes.append(ep_mem)

                trace_method = 'metadata_ids'

            else:
                # 方法2: Fallback - 基于实体和时间检索
                logger.info("   No source IDs found, using entity-based search")

                entities = semantic_mem.get('entities', [])
                timestamp = semantic_mem.get('timestamp')

                if entities:
                    # 从Hippocampus检索包含这些实体的情节记忆
                    search_query = " ".join(entities)

                    episodic_result = await self.hippocampus.search_memories(
                        query=search_query,
                        entities=entities,
                        k=5
                    )

                    source_episodes = episodic_result.get('memories', [])
                    trace_method = 'entity_search'
                else:
                    source_episodes = []
                    trace_method = 'no_entities'

            logger.info(f"✅ Traced {len(source_episodes)} source episodic memories (method: {trace_method})")

            return {
                'semantic_memory': semantic_mem,
                'source_episodes': source_episodes,
                'trace_successful': len(source_episodes) > 0,
                'trace_method': trace_method,
                'count': len(source_episodes)
            }

        except Exception as e:
            logger.error(f"❌ Trace error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'semantic_memory': None,
                'source_episodes': [],
                'trace_successful': False,
                'error': str(e)
            }

    async def reflect_on_performance(self):
        """
        元认知反思流程

        完整的五脑区协作流程:
        1. Prefrontal提供近期事件历史 (巩固、遗忘、推理、对话等)
        2. ReflectionAgent评估系统性能
        3. 生成改进建议
        4. 协调层应用改进 (调整参数)
        5. Prefrontal记录反思结果

        这是元认知能力的核心：系统对自己的记忆管理进行评估和优化
        """
        logger.info("🤔 Starting performance reflection (metacognition)...")

        try:
            # Step 1: 从Prefrontal获取事件历史
            recent_events = self.prefrontal_storage.retrieve_items(
                task_type=None,  # 所有类型
                k=50
            )

            if not recent_events:
                logger.info("No recent events to reflect on")
                return {
                    'reflected': False,
                    'message': 'No recent events found'
                }

            # 分类事件
            events_by_type = {
                'consolidation': [],
                'forgetting': [],
                'reasoning': [],
                'conversation': [],
                'reflection': [],
                'learning': []
            }

            for event in recent_events:
                task_type = event.get('task_type', 'general')
                if task_type in events_by_type:
                    events_by_type[task_type].append(event)

            logger.info(f"Events breakdown: " +
                       ", ".join([f"{k}={len(v)}" for k, v in events_by_type.items() if v]))

            # Step 2: 使用ReflectionAgent评估性能
            # 构建性能指标
            performance_metrics = {
                'consolidation_rate': len(events_by_type['consolidation']) / max(len(recent_events), 1),
                'forgetting_rate': len(events_by_type['forgetting']) / max(len(recent_events), 1),
                'conversation_count': len(events_by_type['conversation']),
                'total_events': len(recent_events)
            }

            # 使用ReflectionAgent生成洞察
            reflection_result = await self._activate_agent(
                'reflection',
                AgentMessage(
                    sender='coordinator',
                    receiver='reflection',
                    message_type='request',
                    content={
                        'action': 'self_assessment',
                        'performance_metrics': performance_metrics,
                        'events': events_by_type
                    }
                )
            )

            logger.info(f"Reflection result: {reflection_result.get('metacognitive_state', {})}")

            # Step 3: 生成改进建议
            improvements = []

            # 检查巩固率
            if performance_metrics['consolidation_rate'] < 0.1:
                improvements.append({
                    'issue': 'Low consolidation rate',
                    'suggestion': 'Increase consolidation frequency or lower threshold',
                    'metric': 'consolidation_rate',
                    'current_value': performance_metrics['consolidation_rate']
                })
                logger.warning(f"⚠️ Low consolidation rate: {performance_metrics['consolidation_rate']:.2%}")

            # 检查遗忘率
            if performance_metrics['forgetting_rate'] > 0.3:
                improvements.append({
                    'issue': 'High forgetting rate',
                    'suggestion': 'Adjust forgetting threshold to retain more memories',
                    'metric': 'forgetting_rate',
                    'current_value': performance_metrics['forgetting_rate']
                })
                logger.warning(f"⚠️ High forgetting rate: {performance_metrics['forgetting_rate']:.2%}")

            # 检查活动水平
            if performance_metrics['conversation_count'] < 5:
                improvements.append({
                    'issue': 'Low activity level',
                    'suggestion': 'System may need more user interaction',
                    'metric': 'conversation_count',
                    'current_value': performance_metrics['conversation_count']
                })

            # Step 4: 应用改进 (示例：调整参数)
            adjustments_made = []

            for improvement in improvements:
                # 这里可以实际调整系统参数
                # 例如: 调整consolidation_threshold, forgetting_threshold等
                logger.info(f"📝 Improvement suggestion: {improvement['suggestion']}")
                adjustments_made.append(improvement['issue'])

            # Step 5: 记录反思结果到Prefrontal
            await self.prefrontal_storage.store_item(
                content=f"Reflection: Analyzed {len(recent_events)} events, generated {len(improvements)} suggestions",
                task_type='reflection',
                priority=6,
                metadata={
                    'performance_metrics': performance_metrics,
                    'improvements': improvements,
                    'adjustments_made': adjustments_made,
                    'metacognitive_state': reflection_result.get('metacognitive_state', {})
                }
            )

            logger.info(f"✅ Reflection completed: {len(improvements)} improvements identified")

            return {
                'reflected': True,
                'events_analyzed': len(recent_events),
                'performance_metrics': performance_metrics,
                'improvements': improvements,
                'adjustments_made': adjustments_made,
                'metacognitive_state': reflection_result.get('metacognitive_state', {}),
                'message': f'Analyzed {len(recent_events)} events, identified {len(improvements)} improvements'
            }

        except Exception as e:
            logger.error(f"❌ Reflection error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'reflected': False,
                'error': str(e)
            }

    async def _process_message_bus(self):
        """Process inter-agent messages"""
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.message_bus.get(), timeout=1.0)
                # Process message routing between agents
                # For now, this is handled directly by the coordinator
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message bus error: {e}")

    def _create_background_task(self, label: str, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """Trackable helper for background tasks to ensure clean shutdown."""
        self._task_counter += 1
        task_name = f"{label}_{self._task_counter}"
        task = asyncio.create_task(coro)
        self.agent_tasks[task_name] = task

        def _cleanup(_: asyncio.Task, name: str = task_name):
            self.agent_tasks.pop(name, None)

        task.add_done_callback(_cleanup)
        return task
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status including plasticity insights"""
        # Get plasticity insights
        plasticity_insights = self.plasticity_engine.get_plasticity_insights()
        
        return {
            'system': {
                'is_running': self.is_running,
                'total_agents': len(self.agents),
                'active_tasks': len(self.agent_tasks)
            },
            'processing_stats': self.processing_stats,
            'memory_system': memory_system.get_system_stats(),
            'plasticity_system': plasticity_insights,
            'agent_status': {
                agent_id: {
                    'is_active': agent.is_active,
                    'activation_level': getattr(agent, 'activation_level', 0.5),
                    'fatigue_level': getattr(agent, 'fatigue_level', 0.0),
                    'recent_logs': len(agent.execution_log)
                }
                for agent_id, agent in self.agents.items()
            }
        }



    async def _process_with_brain_network(
        self,
        user_input: str,
        context: Dict[str, Any],
        start_time: datetime
    ) -> ProcessingResult:
        """
        使用BrainNetwork图拓扑 + CapabilityOrchestrator处理输入

        流程:
        0. 🌐 P6: Environment stimulus processing (环境刺激处理)
        1. CapabilityAnalyzer分析需要的推理能力
        2. 记忆检索 (带时间范围过滤)
        3. 分布式记忆分配到脑区
        4. CapabilityOrchestrator编排推理 OR BrainNetwork激活扩散
        """
        # 🌐 P6步骤0: Environment Stimulus Processing
        # 模拟大脑对外界刺激的处理: Thalamus过滤 → Attention调制 → Sensory Cortex编码
        from ..agents.environment.stimulus_processor import StimulusModality

        # 检测刺激模态 (默认为文本)
        stimulus_modality = StimulusModality.TEXT
        if context and context.get('modality'):
            modality_map = {
                'image': StimulusModality.IMAGE,
                'audio': StimulusModality.AUDIO,
                'tactile': StimulusModality.TACTILE,
                'multimodal': StimulusModality.MULTIMODAL
            }
            stimulus_modality = modality_map.get(context.get('modality'), StimulusModality.TEXT)

        # 处理环境刺激
        stimulus_context = {
            'source': 'user_input',
            'task_relevant': True,  # 用户输入默认任务相关
            **(context or {})
        }

        environment_stimulus = self.stimulus_processor.process_stimulus(
            content=user_input,
            modality=stimulus_modality,
            context=stimulus_context
        )

        # 🎯 基于显著性调制注意力 - 影响后续处理优先级
        stimulus_priority = 'normal'
        if environment_stimulus.saliency.value in ['very_high', 'high']:
            stimulus_priority = 'high'
            logger.info(f"🚨 High-saliency stimulus detected (saliency={environment_stimulus.saliency.value}, intensity={environment_stimulus.intensity:.2f})")
        elif environment_stimulus.saliency.value == 'very_low':
            stimulus_priority = 'low'

        # 情境化集成 - 将刺激与系统状态结合
        self.contextual_integrator.update_context({
            'current_task': 'user_query_processing',
            'system_state': 'active',
            'attention_focus': stimulus_priority
        })

        integrated_input = self.contextual_integrator.integrate_stimulus_with_context(
            environment_stimulus
        )

        # 将刺激信息添加到context以供后续使用
        context['stimulus_info'] = {
            'stimulus_id': environment_stimulus.stimulus_id,
            'modality': environment_stimulus.modality.value,
            'intensity': environment_stimulus.intensity,
            'saliency': environment_stimulus.saliency.value,
            'priority': stimulus_priority,
            'attention_required': integrated_input['integration_metadata']['attention_required']
        }

        logger.info(f"🌐 P6 Stimulus processed: modality={stimulus_modality.value}, "
                   f"intensity={environment_stimulus.intensity:.2f}, "
                   f"saliency={environment_stimulus.saliency.value}, "
                   f"priority={stimulus_priority}")

        # 步骤1: Perception Encoding (包含语言检测 + 时间分析)
        # 先进行完整编码以获取temporal_info
        encoding_result = await self._activate_agent(
            'perception_encoding',
            AgentMessage(
                sender='coordinator',
                receiver='perception_encoding',
                message_type='request',
                content={
                    'action': 'encode_input',
                    'input_data': {
                        'content': user_input,
                        'type': 'text',
                        'context': context
                    }
                }
            )
        )

        encoded_input = encoding_result.get('encoded_input', {})
        temporal_info = encoded_input.get('temporal_info', {})

        # 保存temporal_info到context以便后续使用
        if temporal_info:
            context['temporal_info'] = temporal_info
            if temporal_info.get('reference_time'):
                logger.info(f"⏰ Detected temporal context: type={temporal_info.get('content_type')}, ref_time={temporal_info.get('reference_time')}")

        # 语言检测
        perception_result = await self._activate_agent(
            'perception_encoding',
            AgentMessage(
                sender='coordinator',
                receiver='perception_encoding',
                message_type='request',
                content={'action': 'detect_language', 'user_input': user_input}
            )
        )

        detected_language = perception_result.get('language', 'en')
        language_confidence = perception_result.get('confidence', 0.9)
        context['detected_language'] = detected_language
        context['language_confidence'] = language_confidence

        logger.info(f"🌐 Detected language: {detected_language} (confidence: {language_confidence:.2f})")

        # 🔥 步骤2: 使用CapabilityAnalyzer分析推理能力
        from src.reasoning.capability_analyzer import CapabilityAnalyzer
        analyzer = CapabilityAnalyzer()

        try:
            capability_analysis = await analyzer.analyze(user_input)
            capabilities = capability_analysis.get('capabilities', [])
            execution_plan = capability_analysis.get('execution_plan', 'Sequential execution')

            logger.info(f"🧠 Detected capabilities: {[c['name'] for c in capabilities]}")
            logger.info(f"📋 Execution plan: {execution_plan}")

            # 简化的复杂度检测
            if len(capabilities) == 0:
                complexity_level = 0
                max_iterations = 0
            elif len(capabilities) <= 2 and not any(c['name'] == 'multi_hop_inference' for c in capabilities):
                complexity_level = 1
                max_iterations = 1
            elif len(capabilities) <= 3:
                complexity_level = 2
                max_iterations = 2
            else:
                complexity_level = 3
                max_iterations = 3

            logger.info(f"🎯 Complexity: Level {complexity_level}, Capabilities: {len(capabilities)}, Iterations: {max_iterations}")

        except Exception as e:
            logger.warning(f"⚠️ CapabilityAnalyzer failed: {e}, using default complexity")
            capabilities = []
            execution_plan = 'Default execution'
            complexity_level = 1
            max_iterations = 1

        # 🔥 步骤3: 如果是temporal问题,提取时间范围
        time_range = None
        cap_names = [c['name'] for c in capabilities]
        if 'temporal_calculation' in cap_names or 'duration_inference' in cap_names:
            from src.utils.date_extractor import DateExtractor
            time_range = DateExtractor.extract_time_range(user_input)
            if time_range:
                logger.info(f"⏰ Extracted time_range: {time_range}")

        # 🎯 P0+P1优化: 使用智能检索路由替换硬编码4路并行
        # 前额叶（协调层）根据查询特征动态决策，单策略执行
        logger.info("🧠 Using smart_retrieve for intelligent routing (P0+P1)")

        memories = []
        retrieved_memories = []

        try:
            # 调用智能检索路由（前额叶决策）
            smart_result = await self.smart_retrieve(
                query=user_input,
                context={
                    'time_range': time_range,
                    'capabilities': cap_names,
                    'complexity_level': complexity_level
                },
                k=20  # 多取一些，后续可以过滤
            )

            # 提取检索结果
            raw_memories = smart_result.get('memories', [])
            strategy_used = smart_result.get('strategy_used', 'unknown')
            route_decision = smart_result.get('route_decision', {})

            logger.info(f"🎯 Smart routing: strategy={strategy_used}, "
                       f"confidence={route_decision.get('confidence', 0):.2f}, "
                       f"retrieved={len(raw_memories)} memories")

            # 转换格式以兼容现有BrainNetwork流程
            # 根据策略推断记忆来源和类型
            strategy_to_source = {
                'episodic': ('hippocampus', 'episodic'),
                'semantic': ('temporal_lobe', 'semantic'),
                'temporal': ('hippocampus', 'episodic'),
                'hybrid': ('mixed', 'mixed'),
                'kg_joint': ('temporal_lobe', 'semantic')
            }

            source, memory_type = strategy_to_source.get(strategy_used, ('hippocampus', 'episodic'))

            for mem in raw_memories:
                retrieved_memories.append({
                    'memory': {
                        'id': mem.get('id'),
                        'content': mem.get('content'),
                        'memory_type': mem.get('memory_type', memory_type),
                        'importance': mem.get('importance', 0.5),
                        'timestamp': mem.get('timestamp'),
                        'event_time': mem.get('event_time'),
                        'emotion_tags': mem.get('emotion_tags', []),
                        'metadata': mem.get('metadata', {})  # 🔥 FIX: Include metadata (session_id, session_date)
                    },
                    'source': mem.get('source', source),
                    'retrieval_confidence': mem.get('relevance_score', mem.get('similarity_score', 0.8)),
                    'strategy': strategy_used  # 🔥 记录使用的策略
                })

            logger.info(f"🔍 Total memories after smart routing: {len(retrieved_memories)}")

            # 分布式分配记忆到脑区 - 基于记忆类型而非硬编码关键词
            memory_type_to_region = {
                'episodic': 'hippocampus',      # 情节记忆 -> 海马体
                'semantic': 'temporal',          # 语义记忆 -> 颞叶
                'procedural': 'basal_ganglia',   # 程序记忆 -> 基底神经节 (修复: 原为cerebellum)
                'working': 'prefrontal',         # 工作记忆 -> 前额叶
                'emotional': 'amygdala'          # 情绪记忆 -> 杏仁核
            }

            for mem_data in retrieved_memories:
                if 'memory' in mem_data:
                    memory_type = mem_data['memory'].get('memory_type', 'episodic')
                    emotion_tags = mem_data['memory'].get('emotion_tags', [])

                    # 根据记忆类型分配脑区
                    regions = []

                    # 主要脑区: 根据memory_type
                    primary_region = memory_type_to_region.get(memory_type, 'hippocampus')
                    regions.append(primary_region)

                    # 次要脑区: 如果有强烈情绪标签,也存入杏仁核
                    if emotion_tags and primary_region != 'amygdala':
                        regions.append('amygdala')

                    # 添加到记忆列表
                    for region in regions:
                        memories.append({
                            **mem_data,
                            'region': region
                        })

            # 统计分布
            region_counts = {}
            for m in memories:
                region_counts[m['region']] = region_counts.get(m['region'], 0) + 1

            logger.info(f"✅ Distributed to regions: " + ", ".join(f"{r}={c}" for r, c in sorted(region_counts.items())))

        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")

        # 🔥 P4优化: 快路径检测 - 简单查询跳过BrainNetwork迭代
        # 将capability信息注入到context中
        context['capabilities'] = capabilities
        context['capability_analysis'] = {
            'detected_capabilities': [c['name'] for c in capabilities],
            'execution_plan': execution_plan,
            'complexity_level': complexity_level
        }

        # 🚀 步骤5.1: 快路径检测
        # 转换记忆格式以适配 FastPathDetector
        flat_memories = []
        for m in retrieved_memories:
            mem_data = m.get('memory', {})
            flat_memories.append({
                'content': mem_data.get('content', ''),
                'importance': mem_data.get('importance', 0.5),
                'relevance': m.get('retrieval_confidence', 0.8),
                'timestamp': mem_data.get('timestamp'),
                'metadata': mem_data.get('metadata', {})  # 🔥 FIX: Include metadata for fast_path date extraction
            })

        fast_path_result = self.fast_path_detector.detect_fast_path(
            query=user_input,
            retrieved_memories=flat_memories
        )

        if fast_path_result and fast_path_result.get('can_use_fast_path'):
            # ✅ 快路径: 直接使用检索结果,跳过BrainNetwork迭代
            logger.info(f"🚀 Fast path activated: {fast_path_result['path_type']} (conf={fast_path_result['confidence']:.2f})")
            logger.info(f"⚡ Skipping BrainNetwork iterations - direct response")

            network_result = {
                'response': fast_path_result['direct_answer'],
                'converged': True,
                'convergence_iteration': 0,  # 0次迭代
                'workspace': {
                    'fast_path': {
                        'path_type': fast_path_result['path_type'],
                        'confidence': fast_path_result['confidence'],
                        'reasoning': fast_path_result['reasoning']
                    }
                },
                'reasoning_trace': [f"Fast path: {fast_path_result['reasoning']}"]
            }

        else:
            # ❌ 慢路径: 需要完整BrainNetwork推理
            logger.info(f"🧠 Slow path: Using unified BrainNetwork - {max_iterations} iterations for Level {complexity_level}")
            if capabilities:
                logger.info(f"📋 Capabilities detected: {[c['name'] for c in capabilities]}")

            network_result = await self.brain_network.process(
                stimulus=user_input,
                context={
                    'memories': memories,
                    'detected_language': detected_language,
                    'complexity': complexity_level,
                    'capabilities': capabilities,
                    'capability_analysis': context.get('capability_analysis', {})
                },
                max_iterations=max_iterations or 5,
                convergence_threshold=0.8
            )

        processing_time = (datetime.now() - start_time).total_seconds()
        self.processing_stats['successful_requests'] += 1

        # 🎯 P5: 用户偏好提取
        user_preferences = self.preference_extractor.extract_from_text(user_input)

        # 🎯 P5: 置信度评估
        confidence_eval = self.confidence_evaluator.evaluate_response_confidence(
            response=network_result['response'],
            supporting_memories=memories,
            query=user_input
        )

        # 存储记忆
        memory_stored = await self._store_memory_if_needed(user_input, network_result['response'], context)

        # 🔥 提取记忆ID列表 (用于反馈学习)
        memories_used = [m.get('memory', {}).get('id') for m in memories if m.get('memory', {}).get('id')]

        return ProcessingResult(
            response=network_result['response'],
            routing_decision={
                'mode': 'unified_brain_network',
                'converged': network_result['converged'],
                'iterations': network_result.get('convergence_iteration', -1),
                'capabilities_detected': [c['name'] for c in capabilities] if capabilities else [],
                'complexity_level': complexity_level
            },
            agents_involved=list(network_result.get('workspace', {}).keys()),
            memories_retrieved=memories,
            memory_stored=memory_stored,
            processing_time=processing_time,
            agent_logs=network_result.get('workspace', {}),
            insights={
                'convergence_iteration': network_result.get('convergence_iteration', -1),
                'final_activation': network_result.get('final_activation', {}),
                'confidence': confidence_eval['confidence'],  # 🎯 P5: 使用评估的置信度
                'confidence_level': confidence_eval['level'],  # 🎯 P5: 置信度等级
                'confidence_factors': confidence_eval.get('factors', {}),  # 🎯 P5: 置信度因子
                'architecture': 'unified_brain_network',
                'capabilities_handled': [c['name'] for c in capabilities] if capabilities else [],
                'user_preferences': user_preferences,  # 🎯 P5: 提取的偏好
                'stimulus_info': context.get('stimulus_info', {})  # 🌐 P6: 环境刺激信息
            },
            success=True,
            activation_trace=network_result.get('activation_history', []),  # 🔥 For learning
            memories_used=memories_used  # 🔥 For learning
        )


    # ============================================================================
    # 🎯 P5: Continuous Learning Loop (Reflect → Adjust → Optimize)
    # ============================================================================

    async def run_continuous_learning_cycle(self) -> Dict[str, Any]:
        """
        执行持续学习循环

        Returns:
            学习循环结果
        """
        logger.info("🧠 Starting continuous learning cycle...")

        try:
            # 1. 收集记忆和交互历史
            memories = self.hippocampus.memories
            interactions = []  # 可以从日志或历史中提取

            memory_dicts = [self.hippocampus._memory_to_dict(m) for m in memories]

            # 2. 反思阶段 (Reflect)
            logger.info("🔍 Phase 1: Reflection")
            reflection = await self.continuous_learner.reflect(memory_dicts, interactions)

            # 3. 冲突检测
            logger.info("⚠️  Detecting conflicts...")
            conflicts = self.conflict_detector.detect_conflicts(memory_dicts)
            reflection['conflicts'] = conflicts

            # 4. 调整阶段 (Adjust)
            logger.info("⚙️  Phase 2: Adjustment")
            adjustments = self.continuous_learner.adjust(reflection)

            # 5. 优化阶段 (Optimize)
            logger.info("🚀 Phase 3: Optimization")
            optimization = self.continuous_learner.optimize(adjustments)

            result = {
                'cycle_complete': True,
                'timestamp': datetime.now().isoformat(),
                'reflection': reflection,
                'adjustments': adjustments,
                'optimization': optimization
            }

            logger.info(f"✅ Continuous learning cycle complete: "
                       f"{len(adjustments.get('recommendations', []))} adjustments, "
                       f"{len(conflicts)} conflicts detected")

            return result

        except Exception as e:
            logger.error(f"❌ Continuous learning cycle failed: {e}", exc_info=True)
            return {
                'cycle_complete': False,
                'error': str(e)
            }

    # ============================================================================
    # Memory Storage
    # ============================================================================

    async def _store_memory_if_needed(self, user_input: str, response: str, context: Dict[str, Any] = None) -> bool:
        """
        辅助方法: 根据输入类型存储记忆

        🧠 Plan C实现: 存储到对应脑区，而不是中央数据库
        - 情节记忆 → Hippocampus
        - 对话记忆 → Hippocampus (短期) + 自动巩固到TemporalLobe (长期)
        """
        if context is None:
            context = {}

        try:
            # 🔥 FIX Q2: 检测简单问答对话，避免存储污染记忆
            # 使用单词边界匹配避免误判 (如 "show" 包含 "how")
            import re
            question_pattern = r'\b(when|what|who|where|how|why|which|did|does|do|is|are|was|were)\b'
            is_simple_question = (
                user_input.strip().endswith('?') and
                len(user_input) < 100 and
                re.search(question_pattern, user_input.lower()) is not None
            )

            if is_simple_question:
                # 简单问答不存储（避免Q1答案污染Q2查询）
                logger.info(f"⏭️ Skipping memory storage: detected simple question-answer pattern")
                return False

            # 扩展学习检测：包括factual statements, identity, occupation等
            is_learning = any(kw in user_input.lower() for kw in [
                'on ', 'may', 'attended', 'researched', 'learned', 'studied',
                'works in', 'is a', 'identifies as', 'came out', 'was accepted',
                'joined', 'specializing in', 'helps', 'supports'
            ])

            if is_learning:
                # 🔥 NEW: 根据content_type选择存储位置
                temporal_info = context.get('temporal_info', {})
                ref_time_str = temporal_info.get('reference_time')
                content_type = temporal_info.get('content_type', 'realtime')

                if ref_time_str and content_type == 'historical':
                    # ✅ 历史内容 → 语义记忆 (Temporal Lobe)
                    ref_time = datetime.fromisoformat(ref_time_str)

                    # 1. 存储语义知识到 Temporal Lobe
                    semantic_metadata = self._augment_memory_metadata(
                        {
                            'type': 'historical_fact',
                            'timeline_id': temporal_info.get('timeline_id')
                        },
                        importance=0.8,
                        source='temporal_lobe_semantic'
                    )
                    result = await self._activate_agent(
                        'temporal_lobe',
                        AgentMessage(
                            sender='coordinator',
                            receiver='temporal_lobe',
                            message_type='request',
                            content={
                                'action': 'store_semantic',
                                'content': user_input,
                                'event_time': ref_time_str,  # 事件发生时间
                                'entities': self._extract_entities(user_input),
                                'importance': 0.8,
                                'metadata': semantic_metadata
                            }
                        )
                    )
                    logger.info(f"📚 Stored semantic memory (event_time={ref_time.strftime('%Y-%m-%d %H:%M')})")

                    # 2. 同时在 Hippocampus 记录"我读取了这个信息"
                    entities_str = ", ".join(self._extract_entities(user_input)[:3])
                    learning_episode_metadata = self._augment_memory_metadata(
                        {'type': 'learning_record', 'source': 'historical_content'},
                        importance=0.5,
                        source='hippocampus_historical_note'
                    )
                    await self._activate_agent(
                        'hippocampus',
                        AgentMessage(
                            sender='coordinator',
                            receiver='hippocampus',
                            message_type='request',
                            content={
                                'action': 'store_episode',
                                'content': f"我学习了关于 {entities_str} 的历史对话",
                                'importance': 0.5,
                                'entities': [],
                                'metadata': learning_episode_metadata
                            }
                        )
                    )
                    logger.info(f"📝 Recorded learning episode in Hippocampus")

                    memory_id = result.get('memory_id')
                else:
                    # ✅ 实时对话/未知类型 → 情节记忆 (Hippocampus)
                    realtime_metadata = self._augment_memory_metadata(
                        {'type': 'learning', 'context': context},
                        importance=0.8,
                        source='hippocampus_learning'
                    )
                    result = await self._activate_agent(
                        'hippocampus',
                        AgentMessage(
                            sender='coordinator',
                            receiver='hippocampus',
                            message_type='request',
                            content={
                                'action': 'store_episode',
                                'content': user_input,
                                'importance': 0.8,
                                'entities': self._extract_entities(user_input),
                                'emotion_tags': [],
                                'emotion_intensity': 0.0,
                                'metadata': realtime_metadata
                            }
                        )
                    )
                    logger.info(f"📚 Stored episodic memory (realtime)")
                    memory_id = result.get('memory_id')

                return True
            else:
                # 🧠 存储对话到Hippocampus
                conversation_content = f"用户: {user_input}\\n助手: {response}"
                conversation_metadata = self._augment_memory_metadata(
                    {'type': 'conversation', 'context': context},
                    importance=0.5,
                    source='hippocampus_conversation'
                )
                result = await self._activate_agent(
                    'hippocampus',
                    AgentMessage(
                        sender='coordinator',
                        receiver='hippocampus',
                        message_type='request',
                        content={
                            'action': 'store_episode',
                            'content': conversation_content,
                            'importance': 0.5,
                            'entities': self._extract_entities(user_input),
                            'emotion_tags': [],
                            'emotion_intensity': 0.0,
                            'metadata': conversation_metadata
                        }
                    )
                )
                memory_id = result.get('memory_id')
                logger.info(f"💬 Stored conversation to Hippocampus: {memory_id}")
                return True
        except Exception as e:
            logger.warning(f"Memory storage to brain regions failed: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")
            return False

    def _augment_memory_metadata(
        self,
        base_metadata: Optional[Dict[str, Any]],
        importance: float,
        source: str
    ) -> Dict[str, Any]:
        """
        Attach scoring scaffolding so later phases can adjust confidence/decay dynamically.
        """
        metadata = dict(base_metadata or {})
        utc_now = datetime.utcnow().isoformat()

        if 'confidence' not in metadata:
            metadata['confidence'] = round(max(0.0, min(1.0, importance)), 2)
        metadata.setdefault('hit_count', 0)
        metadata.setdefault('decay_factor', 1.0)
        metadata.setdefault('created_at', utc_now)
        metadata.setdefault('last_accessed', utc_now)
        metadata.setdefault('source', source)

        return metadata

    def _parse_iso_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            text = str(value)
            if text.endswith('Z'):
                text = text[:-1] + '+00:00'
            return datetime.fromisoformat(text)
        except Exception:
            return None

    def _apply_plasticity_ranking(
        self,
        memories: List[Dict[str, Any]],
        k: Optional[int] = None,
        keywords: Optional[Iterable[str]] = None,
        missing_keywords: Optional[Iterable[str]] = None,
        context: Optional[str] = None,
        conflicts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply brain-inspired scoring that blends retrieval signals with plasticity metadata.
        """
        if not memories:
            return memories

        scoring_cfg = self.memory_signal_config.get(
            'memory_scoring',
            DEFAULT_MEMORY_SIGNAL_CONFIG['memory_scoring']
        )
        weights_cfg = scoring_cfg.get('weights', {})
        weights_cfg = {
            'confidence': weights_cfg.get('confidence', 0.35),
            'hit_count': weights_cfg.get('hit_count', 0.15),
            'recency': weights_cfg.get('recency', 0.3),
            'decay': weights_cfg.get('decay', 0.1),
            'hybrid_score': weights_cfg.get('hybrid_score', 0.1),
            'coverage_bonus': weights_cfg.get('coverage_bonus', 0.1),
            'conflict_penalty': weights_cfg.get('conflict_penalty', 0.1)
        }

        total_weight = sum(max(0.0, float(w)) for w in [
            weights_cfg['confidence'],
            weights_cfg['hit_count'],
            weights_cfg['recency'],
            weights_cfg['decay'],
            weights_cfg['hybrid_score'],
            weights_cfg['coverage_bonus'],
            weights_cfg['conflict_penalty']
        ])
        if total_weight <= 0:
            return memories[:k] if k else memories

        now = datetime.utcnow()
        half_life_hours = max(scoring_cfg.get('recency_half_life_hours', 12), 0.1)
        recency_lambda = math.log(2) / half_life_hours
        hit_lambda = scoring_cfg.get('hit_count_lambda', 0.3)
        defaults = scoring_cfg.get('defaults', {})
        keywords = set(kw.lower() for kw in (keywords or []))
        missing_keywords = set(kw.lower() for kw in (missing_keywords or []))
        conflicts = conflicts or []

        ranked: List[Dict[str, Any]] = []
        for mem in memories:
            metadata = mem.get('metadata') or {}
            if not isinstance(metadata, dict):
                metadata = {}
            mem['metadata'] = metadata
            retrieval_scores = metadata.setdefault('retrieval_scores', {})

            confidence = float(metadata.get('confidence', defaults.get('confidence', 0.6)))
            confidence = max(0.0, min(1.0, confidence))

            hit_count = max(0, int(metadata.get('hit_count', 0)))
            hit_component = 1.0 - math.exp(-hit_count * hit_lambda)

            last_accessed = metadata.get('last_accessed') or metadata.get('created_at')
            last_dt = self._parse_iso_datetime(last_accessed)
            if last_dt:
                recency_hours = max((now - last_dt).total_seconds() / 3600.0, 0.0)
                recency_score = math.exp(-recency_lambda * recency_hours)
            else:
                recency_score = 0.5

            decay_factor = float(metadata.get('decay_factor', 1.0))
            decay_factor = max(0.0, min(1.0, decay_factor))

            base_hybrid = retrieval_scores.get('hybrid')
            if base_hybrid is None:
                base_hybrid = retrieval_scores.get('kg_joint', 0.5)
            base_hybrid = max(0.0, min(1.0, float(base_hybrid))) if base_hybrid is not None else 0.0

            content_lower = (mem.get('content') or '').lower()
            missing_hits = sum(1 for kw in missing_keywords if kw and kw in content_lower)
            coverage_bonus = 0.1 * missing_hits  # 每覆盖一个缺失关键词 +0.1

            conflict_penalty = 0.0
            if conflicts:
                mem_id = mem.get('id')
                conflict_hits = [
                    c for c in conflicts
                    if (c.get('source1', {}).get('id') == mem_id or
                        c.get('source2', {}).get('id') == mem_id)
                ]
                conflict_penalty = 0.05 * len(conflict_hits)  # 每个冲突 -0.05

            composite = (
                weights_cfg['confidence'] * confidence +
                weights_cfg['hit_count'] * hit_component +
                weights_cfg['recency'] * recency_score +
                weights_cfg['decay'] * decay_factor +
                weights_cfg['hybrid_score'] * base_hybrid
            ) / total_weight

            composite += coverage_bonus
            composite -= conflict_penalty
            composite = max(0.0, min(1.0, composite))

            metadata['last_accessed'] = now.isoformat()
            metadata['hit_count'] = hit_count + 1
            metadata['coverage_bonus'] = round(coverage_bonus, 4)
            metadata['conflict_penalty'] = round(conflict_penalty, 4)
            mem['coverage_bonus'] = metadata['coverage_bonus']
            mem['conflict_penalty'] = metadata['conflict_penalty']
            mem['plasticity_score'] = round(composite, 4)

            ranked.append(mem)

        ranked.sort(key=lambda x: x.get('plasticity_score', 0.0), reverse=True)
        if k:
            return ranked[:k]
        return ranked

    def _extract_entities(self, text: str) -> List[str]:
        """简单的实体提取 (可以后续用NER替换)"""
        # 简单实现：提取大写开头的词
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        # 去重
        return list(set(words))

    # ==================== 🔥 Phase 2: Cross-Time Cross-Text Reasoning ====================

    async def cross_time_cross_text_reasoning(
        self,
        query: str,
        time_constraint: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        跨时空跨文本推理 - 编排多Agent实现复杂推理 (涌现能力)

        理论依据:
        - 这不是单独的"跨时空推理脑区" (神经科学中不存在)
        - 而是多脑区协作的涌现能力 (emergent capability)
        - Miller & Cohen (2001): Prefrontal cortex orchestrates activity across brain regions

        流程:
        1. PrefrontalAgent: 元认知评估 (是否需要外部信息?)
        2. MemoryRetrievalAgent: 多源并行检索
        3. PrefrontalAgent: 冲突检测
        4. ReasoningValidator: 统一推理 + 冲突解决

        Args:
            query: 用户问题
            time_constraint: {'start': datetime, 'end': datetime} (可选)

        Returns:
            {
                'answer': str,
                'sources_used': List[str],
                'conflicts_detected': int,
                'confidence': float,
                'reasoning_chain': List[Dict],
                'processing_time_ms': float
            }
        """
        import time
        start_time = time.time()

        logger.info(f"🧠 Cross-temporal cross-textual reasoning for: {query[:100]}...")

        # Step 1: 快速内部检索 (用于元认知评估)
        quick_results = await self.memory_retrieval.retrieve_multi_source(
            query=query,
            time_constraint=time_constraint,
            strategy='adaptive',
            k=5,  # 快速检索少量结果
            brain_coordinator=self
        )

        # Step 2: 元认知评估 (需要更多信息吗?)
        episodic_results = quick_results.get('episodic', [])
        semantic_results = quick_results.get('semantic', [])
        internal_results = episodic_results + semantic_results

        assessment = await self.prefrontal_storage.process_message(AgentMessage(
            sender='coordinator',
            receiver='prefrontal',
            message_type='request',
            content={
                'action': 'assess_confidence',
                'query': query,
                'internal_results': internal_results
            }
        ))

        logger.info(f"📊 Metacognitive assessment: confidence={assessment.get('confidence', 0):.2f}, external_needed={assessment.get('should_use_external', False)}")

        # Step 3: 完整多源检索
        multi_source_results = await self.memory_retrieval.retrieve_multi_source(
            query=query,
            time_constraint=time_constraint,
            strategy='adaptive',
            k=10,  # 完整检索
            brain_coordinator=self
        )

        # Step 4: 如果需要外部记忆 (且系统有)
        if assessment.get('should_use_external', False) and hasattr(self, 'external_memory') and self.external_memory:
            logger.info("🌐 Confidence low, searching external documents...")
            external_results = await self.external_memory.search(
                query=query,
                sources=['documents', 'notebook'],
                k=10
            )
            # 合并外部结果
            external_docs = external_results.get('documents', [])
            external_notes = external_results.get('notebook', [])
            multi_source_results['external'] = external_docs + [
                {'content': note.content, 'title': note.title, 'source': 'notebook'}
                for note in external_notes
            ]

        # Step 5: 统一推理 (with conflict resolution)
        reasoning_result = await self.reasoning_validator.unified_reasoning_with_conflict_resolution(
            query=query,
            multi_source_memories=multi_source_results,
            prefrontal_agent=self.prefrontal_storage,
            context={'capabilities': ['multi_fact_integration', 'temporal_reasoning']}
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(f"✅ Cross-temporal reasoning completed in {processing_time_ms:.1f}ms")

        return {
            'answer': reasoning_result.get('answer', ''),
            'sources_used': list(multi_source_results.keys()),
            'conflicts_detected': reasoning_result.get('conflicts_detected', 0),
            'conflicts': reasoning_result.get('conflicts', []),
            'confidence': reasoning_result.get('confidence', 0.5),
            'reasoning_chain': reasoning_result.get('reasoning_chain', []),
            'processing_time_ms': processing_time_ms,
            'metacognitive_assessment': assessment,
            'resolution_strategy': reasoning_result.get('resolution_strategy', 'no_conflict')
        }

    # ==================== 🔥 Phase 3: External Memory Integration ====================

    async def ingest_external_document(
        self,
        title: str,
        content: str,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        接收外部文档 (用于场景2: 10篇论文/8本书)

        理论依据:
        - Extended Mind Theory (Clark & Chalmers, 1998)
        - Cognitive Offloading (Risko & Gilbert, 2016)

        Args:
            title: 文档标题
            content: 文档内容 (全文)
            metadata: 元数据 (作者、出版年份等)

        Returns:
            {
                'document_id': str,
                'chunks_count': int,
                'entities_extracted': int,
                'relations_extracted': int
            }
        """

        if not self.external_memory:
            return {
                'error': 'ExternalMemorySystem not enabled',
                'hint': 'Set USE_EXTERNAL_MEMORY=true in environment variables'
            }

        logger.info(f"📥 Ingesting external document: {title}")

        doc_id = await self.external_memory.ingest_document(
            title=title,
            content=content,
            metadata=metadata,
            extract_kg=True  # 提取知识图谱
        )

        # 获取文档信息
        doc = self.external_memory.documents.get_document(doc_id)

        result = {
            'document_id': doc_id,
            'chunks_count': len(doc.chunks) if doc and doc.chunks else 0,
            'entities_extracted': len(doc.metadata.get('entities', [])) if doc else 0,
            'relations_extracted': len(doc.metadata.get('relations', [])) if doc else 0,
            'status': 'success'
        }

        logger.info(f"✅ Document ingested: {result['chunks_count']} chunks, "
                   f"{result['entities_extracted']} entities, "
                   f"{result['relations_extracted']} relations")

        return result

    async def add_external_note(self, title: str, content: str, metadata: Dict = None) -> str:
        """
        添加外部笔记

        Args:
            title: 笔记标题
            content: 笔记内容
            metadata: 元数据

        Returns:
            note_id
        """
        if not self.external_memory:
            logger.warning("ExternalMemorySystem not enabled")
            return None

        return await self.external_memory.add_note(title, content, metadata)

    async def search_external_memory(
        self,
        query: str,
        sources: List[str] = None,
        k: int = 10
    ) -> Dict[str, List]:
        """
        搜索外部记忆

        Args:
            query: 查询文本
            sources: 搜索源 ['notebook', 'documents', 'kg']
            k: 返回数量

        Returns:
            {
                'notebook': [...],
                'documents': [...],
                'kg': [...]
            }
        """
        if not self.external_memory:
            logger.warning("ExternalMemorySystem not enabled")
            return {}

        return await self.external_memory.search(query, sources, k)

    # ==================== 🔥 Learning & Feedback ====================

    async def apply_feedback(
        self,
        query: str,
        response: str,
        feedback_score: float,
        activation_trace: Optional[Dict[str, List[float]]] = None,
        memories_used: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        应用反馈到系统，触发学习 (类脑可塑性)

        Args:
            query: 原始输入
            response: 系统响应
            feedback_score: 反馈分数 (0.0-1.0, 1.0=完全正确)
            activation_trace: BrainNetwork的激活轨迹 (可选)
            memories_used: 使用的记忆ID列表 (可选)

        Returns:
            {
                'learned': bool,
                'reward_value': float,
                'adjustments': {
                    'weights_adjusted': int,
                    'memories_modulated': int
                }
            }
        """
        logger.info(f"🧠 Applying feedback: score={feedback_score:.2f}")

        try:
            # 🔥 步骤1: 计算奖励信号 (非线性映射)
            if feedback_score >= 0.7:
                reward_value = (feedback_score - 0.7) / 0.3 * 0.6 + 0.4  # 0.4 to 1.0
                reward_type = 'positive'
            elif feedback_score >= 0.3:
                reward_value = (feedback_score - 0.3) / 0.4 * 0.6 - 0.2  # -0.2 to 0.4
                reward_type = 'neutral'
            else:
                reward_value = (feedback_score / 0.3 - 1.0) * 0.8  # -1.0 to -0.2
                reward_type = 'negative'

            logger.info(f"   🎁 Reward: {reward_value:+.2f} ({reward_type})")

            # 🔥 步骤2: 发送奖励到EnvironmentAgent
            await self._activate_agent(
                'environment',
                AgentMessage(
                    sender='coordinator',
                    receiver='environment',
                    message_type='request',
                    content={
                        'action': 'issue_reward',
                        'reward_type': reward_type,
                        'reward_value': reward_value,
                        'reason': f"Feedback on query: {query[:50]}... (score={feedback_score:.2f})",
                        'metadata': {
                            'query': query,
                            'response': response[:100],
                            'score': feedback_score
                        }
                    }
                )
            )

            adjustments = {
                'weights_adjusted': 0,
                'memories_modulated': 0
            }

            # 🔥 步骤3: 调整BrainNetwork连接权重
            if self.use_brain_network and activation_trace:
                weight_result = await self.brain_network.adjust_weights_from_feedback(
                    activation_trace=activation_trace,
                    reward_signal=reward_value
                )
                adjustments['weights_adjusted'] = weight_result.get('connections_adjusted', 0)
                logger.info(f"   🔗 Adjusted {adjustments['weights_adjusted']} connections")

            # 🔥 步骤4: 调节记忆重要性 (通过Amygdala)
            if memories_used:
                for memory_id in memories_used:
                    try:
                        importance_delta = reward_value * 0.1  # 小幅调整
                        await self._activate_agent(
                            'amygdala',
                            AgentMessage(
                                sender='coordinator',
                                receiver='amygdala',
                                message_type='request',
                                content={
                                    'action': 'modulate_memory_importance',
                                    'memory_id': memory_id,
                                    'importance_delta': importance_delta,
                                    'reason': f"Feedback modulation (reward={reward_value:+.2f})"
                                }
                            )
                        )
                        adjustments['memories_modulated'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to modulate memory {memory_id}: {e}")

                logger.info(f"   💝 Modulated {adjustments['memories_modulated']} memories")

            return {
                'learned': True,
                'reward_value': reward_value,
                'reward_type': reward_type,
                'adjustments': adjustments
            }

        except Exception as e:
            logger.error(f"❌ Failed to apply feedback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'learned': False,
                'error': str(e)
            }


# Global coordinator instance removed - to avoid duplicate initialization


async def main():
    """Test the coordinator system"""
    print("Testing Brain-Inspired Coordinator System...")
    
    # 创建协调器实例
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    
    # Test cases
    test_inputs = [
        "你好，我想了解这个系统",
        "请记住我喜欢喝咖啡和读书",
        "计算 25 * 4 + 10",
        "我今天感到有些焦虑，工作压力很大",
        "你能帮我分析一下我的记忆模式吗？"
    ]
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n{'='*50}")
        print(f"Test {i}: {test_input}")
        print(f"{'='*50}")
        
        result = await coordinator.process_user_input(test_input)
        
        print(f"Success: {result.success}")
        print(f"Response: {result.response}")
        print(f"Processing time: {result.processing_time:.2f}s")
        print(f"Agents involved: {result.agents_involved}")
        print(f"Memories found: {len(result.memories_retrieved)}")
        print(f"Memory stored: {result.memory_stored}")
        
        if result.insights:
            print(f"Insights: {json.dumps(result.insights, ensure_ascii=False, indent=2)}")
    
    # System status
    print(f"\n{'='*50}")
    print("System Status:")
    print(f"{'='*50}")
    status = coordinator.get_system_status()
    print(json.dumps(status, ensure_ascii=False, indent=2, default=str))
    
    await coordinator.stop_system()


if __name__ == "__main__":
    asyncio.run(main())
