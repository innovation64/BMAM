"""
Entity-Action Ranking - 实体-动作绑定排序
LLM关系推理

Ranks candidates by entity-action binding precision
"""

import logging
import json
import re
from typing import Optional, List, Dict, Any

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


class EntityActionRanker:
    """
    实体-动作排序器 (Entity-Action Ranker)

    Key | 关键:
    - 区分 "Caroline研究adoption" vs "他人研究气候"
    - 精确匹配 entity-action-object 三元组
    """

    def __init__(self, agent):
        """Initialize ranker"""
        self.agent = agent


    async def rank(
        self, query: str, candidates: List[EpisodicMemory],
        entity: Optional[str], action: Optional[str]
    ) -> List[Dict[str, Any]]:
        """LLM排序 - Rank by Entity-Action Binding"""
        candidates_summary = [
            {'index': i, 'content': mem.content, 'entities': mem.entities,
             'timestamp': mem.timestamp.isoformat()}
            for i, mem in enumerate(candidates[:15])
        ]
        prompt = self._build_prompt(query, entity, action, candidates_summary)
        try:
            response = await self.agent.call_llm(prompt, max_tokens=500, temperature=0.3)
            ranked_results = self._parse_response(response, candidates)
            if ranked_results:
                return ranked_results
        except json.JSONDecodeError as e:
            logger.warning(f"Entity-action ranking failed: {e}")
        return self._fallback_ranking(candidates, entity, action)


    def _build_prompt(
        self, query: str, entity: Optional[str],
        action: Optional[str], candidates_summary: List[Dict]
    ) -> str:
        """构建排序提示"""
        return f"""关系编码排序:
查询: "{query}"
实体-动作: Entity={entity or 'None'}, Action={action or 'None'}
候选记忆: {json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

返回JSON: {{"reasoning": "...", "ranked_indices": [...], "best_match_index": 0, "best_match_reason": "...", "extracted_object": "..."}}"""


    def _parse_response(self, response: str, candidates: List[EpisodicMemory]) -> List[Dict[str, Any]]:
        """解析LLM响应"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return []
        ranking = json.loads(json_match.group())
        ranked_results = []
        for idx in ranking.get('ranked_indices', [])[:15]:
            if 0 <= idx < len(candidates):
                ranked_results.append({
                    'memory': candidates[idx], 'reasoning': ranking.get('reasoning', ''),
                    'binding_score': 1.0 if idx == ranking.get('best_match_index') else 0.5
                })
        return ranked_results


    def _fallback_ranking(
        self, candidates: List[EpisodicMemory],
        entity: Optional[str], action: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Fallback算法排序"""
        scored = []
        for mem in candidates:
            score = 0.0
            if entity and entity in mem.entities:
                score += 0.6
            if action and action in mem.content:
                score += 0.3
            score += mem.importance * 0.1
            scored.append({
                'memory': mem, 'reasoning': f'fallback_score={score:.2f}',
                'binding_score': score
            })
        scored.sort(key=lambda x: x['binding_score'], reverse=True)
        return scored
