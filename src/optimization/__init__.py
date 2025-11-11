"""
Brain Region Optimization Module
脑区优化模块 - 确保记忆系统的稳定性、高效性和可扩展性

核心组件:
1. CapacityManager - 容量管理 (防止overflow)
2. QueryCache - 查询缓存 (加速重复query)
3. FastPathDetector - 快速路径 (简单query跳过推理)
4. ContextLimiter - 上下文限制 (控制推理token)

设计目标:
✅ 稳定性 - 不随记忆增长而崩溃
✅ 高效性 - 性能不随记忆扩展而下降
✅ 容量限制 - 每个脑区有realistic上限
✅ 推理控制 - 传递给LLM的context始终合理
"""

from .capacity_manager import CapacityManager, get_capacity_manager
from .query_cache import QueryCache, get_query_cache
from .fast_path import FastPathDetector, get_fast_path_detector
from .context_limiter import ContextLimiter, get_context_limiter

__all__ = [
    'CapacityManager',
    'QueryCache',
    'FastPathDetector',
    'ContextLimiter',
    'get_capacity_manager',
    'get_query_cache',
    'get_fast_path_detector',
    'get_context_limiter'
]
