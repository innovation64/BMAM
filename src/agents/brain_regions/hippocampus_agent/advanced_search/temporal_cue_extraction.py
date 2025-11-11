"""
Temporal Cue Extraction - 时间线索提取
LLM理解时间语义

Extracts temporal cues from query using LLM
"""

import logging
import json
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TemporalCueExtractor:
    """
    时间线索提取器 (Temporal Cue Extractor)

    Uses LLM to understand temporal semantics | 使用LLM理解时间语义:
    - Explicit time expressions | 显式时间表达
    - Implicit temporal cues | 隐式时间线索
    - Time relations | 时间关系
    """

    def __init__(self, agent):
        """Initialize extractor"""
        self.agent = agent


    async def extract(self, query: str) -> Dict[str, Any]:
        """
        提取时间线索 - Extract Temporal Cues

        Args:
            query: 查询文本

        Returns:
            {
                'explicit_time': str or None,
                'implicit_cues': List[str],
                'time_relation': str,
                'temporal_event': str,
                'is_temporal_query': bool
            }
        """
        prompt = self._build_prompt(query)

        try:
            response = await self.agent.call_llm(
                prompt, max_tokens=200, temperature=0.3
            )

            return self._parse_response(response)

        except json.JSONDecodeError as e:
            logger.warning(f"Temporal cue extraction failed: {e}")
            return {'is_temporal_query': False}


    def _build_prompt(self, query: str) -> str:
        """构建提取提示"""
        return f"""分析查询中的时间线索:

查询: "{query}"

提取:
1. **显式时间**: 明确的日期/时间 (如"2023年5月", "上周")
2. **隐式时间**: 暗示的时序 (如"第一次", "最早", "最近")
3. **时间关系**: 相对时间 (如"之前", "之后")
4. **时序事件**: 涉及时间顺序的事件

返回JSON:
{{
    "explicit_time": "显式时间或null",
    "implicit_cues": ["隐式线索"],
    "time_relation": "before/after/during/none",
    "temporal_event": "时序事件",
    "is_temporal_query": true/false
}}"""


    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {'is_temporal_query': False}
