"""
Event Boundary Detection - 事件边界检测
事件分割理论 (Event Segmentation Theory)

Neural Basis: Hippocampal event boundary detection
Reference: Radvansky & Zacks (2014)
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime

from ..core import EpisodicMemory
from .event_boundary_llm import LLMBoundaryDetector
from .event_boundary_fallback import FallbackBoundaryDetector

logger = logging.getLogger(__name__)


class EventBoundaryMixin:
    """
    事件边界检测混入类 (Event Boundary Detection Mixin)

    Event Segmentation Theory | 事件分割理论:
    - 多维特征识别事件边界
    - LLM动态决策，避免硬编码

    Features | 功能:
    - Time-based segmentation | 时间分割
    - Topic shift detection | 主题切换检测
    - Speaker change detection | 说话人变化检测
    """

    async def _detect_event_boundary(
        self,
        content: str,
        timestamp: datetime,
        speaker: Optional[str],
        emotion_tags: List[str],
        recent_memories: List[EpisodicMemory]
    ) -> Tuple[bool, str]:
        """
        检测事件边界 - Event Boundary Detection

        Args:
            content: 当前记忆内容
            timestamp: 时间戳
            speaker: 说话人
            emotion_tags: 情绪标签
            recent_memories: 最近的记忆

        Returns:
            (is_boundary, reason): 是否为边界 + 原因
        """
        if not recent_memories:
            return True, "first_memory"

        last_memory = recent_memories[-1]
        time_gap = (timestamp - last_memory.timestamp).total_seconds() / 3600

        # Absolute time gap
        if time_gap > 6.0:
            return True, f"large_time_gap_{time_gap:.1f}h"

        # Speaker change
        if speaker and last_memory.speaker and speaker != last_memory.speaker:
            return True, f"speaker_change_{last_memory.speaker}->{speaker}"

        # LLM-based detection
        llm_detector = LLMBoundaryDetector(self)
        is_boundary, reason = await llm_detector.detect(
            content, timestamp, emotion_tags, last_memory, time_gap
        )
        if is_boundary:
            return is_boundary, reason

        # Fallback detection
        fallback_detector = FallbackBoundaryDetector(self)
        return fallback_detector.detect(content, last_memory, time_gap)
