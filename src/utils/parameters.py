"""
System Parameters Loader
系统参数加载器

从 config/system_parameters.yaml 加载所有系统参数
消除代码中的硬编码值
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# 配置文件路径
_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "system_parameters.yaml"

# 全局配置缓存
_config_cache: Optional[Dict[str, Any]] = None


def _load_config() -> Dict[str, Any]:
    """加载配置文件"""
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    if not _CONFIG_PATH.exists():
        logger.warning(f"Config file not found: {_CONFIG_PATH}, using defaults")
        _config_cache = {}
        return _config_cache

    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            _config_cache = yaml.safe_load(f) or {}
        logger.info(f"Loaded system parameters from {_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        _config_cache = {}

    return _config_cache


def get_param(path: str, default: Any = None) -> Any:
    """
    获取配置参数

    Args:
        path: 点分隔的参数路径，如 "memory.hippocampus_capacity"
        default: 默认值

    Returns:
        参数值，如果不存在则返回默认值

    Example:
        >>> get_param("memory.hippocampus_capacity", 70000)
        70000
        >>> get_param("llm.temperature_default", 0.3)
        0.3
    """
    config = _load_config()

    keys = path.split('.')
    value = config

    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def reload_config():
    """重新加载配置（用于运行时更新）"""
    global _config_cache
    _config_cache = None
    _load_config()
    logger.info("Configuration reloaded")


# =============================================================================
# Memory Parameters
# 记忆参数快捷访问
# =============================================================================

class MemoryParams:
    """记忆系统参数"""

    @staticmethod
    def hippocampus_capacity() -> int:
        return get_param("memory.hippocampus_capacity", 70000)

    @staticmethod
    def temporal_lobe_capacity() -> int:
        return get_param("memory.temporal_lobe_capacity", 20000)

    @staticmethod
    def working_memory_capacity() -> int:
        return get_param("memory.working_memory_capacity", 1000)

    @staticmethod
    def prefrontal_capacity() -> int:
        return get_param("memory.prefrontal_capacity", 10)

    @staticmethod
    def basal_ganglia_capacity() -> int:
        return get_param("memory.basal_ganglia_capacity", 500)

    @staticmethod
    def forgetting_decay_threshold() -> float:
        return get_param("memory.forgetting_decay_threshold", 0.3)

    @staticmethod
    def capacity_threshold() -> float:
        return get_param("memory.capacity_threshold", 0.8)

    @staticmethod
    def min_importance() -> float:
        return get_param("memory.min_importance", 0.7)

    @staticmethod
    def consolidation_interval() -> int:
        return get_param("memory.consolidation_interval", 10)


# =============================================================================
# Retrieval Parameters
# 检索参数快捷访问
# =============================================================================

class RetrievalParams:
    """检索系统参数"""

    @staticmethod
    def top_k() -> int:
        return get_param("retrieval.top_k", 10)

    @staticmethod
    def top_k_large() -> int:
        return get_param("retrieval.top_k_large", 30)

    @staticmethod
    def limit() -> int:
        return get_param("retrieval.limit", 10)

    @staticmethod
    def limit_large() -> int:
        return get_param("retrieval.limit_large", 200)

    @staticmethod
    def limit_xlarge() -> int:
        return get_param("retrieval.limit_xlarge", 500)

    @staticmethod
    def similarity_threshold() -> float:
        return get_param("retrieval.similarity_threshold", 0.5)

    @staticmethod
    def min_similarity() -> float:
        return get_param("retrieval.min_similarity", 0.6)

    @staticmethod
    def relative_threshold() -> float:
        return get_param("retrieval.relative_threshold", 0.5)


# =============================================================================
# Cache Parameters
# 缓存参数快捷访问
# =============================================================================

class CacheParams:
    """缓存系统参数"""

    @staticmethod
    def llm_cache_max_size() -> int:
        return get_param("cache.llm_cache_max_size", 1000)

    @staticmethod
    def llm_cache_ttl() -> int:
        return get_param("cache.llm_cache_ttl_seconds", 3600)

    @staticmethod
    def retrieval_cache_max_size() -> int:
        return get_param("cache.retrieval_cache_max_size", 2000)

    @staticmethod
    def retrieval_cache_ttl() -> int:
        return get_param("cache.retrieval_cache_ttl_seconds", 1800)

    @staticmethod
    def kg_cache_max_size() -> int:
        return get_param("cache.kg_cache_max_size", 500)

    @staticmethod
    def kg_cache_ttl() -> int:
        return get_param("cache.kg_cache_ttl_seconds", 600)

    @staticmethod
    def entity_cache_max_size() -> int:
        return get_param("cache.entity_cache_max_size", 1000)

    @staticmethod
    def entity_cache_ttl() -> int:
        return get_param("cache.entity_cache_ttl_seconds", 1800)

    @staticmethod
    def lru_cache_max_size() -> int:
        return get_param("cache.lru_cache_max_size", 200)


# =============================================================================
# LLM Parameters
# LLM参数快捷访问
# =============================================================================

class LLMParams:
    """LLM调用参数"""

    @staticmethod
    def temperature_default() -> float:
        return get_param("llm.temperature_default", 0.3)

    @staticmethod
    def temperature_low() -> float:
        return get_param("llm.temperature_low", 0.1)

    @staticmethod
    def temperature_creative() -> float:
        return get_param("llm.temperature_creative", 0.7)

    @staticmethod
    def max_tokens_default() -> int:
        return get_param("llm.max_tokens_default", 1000)

    @staticmethod
    def max_tokens_short() -> int:
        return get_param("llm.max_tokens_short", 50)

    @staticmethod
    def max_tokens_medium() -> int:
        return get_param("llm.max_tokens_medium", 300)

    @staticmethod
    def max_tokens_long() -> int:
        return get_param("llm.max_tokens_long", 600)

    @staticmethod
    def max_tokens_xlarge() -> int:
        return get_param("llm.max_tokens_xlarge", 2000)

    @staticmethod
    def timeout_seconds() -> int:
        return get_param("llm.timeout_seconds", 30)


# =============================================================================
# Processing Parameters
# 处理参数快捷访问
# =============================================================================

class ProcessingParams:
    """处理参数"""

    @staticmethod
    def batch_size() -> int:
        return get_param("processing.batch_size", 50)

    @staticmethod
    def learning_loop_interval() -> int:
        return get_param("processing.learning_loop_interval", 1800)

    @staticmethod
    def strategic_update_interval() -> int:
        return get_param("processing.strategic_update_interval", 10)

    @staticmethod
    def capacity_limit() -> int:
        return get_param("processing.capacity_limit", 10000)


# =============================================================================
# Threshold Parameters
# 阈值参数快捷访问
# =============================================================================

class ThresholdParams:
    """阈值参数"""

    @staticmethod
    def activation_threshold() -> float:
        return get_param("thresholds.activation_threshold", 0.5)

    @staticmethod
    def confidence_threshold() -> float:
        return get_param("thresholds.confidence_threshold", 0.8)

    @staticmethod
    def confidence_low() -> float:
        return get_param("thresholds.confidence_low", 0.3)

    @staticmethod
    def confidence_medium() -> float:
        return get_param("thresholds.confidence_medium", 0.5)

    @staticmethod
    def confidence_high() -> float:
        return get_param("thresholds.confidence_high", 0.8)


# =============================================================================
# Router Parameters
# 路由参数快捷访问
# =============================================================================

class RouterParams:
    """路由参数"""

    @staticmethod
    def temperature() -> float:
        return get_param("router.temperature", 0.1)

    @staticmethod
    def top_k() -> int:
        return get_param("router.top_k", 2)


# =============================================================================
# Convenience Exports
# 便捷导出
# =============================================================================

# 为向后兼容提供直接访问
memory = MemoryParams
retrieval = RetrievalParams
cache = CacheParams
llm = LLMParams
processing = ProcessingParams
thresholds = ThresholdParams
router = RouterParams
