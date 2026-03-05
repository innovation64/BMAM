"""
Theory of Mind (ToM) Advisory Module
心智理论顾问模块

Read-only advisor that classifies user query intent without modifying
retrieval scores. Designed to provide hints to downstream components.

Design principles:
- Read-only: Never modifies retrieval scores or results
- Rule-based: No LLM calls, pure pattern matching
- Optional: Feature-flagged, default OFF
- Non-invasive: Outputs to context['tom_advisory'] only
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """User query intent categories"""
    INFORMATIONAL = "informational"    # Seeking facts/information
    PREFERENCE = "preference"          # About user preferences/likes/dislikes
    TEMPORAL = "temporal"              # Time-related queries
    COMPARATIVE = "comparative"        # Comparing things
    IDENTITY = "identity"              # About user identity/who they are
    UNKNOWN = "unknown"                # Cannot determine


class ToMAdvisor:
    """
    Theory of Mind Advisory System - Read-only query intent classifier.

    Provides hints about user intent to downstream components without
    modifying any retrieval scores or results.
    """

    def __init__(self):
        self.enabled = os.getenv("BMAM_ENABLE_TOM", "false").lower() == "true"

        # Pattern definitions for rule-based classification
        self._temporal_patterns = [
            r'\b(when|what time|how long|since when|until when)\b',
            r'\b(yesterday|today|tomorrow|last\s+\w+|next\s+\w+)\b',
            r'\b(before|after|during|while|recently|earlier|later)\b',
            r'\b(年|月|日|时候|以前|之后|最近|昨天|今天|明天)\b',
            r'\b(first time|last time|how many times)\b',
        ]

        self._preference_patterns = [
            r'\b(favorite|prefer|like|love|hate|dislike|enjoy)\b',
            r'\b(best|worst|rather|opinion|think about)\b',
            r'\b(喜欢|讨厌|偏好|最爱|最喜欢|觉得怎么样)\b',
            r'\b(recommend|suggestion|choice|choose)\b',
        ]

        self._identity_patterns = [
            r'\b(my name|who am i|what do i do|where.*i.*from)\b',
            r'\b(tell me about myself|what do you know about me)\b',
            r'\b(我是谁|我叫什么|我的名字|关于我)\b',
            r'\b(my job|my work|my age|my hobby|my hobbies)\b',
        ]

        self._comparative_patterns = [
            r'\b(compare|difference|similar|versus|vs\.?|better|worse)\b',
            r'\b(more than|less than|as much as|between)\b',
            r'\b(比较|区别|不同|相似|哪个更)\b',
        ]

        self._total_queries = 0
        self._intent_counts: Dict[str, int] = {
            intent.value: 0 for intent in QueryIntent
        }

    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user query intent using rule-based patterns.

        Args:
            query: The user's query text

        Returns:
            Advisory dict with intent classification and confidence
        """
        if not self.enabled:
            return {'enabled': False}

        self._total_queries += 1
        query_lower = query.lower().strip()

        scores = {
            QueryIntent.TEMPORAL: self._score_patterns(
                query_lower, self._temporal_patterns
            ),
            QueryIntent.PREFERENCE: self._score_patterns(
                query_lower, self._preference_patterns
            ),
            QueryIntent.IDENTITY: self._score_patterns(
                query_lower, self._identity_patterns
            ),
            QueryIntent.COMPARATIVE: self._score_patterns(
                query_lower, self._comparative_patterns
            ),
        }

        # Informational is the default when nothing else matches strongly
        max_score = max(scores.values()) if scores else 0

        if max_score == 0:
            intent = QueryIntent.INFORMATIONAL
            confidence = 0.5
        else:
            intent = max(scores, key=scores.get)
            confidence = min(0.95, 0.5 + max_score * 0.15)

        self._intent_counts[intent.value] += 1

        advisory = {
            'enabled': True,
            'intent': intent.value,
            'confidence': confidence,
            'scores': {k.value: v for k, v in scores.items()},
            'query_length': len(query),
        }

        logger.debug(
            f"ToM advisory: intent={intent.value}, "
            f"confidence={confidence:.2f}"
        )
        return advisory

    def _score_patterns(self, text: str, patterns: List[str]) -> int:
        """Count matching patterns in text."""
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            score += len(matches)
        return score

    def apply_to_context(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify intent and add advisory to context.
        Does NOT modify any existing context values.

        Args:
            query: User query
            context: Processing context dict

        Returns:
            The advisory dict (also stored in context['tom_advisory'])
        """
        advisory = self.classify_intent(query)
        context['tom_advisory'] = advisory
        return advisory

    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        return {
            'enabled': self.enabled,
            'total_queries': self._total_queries,
            'intent_distribution': dict(self._intent_counts),
        }


# Module-level singleton
_tom_advisor: Optional[ToMAdvisor] = None


def get_tom_advisor() -> ToMAdvisor:
    """Get global ToM advisor instance."""
    global _tom_advisor
    if _tom_advisor is None:
        _tom_advisor = ToMAdvisor()
    return _tom_advisor
