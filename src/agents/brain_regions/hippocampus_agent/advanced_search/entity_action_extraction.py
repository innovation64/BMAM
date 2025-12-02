"""
Entity-Action Extraction - 实体-动作提取
LLM理解深层语义

Extracts entity and action from query using LLM
"""

import logging
import json
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EntityActionExtractor:
    """
    实体-动作提取器 (Entity-Action Extractor)

    Uses LLM to understand deep semantics | 使用LLM理解深层语义:
    - No hardcoded verb lists
    - Understands implicit actions
    """

    def __init__(self, agent):
        """Initialize extractor"""
        self.agent = agent


    async def extract(self, query: str) -> Dict[str, Any]:
        """
        提取实体和动作 - Extract Entity and Action

        Examples | 示例:
        - "PersonA研究什么?" → entity=PersonA, action=研究
        - "谁参加了活动?" → entity=None, action=参加

        Args:
            query: 查询文本

        Returns:
            {
                'entity': str or None,
                'action': str or None,
                'object': str or 'unknown',
                'query_intent': str
            }
        """
        prompt = self._build_prompt(query)

        try:
            response = await self.agent.call_llm(
                prompt, max_tokens=200, temperature=0.3
            )

            return self._parse_response(response)

        except json.JSONDecodeError as e:
            logger.warning(f"Entity-action extraction failed: {e}")
            return {}


    def _build_prompt(self, query: str) -> str:
        """构建提取提示"""
        return f"""提取实体和动作:

查询: "{query}"

提取:
1. **实体** (Entity): 人物/组织 (如"PersonA", "PersonB")
   - 如果查询是"谁..."，则entity=null
2. **动作** (Action): 关键行为 (如"研究", "参加", "买")
   - 理解语义，不只匹配动词
3. **对象** (Object): 动作对象
   - "研究什么?" → object=unknown
   - "参加活动" → object=活动

返回JSON:
{{
    "entity": "实体或null",
    "action": "动作或null",
    "object": "对象或unknown",
    "query_intent": "查询意图"
}}"""


    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {}
