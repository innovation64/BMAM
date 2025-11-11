"""
False Memory Mixin
虚假记忆模块
"""

from typing import Dict, Any, List
from datetime import datetime
from ...base import BrainRegion


class FalseMemoryMixin:
    """虚假记忆Mixin"""

    async def _handle_false_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detected false memories with appropriate containment"""

        from ...memory.memory_item import MemoryItem

        # Create a marked false memory record
        false_memory = MemoryItem(
            content=memory_data['content'],
            memory_type='false_memory',
            brain_region=BrainRegion.HIPPOCAMPUS,
            source_reliability=0.0,  # Mark as completely unreliable
            importance=0.1,  # Minimal importance
            decay_rate=0.9,  # High decay rate for quick forgetting
            metadata={
                'false_memory': True,
                'detection_reason': memory_data.get('reason', 'Unknown'),
                'original_context': memory_data.get('context', {}),
                'detection_confidence': memory_data.get('confidence', 0.5),
                'containment_timestamp': datetime.now().isoformat()
            }
        )

        # Apply containment strategies
        containment_strategies = self._apply_containment_strategies(false_memory, memory_data)

        # Store with special isolation
        if self.db_manager:
            self.db_manager.save_memory(false_memory)

        self.false_memory_markers.append(false_memory.id)
        self.false_memories_handled += 1

        return {
            'false_memory_handled': True,
            'memory_id': false_memory.id,
            'containment_strategies': containment_strategies,
            'decay_rate': false_memory.decay_rate,
            'isolation_level': 'high',
            'monitoring_required': True
        }

    async def _check_memory_contamination(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Check for cross-contamination between memories"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        memories = []
        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                memories.append(memory)

        if len(memories) < 2:
            return {'error': 'Need at least 2 memories to check contamination'}

        contamination_results = []

        # Check pairwise contamination
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                mem1, mem2 = memories[i], memories[j]

                contamination_score = self._calculate_contamination_score(mem1, mem2)

                if contamination_score > 0.4:  # Contamination threshold
                    contamination_results.append({
                        'memory1_id': mem1.id,
                        'memory2_id': mem2.id,
                        'contamination_score': contamination_score,
                        'contamination_type': self._identify_contamination_type(mem1, mem2),
                        'recommended_action': self._get_contamination_action(contamination_score)
                    })

        return {
            'contamination_check_complete': True,
            'memories_checked': len(memories),
            'contaminations_found': len(contamination_results),
            'contamination_details': contamination_results,
            'overall_contamination_risk': len(contamination_results) / (len(memories) * (len(memories) - 1) / 2)
        }

    def _apply_containment_strategies(self, false_memory, memory_data: Dict) -> List[str]:
        """Apply containment strategies for false memories"""
        strategies = []

        # Isolation strategy
        false_memory.metadata['isolated'] = True
        strategies.append('isolation')

        # Rapid decay strategy
        false_memory.decay_rate = 0.95
        strategies.append('rapid_decay')

        # Warning tags
        false_memory.context_tags.append('false_memory_warning')
        strategies.append('warning_tags')

        # Prevent association formation
        false_memory.metadata['association_blocked'] = True
        strategies.append('association_blocking')

        return strategies

    def _calculate_contamination_score(self, mem1, mem2) -> float:
        """Calculate contamination score between two memories"""
        score = 0.0

        # Temporal proximity
        if mem1.timestamp and mem2.timestamp:
            time_diff = abs((mem1.timestamp - mem2.timestamp).total_seconds())
            if time_diff < 3600:  # Within an hour
                score += 0.4
            elif time_diff < 86400:  # Within a day
                score += 0.2

        # Content similarity (simple heuristic)
        common_words = set(mem1.content.lower().split()) & set(mem2.content.lower().split())
        if common_words:
            score += min(0.3, len(common_words) * 0.05)

        # Context overlap
        common_context = set(mem1.context_tags) & set(mem2.context_tags)
        if common_context:
            score += min(0.2, len(common_context) * 0.1)

        # Emotional state similarity
        if mem1.emotion_tags and mem2.emotion_tags:
            common_emotions = set(mem1.emotion_tags) & set(mem2.emotion_tags)
            if common_emotions:
                score += 0.1

        return score

    def _identify_contamination_type(self, mem1, mem2) -> str:
        """Identify type of contamination between memories"""
        # Simple heuristics for contamination type
        time_diff = abs((mem1.timestamp - mem2.timestamp).total_seconds()) if mem1.timestamp and mem2.timestamp else float('inf')

        if time_diff < 3600:
            return 'temporal_proximity'
        elif set(mem1.context_tags) & set(mem2.context_tags):
            return 'contextual_overlap'
        elif set(mem1.emotion_tags) & set(mem2.emotion_tags):
            return 'emotional_similarity'
        else:
            return 'content_similarity'

    def _get_contamination_action(self, score: float) -> str:
        """Get recommended action for contamination"""
        if score > 0.7:
            return 'Isolate memories to prevent further contamination'
        elif score > 0.5:
            return 'Monitor for contamination effects'
        else:
            return 'Low contamination risk - continue monitoring'
