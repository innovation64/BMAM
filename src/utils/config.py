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
        
        logging.basicConfig(
            level=level,
            format=format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_path, mode='a')
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


@lru_cache(maxsize=1)
def get_settings() -> SystemSettings:
    """Centralized application settings sourced from env with sane defaults."""
    return SystemSettings(
        parallel_phase_timeout=float(get_env("PARALLEL_PHASE_TIMEOUT", "15.0")),
        buffer_exchange_timeout=float(get_env("BUFFER_EXCHANGE_TIMEOUT", "5.0")),
        buffer_retention_hours=int(get_env("BUFFER_RETENTION_HOURS", "24")),
        buffer_cleanup_frequency=int(get_env("BUFFER_CLEANUP_FREQUENCY", "20")),
        max_faiss_vectors=int(get_env("MAX_FAISS_VECTORS", "5000")),
        faiss_compaction_frequency=int(get_env("FAISS_COMPACTION_FREQUENCY", "50")),
        fallback_cache_size=int(get_env("FALLBACK_CACHE_SIZE", "50")),
        memory_storage_timeout=float(get_env("MEMORY_STORAGE_TIMEOUT", "8.0")),
        llm_call_timeout=float(get_env("LLM_CALL_TIMEOUT", "20.0")),
        max_chunk_tokens=int(get_env("MAX_CHUNK_TOKENS", "2000")),
        max_input_tokens=int(get_env("MAX_INPUT_TOKENS", "8000")),
        chunk_overlap_tokens=int(get_env("CHUNK_OVERLAP_TOKENS", "100")),
        max_short_term_buffer_size=int(get_env("MAX_SHORT_TERM_BUFFER_SIZE", "10000")),
        max_segments_immediate=int(get_env("MAX_SEGMENTS_IMMEDIATE", "50")),
        max_segments_background=int(get_env("MAX_SEGMENTS_BACKGROUND", "100")),
        enable_segment_serialization=get_env("ENABLE_SEGMENT_SERIALIZATION", "true").lower() == "true",
    )
