"""
Sleep Consolidation Mixin
睡眠巩固模块 - 模拟睡眠期间的记忆整合
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class SleepConsolidationMixin:
    """睡眠巩固Mixin - 模拟慢波睡眠期间的记忆巩固"""

    async def _sleep_consolidation(self) -> Dict[str, Any]:
        """Sleep-based consolidation process (simulates slow-wave sleep)"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # During "sleep", prioritize high-importance and emotional memories
        important_memories = self.db_manager.load_memories_by_criteria(min_importance=0.7)
        emotional_memories = self.db_manager.load_memories_by_criteria()  # Filter by emotion later

        # Filter emotional memories
        emotional_memories = [
            mem for mem in emotional_memories
            if mem.emotion_intensity > 0.6 and mem.emotion_tags
        ]

        # Combine and deduplicate
        sleep_candidates = {}
        for mem in important_memories + emotional_memories:
            if mem.consolidation_level < 3:
                sleep_candidates[mem.id] = mem

        sleep_consolidation_results = []

        # Process sleep consolidation (up to 20 memories per sleep cycle)
        for memory in list(sleep_candidates.values())[:20]:
            if memory.consolidation_level < 3:
                # Sleep consolidation provides stronger boost
                old_level = memory.consolidation_level
                memory.consolidation_level = min(3, memory.consolidation_level + 1)
                memory.decay_rate = max(0.01, memory.decay_rate * 0.7)  # Stronger protection
                memory.last_consolidated = datetime.now()

                # Sleep consolidation enhances memory integration
                memory.metadata['sleep_consolidated'] = True
                memory.metadata['sleep_consolidation_time'] = datetime.now().isoformat()

                self.db_manager.save_memory(memory)

                sleep_consolidation_results.append({
                    'memory_id': memory.id,
                    'old_level': old_level,
                    'new_level': memory.consolidation_level,
                    'memory_type': memory.memory_type,
                    'importance': memory.importance
                })

        # Simulate slow-wave sleep processes
        slow_waves = len(sleep_consolidation_results) // 3  # Approximate slow wave count

        # Clear some replay buffer during sleep (memory cleanup)
        cleared_replay_items = min(10, len(self.replay_buffer))
        self.replay_buffer = self.replay_buffer[cleared_replay_items:]

        return {
            'sleep_consolidation_complete': True,
            'memories_processed': len(sleep_candidates),
            'memories_consolidated': len(sleep_consolidation_results),
            'slow_wave_events': slow_waves,
            'replay_buffer_cleared': cleared_replay_items,
            'consolidation_results': sleep_consolidation_results
        }
