"""
MBTI Personality Package
MBTI人格包

A comprehensive MBTI-based personality system implementing all 16 personality
types with cognitive functions and type-specific interaction patterns.

一个全面的基于MBTI的人格系统，实现所有16种人格类型，包含认知功能和
特定类型的交互模式。

Usage:
    from src.agents.core.mbti_personality import MBTIPersonalityAgent, MBTIType

    agent = MBTIPersonalityAgent(mbti_type=MBTIType.INTJ)
"""

# Import core types and enums
from .types import MBTIType, CognitiveFunctionType

# Import profile dataclass
from .profile import MBTIProfile

# Import factory
from .factory import MBTIPersonalityFactory

# Import main agent (composed with mixins)
from .core import MBTIPersonalityCore

# Create alias for backward compatibility
# 为向后兼容创建别名
MBTIPersonalityAgent = MBTIPersonalityCore

# Public API
__all__ = [
    # Main agent class
    'MBTIPersonalityAgent',
    'MBTIPersonalityCore',

    # Types and enums
    'MBTIType',
    'CognitiveFunctionType',

    # Profile and factory
    'MBTIProfile',
    'MBTIPersonalityFactory',
]

# Version info
__version__ = '1.0.0'
