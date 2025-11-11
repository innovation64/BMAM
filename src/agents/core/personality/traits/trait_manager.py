"""
Trait Manager
人格特质管理器 - 管理人格特质和档案
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import asdict

from ..models import PersonalityProfile, PersonalityTrait, EmotionalState

logger = logging.getLogger(__name__)


class TraitManager:
    """
    人格特质管理器

    职责:
    - 管理人格档案
    - 更新人格特征
    - 记录人格演化历史
    - 提供人格信息查询
    """

    def __init__(self, profile: PersonalityProfile):
        """
        初始化特质管理器

        Args:
            profile: 人格档案
        """
        self.profile = profile
        self.personality_evolution: List[Dict[str, Any]] = []

    def update_personality(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新人格特征

        Args:
            updates: 更新字典, 可包含:
                - traits: Dict[str, float] - 特质更新
                - current_emotion: str - 情绪状态
                - emotion_intensity: float - 情绪强度
                - interests: List[str] - 兴趣爱好

        Returns:
            更新结果
        """
        # 更新特质
        if 'updates' in updates:
            updates = updates['updates']

        for trait, value in updates.items():
            if trait in self.profile.traits:
                # 确保值在 [0.0, 1.0] 范围内
                self.profile.traits[trait] = max(0.0, min(1.0, value))

        # 更新情绪状态
        if 'current_emotion' in updates:
            emotion_name = updates['current_emotion']
            for emotion in EmotionalState:
                if emotion.value == emotion_name:
                    self.profile.current_emotion = emotion
                    break

        # 更新情绪强度
        if 'emotion_intensity' in updates:
            self.profile.emotion_intensity = max(0.0, min(1.0, updates['emotion_intensity']))

        # 更新兴趣
        if 'interests' in updates:
            new_interests = updates['interests']
            if isinstance(new_interests, list):
                self.profile.interests = new_interests

        # 记录演化
        self._record_personality_evolution(
            change_type='manual_update',
            description='手动更新人格特征',
            details=updates
        )

        return {
            'updated': True,
            'current_traits': self.profile.traits,
            'current_emotion': self.profile.current_emotion.value,
            'response': '人格特征已更新'
        }

    def get_personality_info(self) -> Dict[str, Any]:
        """
        获取完整人格信息

        Returns:
            包含人格档案的完整字典
        """
        return {
            'profile': asdict(self.profile),
            'personality_evolution_count': len(self.personality_evolution),
            'response': '人格信息获取完成'
        }

    def get_personality_summary(self) -> str:
        """
        获取人格摘要文本

        Returns:
            简洁的人格描述字符串
        """
        top_traits = sorted(
            self.profile.traits.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        trait_desc = ', '.join([f"{trait}({value:.1f})" for trait, value in top_traits])

        return (f"{self.profile.name} - "
                f"{self.profile.current_emotion.value}({self.profile.emotion_intensity:.1f}) | "
                f"主要特质: {trait_desc}")

    def _record_personality_evolution(self, change_type: str, description: str,
                                     details: Dict[str, Any] = None):
        """
        记录人格演化

        Args:
            change_type: 变化类型
            description: 描述
            details: 详细信息
        """
        evolution_record = {
            'timestamp': datetime.now().isoformat(),
            'change_type': change_type,
            'description': description,
            'traits': self.profile.traits.copy(),
            'details': details or {}
        }
        self.personality_evolution.append(evolution_record)

        # 只保留最近50条记录
        if len(self.personality_evolution) > 50:
            self.personality_evolution = self.personality_evolution[-50:]

    def adapt_personality_from_interactions(self, recent_interactions: List[Dict[str, Any]],
                                           interaction_count: int) -> bool:
        """
        基于最近的交互历史调整人格特征

        Args:
            recent_interactions: 最近的交互记录
            interaction_count: 交互计数

        Returns:
            是否进行了调整
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
            old_empathy = self.profile.traits[PersonalityTrait.EMPATHY.value]
            old_patience = self.profile.traits[PersonalityTrait.PATIENCE.value]

            self.profile.traits[PersonalityTrait.EMPATHY.value] = min(1.0,
                self.profile.traits[PersonalityTrait.EMPATHY.value] + 0.05)
            self.profile.traits[PersonalityTrait.PATIENCE.value] = min(1.0,
                self.profile.traits[PersonalityTrait.PATIENCE.value] + 0.05)

            adapted = True
            logger.info("人格适应: 增强同理心和耐心 (响应用户负面情绪)")

        elif emotion_counts.get('positive', 0) > 3:
            # 用户情绪积极，可以增强幽默感
            old_humor = self.profile.traits[PersonalityTrait.HUMOR.value]

            self.profile.traits[PersonalityTrait.HUMOR.value] = min(1.0,
                self.profile.traits[PersonalityTrait.HUMOR.value] + 0.03)

            adapted = True
            logger.info("人格适应: 增强幽默感 (响应用户积极情绪)")

        # 记录人格发展
        if adapted:
            self._record_personality_evolution(
                change_type='interaction_adaptation',
                description='基于交互分析调整人格',
                details={
                    'interaction_count': interaction_count,
                    'emotion_counts': emotion_counts
                }
            )

        return adapted

    def get_evolution_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        获取人格演化历史

        Args:
            count: 返回的记录数量

        Returns:
            人格演化记录列表
        """
        return self.personality_evolution[-count:]
