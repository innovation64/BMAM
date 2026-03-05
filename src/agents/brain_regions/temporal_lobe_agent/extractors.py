"""
LLM-based extractors for Temporal Lobe Agent
LLM提取器模块
"""

import logging
import asyncio
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ExtractorsMixin:
    """LLM-based extractors mixin for TemporalLobeAgent"""

    async def extract_factual_statements(self, session_text: str, session_id: int) -> List[str]:
        """
        从会话中提取客观事实陈述

        Args:
            session_text: 会话文本
            session_id: 会话编号

        Returns:
            List of factual statements
        """
        prompt = f"""Extract key factual statements from this conversation session.
Focus on objective facts, events, and verifiable information.

Session text:
{session_text[:3000]}  # Limit to avoid token overflow

Return 5-10 most important factual statements, one per line.
Format: Just the statement, no numbering or bullets."""

        try:
            response = await self._call_llm(prompt)
            facts = [line.strip() for line in response.split('\n') if line.strip()]
            return facts[:10]  # Limit to 10
        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to extract factual statements: {e}")
            return []

    async def extract_relations(self, session_text: str, session_id: int) -> List[Tuple[str, str, str]]:
        """
        从会话中提取实体关系

        Args:
            session_text: 会话文本
            session_id: 会话编号

        Returns:
            List of (source, relation, target) tuples
        """
        prompt = f"""Extract key entity relationships from this conversation session.
Focus on relationships between people, concepts, and things.

Session text:
{session_text[:3000]}  # Limit to avoid token overflow

Return 5-10 most important relationships.
Format: source | relation | target
Example: PersonA | interested_in | topic
Example: PersonB | supports | cause"""

        try:
            response = await self._call_llm(prompt)
            relations = []
            for line in response.split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) == 3:
                        relations.append((parts[0], parts[1], parts[2]))
            return relations[:10]  # Limit to 10
        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to extract relations: {e}")
            return []

    async def extract_temporal_events(self, session_text: str, session_id: int) -> List[str]:
        """
        从会话中提取时间线事件

        Args:
            session_text: 会话文本
            session_id: 会话编号

        Returns:
            List of temporal event descriptions
        """
        prompt = f"""Extract key temporal events from this conversation session.
Focus on events with time references (dates, sequences, temporal ordering).

Session text:
{session_text[:3000]}  # Limit to avoid token overflow

Return 5-10 most important temporal events.
Format: Brief event description with time context
Example: May 2023: PersonA attended an event
Example: After meeting PersonB, PersonA researched a topic"""

        try:
            response = await self._call_llm(prompt)
            events = [line.strip() for line in response.split('\n') if line.strip()]
            return events[:10]  # Limit to 10
        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to extract temporal events: {e}")
            return []

    async def _call_llm(self, prompt: str) -> str:
        """Helper method to call LLM for extraction tasks"""
        try:
            # Use the inherited call_llm method from BrainAgent base class
            response = await self.call_llm(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3,
                system_prompt="You are a precise information extractor. Extract only the requested information."
            )
            return response.strip()
        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.warning(f"LLM call failed: {e}")
            return ""
