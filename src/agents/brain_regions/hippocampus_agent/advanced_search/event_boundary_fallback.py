"""
Fallback Event Boundary Detection - 后备事件边界检测
基于算法的边界检测

Algorithmic boundary detection when LLM fails
"""

import logging
from typing import Tuple

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class FallbackBoundaryDetector:
    """
    后备边界检测器 (Fallback Boundary Detector)

    Algorithm-based detection | 基于算法的检测:
    - Semantic similarity | 语义相似度
    - Keyword overlap | 关键词重叠
    - Dynamic thresholds | 动态阈值
    """

    def __init__(self, agent):
        """
        Initialize detector

        Args:
            agent: The hippocampus agent
        """
        self.agent = agent


    def detect(self, content: str, last_memory: EpisodicMemory, time_gap: float) -> Tuple[bool, str]:
        """后备边界检测"""
        is_boundary, reason = self._semantic_detection(content, last_memory, time_gap)
        if is_boundary:
            return is_boundary, reason
        return self._keyword_detection(content, last_memory, time_gap)


    def _semantic_detection(self, content: str, last_memory: EpisodicMemory, time_gap: float) -> Tuple[bool, str]:
        """语义相似度检测"""
        if not hasattr(self.agent, 'embedding_service') or not self.agent.embedding_service or not last_memory.embedding:
            return False, "no_embedding"
        try:
            import asyncio
            current_emb = asyncio.create_task(self.agent.embedding_service.encode_text(content))
            current_emb = asyncio.run(current_emb)
            current_emb = current_emb.tolist() if hasattr(current_emb, 'tolist') else current_emb
            similarity = self.agent._cosine_similarity(current_emb, last_memory.embedding)
            threshold = 0.3 + (time_gap / 6.0) * 0.2
            if similarity < threshold:
                return True, f"topic_shift_sim={similarity:.2f}_thresh={threshold:.2f}"
        except (RuntimeError, ValueError) as e:
            logger.warning(f"Semantic detection failed: {e}")
        return False, "semantic_similar"

    def _keyword_detection(self, content: str, last_memory: EpisodicMemory, time_gap: float) -> Tuple[bool, str]:
        """关键词相似度检测"""
        content_words = set(content.lower().split())
        last_words = set(last_memory.content.lower().split())
        overlap = len(content_words & last_words)
        keyword_sim = overlap / len(content_words) if content_words else 0
        keyword_threshold = 0.2 + (time_gap / 6.0) * 0.1
        if keyword_sim < keyword_threshold:
            return True, f"keyword_shift_sim={keyword_sim:.2f}"
        return False, "continue_current_event"
