"""
Preference Tracker
偏好跟踪器 - 跟踪用户风格偏好
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from ..models import StylePreferences

logger = logging.getLogger(__name__)


class PreferenceTracker:
    """
    偏好跟踪器

    职责:
    - 跟踪和管理用户的对话风格偏好
    - 从记忆中更新风格偏好
    - 记录交互历史用于偏好学习
    """

    def __init__(self):
        """初始化偏好跟踪器"""
        self.style_preferences = StylePreferences(
            formality=0.4,
            emoji=False,
            brevity='balanced',
            tone_hint=None
        )
        self.interaction_history: List[Dict[str, Any]] = []

    def update_style_preferences(
        self,
        persona_memories: List[Dict[str, Any]],
        retrieved_memories: List[Dict[str, Any]]
    ):
        """
        从记忆中更新风格偏好

        分析:
        - 用户的沟通风格
        - 历史对话模式
        - 明确的偏好声明

        Args:
            persona_memories: 人设记忆列表
            retrieved_memories: 检索到的记忆列表
        """
        # 合并所有记忆源
        memory_sources = []

        # 从persona记忆提取
        for entry in persona_memories:
            memory = entry.get('memory', entry) if isinstance(entry, dict) else entry
            content = memory.get('content', '') if isinstance(memory, dict) else str(memory)
            if content:
                memory_sources.append(content)

        # 从retrieved记忆提取
        for memory in retrieved_memories:
            content = memory.get('content', '')
            if content:
                memory_sources.append(content)

        combined = "\n".join(memory_sources)
        if not combined:
            return

        # 分析并更新偏好
        self._analyze_formality(combined)
        self._analyze_emoji_preference(combined)
        self._analyze_brevity(combined)

    def _analyze_formality(self, text: str):
        """
        分析正式程度偏好

        Args:
            text: 记忆文本
        """
        formal_keywords = ['正式', '严肃', '专业']
        casual_keywords = ['轻松', '随意', '放松']

        if self._contains_keywords(text, formal_keywords) and self.style_preferences.formality < 0.7:
            self.style_preferences.formality = 0.7
            self.style_preferences.tone_hint = '更正式'
            logger.debug("更新风格偏好: 正式程度 -> 0.7")

        if self._contains_keywords(text, casual_keywords) and self.style_preferences.formality > 0.3:
            self.style_preferences.formality = 0.3
            self.style_preferences.tone_hint = '轻松自然'
            logger.debug("更新风格偏好: 正式程度 -> 0.3")

    def _analyze_emoji_preference(self, text: str):
        """
        分析表情符号使用偏好

        Args:
            text: 记忆文本
        """
        emoji_keywords = ['表情', 'emoji', '可爱']

        if self._contains_keywords(text, emoji_keywords) and not self.style_preferences.emoji:
            self.style_preferences.emoji = True
            logger.debug("更新风格偏好: 启用表情符号")

    def _analyze_brevity(self, text: str):
        """
        分析简洁度偏好

        Args:
            text: 记忆文本
        """
        concise_keywords = ['简洁', '直截了当', '短句']
        detailed_keywords = ['详细', '展开说', '多讲']

        if self._contains_keywords(text, concise_keywords) and self.style_preferences.brevity != 'concise':
            self.style_preferences.brevity = 'concise'
            logger.debug("更新风格偏好: 简洁度 -> concise")

        if self._contains_keywords(text, detailed_keywords) and self.style_preferences.brevity != 'elaborate':
            self.style_preferences.brevity = 'elaborate'
            logger.debug("更新风格偏好: 简洁度 -> elaborate")

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        检查文本是否包含关键词

        Args:
            text: 文本
            keywords: 关键词列表

        Returns:
            是否包含任一关键词
        """
        return any(kw in text for kw in keywords)

    def get_style_preferences(self) -> StylePreferences:
        """
        获取当前风格偏好

        Returns:
            StylePreferences对象
        """
        return self.style_preferences

    def get_style_preferences_dict(self) -> Dict[str, Any]:
        """
        获取风格偏好字典

        Returns:
            风格偏好字典
        """
        return {
            'formality': self.style_preferences.formality,
            'emoji': self.style_preferences.emoji,
            'brevity': self.style_preferences.brevity,
            'tone_hint': self.style_preferences.tone_hint
        }

    def record_interaction(
        self,
        user_input: str,
        response: str,
        emotional_context: Dict[str, Any]
    ):
        """
        记录交互用于偏好学习

        Args:
            user_input: 用户输入
            response: 系统响应
            emotional_context: 情绪上下文
        """
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'response': response,
            'emotional_context': emotional_context
        }

        self.interaction_history.append(interaction)

        # 只保留最近的交互
        if len(self.interaction_history) > 10:
            self.interaction_history = self.interaction_history[-10:]

    def get_recent_interactions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近的交互记录

        Args:
            count: 返回的记录数量

        Returns:
            交互记录列表
        """
        return self.interaction_history[-count:]

    def set_formality(self, formality: float):
        """
        手动设置正式程度

        Args:
            formality: 正式程度 [0.0, 1.0]
        """
        self.style_preferences.formality = max(0.0, min(1.0, formality))
        logger.debug(f"手动设置正式程度: {self.style_preferences.formality}")

    def set_emoji(self, enabled: bool):
        """
        手动设置表情符号使用

        Args:
            enabled: 是否启用
        """
        self.style_preferences.emoji = enabled
        logger.debug(f"手动设置表情符号: {enabled}")

    def set_brevity(self, brevity: str):
        """
        手动设置简洁度

        Args:
            brevity: 简洁度 ('concise', 'balanced', 'elaborate')
        """
        if brevity in ['concise', 'balanced', 'elaborate']:
            self.style_preferences.brevity = brevity
            logger.debug(f"手动设置简洁度: {brevity}")
        else:
            logger.warning(f"无效的简洁度值: {brevity}")

    def reset_preferences(self):
        """重置为默认偏好"""
        self.style_preferences = StylePreferences(
            formality=0.4,
            emoji=False,
            brevity='balanced',
            tone_hint=None
        )
        logger.info("风格偏好已重置为默认值")
