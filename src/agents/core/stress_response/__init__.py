"""
Stress Response Package
应激反应智能体模块

This package provides stress response and emotional processing functionality
through a modular architecture using mixins.
"""

from .stress_response import StressResponseAgent
from .data_models import (
    EmotionalState,
    THREAT_KEYWORDS,
    EMOTION_CATEGORIES,
    HPA_DEFAULTS,
    STRESS_THRESHOLDS,
    THREAT_THRESHOLDS
)

__all__ = [
    'StressResponseAgent',
    'EmotionalState',
    'THREAT_KEYWORDS',
    'EMOTION_CATEGORIES',
    'HPA_DEFAULTS',
    'STRESS_THRESHOLDS',
    'THREAT_THRESHOLDS'
]
