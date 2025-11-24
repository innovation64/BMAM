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


@lru_cache(maxsize=1)
def get_settings() -> SystemSettings:
    """Centralized application settings sourced from env with sane defaults."""
    # 统一模型配置：默认所有模型都使用同一个，消除模型混乱
    default_model = get_env("DEFAULT_MODEL", "gpt-4o-mini")
    fast_model = get_env("FAST_MODEL", default_model)
    heavy_model = get_env("HEAVY_MODEL", fast_model)

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
        llm_cache_similarity_threshold=float(get_env("LLM_CACHE_SIMILARITY_THRESHOLD", "0.95")),
        enable_retrieval_cache=get_env("ENABLE_RETRIEVAL_CACHE", "true").lower() == "true",
        retrieval_cache_max_size=int(get_env("RETRIEVAL_CACHE_MAX_SIZE", "2000")),
        retrieval_cache_ttl_seconds=int(get_env("RETRIEVAL_CACHE_TTL_SECONDS", "300")),  # 5 minutes
        default_llm_model=default_model,
        fast_llm_model=fast_model,
        heavy_llm_model=heavy_model,
    )
