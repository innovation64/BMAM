"""
Entity-Action Extraction
Extracts entity and action from query using LLM

LLM understands deep semantics for entity-action binding.
"""

import logging
import json
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EntityActionExtractor:
    """
    Entity-Action Extractor

    Uses LLM to understand deep semantics:
    - No hardcoded verb lists
    - Understands implicit actions
    """

    def __init__(self, agent):
        """Initialize extractor"""
        self.agent = agent


    async def extract(self, query: str) -> Dict[str, Any]:
        """
        Extract Entity and Action from query

        Examples:
        - "What does PersonA research?" → entity=PersonA, action=research
        - "Who attended the event?" → entity=None, action=attend

        Args:
            query: Query text

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
        """Build extraction prompt"""
        return f"""Extract entity and action:

Query: "{query}"

Extract:
1. **Entity**: Person/organization (e.g., "PersonA", "PersonB")
   - If query is "Who...", then entity=null
2. **Action**: Key behavior (e.g., "research", "attend", "buy")
   - Understand semantics, not just verb matching
3. **Object**: Target of action
   - "What does X research?" → object=unknown
   - "Attend the event" → object=event

Return JSON:
{{
    "entity": "entity or null",
    "action": "action or null",
    "object": "object or unknown",
    "query_intent": "query intent type"
}}"""


    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {}
