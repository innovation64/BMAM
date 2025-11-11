"""
Traits Module
人格特质模块 - 管理人格特质和构建上下文
"""

from .trait_manager import TraitManager
from .personality_builder import PersonalityContextBuilder

__all__ = [
    'TraitManager',
    'PersonalityContextBuilder',
]
