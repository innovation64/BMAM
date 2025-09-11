"""
Brain Plasticity Module
神经可塑性模块 - 实现类脑动态连接和学习
"""

from .neural_plasticity import NeuralPlasticityEngine
from .connection_matrix import ConnectionMatrix
from .synaptic_plasticity import SynapticPlasticity

__all__ = [
    'NeuralPlasticityEngine',
    'ConnectionMatrix', 
    'SynapticPlasticity'
]