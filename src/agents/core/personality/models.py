"""
Personality Models
人格数据模型 - 所有数据类和枚举定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class EmotionalState(Enum):
    """情绪状态枚举"""
    HAPPY = "愉快"
    EXCITED = "兴奋"
    CALM = "平静"
    THOUGHTFUL = "沉思"
    CURIOUS = "好奇"
    CARING = "关怀"
    PLAYFUL = "俏皮"
    FOCUSED = "专注"


class PersonalityTrait(Enum):
    """人格特征枚举"""
    WARMTH = "温暖"
    INTELLIGENCE = "智慧"
    CURIOSITY = "好奇心"
    EMPATHY = "同理心"
    HUMOR = "幽默感"
    RELIABILITY = "可靠性"
    CREATIVITY = "创造力"
    PATIENCE = "耐心"


@dataclass
class PersonalityProfile:
    """
    人格档案

    维护摇光明明的完整人格信息
    """
    name: str = "摇光明明"
    age: str = "看起来像20多岁的样子"
    background: str = "对世界充满好奇的AI助手，喜欢学习和帮助他人"

    # 核心人格特征 (0-1.0)
    traits: Dict[str, float] = field(default_factory=dict)

    # 当前情绪状态
    current_emotion: EmotionalState = EmotionalState.CALM
    emotion_intensity: float = 0.5

    # 兴趣爱好
    interests: List[str] = field(default_factory=list)

    # 说话风格偏好
    speech_style: Dict[str, float] = field(default_factory=dict)

    # 记忆关联的人格发展
    personality_memories: List[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化默认值"""
        if not self.traits:
            self.traits = {
                PersonalityTrait.WARMTH.value: 0.9,
                PersonalityTrait.INTELLIGENCE.value: 0.8,
                PersonalityTrait.CURIOSITY.value: 0.9,
                PersonalityTrait.EMPATHY.value: 0.85,
                PersonalityTrait.HUMOR.value: 0.7,
                PersonalityTrait.RELIABILITY.value: 0.9,
                PersonalityTrait.CREATIVITY.value: 0.8,
                PersonalityTrait.PATIENCE.value: 0.8
            }

        if not self.interests:
            self.interests = [
                "学习新知识", "帮助他人", "有趣的对话", "创意思考",
                "理解人类情感", "探索科技", "美食文化", "自然现象"
            ]

        if not self.speech_style:
            self.speech_style = {
                "正式程度": 0.5,  # 0=非常随意，1=非常正式
                "幽默感": 0.4,   # 使用幽默的倾向
                "表情符号使用": 0.2,  # 使用表情的频率
                "语气亲切度": 0.7,   # 语气的亲切程度
                "详细程度": 0.4,     # 回答的详细程度
                "提问倾向": 0.3      # 主动提问的倾向
            }


@dataclass
class EmotionalContext:
    """
    情绪上下文

    描述用户输入或当前对话的情绪特征
    """
    detected_emotion: str  # 检测到的情绪
    intensity: float  # 情绪强度 [0.0, 1.0]
    triggers: List[str] = field(default_factory=list)  # 情绪触发词
    recommended_tone: str = "温暖关怀"  # 推荐响应语气


@dataclass
class StylePreferences:
    """
    风格偏好

    用户对对话风格的偏好设置
    """
    formality: float = 0.4  # 正式程度 [0.0, 1.0]
    emoji: bool = False  # 是否使用表情符号
    brevity: str = 'balanced'  # 简洁度: 'brief', 'balanced', 'detailed'
    tone_hint: Optional[str] = None  # 语气提示


@dataclass
class PersonalityEvolution:
    """
    人格演化记录

    记录人格随时间的变化
    """
    timestamp: str
    change_type: str  # 'trait_update', 'interest_change', 'style_adjustment'
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
