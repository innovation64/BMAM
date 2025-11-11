"""
Consolidation Package
记忆巩固模块
"""

from .consolidation import ConsolidationAgent
from .data_models import (
    ConsolidationStage,
    ConsolidationJob,
    ConsolidationResult,
    CONSOLIDATION_CONFIG
)

__all__ = [
    'ConsolidationAgent',
    'ConsolidationStage',
    'ConsolidationJob',
    'ConsolidationResult',
    'CONSOLIDATION_CONFIG'
]
