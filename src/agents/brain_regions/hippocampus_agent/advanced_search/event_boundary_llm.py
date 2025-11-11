"""
LLM-Based Event Boundary Detection - LLM事件边界检测
动态事件分割决策

Neural Basis: Dynamic event segmentation using LLM reasoning
"""

import logging
import json
import re
from typing import Tuple
from datetime import datetime

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class LLMBoundaryDetector:
    """
    LLM事件边界检测器 (LLM Boundary Detector)

    Uses LLM to dynamically decide event boundaries based on:
    - Topic shift | 主题切换
    - Time gap significance | 时间跳跃重要性
    - Emotional shift | 情绪变化
    - Context change | 情境变化
    """

    def __init__(self, agent):
        """
        Initialize detector

        Args:
            agent: The hippocampus agent (for call_llm)
        """
        self.agent = agent


    async def detect(
        self,
        content: str,
        timestamp: datetime,
        emotion_tags: list,
        last_memory: EpisodicMemory,
        time_gap: float
    ) -> Tuple[bool, str]:
        """
        LLM动态事件边界判断

        Args:
            content: 当前内容
            timestamp: 时间戳
            emotion_tags: 情绪标签
            last_memory: 上一个记忆
            time_gap: 时间间隔（小时）

        Returns:
            (is_boundary, reason)
        """
        prompt = self._build_prompt(
            content, timestamp, emotion_tags,
            last_memory, time_gap
        )

        try:
            response = await self.agent.call_llm(
                prompt, max_tokens=150,
                temperature=0.3, quick_fail=True
            )

            return self._parse_response(response)

        except json.JSONDecodeError as e:
            logger.warning(f"LLM boundary detection parse failed: {e}")
            return False, "llm_failed"


    def _build_prompt(
        self,
        content: str,
        timestamp: datetime,
        emotion_tags: list,
        last_memory: EpisodicMemory,
        time_gap: float
    ) -> str:
        """构建LLM提示"""
        return f"""判断是否是新事件边界 (Event Boundary Detection):

当前记忆: {content}
- 时间: {timestamp.strftime('%Y-%m-%d %H:%M')}
- 情绪: {', '.join(emotion_tags) if emotion_tags else '无'}

最近记忆: {last_memory.content}
- 时间: {last_memory.timestamp.strftime('%Y-%m-%d %H:%M')}
- 情绪: {', '.join(last_memory.emotion_tags) if last_memory.emotion_tags else '无'}

时间间隔: {time_gap:.1f}小时

判断标准:
1. 主题切换 (topic shift)
2. 时间跳跃 (1-6小时)
3. 情绪变化 (emotional shift)
4. 情境变化 (context change)

返回JSON: {{"is_new_event": true/false, "reason": "简短理由"}}"""


    def _parse_response(self, response: str) -> Tuple[bool, str]:
        """解析LLM响应"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group())
            is_new = decision.get('is_new_event', False)
            reason = decision.get('reason', 'llm_decision')

            return is_new, f"llm_{reason}" if is_new else (False, "continue_event")

        return False, "parse_failed"
