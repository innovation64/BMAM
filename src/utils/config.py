"""
Centralized configuration module for environment and logging setup
"""

import logging
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables once at module import
_env_loaded = False

def init_environment():
    """Initialize environment variables from .env file"""
    global _env_loaded
    if not _env_loaded:
        # Find .env file in project root
        current = Path(__file__).resolve()
        while current.parent != current:
            env_file = current / '.env'
            if env_file.exists():
                load_dotenv(env_file)
                _env_loaded = True
                break
            current = current.parent
        
        # Fallback to default load_dotenv()
        if not _env_loaded:
            load_dotenv()
            _env_loaded = True

# Initialize environment on module import
init_environment()

# Logging configuration
_logging_configured = False

def setup_logging(level: int = logging.INFO, 
                  format: Optional[str] = None) -> logging.Logger:
    """
    Configure logging for the application
    
    Args:
        level: Logging level (default: INFO)
        format: Custom format string (optional)
    
    Returns:
        Root logger instance
    """
    global _logging_configured
    
    if not _logging_configured:
        if format is None:
            format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 确定日志文件路径 - 固定到项目根目录
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(project_root, 'bmam.log')
        
        class _VerboseFilter(logging.Filter):
            """Filter noisy debug statements unless verbose mode is enabled."""

            def __init__(self, verbose_enabled: bool):
                super().__init__()
                self._verbose_enabled = verbose_enabled

            def filter(self, record: logging.LogRecord) -> bool:
                if record.levelno >= logging.INFO:
                    return True
                return self._verbose_enabled

        verbose_debug = os.getenv('BMAM_VERBOSE_DEBUG', '').lower() in ('1', 'true', 'yes')
        stream_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_path, mode='a')
        debug_filter = _VerboseFilter(verbose_enabled=verbose_debug)
        stream_handler.addFilter(debug_filter)
        file_handler.addFilter(debug_filter)

        logging.basicConfig(
            level=level,
            format=format,
            handlers=[
                stream_handler,
                file_handler
            ]
        )
        _logging_configured = True
    
    return logging.getLogger()

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    # Ensure logging is configured
    if not _logging_configured:
        setup_logging()
    
    return logging.getLogger(name)

# Path utilities
def get_project_root() -> Path:
    """Get the absolute path to the project root directory"""
    return Path(__file__).resolve().parent.parent.parent

def get_absolute_path(relative_path: str) -> Path:
    """Convert relative path to absolute path relative to project root"""
    return get_project_root() / relative_path

# Environment variable helpers
def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable value
    
    Args:
        key: Environment variable name
        default: Default value if not found
    
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)

