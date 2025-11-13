"""
Amygdala Emotion Tags - 杏仁核情绪标记

功能: 存储情绪强度标记
结构: 简单字典 (不需要复杂图结构)
用途: 筛选情绪强烈的记忆

灵感来源:
- 杏仁核负责情绪记忆
- 高情绪强度的记忆更容易被回忆
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmotionData:
    """情绪数据"""
    emotions: List[str]  # ['joy', 'acceptance', 'fear']
    intensity: float  # 0.0-1.0
    tagged_at: datetime


class AmygdalaEmotionTags:
    """
    杏仁核情绪标记 - 存储情绪强度

    核心特点:
    1. 轻量级结构 (Dict)
    2. 快速情绪过滤
    3. 支持情绪类型查询
    """

    def __init__(self):
        self.emotion_map: Dict[str, EmotionData] = {}  # {memory_id: EmotionData}


    def tag_emotion(
        self,
        memory_id: str,
        emotions: List[str],
        intensity: float
    ) -> None:
        """
        标记记忆的情绪

        Args:
            memory_id: 记忆ID
            emotions: 情绪类型列表 ['joy', 'acceptance']
            intensity: 情绪强度 0.0-1.0
        """
        self.emotion_map[memory_id] = EmotionData(
            emotions=emotions,
            intensity=intensity,
            tagged_at=datetime.now()
        )


    def get_emotion(self, memory_id: str) -> Optional[EmotionData]:
        """获取记忆的情绪数据"""
        return self.emotion_map.get(memory_id)

    def get_high_emotion_memories(
        self,
        threshold: float = 0.7
    ) -> List[str]:
        """
        获取高情绪强度的记忆ID列表

        Args:
            threshold: 情绪强度阈值

        Returns:
            记忆ID列表
        """
        high_emotion_ids = [
            mem_id for mem_id, data in self.emotion_map.items()
            if data.intensity >= threshold
        ]


        return high_emotion_ids

    def filter_by_emotion_type(
        self,
        memory_ids: List[str],
        emotion_type: str
    ) -> List[str]:
        """
        按情绪类型过滤记忆

        Args:
            memory_ids: 记忆ID列表
            emotion_type: 情绪类型 'joy', 'fear', 'anger'等

        Returns:
            包含该情绪的记忆ID列表
        """
        filtered = [
            mem_id for mem_id in memory_ids
            if mem_id in self.emotion_map and
            emotion_type in self.emotion_map[mem_id].emotions
        ]


        return filtered

    def get_emotions_by_intensity_range(
        self,
        min_intensity: float = 0.0,
        max_intensity: float = 1.0
    ) -> List[str]:
        """
        获取指定强度范围的记忆

        Args:
            min_intensity: 最小强度
            max_intensity: 最大强度

        Returns:
            记忆ID列表
        """
        filtered = [
            mem_id for mem_id, data in self.emotion_map.items()
            if min_intensity <= data.intensity <= max_intensity
        ]


        return filtered

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.emotion_map:
            return {
                'total_memories': 0,
                'avg_intensity': 0.0,
                'emotion_distribution': {}
            }

        # 情绪分布统计
        emotion_counts = {}
        for data in self.emotion_map.values():
            for emotion in data.emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        return {
            'total_memories': len(self.emotion_map),
            'avg_intensity': sum(d.intensity for d in self.emotion_map.values()) / len(self.emotion_map),
            'emotion_distribution': emotion_counts,
            'high_emotion_count': len(self.get_high_emotion_memories(threshold=0.7))
        }

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            memory_id: {
                'emotions': data.emotions,
                'intensity': data.intensity,
                'tagged_at': data.tagged_at.isoformat()
            }
            for memory_id, data in self.emotion_map.items()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AmygdalaEmotionTags':
        """从字典反序列化"""
        tags = cls()

        for memory_id, emotion_data in data.items():
            tags.emotion_map[memory_id] = EmotionData(
                emotions=emotion_data['emotions'],
                intensity=emotion_data['intensity'],
                tagged_at=datetime.fromisoformat(emotion_data['tagged_at'])
            )


        return tags
