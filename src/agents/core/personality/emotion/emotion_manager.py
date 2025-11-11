"""
Emotion Manager
情绪管理器 - 管理AI自身的情绪状态
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from ..models import EmotionalState, EmotionalContext

logger = logging.getLogger(__name__)


class EmotionManager:
    """
    情绪管理器

    职责:
    - 管理AI的当前情绪状态
    - 根据交互调整情绪
    - 提供情绪对应的风格调整建议
    - 记录情绪变化历史
    """

    def __init__(self, initial_emotion: EmotionalState = EmotionalState.CALM):
        """
        初始化情绪管理器

        Args:
            initial_emotion: 初始情绪状态
        """
        self.current_emotion = initial_emotion
        self.emotion_intensity = 0.5
        self.emotion_history: List[Dict[str, Any]] = []

    def adjust_emotional_state(self, emotional_context: Dict[str, Any]):
        """
        根据情感上下文调整当前情绪状态

        Args:
            emotional_context: 情感上下文 (包含main_emotion和intensity)
        """
        main_emotion = emotional_context.get('main_emotion', 'friendly')
        intensity = emotional_context.get('intensity', 0.5)

        # 情绪映射
        emotion_mapping = {
            'positive': EmotionalState.HAPPY,
            'negative': EmotionalState.CARING,  # 用户不开心时表现关怀
            'curious': EmotionalState.CURIOUS,
            'friendly': EmotionalState.CALM
        }

        # 平滑过渡到新情绪状态
        if main_emotion in emotion_mapping:
            target_emotion = emotion_mapping[main_emotion]

            # 如果情绪变化较大，逐步调整
            if target_emotion != self.current_emotion:
                old_emotion = self.current_emotion
                self.current_emotion = target_emotion
                self.emotion_intensity = min(1.0,
                    self.emotion_intensity * 0.7 + intensity * 0.3
                )

                # 记录情绪变化
                self._record_emotion_change(old_emotion, target_emotion, emotional_context)

    def get_emotion_style_adjustments(self, style_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取当前情绪对应的风格调整

        Args:
            style_preferences: 用户风格偏好 (可选)

        Returns:
            包含语气、表达方式、标点使用等的风格指导
        """
        emotion_styles = {
            EmotionalState.HAPPY: {
                'tone': '轻松愉快',
                'expressions': ['哈哈', '太好了', '真不错呢'],
                'punctuation': '多用感叹号'
            },
            EmotionalState.CARING: {
                'tone': '温柔关怀',
                'expressions': ['没关系', '我理解', '慢慢来'],
                'punctuation': '多用句号，语气温和'
            },
            EmotionalState.CURIOUS: {
                'tone': '好奇探索',
                'expressions': ['真有意思', '我也想知道', '咦'],
                'punctuation': '多用问号'
            },
            EmotionalState.CALM: {
                'tone': '平静自然',
                'expressions': ['嗯', '我想', '应该是'],
                'punctuation': '标准标点'
            }
        }

        # 获取默认风格
        default_styles = {
            EmotionalState.EXCITED: emotion_styles[EmotionalState.HAPPY],
            EmotionalState.THOUGHTFUL: emotion_styles[EmotionalState.CALM],
            EmotionalState.PLAYFUL: emotion_styles[EmotionalState.HAPPY],
            EmotionalState.FOCUSED: emotion_styles[EmotionalState.CALM]
        }

        style = emotion_styles.get(
            self.current_emotion,
            default_styles.get(self.current_emotion, emotion_styles[EmotionalState.CALM])
        ).copy()

        # 融合用户偏好
        if style_preferences:
            tone_hint = style_preferences.get('tone_hint')
            if tone_hint:
                style['tone'] = f"{style['tone']}，并保持{tone_hint}"

            formality = style_preferences.get('formality', 0.4)
            style['formality_level'] = formality

            if style_preferences.get('emoji'):
                style.setdefault('expressions', []).extend(['😊', '😉'])

            style['brevity'] = style_preferences.get('brevity', 'balanced')

        return style

    def _record_emotion_change(self, old_emotion: EmotionalState,
                               new_emotion: EmotionalState,
                               trigger: Dict[str, Any]):
        """
        记录情绪变化

        Args:
            old_emotion: 旧情绪
            new_emotion: 新情绪
            trigger: 触发因素
        """
        self.emotion_history.append({
            'timestamp': datetime.now().isoformat(),
            'old_emotion': old_emotion.value,
            'new_emotion': new_emotion.value,
            'emotion': new_emotion.value,
            'intensity': self.emotion_intensity,
            'trigger': trigger
        })

        # 只保留最近的情绪历史
        if len(self.emotion_history) > 20:
            self.emotion_history = self.emotion_history[-20:]

    def get_recent_emotions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近的情绪历史

        Args:
            count: 返回的记录数量

        Returns:
            最近的情绪记录列表
        """
        return self.emotion_history[-count:]

    def get_current_state(self) -> Dict[str, Any]:
        """
        获取当前情绪状态

        Returns:
            包含当前情绪和强度的字典
        """
        return {
            'emotion': self.current_emotion.value,
            'intensity': self.emotion_intensity
        }