def require_env(key: str) -> str:
    """
    Get required environment variable value
    
    Args:
        key: Environment variable name
    
    Returns:
        Environment variable value
    
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


from datetime import datetime
from typing import List, Dict, Tuple

# ============================================================================
# 🧠 统一配置系统 - 消除所有硬编码
# ============================================================================

@dataclass(frozen=True)
class TemporalConfig:
    """时间相关配置 - 消除时间硬编码"""
    # 使用当前年份而非硬编码的2023
    default_reference_year: int = datetime.now().year

    # 时间窗口配置
    time_range_buffer_days: int = 7  # 时间检索的±天数缓冲
    context_window_hours: float = 6.0  # 事件上下文窗口（小时）

    # 相对时间解析
    days_per_month: int = 30  # 月份近似天数
    days_per_year: int = 365  # 年份近似天数


@dataclass(frozen=True)
class ThresholdConfig:
    """阈值配置 - 消除魔数硬编码"""
    # 语义搜索阈值
    min_semantic_threshold: float = 0.25
    max_semantic_threshold: float = 0.75
    fallback_thresholds: Tuple[float, ...] = (0.3, 0.15, 0.05)

    # 相关性阈值
    entity_match_min_score: float = 0.3
    collaborative_boost_threshold: float = 0.3
    kg_relation_boost: float = 0.15
    kg_type_boost: float = 0.1
    max_kg_boost: float = 0.5

    # 情绪阈值
    high_emotion_threshold: float = 0.5
    medium_intensity_threshold: float = 0.6
    high_intensity_threshold: float = 0.9

    # 显著性阈值
    saliency_very_high: float = 0.8
    saliency_high: float = 0.6
    saliency_medium: float = 0.4
    saliency_low: float = 0.2

    # 响应时间阈值
    fast_response_time: float = 0.5
    slow_response_time: float = 3.0

    # 收敛阈值
    high_convergence_ratio: float = 0.8
    medium_convergence_ratio: float = 0.5


@dataclass(frozen=True)
class CapacityConfig:
    """容量配置 - 消除容量硬编码"""
    # 嵌入服务
    embedding_cache_max_size: int = 10000
    embedding_cache_ttl_hours: int = 24
    embedding_batch_size: int = 100
    embedding_write_threshold: int = 10

    # 脑区容量
    prefrontal_max_items: int = 10
    prefrontal_context_items: int = 7  # Miller's Law
    hippocampus_max_items: int = 20000
    hippocampus_context_items: int = 50
    temporal_max_items: int = 50000
    temporal_context_items: int = 100
    amygdala_max_items: int = 5000
    amygdala_context_items: int = 20
    basal_ganglia_max_items: int = 1000
    basal_ganglia_context_items: int = 10

    # 检索限制
    default_search_k: int = 10
    expanded_search_k: int = 50
    min_results: int = 3


@dataclass(frozen=True)
class WeightConfig:
    """权重配置 - 消除权重硬编码"""
    # 显著性权重
    saliency_novelty: float = 0.3
    saliency_intensity: float = 0.25
    saliency_relevance: float = 0.25
    saliency_emotional: float = 0.2

    # 路由评分权重
    routing_word_count: float = 0.3
    routing_question_word: float = 0.15
    routing_relation_word: float = 0.3
    routing_multi_entity: float = 0.2

    # 事件关键词增强
    event_keyword_boost_per_match: float = 0.2
    event_keyword_max_boost: float = 0.5


@dataclass(frozen=True)
class HRMConfig:
    """HRM(Hierarchical Reasoning Model)配置"""
    fixed_point_threshold: int = 3  # 固定点出现次数阈值
    convergence_window: int = 5  # 收敛检查步数
    learning_rate: float = 0.3
    initial_confidence: float = 0.5
    top_k_fixed_points: int = 5

    # 收敛预测步数
    fast_convergence_steps: int = 1
    medium_convergence_steps: int = 3
    slow_convergence_steps: int = 5


@dataclass(frozen=True)
class AgentRetryConfig:
    """Agent重试配置"""
    base_delay: float = 1.0
    max_retries: int = 3
    default_max_tokens: int = 1500
    default_temperature: float = 0.7


@dataclass(frozen=True)
class SilentEngramConfig:
    """Silent Engram配置"""
    activation_threshold: float = 0.85
    base_threshold: float = 0.85
    min_threshold: float = 0.6
    default_importance: float = 0.5
    default_emotion_intensity: float = 0.0


@dataclass(frozen=True)
class KnowledgeGraphConfig:
    """知识图谱配置"""
    default_node_importance: float = 0.5
    default_edge_strength: float = 0.5
    default_confidence: float = 0.7


@dataclass(frozen=True)
class SystemSettings:
    parallel_phase_timeout: float
    buffer_exchange_timeout: float
    buffer_retention_hours: int
    buffer_cleanup_frequency: int
    max_faiss_vectors: int
    faiss_compaction_frequency: int
    fallback_cache_size: int
    memory_storage_timeout: float
    llm_call_timeout: float
    max_chunk_tokens: int
    max_input_tokens: int
    chunk_overlap_tokens: int
    max_short_term_buffer_size: int
    max_segments_immediate: int
    max_segments_background: int
    enable_segment_serialization: bool

    # 🔥 P0-1 缓存配置（支持 A/B 测试和快速关闭）
    enable_llm_cache: bool
    llm_cache_max_size: int
    llm_cache_ttl_seconds: int
    llm_cache_similarity_threshold: float
    enable_retrieval_cache: bool
    retrieval_cache_max_size: int
    retrieval_cache_ttl_seconds: int
    # 🔧 LLM 模型配置（统一管理，禁止硬编码）
    default_llm_model: str
    fast_llm_model: str
    heavy_llm_model: str

    # 🧠 扩展配置（消除硬编码）
    temporal: TemporalConfig = None
    thresholds: ThresholdConfig = None
    capacity: CapacityConfig = None
    weights: WeightConfig = None
    hrm: HRMConfig = None
    agent_retry: AgentRetryConfig = None
    silent_engram: SilentEngramConfig = None
    knowledge_graph: KnowledgeGraphConfig = None


@lru_cache(maxsize=1)
def get_settings() -> SystemSettings:
    """Centralized application settings sourced from env with sane defaults."""
    # 统一模型配置：默认所有模型都使用同一个，消除模型混乱
    default_model = get_env("DEFAULT_MODEL", "gpt-4o-mini")
    fast_model = get_env("FAST_MODEL", default_model)
    heavy_model = get_env("HEAVY_MODEL", fast_model)

    # 🧠 初始化扩展配置（消除硬编码）
    temporal_config = TemporalConfig(
        default_reference_year=int(get_env("DEFAULT_REFERENCE_YEAR", str(datetime.now().year))),
        time_range_buffer_days=int(get_env("TIME_RANGE_BUFFER_DAYS", "7")),
        context_window_hours=float(get_env("CONTEXT_WINDOW_HOURS", "6.0")),
    )

    threshold_config = ThresholdConfig(
        min_semantic_threshold=float(get_env("MIN_SEMANTIC_THRESHOLD", "0.25")),
        max_semantic_threshold=float(get_env("MAX_SEMANTIC_THRESHOLD", "0.75")),
        entity_match_min_score=float(get_env("ENTITY_MATCH_MIN_SCORE", "0.3")),
        collaborative_boost_threshold=float(get_env("COLLABORATIVE_BOOST_THRESHOLD", "0.3")),
        kg_relation_boost=float(get_env("KG_RELATION_BOOST", "0.15")),
        max_kg_boost=float(get_env("MAX_KG_BOOST", "0.5")),
        high_emotion_threshold=float(get_env("HIGH_EMOTION_THRESHOLD", "0.5")),
        saliency_very_high=float(get_env("SALIENCY_VERY_HIGH", "0.8")),
        saliency_high=float(get_env("SALIENCY_HIGH", "0.6")),
        saliency_medium=float(get_env("SALIENCY_MEDIUM", "0.4")),
        saliency_low=float(get_env("SALIENCY_LOW", "0.2")),
    )

    capacity_config = CapacityConfig(
        embedding_cache_max_size=int(get_env("EMBEDDING_CACHE_MAX_SIZE", "10000")),
        embedding_cache_ttl_hours=int(get_env("EMBEDDING_CACHE_TTL_HOURS", "24")),
        embedding_batch_size=int(get_env("EMBEDDING_BATCH_SIZE", "100")),
        hippocampus_max_items=int(get_env("HIPPOCAMPUS_MAX_ITEMS", "20000")),
        hippocampus_context_items=int(get_env("HIPPOCAMPUS_CONTEXT_ITEMS", "50")),
        default_search_k=int(get_env("DEFAULT_SEARCH_K", "10")),
        expanded_search_k=int(get_env("EXPANDED_SEARCH_K", "50")),
    )

    weight_config = WeightConfig(
        saliency_novelty=float(get_env("SALIENCY_NOVELTY_WEIGHT", "0.3")),
        saliency_intensity=float(get_env("SALIENCY_INTENSITY_WEIGHT", "0.25")),
        saliency_relevance=float(get_env("SALIENCY_RELEVANCE_WEIGHT", "0.25")),
        saliency_emotional=float(get_env("SALIENCY_EMOTIONAL_WEIGHT", "0.2")),
        event_keyword_boost_per_match=float(get_env("EVENT_KEYWORD_BOOST", "0.2")),
        event_keyword_max_boost=float(get_env("EVENT_KEYWORD_MAX_BOOST", "0.5")),
    )

    hrm_config = HRMConfig(
        fixed_point_threshold=int(get_env("HRM_FIXED_POINT_THRESHOLD", "3")),
        convergence_window=int(get_env("HRM_CONVERGENCE_WINDOW", "5")),
        learning_rate=float(get_env("HRM_LEARNING_RATE", "0.3")),
        initial_confidence=float(get_env("HRM_INITIAL_CONFIDENCE", "0.5")),
        top_k_fixed_points=int(get_env("HRM_TOP_K_FIXED_POINTS", "5")),
    )

    agent_retry_config = AgentRetryConfig(
        base_delay=float(get_env("AGENT_RETRY_DELAY", "1.0")),
        max_retries=int(get_env("AGENT_MAX_RETRIES", "3")),
        default_max_tokens=int(get_env("DEFAULT_MAX_TOKENS", "1500")),
        default_temperature=float(get_env("DEFAULT_TEMPERATURE", "0.7")),
    )

    silent_engram_config = SilentEngramConfig(
        activation_threshold=float(get_env("SILENT_ENGRAM_ACTIVATION", "0.85")),
        min_threshold=float(get_env("SILENT_ENGRAM_MIN_THRESHOLD", "0.6")),
        default_importance=float(get_env("DEFAULT_IMPORTANCE", "0.5")),
    )

    kg_config = KnowledgeGraphConfig(
        default_node_importance=float(get_env("KG_NODE_IMPORTANCE", "0.5")),
        default_edge_strength=float(get_env("KG_EDGE_STRENGTH", "0.5")),
        default_confidence=float(get_env("KG_DEFAULT_CONFIDENCE", "0.7")),
    )

    return SystemSettings(
        parallel_phase_timeout=float(get_env("PARALLEL_PHASE_TIMEOUT", "15.0")),
        buffer_exchange_timeout=float(get_env("BUFFER_EXCHANGE_TIMEOUT", "5.0")),
        buffer_retention_hours=int(get_env("BUFFER_RETENTION_HOURS", "24")),
        buffer_cleanup_frequency=int(get_env("BUFFER_CLEANUP_FREQUENCY", "20")),
        max_faiss_vectors=int(get_env("MAX_FAISS_VECTORS", "5000")),
        faiss_compaction_frequency=int(get_env("FAISS_COMPACTION_FREQUENCY", "50")),
        fallback_cache_size=int(get_env("FALLBACK_CACHE_SIZE", "50")),
        memory_storage_timeout=float(get_env("MEMORY_STORAGE_TIMEOUT", "8.0")),
        llm_call_timeout=float(get_env("LLM_CALL_TIMEOUT", "30.0")),  # 增加到30秒以适应复杂查询
        max_chunk_tokens=int(get_env("MAX_CHUNK_TOKENS", "2000")),
        max_input_tokens=int(get_env("MAX_INPUT_TOKENS", "8000")),
        chunk_overlap_tokens=int(get_env("CHUNK_OVERLAP_TOKENS", "100")),
        max_short_term_buffer_size=int(get_env("MAX_SHORT_TERM_BUFFER_SIZE", "10000")),
        max_segments_immediate=int(get_env("MAX_SEGMENTS_IMMEDIATE", "50")),
        max_segments_background=int(get_env("MAX_SEGMENTS_BACKGROUND", "100")),
        enable_segment_serialization=get_env("ENABLE_SEGMENT_SERIALIZATION", "true").lower() == "true",

        # 🔥 P0-1 缓存配置（默认启用，可通过环境变量关闭）
        enable_llm_cache=get_env("ENABLE_LLM_CACHE", "true").lower() == "true",
        llm_cache_max_size=int(get_env("LLM_CACHE_MAX_SIZE", "1000")),
        llm_cache_ttl_seconds=int(get_env("LLM_CACHE_TTL_SECONDS", "3600")),  # 1 hour
        llm_cache_similarity_threshold=float(get_env("LLM_CACHE_SIMILARITY_THRESHOLD", "0.99")),
        enable_retrieval_cache=get_env("ENABLE_RETRIEVAL_CACHE", "true").lower() == "true",
        retrieval_cache_max_size=int(get_env("RETRIEVAL_CACHE_MAX_SIZE", "2000")),
        retrieval_cache_ttl_seconds=int(get_env("RETRIEVAL_CACHE_TTL_SECONDS", "300")),  # 5 minutes
        default_llm_model=default_model,
        fast_llm_model=fast_model,
        heavy_llm_model=heavy_model,

        # 🧠 扩展配置（消除硬编码）
        temporal=temporal_config,
        thresholds=threshold_config,
        capacity=capacity_config,
        weights=weight_config,
        hrm=hrm_config,
        agent_retry=agent_retry_config,
        silent_engram=silent_engram_config,
        knowledge_graph=kg_config,
    )
