"""
Brain-Inspired Multi-Agent Memory Framework
类脑多智能体记忆框架

A comprehensive implementation of brain-inspired cognitive architecture
with 12 specialized agents for memory processing and conversation.

Usage:
    # Lazy import - only loads what you need
    from src.coordination import BrainInspiredCoordinator
    from src.memory import HippocampusAgent

    # Or import submodules explicitly
    from src import coordination
"""

__version__ = "1.0.0"
__author__ = "Brain-Inspired AI Team"
__description__ = "A neuroscience-inspired 12-agent memory system with OpenAI and FAISS integration"

# Available submodules (lazy loaded)
__all__ = [
    "coordination",
    "memory",
    "agents",
    "services",
    "utils",
    "core",
]

# Lazy import implementation - modules are only loaded when accessed
def __getattr__(name: str):
    """
    Lazy module loader - prevents cascade imports on package import.
    模块只在实际访问时才加载，避免导入时触发全系统初始化。
    """
    if name in __all__:
        import importlib
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
