"""
Emotion Detector
情绪检测器 - 从文本中检测情绪信号
"""

import logging
from typing import Dict, Any, List

from ..models import EmotionalContext, EmotionalState

logger = logging.getLogger(__name__)


class EmotionDetector:
    """
    情绪检测器

    职责:
    - 从用户输入中检测情绪关键词
    - 分析情绪强度
    - 推荐合适的响应语气
    """

    def __init__(self):
        """初始化情绪检测器"""
        # 情绪关键词库
        self.positive_keywords = ['开心', '高兴', '兴奋', '满意', '喜欢', '棒', '好', '谢谢', '哈哈']
        self.negative_keywords = ['难过', '生气', '不开心', '失望', '担心', '焦虑', '烦恼', '不好']
        self.curious_keywords = ['为什么', '怎么', '什么', '哪里', '谁', '怎样', '如何']
        self.friendly_keywords = ['你好', '早上好', '晚上好', '最近怎么样', '你呢']

    def detect_emotional_context(self, user_input: str) -> Dict[str, Any]:
        """
        检测用户输入的情绪上下文

        Args:
            user_input: 用户输入文本

        Returns:
            包含情绪分析结果的字典:
            {
                'emotion_scores': {...},
                'main_emotion': 'positive',
                'intensity': 0.5
            }
        """
        user_input_lower = user_input.lower()

        # 计算各类情绪得分
        emotion_scores = {
            'positive': sum(1 for kw in self.positive_keywords if kw in user_input_lower),
            'negative': sum(1 for kw in self.negative_keywords if kw in user_input_lower),
            'curious': sum(1 for kw in self.curious_keywords if kw in user_input_lower),
            'friendly': sum(1 for kw in self.friendly_keywords if kw in user_input_lower)
        }

        # 确定主要情感倾向
        main_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])

        # 计算情绪强度
        word_count = len(user_input.split()) if user_input.split() else 1
        intensity = max(emotion_scores.values()) / word_count if word_count > 0 else 0

        return {
            'emotion_scores': emotion_scores,
            'main_emotion': main_emotion,
            'intensity': intensity
        }

    def analyze_emotional_context(self, text: str) -> EmotionalContext:
        """
        分析文本的情绪上下文 (返回结构化对象)

        Args:
            text: 要分析的文本

        Returns:
            EmotionalContext对象
        """
        context = self.detect_emotional_context(text)

        # 提取触发词
        triggers = self._extract_emotion_triggers(text, context['main_emotion'])

        # 推荐响应语气
        recommended_tone = self._get_recommended_tone(
            context['main_emotion'],
            context['intensity']
        )

        return EmotionalContext(
            detected_emotion=context['main_emotion'],
            intensity=context['intensity'],
            triggers=triggers,
            recommended_tone=recommended_tone
        )

    def _extract_emotion_triggers(self, text: str, main_emotion: str) -> List[str]:
        """
        提取情绪触发词

        Args:
            text: 文本
            main_emotion: 主要情绪

        Returns:
            触发词列表
        """
        text_lower = text.lower()
        triggers = []

        keyword_map = {
            'positive': self.positive_keywords,
            'negative': self.negative_keywords,
            'curious': self.curious_keywords,
            'friendly': self.friendly_keywords
        }

        keywords = keyword_map.get(main_emotion, [])
        for keyword in keywords:
            if keyword in text_lower:
                triggers.append(keyword)

        return triggers

    def _get_recommended_tone(self, main_emotion: str, intensity: float) -> str:
        """
        根据情绪推荐响应语气

        Args:
            main_emotion: 主要情绪
            intensity: 情绪强度

        Returns:
            推荐的语气描述
        """
        tone_map = {
            'positive': '轻松愉快' if intensity > 0.3 else '温暖友好',
            'negative': '温柔关怀',
            'curious': '好奇探索',
            'friendly': '平静自然'
        }
        return tone_map.get(main_emotion, '温暖友好')

    def recommend_emotion(self, emotional_context: Dict[str, Any]) -> str:
        """
        基于情感上下文推荐合适的情绪反应

        Args:
            emotional_context: 情感上下文字典

        Returns:
            推荐的情绪状态值
        """
        main_emotion = emotional_context['main_emotion']
        intensity = emotional_context['intensity']

        recommendations = {
            'positive': EmotionalState.HAPPY.value if intensity > 0.3 else EmotionalState.CALM.value,
            'negative': EmotionalState.CARING.value,
            'curious': EmotionalState.CURIOUS.value,
            'friendly': EmotionalState.CALM.value
        }

        return recommendations.get(main_emotion, EmotionalState.CALM.value)
