"""
Brain-Inspired Multi-Agent Memory Framework
类脑多智能体记忆框架

A comprehensive implementation of brain-inspired cognitive architecture
with 12 specialized agents for memory processing and conversation.
"""

__version__ = "1.0.0"
__author__ = "Brain-Inspired AI Team"
__description__ = "A neuroscience-inspired 12-agent memory system with OpenAI and FAISS integration"

# 确保所有子模块可以被正确导入
try:
    from . import coordination
    from . import memory
    from . import agents
    from . import services
    from . import monitoring
    
    __all__ = [
        "coordination",
        "memory", 
        "agents",
        "services",
        "monitoring"
    ]
except ImportError as e:
    # 如果某些模块不存在，继续运行但记录警告
    import warnings
    warnings.warn(f"Some modules could not be imported: {e}")
    __all__ = []