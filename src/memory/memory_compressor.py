"""
Memory Compressor — 存储时语义压缩层

Brain-inspired: 模拟海马体→新皮层的记忆巩固过程。
原始对话（情景记忆）保留在海马体，同时提取原子事实（语义记忆）
存入颞叶 + ConsolidatedFactStore。

Architecture:
  对话输入 → [原始存储到海马体] (保留完整细节)
           → [压缩为原子事实]   (快速检索层)
           → [积累到事实库]     (隐性知识)

This is the "encoding" phase of memory — not just storing,
but also understanding and compressing.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from ..utils.config import get_logger

logger = get_logger(__name__)


class MemoryCompressor:
    """
    Compress dialogue turns into atomic facts at storage time.

    Two modes:
    1. Rule-based (fast, no LLM call) — for shaping phase with hundreds of turns
    2. LLM-based (better quality) — for real-time conversation
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: Whether to use LLM for compression (slower but better)
        """
        self.use_llm = use_llm
        self._llm_service = None

    def compress_to_atomic_facts(
        self,
        content: str,
        speaker: str = None,
        context_date: str = None
    ) -> List[Dict[str, str]]:
        """
        Compress a dialogue turn into atomic facts.

        Args:
            content: Raw dialogue content
            speaker: Who said it (user/assistant)
            context_date: Conversation date string

        Returns:
            List of {fact, entity, category, source_snippet}
        """
        if not content or len(content) < 15:
            return []

        # Strip [Context:...] prefix
        clean = re.sub(r'\[Context:.*?\]\s*', '', content)
        clean = re.sub(r'\[Chunk.*?\]\s*', '', clean)

        # Split into sentences
        sentences = self._split_sentences(clean)

        facts = []
        for sent in sentences:
            extracted = self._extract_facts_from_sentence(sent, speaker)
            facts.extend(extracted)

        # Deduplicate
        seen = set()
        unique = []
        for f in facts:
            key = f['fact'][:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(f)
                if context_date:
                    f['context_date'] = context_date

        return unique

    async def compress_with_llm(
        self,
        content: str,
        speaker: str = None,
        context_date: str = None
    ) -> List[Dict[str, str]]:
        """
        LLM-based compression — high quality atomic fact extraction.
        """
        if not self._llm_service:
            try:
                from ..services.shared_openai_client import shared_client_manager
                self._llm_service = shared_client_manager
            except Exception:
                return self.compress_to_atomic_facts(content, speaker, context_date)

        date_hint = f"\nConversation date: {context_date}" if context_date else ""

        prompt = f"""Extract key facts from this dialogue as atomic statements.{date_hint}

Rules:
- Each fact: "[Person] [verb] [what]" format
- ALWAYS include the person's NAME (never "she/he/they")
- If a date or time is mentioned, INCLUDE IT in the fact
- Convert relative times to absolute: "yesterday" on 8 May = "on 7 May"
- Include relationships, preferences, activities, identity facts
- Max 5 most important facts

Dialogue:
{content[:1000]}

