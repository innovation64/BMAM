"""
Episodic Retrieval Strategy
情节检索策略 - 基于线索的情节记忆检索
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class EpisodicRetrievalStrategy(RetrievalStrategy):
    """
    情节检索策略

    功能:
    - 基于多维线索(情绪、位置、人物等)检索情节记忆
    - 计算线索匹配度
    - 支持部分线索匹配
    """

    @property
    def strategy_name(self) -> str:
        return "episodic"

    async def retrieve(
        self,
        cues: Optional[Dict[str, Any]] = None,
        k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        情节检索

        Args:
            cues: 线索字典 {'emotion': '开心', 'location': '公园', ...}
            k: 返回数量

        Returns:
            检索结果
        """
        if not self.db_manager or not cues:
            return {'memories': [], 'total_count': 0, 'strategy': self.strategy_name}

        logger.info(f"Episodic retrieval: cues={list(cues.keys())}")

        # 获取所有记忆
        all_memories = self.db_manager.search_memories(limit=200)

        # 计算每个记忆的线索匹配分数
        scored_memories = []
        for memory in all_memories:
            score = self._calculate_episodic_score(memory, cues)

            if score > 0:
                matched_cues = self._get_matched_cues(memory, cues)

                scored_memories.append({
                    'memory': memory.to_dict(),
                    'episodic_score': score,
                    'retrieval_confidence': score,
                    'retrieval_method': 'episodic',
                    'matched_cues': matched_cues
                })

        # 排序并返回top-k
        scored_memories.sort(key=lambda m: m['episodic_score'], reverse=True)

        return {
            'memories': scored_memories[:k],
            'total_count': len(scored_memories),
            'strategy': self.strategy_name,
            'cues_used': list(cues.keys())
        }

    def _calculate_episodic_score(self, memory, cues: Dict[str, Any]) -> float:
        """计算情节匹配分数"""
        if not cues:
            return 0.0

        match_count = 0
        total_cues = len(cues)

        memory_dict = memory.to_dict() if hasattr(memory, 'to_dict') else {}
        metadata = memory_dict.get('metadata', {})

        for cue_key, cue_value in cues.items():
            if cue_key in metadata and metadata[cue_key] == cue_value:
                match_count += 1

        return match_count / total_cues if total_cues > 0 else 0.0

    def _get_matched_cues(self, memory, cues: Dict) -> List[str]:
        """获取匹配的线索列表"""
        matched = []
        memory_dict = memory.to_dict() if hasattr(memory, 'to_dict') else {}
        metadata = memory_dict.get('metadata', {})

        for cue_key in cues:
            if cue_key in metadata:
                matched.append(cue_key)

        return matched
