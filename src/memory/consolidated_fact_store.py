"""
Consolidated Fact Store — 隐性知识层

Brain-inspired implicit knowledge formation through repetition-based consolidation.

Neuroscience basis:
- Repeated activation of neural pathways strengthens synaptic connections (Hebb's rule)
- Hippocampal replay during sleep consolidates episodic → semantic knowledge
- Neocortical slow learning accumulates statistical regularities into "intuitions"

Architecture:
- Input: memories stored during conversation shaping
- Process: extract entity-fact pairs, track frequency, promote high-frequency facts
- Output: always-available fact context injected BEFORE retrieval

This creates a "familiarity signal" — the system "just knows" certain facts
without needing to retrieve them, like how you know your friend's name.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..utils.config import get_logger

logger = get_logger(__name__)


@dataclass
class ConsolidatedFact:
    """A single consolidated fact — implicit knowledge unit."""
    entity: str                     # Primary entity (person name)
    fact_text: str                  # The fact itself
    category: str                   # identity, relationship, activity, attribute, preference
    confidence: float = 0.5         # Higher = more sources agree
    source_count: int = 1           # How many memories contributed
    first_seen: str = ""            # ISO datetime
    last_updated: str = ""          # ISO datetime


class ConsolidatedFactStore:
    """
    Implicit knowledge layer — facts that don't need retrieval.

    Like neocortical semantic memory in the brain: slow-learning,
    high-confidence knowledge accumulated from repeated episodic exposure.

    Usage:
        store = ConsolidatedFactStore(data_dir)

        # During memory shaping (accumulate)
        store.extract_and_accumulate(memory_content, entities)

        # During QA (inject)
        facts = store.get_entity_facts("Caroline", top_k=10)
        # → These facts are injected into LLM context WITHOUT retrieval
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.store_path = self.data_dir / "consolidated_facts.json"
        # entity → [ConsolidatedFact, ...]
        self.facts: Dict[str, List[ConsolidatedFact]] = {}
        self._load()

    def _load(self):
        """Load from disk."""
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for entity, fact_list in data.items():
                    self.facts[entity] = [
                        ConsolidatedFact(**fd) for fd in fact_list
                    ]
                total = sum(len(v) for v in self.facts.values())
                logger.info(
                    f"✅ Loaded {total} consolidated facts "
                    f"for {len(self.facts)} entities"
                )
            except Exception as e:
                logger.warning(f"Failed to load fact store: {e}")
                self.facts = {}

    def save(self):
        """Persist to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = {}
        for entity, fact_list in self.facts.items():
            data[entity] = [asdict(f) for f in fact_list]
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def clear(self):
        """Clear all facts (for benchmark reset)."""
        self.facts = {}
        if self.store_path.exists():
            self.store_path.unlink()

    def extract_and_accumulate(
        self,
        content: str,
        entities: List[str] = None
    ):
        """
        Extract facts from a memory and accumulate into the store.

        This is the "slow learning" process — each memory slightly
        strengthens relevant facts, like synaptic potentiation.

        Args:
            content: Memory content text
            entities: Pre-extracted entity names (optional)
        """
        if not content or len(content) < 10:
            return

        # Auto-detect entities if not provided
        if not entities:
            entities = self._extract_entities(content)

        if not entities:
            return

        # Extract fact-like statements
        facts = self._extract_facts_from_content(content, entities)

        now = datetime.now().isoformat()
        for entity, fact_text, category in facts:
            entity_lower = entity.lower()
            if entity_lower not in self.facts:
                self.facts[entity_lower] = []

            # Check if similar fact exists (merge if so)
            merged = False
            for existing in self.facts[entity_lower]:
                if self._facts_similar(existing.fact_text, fact_text):
                    # Strengthen: increase confidence and source count
                    existing.source_count += 1
                    existing.confidence = min(
                        0.95,
                        existing.confidence + 0.1 * (1 - existing.confidence)
                    )
                    existing.last_updated = now
                    merged = True
                    break

            if not merged:
                self.facts[entity_lower].append(ConsolidatedFact(
                    entity=entity,
                    fact_text=fact_text,
                    category=category,
                    confidence=0.4,  # Initial confidence — promoted by repetition
                    source_count=1,
                    first_seen=now,
                    last_updated=now
                ))

    def get_entity_facts(
        self,
        entity: str,
        top_k: int = 10,
        min_confidence: float = 0.4
    ) -> List[ConsolidatedFact]:
        """
        Get consolidated facts for an entity.

        Returns high-confidence facts sorted by confidence.
        These are "implicit knowledge" — no retrieval needed.
        """
        entity_lower = entity.lower()
        facts = self.facts.get(entity_lower, [])
        # Filter by confidence threshold
        qualified = [f for f in facts if f.confidence >= min_confidence]
        # Sort by confidence * source_count (well-established facts first)
        qualified.sort(
            key=lambda f: f.confidence * f.source_count,
            reverse=True
        )
        return qualified[:top_k]

    def get_facts_for_query(
        self,
        query: str,
        top_k: int = 8,
        min_confidence: float = 0.4
    ) -> List[ConsolidatedFact]:
        """
        Get facts relevant to a query — the "familiarity signal".

        Extracts entities from query, then returns their consolidated facts.
        This is a FAST operation (no vector search, no LLM call).
        """
        entities = self._extract_entities(query)
        all_facts = []
        for entity in entities:
            all_facts.extend(
                self.get_entity_facts(entity, top_k=top_k,
                                      min_confidence=min_confidence)
            )

        # Deduplicate and sort
        seen = set()
        unique = []
        for f in all_facts:
            key = (f.entity.lower(), f.fact_text[:50])
            if key not in seen:
                seen.add(key)
                unique.append(f)

        unique.sort(
            key=lambda f: f.confidence * f.source_count,
            reverse=True
        )
        return unique[:top_k]

    def format_facts_for_context(
        self,
        facts: List[ConsolidatedFact]
    ) -> str:
        """Format facts as a context string for LLM injection."""
        if not facts:
            return ""

        lines = ["[Consolidated Knowledge — high-confidence facts]:"]
        for f in facts:
            lines.append(f"- {f.entity}: {f.fact_text}")
        return "\n".join(lines)

    def get_familiarity_signal(self, query: str) -> Tuple[bool, float]:
        """
        Fast familiarity check — "Do I know about this?"

        Returns (is_familiar, confidence).
        Used for adversarial detection: if query asks about something
        we have NO facts about, the premise may be false.
        """
        entities = self._extract_entities(query)
        if not entities:
            return False, 0.0

        max_confidence = 0.0
        for entity in entities:
            facts = self.get_entity_facts(entity, top_k=1,
                                          min_confidence=0.3)
            if facts:
                max_confidence = max(max_confidence, facts[0].confidence)

        return max_confidence > 0.3, max_confidence

    # ================================================================
    # Internal helpers
    # ================================================================

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity names (capitalized words, filtered)."""
        stop_words = {
            'when', 'what', 'how', 'where', 'who', 'which', 'the',
            'a', 'an', 'to', 'did', 'does', 'is', 'was', 'has', 'had',
            'will', 'would', 'could', 'should', 'do', 'are', 'were',
            'been', 'being', 'have', 'in', 'on', 'at', 'for', 'of',
            'and', 'or', 'not', 'no', 'yes', 'recently', 'today',
            'yesterday', 'context', 'this', 'that', 'with', 'from',
            'about', 'into', 'during', 'before', 'after', 'between',
            'but', 'if', 'then', 'than', 'also', 'just', 'like',
            'very', 'really', 'some', 'any', 'all', 'each', 'every',
            'both', 'few', 'more', 'most', 'other', 'new', 'old',
            'first', 'last', 'long', 'great', 'little', 'own', 'same',
            'big', 'high', 'different', 'small', 'large', 'next', 'early',
            'may', 'june', 'july', 'august', 'september', 'october',
            'november', 'december', 'january', 'february', 'march', 'april',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'conversation',
        }
        words = text.split()
        entities = []
        for w in words:
            clean = re.sub(r'[^a-zA-Z]', '', w)
            if (len(clean) > 1 and clean[0].isupper()
                    and clean.lower() not in stop_words):
                entities.append(clean)
        return list(dict.fromkeys(entities))  # deduplicate, preserve order

    def _extract_facts_from_content(
        self,
        content: str,
        entities: List[str]
    ) -> List[Tuple[str, str, str]]:
        """
        Rule-based fact extraction from memory content.

        Returns list of (entity, fact_text, category).
        No LLM call — fast and deterministic.
        """
        facts = []
        content_lower = content.lower()

        # Pattern-based extraction
        for entity in entities:
            el = entity.lower()
            if el not in content_lower:
                continue

            # Identity patterns
            identity_patterns = [
                (r'(?i)' + re.escape(entity) + r'\s+is\s+(?:a|an)\s+(.+?)(?:\.|,|$)',
                 'identity'),
                (r'(?i)' + re.escape(entity) + r'\s+works?\s+(?:as|at|in)\s+(.+?)(?:\.|,|$)',
                 'identity'),
                (r'(?i)' + re.escape(entity) + r'\s+(?:is|was)\s+(?:born|raised)\s+(.+?)(?:\.|,|$)',
                 'identity'),
            ]

            # Relationship patterns
            rel_patterns = [
                (r'(?i)' + re.escape(entity) + r"'s\s+((?:mother|father|sister|brother|daughter|son|wife|husband|partner|friend|pet|dog|cat|guinea pig)\b.+?)(?:\.|,|$)",
                 'relationship'),
                (r'(?i)' + re.escape(entity) + r'\s+(?:has|have|had)\s+(?:a|an|two|three)?\s*(.+?)(?:\.|,|$)',
                 'attribute'),
            ]

            # Preference patterns
            pref_patterns = [
                (r'(?i)' + re.escape(entity) + r'\s+(?:loves?|likes?|enjoys?|prefers?)\s+(.+?)(?:\.|,|$)',
                 'preference'),
                (r'(?i)' + re.escape(entity) + r"'s\s+favorite\s+(.+?)(?:\.|,|$)",
                 'preference'),
            ]

            # Activity patterns
            act_patterns = [
                (r'(?i)' + re.escape(entity) + r'\s+(?:started|began|joined|enrolled|signed up|opened|launched)\s+(.+?)(?:\.|,|$)',
                 'activity'),
            ]

            all_patterns = (identity_patterns + rel_patterns +
                           pref_patterns + act_patterns)

            for pattern, category in all_patterns:
                try:
                    matches = re.findall(pattern, content[:500])
                    for match in matches[:2]:  # Max 2 per pattern
                        fact = match.strip()
                        if 5 < len(fact) < 100:
                            facts.append((entity, fact, category))
                except re.error:
                    continue

        return facts

    def _facts_similar(self, fact_a: str, fact_b: str) -> bool:
        """Check if two facts are semantically similar (simple overlap)."""
        words_a = set(fact_a.lower().split())
        words_b = set(fact_b.lower().split())
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b)
        min_len = min(len(words_a), len(words_b))
        return overlap / max(min_len, 1) >= 0.6

    def get_stats(self) -> Dict:
        """Get statistics about the fact store."""
        total = sum(len(v) for v in self.facts.values())
        high_conf = sum(
            1 for facts in self.facts.values()
            for f in facts if f.confidence >= 0.6
        )
        return {
            'total_entities': len(self.facts),
            'total_facts': total,
            'high_confidence_facts': high_conf,
            'avg_confidence': (
                sum(f.confidence for facts in self.facts.values()
                    for f in facts) / max(total, 1)
            )
        }