Facts:
1."""

        try:
            response = await self._llm_service.chat_completion(
                messages=[
                    {"role": "system",
                     "content": "Extract atomic facts from dialogue. Each fact must name the person explicitly and include dates when available. Output numbered list only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=250
            )
            text = response.choices[0].message.content
            facts = []
            for line in text.strip().split('\n'):
                line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                if not line or len(line) < 10:
                    continue
                entities = self._extract_entities(line)
                # Classify fact category
                line_lower = line.lower()
                if any(w in line_lower for w in ['is a', 'works as', 'born']):
                    cat = 'identity'
                elif any(w in line_lower for w in ['loves', 'likes', 'enjoys', 'favorite', 'prefers']):
                    cat = 'preference'
                elif any(w in line_lower for w in ['mother', 'father', 'friend', 'pet', 'daughter', 'son', 'partner']):
                    cat = 'relationship'
                elif any(w in line_lower for w in ['went', 'visited', 'started', 'joined', 'painted', 'created']):
                    cat = 'activity'
                else:
                    cat = 'general'
                facts.append({
                    'fact': line,
                    'entity': entities[0] if entities else '',
                    'category': cat,
                    'source_snippet': content[:100],
                    'context_date': context_date or ''
                })
            return facts[:5]
        except Exception as e:
            logger.debug(f"LLM compression failed: {e}, using rule-based")
            return self.compress_to_atomic_facts(content, speaker, context_date)

    # ================================================================
    # Rule-based extraction (fast, no LLM)
    # ================================================================

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Split on sentence boundaries
        parts = re.split(r'(?<=[.!?])\s+|(?<=。)\s*', text)
        # Also split on dialogue turns
        expanded = []
        for part in parts:
            turns = re.split(r'(?:User|Assistant|Speaker \d+):\s*', part)
            expanded.extend(t.strip() for t in turns if t.strip())
        return [s for s in expanded if len(s) > 10]

    def _extract_facts_from_sentence(
        self,
        sentence: str,
        speaker: str = None
    ) -> List[Dict[str, str]]:
        """Extract atomic facts from a single sentence."""
        facts = []
        entities = self._extract_entities(sentence)

        if not entities:
            return facts

        sent_lower = sentence.lower()

        # Pattern groups for different fact types
        patterns = {
            'identity': [
                r'(\w+)\s+is\s+(?:a|an)\s+(.{5,60}?)(?:\.|,|$|who|and)',
                r'(\w+)\s+works?\s+(?:as|at|in|for)\s+(.{5,60}?)(?:\.|,|$)',
                r'(\w+)\s+(?:is|was)\s+(?:from|born in)\s+(.{5,60}?)(?:\.|,|$)',
            ],
            'preference': [
                r'(\w+)\s+(?:loves?|likes?|enjoys?|prefers?)\s+(.{5,60}?)(?:\.|,|$)',
                r'(\w+)\'s\s+favorite\s+(\w+)\s+(?:is|was)\s+(.{5,60}?)(?:\.|,|$)',
                r'(\w+)\s+(?:is\s+)?(?:interested|passionate)\s+(?:in|about)\s+(.{5,60}?)(?:\.|,|$)',
            ],
            'relationship': [
                r'(\w+)\'s\s+(mother|father|sister|brother|daughter|son|wife|husband|partner|friend|pet|dog|cat|guinea pig)\s+(?:is|was|named)\s+(.{3,40}?)(?:\.|,|$)',
                r'(\w+)\s+has\s+(?:a|an|two|three)\s+(daughter|son|sister|brother|pet|dog|cat|guinea pig)s?\s*(?:named\s+)?(.{0,30}?)(?:\.|,|$)',
            ],
            'activity': [
                r'(\w+)\s+(?:went|goes|visited|attended)\s+(?:to\s+)?(.{5,60}?)(?:\.|,|$)',
                r'(\w+)\s+(?:started|began|joined|signed up|enrolled)\s+(?:for|in)?\s*(.{5,60}?)(?:\.|,|$)',
                r'(\w+)\s+(?:painted|wrote|created|made|built|opened|launched)\s+(.{5,60}?)(?:\.|,|$)',
            ],
            'attribute': [
                r'(\w+)\s+has\s+(?:been|always been)\s+(.{5,60}?)(?:\.|,|$)',
                r'(\w+)\s+(?:recently|just)\s+(.{5,60}?)(?:\.|,|$)',
            ],
        }

        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                try:
                    matches = re.finditer(pattern, sentence, re.IGNORECASE)
                    for match in matches:
                        groups = match.groups()
                        entity = groups[0]
                        # Only extract for known entities
                        if entity.lower() not in {e.lower() for e in entities}:
                            continue
                        fact_parts = [g for g in groups[1:] if g]
                        fact_text = f"{entity} {' '.join(fact_parts)}"
                        if len(fact_text) > 10:
                            facts.append({
                                'fact': fact_text.strip(),
                                'entity': entity,
                                'category': category,
                                'source_snippet': sentence[:100]
                            })
                except re.error:
                    continue

        # If no patterns matched but we have entities, create a general fact
        if not facts and entities and len(sentence) < 150:
            primary_entity = entities[0]
            if primary_entity.lower() in sent_lower:
                facts.append({
                    'fact': sentence.strip(),
                    'entity': primary_entity,
                    'category': 'general',
                    'source_snippet': sentence[:100]
                })

        return facts[:3]  # Max 3 facts per sentence

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity names from text."""
        stop_words = {
            'the', 'a', 'an', 'to', 'in', 'on', 'at', 'for', 'of',
            'and', 'or', 'but', 'is', 'was', 'are', 'were', 'been',
            'has', 'had', 'have', 'did', 'does', 'do', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that',
            'with', 'from', 'about', 'not', 'also', 'just', 'very',
            'really', 'context', 'conversation', 'today', 'yesterday',
            'recently', 'actually', 'well', 'yeah', 'sure', 'okay',
            'hey', 'hello', 'thanks', 'thank', 'please', 'sorry',
            'event', 'chunk', 'speaker', 'user', 'assistant',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'during', 'after', 'before',
            # Pronouns
            'she', 'he', 'her', 'his', 'they', 'them', 'their',
            'it', 'its', 'we', 'our', 'you', 'your', 'my', 'mine',
        }
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        return list(dict.fromkeys(
            w for w in words if w.lower() not in stop_words
        ))
