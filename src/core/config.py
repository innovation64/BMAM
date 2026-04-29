"""
Centralized Configuration Management
集中配置管理

Type-safe configuration using dataclasses
使用数据类的类型安全配置
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os
from pathlib import Path
from functools import lru_cache

from src.core.constants import (
    DEFAULT_LLM_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MAX_LENGTH,
)
from src.utils.paths import BMAMPaths


@dataclass(frozen=True)
class MemorySystemConfig:
    """
    Memory system configuration
    记忆系统配置
    """
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION
    embedding_max_length: int = DEFAULT_EMBEDDING_MAX_LENGTH
    enable_cache: bool = True
    cache_dir: str = str(BMAMPaths.EMBEDDING_CACHE_DIR)
    cache_max_size: int = 10000
    cache_ttl_hours: int = 24

    vector_db_index_path: str = str(BMAMPaths.DATA_DIR / "faiss_index")
    max_vectors: int = 5000
    compaction_frequency: int = 50

    database_url: str = f"sqlite:///{BMAMPaths.BRAIN_MEMORY_DB}"
    connection_pool_size: int = 5


@dataclass(frozen=True)
class AgentConfig:
    """
    Agent system configuration
    智能体系统配置
    """
    default_model: str = DEFAULT_LLM_MODEL
    max_tokens: int = 1500
    temperature: float = 0.7
    llm_call_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

    fallback_cache_size: int = 50
    enable_activation_logging: bool = True


@dataclass(frozen=True)
class CoordinatorConfig:
    """
    Brain coordinator configuration
    大脑协调器配置
    """
    parallel_phase_timeout: float = 15.0
    buffer_exchange_timeout: float = 5.0
    memory_storage_timeout: float = 8.0
    request_timeout: float = 90.0

    max_concurrent_agents: int = 10
    enable_learning: bool = True
    enable_background_processes: bool = True

    consolidation_interval_seconds: int = 3600
    forgetting_interval_seconds: int = 7200
    reconsolidation_interval_seconds: int = 1800

    default_language: str = "en"


@dataclass(frozen=True)
class RetrievalConfig:
    """Retrieval system configuration / 检索系统配置"""
    learning_rate: float = 0.1
    quality_threshold: float = 0.3
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    kg_coverage_threshold: float = 0.5
    default_top_k: int = 10
    max_retrieval_rounds: int = 3
    confidence_threshold: float = 0.85
    gap_threshold: float = 0.3
    min_memories_for_quality: int = 3


@dataclass(frozen=True)
class ConsolidationConfig:
    """Memory consolidation configuration / 记忆固化配置"""
    min_hit_count: int = 3
    min_confidence: float = 0.7
    interval_seconds: int = 3600
    batch_size: int = 50
    max_consolidation_items: int = 100


@dataclass(frozen=True)
class ForgettingConfig:
    """Memory forgetting configuration / 记忆遗忘配置"""
    interval_seconds: int = 7200
    importance_weight: float = 0.3
    access_weight: float = 0.25
    age_weight: float = 0.25
    emotion_weight: float = 0.2
    min_importance_to_keep: float = 0.3
    max_forget_per_cycle: int = 50


@dataclass(frozen=True)
class TokenConfig:
    """Token processing configuration / Token处理配置"""
    short_threshold: int = 1000
    medium_threshold: int = 5000
    extraction_temperature: float = 0.3
    max_chunk_tokens: int = 1000
    chunk_overlap: int = 150


@dataclass(frozen=True)
class EmotionConfig:
    """Emotion system configuration / 情绪系统配置"""
    high_intensity_threshold: float = 0.7
    stress_threshold: float = 0.8
    moderate_arousal_threshold: float = 0.5
    emotion_boost_factor: float = 0.2
    emotion_decay_rate: float = 0.95


@dataclass(frozen=True)
class BMAMConfig:
    """
    Root configuration object
    根配置对象
    """
    memory: MemorySystemConfig = field(default_factory=MemorySystemConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    coordinator: CoordinatorConfig = field(default_factory=CoordinatorConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    consolidation: ConsolidationConfig = field(default_factory=ConsolidationConfig)
    forgetting: ForgettingConfig = field(default_factory=ForgettingConfig)
    token: TokenConfig = field(default_factory=TokenConfig)
    emotion: EmotionConfig = field(default_factory=EmotionConfig)

    # Environment / 环境
    openai_api_key: Optional[str] = None
    environment: str = "production"  # production, development, test
    log_level: str = "INFO"
    log_file: Optional[str] = "bmam.log"

    @classmethod
    def from_env(cls) -> 'BMAMConfig':
        """
        Load configuration from environment variables
        从环境变量加载配置

        Environment variables:
        - BMAM_ENV: Environment (production/development/test)
        - OPENAI_API_KEY: OpenAI API key
        - EMBEDDING_MODEL: Embedding model name
        - EMBEDDING_DIMENSION: Embedding vector dimension
        - DEFAULT_MODEL: Default LLM model
        - LLM_CALL_TIMEOUT: LLM call timeout in seconds
        """

        # Memory system config / 记忆系统配置
        memory_config = MemorySystemConfig(
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
            ),
            embedding_dimension=int(os.getenv(
                "EMBEDDING_DIMENSION",
                str(DEFAULT_EMBEDDING_DIMENSION)
            )),
            embedding_max_length=int(os.getenv(
                "EMBEDDING_MAX_LENGTH",
                str(DEFAULT_EMBEDDING_MAX_LENGTH)
            )),
            enable_cache=os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true",
            cache_dir=os.getenv("EMBEDDING_CACHE_DIR", str(BMAMPaths.EMBEDDING_CACHE_DIR)),
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "10000")),
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
            vector_db_index_path=os.getenv(
                "FAISS_INDEX_PATH",
                str(BMAMPaths.DATA_DIR / "faiss_index")
            ),
            max_vectors=int(os.getenv("MAX_FAISS_VECTORS", "5000")),
            compaction_frequency=int(os.getenv("FAISS_COMPACTION_FREQUENCY", "50")),
            database_url=os.getenv(
                "DATABASE_URL",
                f"sqlite:///{BMAMPaths.BRAIN_MEMORY_DB}"
            ),
            connection_pool_size=int(os.getenv("DB_POOL_SIZE", "5"))
        )

        # Agent config / 智能体配置
        agent_config = AgentConfig(
            default_model=os.getenv("DEFAULT_MODEL", DEFAULT_LLM_MODEL),
            max_tokens=int(os.getenv("MAX_TOKENS", "1500")),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            llm_call_timeout=float(os.getenv("LLM_CALL_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("LLM_RETRY_DELAY", "1.0")),
            fallback_cache_size=int(os.getenv("FALLBACK_CACHE_SIZE", "50")),
            enable_activation_logging=os.getenv("ENABLE_ACTIVATION_LOGGING", "true").lower() == "true"
        )

        # Coordinator config / 协调器配置
        coordinator_config = CoordinatorConfig(
            parallel_phase_timeout=float(os.getenv("PARALLEL_PHASE_TIMEOUT", "15.0")),
            buffer_exchange_timeout=float(os.getenv("BUFFER_EXCHANGE_TIMEOUT", "5.0")),
            memory_storage_timeout=float(os.getenv("MEMORY_STORAGE_TIMEOUT", "8.0")),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "90.0")),
            max_concurrent_agents=int(os.getenv("MAX_CONCURRENT_AGENTS", "10")),
            enable_learning=os.getenv("ENABLE_LEARNING", "true").lower() == "true",
            enable_background_processes=os.getenv("ENABLE_BACKGROUND_PROCESSES", "true").lower() == "true",
            consolidation_interval_seconds=int(os.getenv("CONSOLIDATION_INTERVAL", "3600")),
            forgetting_interval_seconds=int(os.getenv("FORGETTING_INTERVAL", "7200")),
            reconsolidation_interval_seconds=int(os.getenv("RECONSOLIDATION_INTERVAL", "1800")),
            default_language=os.getenv("BMAM_DEFAULT_LANGUAGE", "en").lower()
        )

        # Retrieval config / 检索配置
        retrieval_config = RetrievalConfig(
            learning_rate=float(os.getenv("RETRIEVAL_LEARNING_RATE", "0.1")),
            quality_threshold=float(os.getenv("RETRIEVAL_QUALITY_THRESHOLD", "0.3")),
            bm25_k1=float(os.getenv("BM25_K1", "1.5")),
            bm25_b=float(os.getenv("BM25_B", "0.75")),
            kg_coverage_threshold=float(os.getenv("KG_COVERAGE_THRESHOLD", "0.5")),
            default_top_k=int(os.getenv("RETRIEVAL_DEFAULT_TOP_K", "10")),
            max_retrieval_rounds=int(os.getenv("MAX_RETRIEVAL_ROUNDS", "3")),
            confidence_threshold=float(os.getenv("RETRIEVAL_CONFIDENCE_THRESHOLD", "0.85")),
            gap_threshold=float(os.getenv("RETRIEVAL_GAP_THRESHOLD", "0.3")),
            min_memories_for_quality=int(os.getenv("MIN_MEMORIES_FOR_QUALITY", "3"))
        )

        # Consolidation config / 固化配置
        consolidation_config = ConsolidationConfig(
            min_hit_count=int(os.getenv("CONSOLIDATION_MIN_HIT_COUNT", "3")),
            min_confidence=float(os.getenv("CONSOLIDATION_MIN_CONFIDENCE", "0.7")),
            interval_seconds=int(os.getenv("CONSOLIDATION_INTERVAL", "3600")),
            batch_size=int(os.getenv("CONSOLIDATION_BATCH_SIZE", "50")),
            max_consolidation_items=int(os.getenv("MAX_CONSOLIDATION_ITEMS", "100"))
        )

        # Forgetting config / 遗忘配置
        forgetting_config = ForgettingConfig(
            interval_seconds=int(os.getenv("FORGETTING_INTERVAL", "7200")),
            importance_weight=float(os.getenv("FORGETTING_IMPORTANCE_WEIGHT", "0.3")),
            access_weight=float(os.getenv("FORGETTING_ACCESS_WEIGHT", "0.25")),
            age_weight=float(os.getenv("FORGETTING_AGE_WEIGHT", "0.25")),
            emotion_weight=float(os.getenv("FORGETTING_EMOTION_WEIGHT", "0.2")),
            min_importance_to_keep=float(os.getenv("FORGETTING_MIN_IMPORTANCE", "0.3")),
            max_forget_per_cycle=int(os.getenv("MAX_FORGET_PER_CYCLE", "50"))
        )

        # Token config / Token配置
        token_config = TokenConfig(
            short_threshold=int(os.getenv("TOKEN_SHORT_THRESHOLD", "1000")),
            medium_threshold=int(os.getenv("TOKEN_MEDIUM_THRESHOLD", "5000")),
            extraction_temperature=float(os.getenv("EXTRACTION_TEMPERATURE", "0.3")),
            max_chunk_tokens=int(os.getenv("MAX_CHUNK_TOKENS", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150"))
        )

        # Emotion config / 情绪配置
        emotion_config = EmotionConfig(
            high_intensity_threshold=float(os.getenv("EMOTION_HIGH_INTENSITY", "0.7")),
            stress_threshold=float(os.getenv("EMOTION_STRESS_THRESHOLD", "0.8")),
            moderate_arousal_threshold=float(os.getenv("EMOTION_MODERATE_AROUSAL", "0.5")),
            emotion_boost_factor=float(os.getenv("EMOTION_BOOST_FACTOR", "0.2")),
            emotion_decay_rate=float(os.getenv("EMOTION_DECAY_RATE", "0.95"))
        )

        return cls(
            memory=memory_config,
            agent=agent_config,
            coordinator=coordinator_config,
            retrieval=retrieval_config,
            consolidation=consolidation_config,
            forgetting=forgetting_config,
            token=token_config,
            emotion=emotion_config,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            environment=os.getenv("BMAM_ENV", "production"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "bmam.log")
        )

    @classmethod
    def for_testing(cls) -> 'BMAMConfig':
        """
        Create configuration optimized for testing
        创建针对测试优化的配置
        """

        memory_config = MemorySystemConfig(
            enable_cache=False,  # Disable cache for predictable tests
            cache_dir="test_data/cache",
            max_vectors=100,  # Small limits for fast tests
            database_url="sqlite:///:memory:",  # In-memory database
            connection_pool_size=1
        )

        agent_config = AgentConfig(
            llm_call_timeout=5.0,  # Short timeout for tests
            max_retries=0,  # No retries in tests
            fallback_cache_size=10,
            enable_activation_logging=False
        )

        coordinator_config = CoordinatorConfig(
            parallel_phase_timeout=5.0,
            enable_learning=False,  # Disable learning in tests
            enable_background_processes=False,  # No background processes
            consolidation_interval_seconds=30,
            forgetting_interval_seconds=60
        )

        # Use defaults for new configs in testing (same behavior)
        retrieval_config = RetrievalConfig()
        consolidation_config = ConsolidationConfig()
        forgetting_config = ForgettingConfig()
        token_config = TokenConfig()
        emotion_config = EmotionConfig()

        return cls(
            memory=memory_config,
            agent=agent_config,
            coordinator=coordinator_config,
            retrieval=retrieval_config,
            consolidation=consolidation_config,
            forgetting=forgetting_config,
            token=token_config,
            emotion=emotion_config,
            environment="test",
            log_level="DEBUG",
            log_file=None  # No log file in tests
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert config to dictionary
        转换配置为字典
        """
        return {
            'memory': self.memory.__dict__,
            'agent': self.agent.__dict__,
            'coordinator': self.coordinator.__dict__,
            'retrieval': self.retrieval.__dict__,
            'consolidation': self.consolidation.__dict__,
            'forgetting': self.forgetting.__dict__,
            'token': self.token.__dict__,
            'emotion': self.emotion.__dict__,
            'environment': self.environment,
            'log_level': self.log_level,
            'log_file': self.log_file
        }


@lru_cache(maxsize=1)
def get_config() -> BMAMConfig:
    """
    Get global configuration instance (cached)
    获取全局配置实例（缓存）
    """
    return BMAMConfig.from_env()


def reset_config():
    """
    Reset cached configuration (for testing)
    重置缓存配置（用于测试）
    """
    get_config.cache_clear()
