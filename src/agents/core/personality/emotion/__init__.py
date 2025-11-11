"""
Emotion Module
情绪管理模块 - 检测和管理情绪状态
"""

from .emotion_detector import EmotionDetector
from .emotion_manager import EmotionManager

__all__ = [
    'EmotionDetector',
    'EmotionManager',
]
