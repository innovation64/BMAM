"""
Context Compaction Agent
Implements conversation history compression and restart

Based on Anthropic's effective context engineering principles:
- Compaction: Compress long conversations into structured summaries
- Reinitiate: Restart conversation with summary, freeing context window
- Structured Note-Taking: Persist key information to external storage
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion

logger = logging.getLogger(__name__)


class ContextCompactionAgent(BrainAgent):
    """
    Context Compaction Agent

    Core functions:
    - Compress long conversation history into structured notes
    - Extract key decisions and unresolved questions
    - Clean up context window to avoid token waste
    """

    def __init__(self):
        super().__init__(
            agent_id="context_compaction",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""You compress conversation history into structured notes.
            Extract key facts, decisions, preferences, and open questions. Be concise."""
        )

        # Compaction history
        self.compaction_history = []
        self.max_history = 10

        # Compaction threshold (number of turns)
        self.compaction_threshold = 10  # Lowered to 10 for testing (can adjust to 15 in production)

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process compaction request"""
        action = message.content.get('action')

        if action == 'compact_conversation':
            return await self._compact_conversation(
                message.content['conversation_history']
            )
        elif action == 'should_compact':
            return self._should_compact(message.content['turn_count'])
        elif action == 'get_compaction_summary':
            return self._get_latest_summary()

        return {'error': f'Unknown compaction action: {action}'}

    async def _compact_conversation(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Compress conversation history into structured notes"""
        if len(conversation_history) < 3:
            return {
                'compacted': False,
                'reason': 'Too few turns to compact'
            }

        # Build compression prompt
        history_text = self._format_history_for_compression(conversation_history)

        compression_prompt = f"""Analyze the following conversation history and extract structured notes:

{history_text}

Output format:
1. Core facts: [List 3-5 key pieces of information]
2. User preferences: [If any]
3. Pending tasks: [Incomplete tasks]
4. Key decisions: [Important decisions made]
5. Open questions: [Unresolved questions]

Requirement: Be extremely concise, keep only the most important information."""

        try:
            summary = await self.call_llm(
                compression_prompt,
                max_tokens=400,
                temperature=0.3  # Low temperature for factuality
            )

            # Store compaction record
            compaction_record = {
                'timestamp': datetime.now().isoformat(),
                'turns_compressed': len(conversation_history),
                'summary': summary,
                'original_tokens': self._estimate_tokens(history_text),
                'compressed_tokens': self._estimate_tokens(summary)
            }

            self.compaction_history.append(compaction_record)
            if len(self.compaction_history) > self.max_history:
                self.compaction_history.pop(0)

            compression_ratio = compaction_record['compressed_tokens'] / max(compaction_record['original_tokens'], 1)

            logger.info(f"Compacted {len(conversation_history)} turns: "
                       f"{compaction_record['original_tokens']}->{compaction_record['compressed_tokens']} tokens "
                       f"(ratio: {compression_ratio:.2%})")

            return {
                'compacted': True,
                'summary': summary,
                'compression_ratio': compression_ratio,
                'turns_processed': len(conversation_history),
                'tokens_saved': compaction_record['original_tokens'] - compaction_record['compressed_tokens']
            }

        except Exception as e:
            logger.error(f"Compaction failed: {e}")
            return {
                'compacted': False,
                'error': str(e)
            }

    def _should_compact(self, turn_count: int) -> Dict[str, Any]:
        """Determine if compaction should be triggered"""
        should_compact = turn_count >= self.compaction_threshold

        return {
            'should_compact': should_compact,
            'turn_count': turn_count,
            'threshold': self.compaction_threshold,
            'reason': f'Turn count ({turn_count}) {"exceeds" if should_compact else "below"} threshold ({self.compaction_threshold})'
        }

    def _get_latest_summary(self) -> Dict[str, Any]:
        """Get the most recent compaction summary"""
        if not self.compaction_history:
            return {
                'has_summary': False,
                'summary': None
            }

        latest = self.compaction_history[-1]
        return {
            'has_summary': True,
            'summary': latest['summary'],
            'timestamp': latest['timestamp'],
            'compression_ratio': latest['compressed_tokens'] / max(latest['original_tokens'], 1)
        }

    def _format_history_for_compression(self, history: List[Dict]) -> str:
        """Format conversation history for compression"""
        formatted = []
        for turn in history[-20:]:  # Only process last 20 turns
            role = turn.get('role', 'unknown')
            content = turn.get('content', '')
            formatted.append(f"{role}: {content[:200]}")  # Truncate long messages

        return '\n'.join(formatted)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (Chinese by char, English by word)"""
        # Simplified estimation: Chinese 1 char ≈ 1.5 tokens, English 1 word ≈ 1 token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len([w for w in text.split() if w.isalpha()])
        return int(chinese_chars * 1.5 + english_words)

    def get_stats(self) -> Dict[str, Any]:
        """Get compaction statistics"""
        if not self.compaction_history:
            return {
                'total_compactions': 0,
                'avg_compression_ratio': 0,
                'total_tokens_saved': 0
            }

        total_saved = sum(
            r['original_tokens'] - r['compressed_tokens']
            for r in self.compaction_history
        )

        avg_ratio = sum(
            r['compressed_tokens'] / max(r['original_tokens'], 1)
            for r in self.compaction_history
        ) / len(self.compaction_history)

        return {
            'total_compactions': len(self.compaction_history),
            'avg_compression_ratio': f"{avg_ratio:.2%}",
            'total_tokens_saved': total_saved,
            'recent_compactions': self.compaction_history[-3:]
        }
