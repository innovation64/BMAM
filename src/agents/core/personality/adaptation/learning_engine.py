"""
Learning Engine
学习引擎 - 从交互中学习并适应用户偏好
"""

import logging
from typing import Dict, Any, List, Optional

from ..models import PersonalityProfile, PersonalityTrait

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    学习引擎

    职责:
    - 从交互中学习用户偏好
    - 提取偏好信息
    - 适应人格特征
    - 管理学习历史
    """

    def __init__(self, adaptation_threshold: int = 5):
        """
        初始化学习引擎

        Args:
            adaptation_threshold: 多少次交互后触发适应
        """
        self.adaptation_threshold = adaptation_threshold
        self.interaction_count = 0
        self.learned_preferences: Dict[str, List[str]] = {}
        self.recent_interactions: List[Dict[str, Any]] = []

    async def learn_from_interaction(
        self,
        user_input: str,
        response: str,
        user_reaction: str = 'neutral',
        profile: Optional[PersonalityProfile] = None,
        persona_memory_agent = None
    ) -> Dict[str, Any]:
        """
        从交互中学习

        分析:
        - 用户偏好
        - 对话模式
        - 反馈信号

        Args:
            user_input: 用户输入
            response: 系统响应
            user_reaction: 用户反应 ('positive', 'negative', 'neutral')
            profile: 人格档案 (用于调整)
            persona_memory_agent: 人设记忆代理 (用于存储偏好)

        Returns:
            学习结果
        """
        # 提取可能的偏好信息
        preferences = self.extract_preferences(user_input)

        # 存储偏好
        for pref_type, pref_value in preferences.items():
            if pref_type not in self.learned_preferences:
                self.learned_preferences[pref_type] = []

            if pref_value not in self.learned_preferences[pref_type]:
                self.learned_preferences[pref_type].append(pref_value)

            # 如果有persona_memory_agent，存储到人设记忆
            if persona_memory_agent is not None:
                try:
                    await persona_memory_agent.store_persona({
                        'content': f"用户{pref_type}: {pref_value}",
                        'category': 'preference',
                        'importance': 0.7 if user_reaction == 'positive' else 0.55,
                        'emotion_tags': ['positive'] if user_reaction == 'positive' else ['neutral'],
                        'metadata': {
                            'preference_type': pref_type,
                            'value_alignment': 'positive' if user_reaction == 'positive' else 'neutral',
                            'source': 'personality_agent'
                        }
                    })
                except Exception as exc:
                    logger.warning(f"Failed to store persona preference memory: {exc}")

        # 根据用户反应调整人格特征
        if profile:
            if user_reaction == 'positive':
                # 强化当前的人格表现
                for trait in profile.traits:
                    profile.traits[trait] = min(1.0, profile.traits[trait] + 0.01)

            elif user_reaction == 'negative':
                # 轻微调整，变得更温和或正式
                profile.traits[PersonalityTrait.PATIENCE.value] = min(1.0,
                    profile.traits[PersonalityTrait.PATIENCE.value] + 0.02)

        return {
            'learned': True,
            'new_preferences': preferences,
            'total_preferences': len(self.learned_preferences),
            'response': '从交互中学到新信息'
        }

    def extract_preferences(self, user_input: str) -> Dict[str, str]:
        """
        从用户输入中提取偏好信息

        Args:
            user_input: 用户输入

        Returns:
            提取的偏好字典
        """
        preferences = {}

        # 简单的偏好识别
        if '喜欢' in user_input:
            # 尝试提取喜欢的内容
            parts = user_input.split('喜欢')
            if len(parts) > 1:
                liked_item = parts[1].split('，')[0].split('。')[0].strip()
                if liked_item:
                    preferences['喜欢'] = liked_item

        if '不喜欢' in user_input:
            parts = user_input.split('不喜欢')
            if len(parts) > 1:
                disliked_item = parts[1].split('，')[0].split('。')[0].strip()
                if disliked_item:
                    preferences['不喜欢'] = disliked_item

        # 时间偏好
        time_indicators = ['早上', '下午', '晚上', '中午', '傍晚']
        for time in time_indicators:
            if time in user_input:
                preferences['时间偏好'] = time
                break

        return preferences

    async def check_and_adapt(
        self,
        profile: PersonalityProfile,
        recent_interactions: List[Dict[str, Any]]
    ) -> bool:
        """
        检查是否需要适应, 并执行适应

        Args:
            profile: 人格档案
            recent_interactions: 最近的交互记录

        Returns:
            是否进行了适应
        """
        self.interaction_count += 1

        # 检查是否达到适应阈值
        if self.interaction_count % self.adaptation_threshold == 0:
            return await self.adapt_personality(profile, recent_interactions)

        return False

    async def adapt_personality(
        self,
        profile: PersonalityProfile,
        recent_interactions: List[Dict[str, Any]]
    ) -> bool:
        """
        基于学习到的信息适应人格

        Args:
            profile: 人格档案
            recent_interactions: 最近的交互记录

        Returns:
            是否进行了适应
        """
        if len(recent_interactions) < 3:
            return False

        # 分析最近交互中的情感倾向
        emotion_counts = {}
        for interaction in recent_interactions[-5:]:
            emotion = interaction.get('emotional_context', {}).get('main_emotion', 'friendly')
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        adapted = False

        # 根据用户的情感倾向微调人格特征
        if emotion_counts.get('negative', 0) > 2:
            # 用户情绪较负面，增强同理心和关怀
            profile.traits[PersonalityTrait.EMPATHY.value] = min(1.0,
                profile.traits[PersonalityTrait.EMPATHY.value] + 0.05)
            profile.traits[PersonalityTrait.PATIENCE.value] = min(1.0,
                profile.traits[PersonalityTrait.PATIENCE.value] + 0.05)
            adapted = True
            logger.info("人格适应: 增强同理心和耐心 (响应用户负面情绪)")

        elif emotion_counts.get('positive', 0) > 3:
            # 用户情绪积极，可以增强幽默感
            profile.traits[PersonalityTrait.HUMOR.value] = min(1.0,
                profile.traits[PersonalityTrait.HUMOR.value] + 0.03)
            adapted = True
            logger.info("人格适应: 增强幽默感 (响应用户积极情绪)")

        return adapted

    def get_learned_preferences(self) -> Dict[str, List[str]]:
        """
        获取已学习的偏好

        Returns:
            偏好字典
        """
        return self.learned_preferences.copy()

    def get_interaction_count(self) -> int:
        """
        获取交互计数

        Returns:
            交互次数
        """
        return self.interaction_count

    def reset_interaction_count(self):
        """重置交互计数"""
        self.interaction_count = 0

    def clear_learned_preferences(self):
        """清除已学习的偏好"""
        self.learned_preferences.clear()
        logger.info("已清除所有学习到的偏好")
