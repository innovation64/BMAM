"""
Personality Module
人格模块 - 为系统提供真实、连贯的人格表现

这个模块负责：
1. 维护一致的人格特征和行为模式
2. 基于记忆和经历动态调整人格
3. 提供自然、类人的对话风格
4. 记录和学习个人偏好与习惯
"""

# 数据模型
from .models import (
    EmotionalState,
    PersonalityTrait,
    PersonalityProfile,
    EmotionalContext,
    StylePreferences,
    PersonalityEvolution
)

# 情绪管理
from .emotion.emotion_detector import EmotionDetector
from .emotion.emotion_manager import EmotionManager

# 人格特质
from .traits.trait_manager import TraitManager
from .traits.personality_builder import PersonalityContextBuilder

# 对话风格
from .style.style_generator import StyleGenerator
from .style.response_processor import ResponseProcessor

# 自适应学习
from .adaptation.learning_engine import LearningEngine
from .adaptation.preference_tracker import PreferenceTracker

# 核心编排器
from .core import PersonalityAgent

__all__ = [
    # 核心编排器
    'PersonalityAgent',
    # 数据模型
    'EmotionalState',
    'PersonalityTrait',
    'PersonalityProfile',
    'EmotionalContext',
    'StylePreferences',
    'PersonalityEvolution',
    # 情绪管理
    'EmotionDetector',
    'EmotionManager',
    # 人格特质
    'TraitManager',
    'PersonalityContextBuilder',
    # 对话风格
    'StyleGenerator',
    'ResponseProcessor',
    # 自适应学习
    'LearningEngine',
    'PreferenceTracker',
]
