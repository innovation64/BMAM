"""
Temporal Ranking - 时间推理排序
LLM理解时间意图

Ranks candidates by temporal relevance using LLM
"""

import logging
import json
import re
from typing import Dict, List, Any

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class TemporalRanker:
    """
    时间推理排序器 (Temporal Ranker)

    Key Innovation | 关键创新:
    - 理解时间意图 (not simple matching)
    - "第一次" → earliest time
    - "最近" → latest time
    """

    def __init__(self, agent):
        """Initialize ranker"""
        self.agent = agent


    async def rank(
        self, query: str, candidates: List[EpisodicMemory], temporal_cues: Dict
    ) -> List[Dict[str, Any]]:
        """LLM时间推理排序 - Rank by Temporal Relevance"""
        candidates_summary = [
            {'index': i, 'content': mem.content[:150],
             'timestamp': mem.timestamp.isoformat(), 'entities': mem.entities}
            for i, mem in enumerate(candidates[:10])
        ]
        prompt = self._build_prompt(query, temporal_cues, candidates_summary)
        try:
            response = await self.agent.call_llm(prompt, max_tokens=400, temperature=0.3)
            ranked_results = self._parse_response(response, candidates)
            if ranked_results:
                return ranked_results
        except json.JSONDecodeError as e:
            logger.warning(f"Temporal ranking failed: {e}")
        return self._fallback_sort(candidates, temporal_cues)


    def _build_prompt(self, query: str, temporal_cues: Dict, candidates_summary: List[Dict]) -> str:
        """构建排序提示"""
        return f"""时间推理排序:
查询: "{query}"
时间线索: {json.dumps(temporal_cues, indent=2, ensure_ascii=False)}
候选: {json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

返回JSON: {{"reasoning": "...", "ranked_indices": [...], "most_relevant_index": 0, "most_relevant_reason": "..."}}"""


    def _parse_response(self, response: str, candidates: List[EpisodicMemory]) -> List[Dict[str, Any]]:
        """解析LLM响应"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return []
        ranking = json.loads(json_match.group())
        ranked_results = []
        for idx in ranking.get('ranked_indices', [])[:10]:
            if 0 <= idx < len(candidates):
                ranked_results.append({
                    'memory': candidates[idx], 'reasoning': ranking.get('reasoning', ''),
                    'temporal_relevance': 1.0 if idx == ranking.get('most_relevant_index') else 0.5
                })
        return ranked_results


    def _fallback_sort(self, candidates: List[EpisodicMemory], temporal_cues: Dict) -> List[Dict[str, Any]]:
        """Fallback时间排序"""
        implicit_cues = temporal_cues.get('implicit_cues', [])
        if any(c in ['第一次', '最早', 'first', 'earliest'] for c in implicit_cues):
            sorted_cands = sorted(candidates, key=lambda m: m.timestamp)
        elif any(c in ['最近', '最后', 'recent', 'latest', 'last'] for c in implicit_cues):
            sorted_cands = sorted(candidates, key=lambda m: m.timestamp, reverse=True)
        else:
            sorted_cands = candidates
        return [{'memory': m, 'reasoning': 'fallback_sort', 'temporal_relevance': 0.5} for m in sorted_cands]
