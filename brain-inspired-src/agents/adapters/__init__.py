"""
Agent适配器模块
用于实现Agent的独立修改和接口适配
"""

from .base_adapter import AgentAdapter, MessageAdapter
from .agent_factory import AgentFactory

__all__ = [
    'AgentAdapter',
    'MessageAdapter', 
    'AgentFactory'
]