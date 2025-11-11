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


@dataclass(frozen=True)
class MemorySystemConfig:
    """
    Memory system configuration
    记忆系统配置
    """
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_max_length: int = 8191
    enable_cache: bool = True
    cache_dir: str = "data/embedding_cache"
    cache_max_size: int = 10000
    cache_ttl_hours: int = 24

    vector_db_index_path: str = "data/faiss_index"
    max_vectors: int = 5000
    compaction_frequency: int = 50

    database_url: str = "sqlite:///data/memories.db"
    connection_pool_size: int = 5


@dataclass(frozen=True)
class AgentConfig:
    """
    Agent system configuration
    智能体系统配置
    """
    default_model: str = "gpt-4o-mini"
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

    max_concurrent_agents: int = 10
    enable_learning: bool = True
    enable_background_processes: bool = True

    consolidation_interval_seconds: int = 3600
    forgetting_interval_seconds: int = 7200
    reconsolidation_interval_seconds: int = 1800

    default_language: str = "en"


@dataclass(frozen=True)
class BMAMConfig:
    """
    Root configuration object
    根配置对象
    """
    memory: MemorySystemConfig = field(default_factory=MemorySystemConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    coordinator: CoordinatorConfig = field(default_factory=CoordinatorConfig)

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
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            embedding_max_length=int(os.getenv("EMBEDDING_MAX_LENGTH", "8191")),
            enable_cache=os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true",
            cache_dir=os.getenv("EMBEDDING_CACHE_DIR", "data/embedding_cache"),
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "10000")),
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
            vector_db_index_path=os.getenv("FAISS_INDEX_PATH", "data/faiss_index"),
            max_vectors=int(os.getenv("MAX_FAISS_VECTORS", "5000")),
            compaction_frequency=int(os.getenv("FAISS_COMPACTION_FREQUENCY", "50")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///data/memories.db"),
            connection_pool_size=int(os.getenv("DB_POOL_SIZE", "5"))
        )

        # Agent config / 智能体配置
        agent_config = AgentConfig(
            default_model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
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
            max_concurrent_agents=int(os.getenv("MAX_CONCURRENT_AGENTS", "10")),
            enable_learning=os.getenv("ENABLE_LEARNING", "true").lower() == "true",
            enable_background_processes=os.getenv("ENABLE_BACKGROUND_PROCESSES", "true").lower() == "true",
            consolidation_interval_seconds=int(os.getenv("CONSOLIDATION_INTERVAL", "3600")),
            forgetting_interval_seconds=int(os.getenv("FORGETTING_INTERVAL", "7200")),
            reconsolidation_interval_seconds=int(os.getenv("RECONSOLIDATION_INTERVAL", "1800")),
            default_language=os.getenv("BMAM_DEFAULT_LANGUAGE", "en").lower()
        )

        return cls(
            memory=memory_config,
            agent=agent_config,
            coordinator=coordinator_config,
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

        return cls(
            memory=memory_config,
            agent=agent_config,
            coordinator=coordinator_config,
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
