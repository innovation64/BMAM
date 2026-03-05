"""
Brain Module
神经网络模块 - 脑区协作与记忆处理
"""

from .brain_network import BrainNetwork
from .collaborative_output import CollaborativeOutput
from .region_activation import RegionActivationDynamics

__all__ = [
    'BrainNetwork',
    'CollaborativeOutput',
    'RegionActivationDynamics'
]
