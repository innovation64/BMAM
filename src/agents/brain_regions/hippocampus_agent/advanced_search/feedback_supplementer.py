"""
Feedback Supplementer - 反馈补充器
缺失维度补充

Supplements missing aspects when filtered results are insufficient
"""

import logging
from typing import Dict, List, Any

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class FeedbackSupplementer:
    """
    反馈补充器 (Feedback Supplementer)

    When filtered results < threshold | 当过滤结果不足时:
    - Search for missing aspects | 搜索缺失维度
    - Apply same filters | 应用相同过滤器
    - Deduplicate results | 去重
    """

    def __init__(self, agent):
        """Initialize supplementer"""
        self.agent = agent


    async def supplement(
        self, query: str, current_memories: List[EpisodicMemory], feedback: Dict[str, Any]
    ) -> List[EpisodicMemory]:
        """补充缺失维度 - Supplement Missing Aspects"""
        refined = current_memories.copy()
        existing_ids = {m.id for m in refined}
        for aspect in feedback['missing_aspects']:
            new_memories = await self._search_aspect(query, aspect, feedback, existing_ids)
            refined.extend(new_memories)
            existing_ids.update(m.id for m in new_memories)
        return refined


    async def _search_aspect(self, query: str, aspect: str, feedback: Dict, existing_ids: set) -> List[EpisodicMemory]:
        """搜索单个缺失维度"""
        supplementary_query = f"{query} {aspect}"
        search_kwargs = self._build_search_kwargs(supplementary_query, feedback)
        additional_result = await self.agent.search_memories(**search_kwargs)
        return self._extract_new_memories(additional_result, existing_ids, feedback)


    def _build_search_kwargs(self, query: str, feedback: Dict) -> Dict[str, Any]:
        """构建搜索参数"""
        search_kwargs = {'query': query, 'k': 10}
        if 'preferred_entities' in feedback:
            search_kwargs['entities'] = feedback['preferred_entities']
        if 'preferred_time_range' in feedback:
            start_str, end_str = feedback['preferred_time_range']
            search_kwargs['time_range'] = {
                'start': start_str if isinstance(start_str, str) else start_str.isoformat(),
                'end': end_str if isinstance(end_str, str) else end_str.isoformat()
            }
        return search_kwargs


    def _extract_new_memories(self, search_result: Dict, existing_ids: set, feedback: Dict) -> List[EpisodicMemory]:
        """提取新记忆"""
        new_memories = []
        for mem_dict in search_result['memories']:
            mem_id = mem_dict.get('id')
            if not mem_id or mem_id not in self.agent.memory_dict or mem_id in existing_ids:
                continue
            mem = self.agent.memory_dict[mem_id]
            if self._passes_filters(mem, feedback):
                new_memories.append(mem)
        return new_memories

    def _passes_filters(self, mem: EpisodicMemory, feedback: Dict) -> bool:
        """检查记忆是否通过过滤器"""
        if 'min_importance' in feedback and mem.importance < feedback['min_importance']:
            return False
        if 'min_emotion_intensity' in feedback and mem.emotion_intensity < feedback['min_emotion_intensity']:
            return False
        return True
