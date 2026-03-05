"""
Response Processor
响应处理器 - 后处理和风格应用
"""

import logging
import random
from typing import Dict, Any

from ..models import PersonalityTrait, EmotionalState, StylePreferences

logger = logging.getLogger(__name__)


class ResponseProcessor:
    """
    响应后处理器

    职责:
    - 应用风格调整到响应
    - 后处理响应文本
    - 确保响应符合人格一致性
    """

    def apply_style_to_response(
        self,
        response: str,
        personality_context: Dict[str, Any],
        emotional_context: Dict[str, Any],
        style_preferences: Dict[str, Any]
    ) -> str:
        """
        应用风格到响应

        调整:
        - 正式程度 (你/您)
        - 表情符号
        - 语气亲切度
        - 详细程度

        Args:
            response: 原始响应
            personality_context: 人格上下文
            emotional_context: 情绪上下文
            style_preferences: 风格偏好

        Returns:
            应用风格后的响应
        """
        styled = response

        style = personality_context.get('style_adjustments', {})
        tone_hint = style.get('tone', '')
        formality = style_preferences.get('formality', 0.4)
        brevity = style_preferences.get('brevity', 'balanced')

        # 调整正式程度
        if formality < 0.4:
            styled = styled.replace('您', '你')
        elif formality > 0.7:
            styled = styled.replace('你', '您')

        # 调整详细程度
        if brevity == 'concise' and len(styled) > 200:
            # 简洁模式：只保留前两句
            sentences = [s for s in styled.replace('?', '？').replace('!', '！').split('。') if s]
            styled = '。'.join(sentences[:2]) + ('。' if sentences else '')

        # 添加语气提示（如果还没有）
        if tone_hint and tone_hint not in styled:
            # 避免重复添加
            pass  # 语气已经在生成阶段体现

        # 添加表情符号（如果用户偏好）
        if style_preferences.get('emoji') and '😊' not in styled and len(styled) < 220:
            styled = styled + ' 😊'

        # 最终后处理
        processed = self.post_process_response(styled, personality_context, response)
        return processed

    def post_process_response(
        self,
        response: str,
        personality_context: Dict[str, Any],
        base_response: str = ""
    ) -> str:
        """
        后处理响应

        清理:
        - 移除"作为AI"表述
        - 调整口语化程度
        - 确保人格一致性
        - 智能保留事实信息

        Args:
            response: 原始响应
            personality_context: 人格上下文
            base_response: 基础响应

        Returns:
            后处理后的响应
        """
        # 移除AI自我指称
        response = self._remove_ai_phrases(response)

        # 根据幽默感特征适当添加轻松元素
        traits = personality_context.get('personality_traits', {})
        humor_level = traits.get(PersonalityTrait.HUMOR.value, 0.7)
        current_emotion = personality_context.get('current_emotion', '平静')

        if humor_level > 0.6 and len(response) > 50 and '哈' not in response:
            if current_emotion in [EmotionalState.HAPPY.value, EmotionalState.PLAYFUL.value]:
                # 有小概率添加轻松的表达
                if random.random() < 0.3:
                    casual_expressions = ['呢', '哦', '嘛']
                    response += random.choice(casual_expressions)

        # 确保回应长度适中
        if len(response) > 200:
            # 如果太长，尝试精简
            sentences = response.split('。')
            if len(sentences) > 2:
                response = '。'.join(sentences[:2]) + '。'

        response = response.strip()

        # 智能事实保留检查 - 避免润色后的重复
        base_response = (base_response or "").strip()
        if base_response and len(base_response) > 20:
            # 检查核心关键词而非逐字匹配，避免润色后重复
            base_keywords = self._extract_keywords(base_response)
            response_keywords = self._extract_keywords(response)

            # 只有当大部分关键信息缺失时才补充
            overlap_ratio = len(base_keywords & response_keywords) / max(len(base_keywords), 1)
            if overlap_ratio < 0.3:  # 关键词重叠度低于30%才补充
                response = f"{response}\n补充：{base_response}"

        return response

    def _remove_ai_phrases(self, text: str) -> str:
        """
        移除AI相关表述

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 移除常见的AI自我指称
        text = text.replace('作为AI', '')
        text = text.replace('作为人工智能', '')
        text = text.replace('我是AI助手', '我')
        text = text.replace('AI助手', '我')
        text = text.replace('作为一个AI', '')
        text = text.replace('作为语言模型', '')

        return text

    def _extract_keywords(self, text: str) -> set:
        """
        提取文本关键词

        Args:
            text: 文本

        Returns:
            关键词集合
        """
        # 停用词
        stop_words = {'我们', '可以', '这个', '那个', '一些', '非常', '的', '是', '在', '了', '和'}

        keywords = set()
        # 按标点分割
        for phrase in text.replace('，', ' ').replace('。', ' ').replace('、', ' ').split():
            if len(phrase) > 1 and phrase not in stop_words:
                keywords.add(phrase)

        return keywords

    def ensure_response_quality(self, response: str) -> bool:
        """
        检查响应质量

        Args:
            response: 响应文本

        Returns:
            是否通过质量检查
        """
        # 基本质量检查
        if not response or len(response) < 2:
            return False

        # 检查是否过短
        if len(response) < 5:
            logger.warning("响应过短")
            return False

        # 检查是否过长
        if len(response) > 500:
            logger.warning("响应过长")
            return False

        return True

    def apply_emotion_markers(self, response: str, emotion: str, intensity: float) -> str:
        """
        应用情绪标记 (如标点、语气词)

        Args:
            response: 响应文本
            emotion: 情绪
            intensity: 强度

        Returns:
            添加情绪标记后的响应
        """
        # 根据情绪和强度调整标点
        if emotion == EmotionalState.HAPPY.value and intensity > 0.7:
            # 高兴时可能更多感叹号
            if '!' not in response and '！' not in response:
                response = response.rstrip('。') + '！'

        elif emotion == EmotionalState.CURIOUS.value and intensity > 0.6:
            # 好奇时可能更多问号
            if '?' not in response and '？' not in response and len(response) < 100:
                response = response.rstrip('。') + '吗？'

        return response
