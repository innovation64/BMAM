"""
Temporal Cue Extraction
Extracts temporal cues from query using LLM

LLM understands temporal semantics to identify time-related information.
"""

import logging
import json
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TemporalCueExtractor:
    """
    Temporal Cue Extractor

    Uses LLM to understand temporal semantics:
    - Explicit time expressions
    - Implicit temporal cues
    - Time relations
    """

    def __init__(self, agent):
        """Initialize extractor"""
        self.agent = agent


    async def extract(self, query: str) -> Dict[str, Any]:
        """
        Extract Temporal Cues from query

        Args:
            query: Query text

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
        """Build extraction prompt"""
        return f"""Analyze temporal cues in the query:

Query: "{query}"

Extract:
1. **Explicit time**: Specific dates/times (e.g., "May 2023", "last week")
2. **Implicit cues**: Implied temporal markers (e.g., "first time", "earliest", "most recent")
3. **Time relation**: Relative time (e.g., "before", "after")
4. **Temporal event**: Events involving time order

Return JSON:
{{
    "explicit_time": "explicit time or null",
    "implicit_cues": ["implicit cues"],
    "time_relation": "before/after/during/none",
    "temporal_event": "temporal event",
    "is_temporal_query": true/false
}}"""


    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {'is_temporal_query': False}
