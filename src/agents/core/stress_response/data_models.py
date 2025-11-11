"""
Stress Response Data Models
应激反应数据模型
"""

from typing import Dict, List
from collections import deque


class EmotionalState:
    """情绪状态"""
    def __init__(self):
        self.valence = 0.0      # -1 (negative) to +1 (positive)
        self.arousal = 0.3      # 0 (calm) to 1 (excited)
        self.dominance = 0.5    # 0 (submissive) to 1 (dominant)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'valence': self.valence,
            'arousal': self.arousal,
            'dominance': self.dominance
        }

    def copy(self) -> Dict[str, float]:
        """Return a copy as dictionary"""
        return self.to_dict()

    def update(self, values: Dict[str, float]):
        """Update emotional state values"""
        if 'valence' in values:
            self.valence = values['valence']
        if 'arousal' in values:
            self.arousal = values['arousal']
        if 'dominance' in values:
            self.dominance = values['dominance']


# 威胁关键词字典
THREAT_KEYWORDS = {
    'danger': 0.8,
    'risk': 0.6,
    'threat': 0.9,
    'fear': 0.7,
    'panic': 0.9,
    'emergency': 0.8,
    'critical': 0.7,
    'urgent': 0.6,
    'crisis': 0.8,
    'warning': 0.5,
    'alarm': 0.7,
    'hazard': 0.7
}


# 情绪分类
EMOTION_CATEGORIES = {
    'positive': ['joy', 'happiness', 'satisfaction', 'excitement', 'love', 'gratitude', 'pride', 'relief'],
    'negative': ['sadness', 'anger', 'fear', 'anxiety', 'frustration', 'disappointment', 'disgust', 'shame'],
    'neutral': ['calm', 'neutral', 'indifferent', 'contemplative']
}


# HPA轴参数
HPA_DEFAULTS = {
    'cortisol_level': 0.3,
    'adrenaline_level': 0.2,
    'recovery_rate': 0.05
}


# 压力分类阈值
STRESS_THRESHOLDS = {
    'low': 0.3,
    'moderate': 0.6,
    'high': 0.8,
    'extreme': 1.0
}


# 威胁级别阈值
THREAT_THRESHOLDS = {
    'minimal': 0.2,
    'low': 0.4,
    'moderate': 0.6,
    'high': 0.8,
    'critical': 1.0
}
