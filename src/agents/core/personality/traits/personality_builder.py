"""
Personality Context Builder
人格上下文构建器 - 为响应生成准备人格上下文
"""

import logging
from typing import Dict, Any, List

from ..models import PersonalityProfile

logger = logging.getLogger(__name__)


class PersonalityContextBuilder:
    """
    人格上下文构建器

    职责:
    - 从记忆中提取相关信息
    - 构建人格上下文用于响应生成
    - 整合人格特质、记忆和情绪
    """

    def build_personality_context(
        self,
        user_input: str,
        memories: List[Dict[str, Any]],
        persona_memories: List[Dict[str, Any]],
        profile: PersonalityProfile,
        current_emotion: str,
        emotion_intensity: float,
        style_adjustments: Dict[str, Any],
        learned_preferences: Dict[str, Any],
        base_response: str = ""
    ) -> Dict[str, Any]:
        """
        构建人格上下文

        Args:
            user_input: 用户输入
            memories: 检索到的记忆
            persona_memories: 人设记忆
            profile: 人格档案
            current_emotion: 当前情绪
            emotion_intensity: 情绪强度
            style_adjustments: 风格调整
            learned_preferences: 已学习的偏好
            base_response: 基础响应

        Returns:
            构建好的人格上下文
        """
        # 提取相关记忆
        relevant_info = self._extract_relevant_memories(memories, user_input)

        # 提取个人细节
        personal_details = self._extract_personal_details(memories)

        # 构建人设上下文
        persona_details = self._build_persona_context(persona_memories)

        return {
            'relevant_memories': relevant_info,
            'personal_details': personal_details,
            'persona_details': persona_details,
            'current_emotion': current_emotion,
            'emotion_intensity': emotion_intensity,
            'style_adjustments': style_adjustments,
            'personality_traits': profile.traits,
            'interests': profile.interests,
            'learned_preferences': learned_preferences,
            'base_response': base_response
        }

    def _extract_relevant_memories(self, memories: List[Dict[str, Any]],
                                   user_input: str) -> List[str]:
        """
        提取相关记忆

        Args:
            memories: 记忆列表
            user_input: 用户输入

        Returns:
            相关记忆内容列表
        """
        relevant_info = []

        # 只使用前3个最相关的记忆
        for memory in memories[:3]:
            content = memory.get('content', '')
            if content:
                relevant_info.append(content)

        return relevant_info

    def _extract_personal_details(self, memories: List[Dict[str, Any]]) -> List[str]:
        """
        提取个人细节信息

        Args:
            memories: 记忆列表

        Returns:
            个人细节列表
        """
        personal_details = []
        personal_keywords = ['喜欢', '不喜欢', '习惯', '总是', '经常']

        for memory in memories[:3]:
            content = memory.get('content', '')
            if content and any(word in content for word in personal_keywords):
                personal_details.append(content)

        return personal_details

    def _build_persona_context(self, persona_memories: List[Dict[str, Any]]) -> List[str]:
        """
        构建人设上下文

        Args:
            persona_memories: 人设记忆列表

        Returns:
            人设上下文列表
        """
        persona_details = []

        for entry in persona_memories[:3]:
            # 兼容不同的记忆格式
            memory_dict = entry.get('memory', entry) if isinstance(entry, dict) else entry
            content = memory_dict.get('content', '') if isinstance(memory_dict, dict) else str(memory_dict)
            if content:
                persona_details.append(content)

        return persona_details

    def build_context_summary(self, personality_context: Dict[str, Any]) -> str:
        """
        构建上下文摘要 (用于日志或调试)

        Args:
            personality_context: 人格上下文

        Returns:
            上下文摘要字符串
        """
        summary_parts = []

        # 情绪状态
        emotion = personality_context.get('current_emotion', '未知')
        intensity = personality_context.get('emotion_intensity', 0)
        summary_parts.append(f"情绪: {emotion}({intensity:.1f})")

        # 记忆数量
        memories_count = len(personality_context.get('relevant_memories', []))
        persona_count = len(personality_context.get('persona_details', []))
        summary_parts.append(f"记忆: {memories_count}条, 人设: {persona_count}条")

        # 主要特质
        traits = personality_context.get('personality_traits', {})
        top_trait = max(traits.items(), key=lambda x: x[1])[0] if traits else '未知'
        summary_parts.append(f"主特质: {top_trait}")

        return " | ".join(summary_parts)
