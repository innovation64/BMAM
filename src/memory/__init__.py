from .memory_system import AdvancedMemorySystem, memory_system

# 新增模块 (2025-11-30): 基于 "Key-value memory in the brain" 论文优化
# 使用延迟导入避免循环依赖
def _lazy_imports():
    """延迟导入新模块"""
    from .silent_engram import SilentEngram, SilentEngramStore
    from .pattern_separator import PatternSeparator, DiscriminativeFeatures
    from .key_value_stores import KeyStore, ValueStore, KeyValueMemoryStore
    from .contrastive_key_optimizer import ContrastiveKeyOptimizer, AdaptiveContrastiveOptimizer
    from .metamemory import MetamemoryMonitor, MetamemoryController, TOTState, FOKJudgment
    return {
        'SilentEngram': SilentEngram,
        'SilentEngramStore': SilentEngramStore,
        'PatternSeparator': PatternSeparator,
        'DiscriminativeFeatures': DiscriminativeFeatures,
        'KeyStore': KeyStore,
        'ValueStore': ValueStore,
        'KeyValueMemoryStore': KeyValueMemoryStore,
        'ContrastiveKeyOptimizer': ContrastiveKeyOptimizer,
        'AdaptiveContrastiveOptimizer': AdaptiveContrastiveOptimizer,
        'MetamemoryMonitor': MetamemoryMonitor,
        'MetamemoryController': MetamemoryController,
        'TOTState': TOTState,
        'FOKJudgment': FOKJudgment,
    }

__all__ = [
    'AdvancedMemorySystem',
    'memory_system',
    # 新增模块
    'SilentEngram',
    'SilentEngramStore',
    'PatternSeparator',
    'DiscriminativeFeatures',
    'KeyStore',
    'ValueStore',
    'KeyValueMemoryStore',
    'ContrastiveKeyOptimizer',
    'AdaptiveContrastiveOptimizer',
    'MetamemoryMonitor',
    'MetamemoryController',
    'TOTState',
    'FOKJudgment',
]