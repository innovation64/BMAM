"""
Centralized Constants for BMAM Framework
BMAM框架集中常量定义

This module contains fixed values that are unlikely to change
and don't need runtime configuration (unlike config.py).

这个模块包含不太可能改变的固定值，
与 config.py 不同，这些值不需要运行时配置。
"""

# ============================================================
# Text Processing Constants / 文本处理常量
# ============================================================

# Maximum text length for processing (characters)
TEXT_TRUNCATION_LIMIT = 3000

# Chunk size for text splitting (tokens)
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150

# Text length thresholds for categorization
SHORT_TEXT_THRESHOLD = 100  # tokens
MEDIUM_TEXT_THRESHOLD = 1000  # tokens
LONG_TEXT_THRESHOLD = 5000  # tokens


# ============================================================
# Memory System Constants / 记忆系统常量
# ============================================================

# Default importance score for new memories
DEFAULT_IMPORTANCE = 0.5

# Maximum items per brain region
MAX_TEMPORAL_LOBE_ITEMS = 50000
MAX_AMYGDALA_ITEMS = 5000
MAX_HIPPOCAMPUS_ITEMS = 10000
MAX_PREFRONTAL_ITEMS = 1000

# Memory history limits
MAX_MODULATION_HISTORY = 100
MAX_RETRIEVAL_HISTORY = 1000
MAX_LEARNING_HISTORY = 1000

# Silent engram limit
MAX_ENGRAMS = 10000


# ============================================================
# Context Management Constants / 上下文管理常量
# ============================================================

# Maximum context tokens for LLM
DEFAULT_MAX_CONTEXT_TOKENS = 8000

# Answer length limit
MAX_ANSWER_LENGTH = 500


# ============================================================
# Timing Constants (seconds) / 时间常量（秒）
# ============================================================

# Proactive inquiry cooldown
INQUIRY_COOLDOWN_SECONDS = 300  # 5 minutes

# Background process intervals
DEFAULT_CONSOLIDATION_INTERVAL = 3600  # 1 hour
DEFAULT_FORGETTING_INTERVAL = 7200  # 2 hours
DEFAULT_RECONSOLIDATION_INTERVAL = 1800  # 30 minutes

# High load scaling factors
INTERVAL_SCALE_HIGH_LOAD = 2.0
INTERVAL_SCALE_CRITICAL = 5.0
MIN_PROCESS_INTERVAL = 10.0


# ============================================================
# Cache Constants / 缓存常量
# ============================================================

# Cache sizes
DEFAULT_CACHE_SIZE = 1000
LRU_CACHE_DEFAULT_SIZE = 128


# ============================================================
# Audio/UI Constants / 音频/UI常量
# ============================================================

# Audio defaults
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_AUDIO_CHUNK_SIZE = 1024
DEFAULT_AUDIO_CHANNELS = 1
DEFAULT_RECORD_SECONDS = 5
DEFAULT_SILENCE_THRESHOLD = 100
DEFAULT_SILENCE_DURATION = 1.5

# UI animation
DEFAULT_TYPE_SPEED = 30  # characters per second
DEFAULT_BLINK_INTERVAL = 3.0  # seconds


# ============================================================
# Model Identifiers / 模型标识符
# ============================================================

# Default models (can be overridden by environment variables)
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSION = 1536
DEFAULT_EMBEDDING_MAX_LENGTH = 8191

# SpaCy model for NLP
DEFAULT_SPACY_MODEL = "en_core_web_sm"


# ============================================================
# Version Information / 版本信息
# ============================================================

# Archive format version
ARCHIVE_FORMAT_VERSION = "1.0.0"
MIN_BMAM_VERSION = "1.0.0"
ARCHIVE_TYPE = "bmam_memory_archive"

# Required features for archive compatibility
REQUIRED_ARCHIVE_FEATURES = ["sqlite3", "faiss"]


# ============================================================
# Network Constants / 网络常量
# ============================================================

# Default ports
DEFAULT_WEB_UI_PORT = 8080
DEFAULT_API_PORT = 8000

# Default host
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOCALHOST = "localhost"
