"""
Rehearsal Consolidation Mixin
复述巩固模块 - 记忆重播和强化
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class RehearsalMixin:
    """复述巩固Mixin - 处理记忆重播和间隔复述"""

    async def _memory_replay(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Memory replay for consolidation strengthening (simulates hippocampal replay)"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        replay_results = []

        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                # Simulate memory replay strengthening
                replay_strength = self._calculate_replay_strength(memory)

                # Update memory based on replay
                if replay_strength > 0.5:
                    memory.consolidation_level = min(3, memory.consolidation_level + 1)
                    memory.importance = min(1.0, memory.importance + 0.1)

                # Update access patterns to reflect replay
                memory.access_frequency += 1
                memory.last_accessed = datetime.now()
                memory.metadata['last_replay'] = datetime.now().isoformat()

                # Add to replay buffer for future offline processing
                if len(self.replay_buffer) < self.replay_capacity:
                    self.replay_buffer.append({
                        'memory_id': memory_id,
                        'content': memory.content,
                        'replay_strength': replay_strength,
                        'timestamp': datetime.now().isoformat()
                    })

                self.db_manager.save_memory(memory)
                self.replay_events += 1

                replay_results.append({
                    'memory_id': memory_id,
                    'replay_strength': replay_strength,
                    'new_consolidation_level': memory.consolidation_level,
                    'importance_boost': 0.1 if replay_strength > 0.5 else 0
                })

        # Simulate sharp-wave ripple events (SWRs) during replay
        swr_events = self._simulate_sharp_wave_ripples(len(replay_results))

        return {
            'memory_replay_complete': True,
            'replayed_memories': len(replay_results),
            'results': replay_results,
            'replay_buffer_size': len(self.replay_buffer),
            'swr_events': swr_events,
            'total_replay_events': self.replay_events
        }

    async def _replay_consolidation(self, replay_count: int = 3) -> Dict[str, Any]:
        """Execute memory replay consolidation"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # Select memories from replay buffer or find candidates
        if self.replay_buffer:
            replay_memories = self.replay_buffer[:10]  # Take first 10 from buffer
        else:
            # Find memories that would benefit from replay
            all_memories = self.db_manager.load_memories_by_criteria()
            replay_candidates = []

            for memory in all_memories:
                if memory.consolidation_level < 3:  # Not fully consolidated
                    replay_strength = self._calculate_replay_strength(memory)
                    if replay_strength > 0.6:
                        replay_candidates.append({
                            'memory': memory,
                            'strength': replay_strength
                        })

            # Sort by replay strength and take top candidates
            replay_candidates.sort(key=lambda x: x['strength'], reverse=True)
            replay_memories = [c['memory'] for c in replay_candidates[:10]]

        if not replay_memories:
            return {
                'replay_consolidation_complete': True,
                'memories_processed': 0,
                'message': 'No suitable memories found for replay consolidation'
            }

        replay_results = []

        for memory in replay_memories:
            for replay_cycle in range(replay_count):
                # Simulate replay process
                replay_strength = self._calculate_replay_strength(memory)

                # Strengthen memory during replay
                if replay_strength > 0.7:
                    memory.consolidation_level = min(3, memory.consolidation_level + 0.1)
                    memory.importance = min(1.0, memory.importance + 0.05)

                replay_results.append({
                    'memory_id': memory.id,
                    'replay_cycle': replay_cycle + 1,
                    'replay_strength': replay_strength,
                    'consolidation_boost': 0.1 if replay_strength > 0.7 else 0.05
                })

        # Save updated memories
        for memory in replay_memories:
            if self.db_manager:
                self.db_manager.save_memory(memory)

        # Simulate sharp-wave ripples during replay
        swr_events = self._simulate_sharp_wave_ripples(len(replay_memories))

        self.replay_events += 1

        return {
            'replay_consolidation_complete': True,
            'memories_replayed': len(replay_memories),
            'replay_cycles': replay_count,
            'total_replay_events': len(replay_results),
            'sharp_wave_ripples': swr_events,
            'replay_buffer_updated': True,
            'results': replay_results
        }

    def _calculate_replay_strength(self, memory) -> float:
        """Calculate memory replay strength"""

        # Base replay strength
        strength = 0.5

        # Recent memories replay stronger
        age_hours = (datetime.now() - memory.timestamp).total_seconds() / 3600
        if age_hours < 24:
            strength += 0.3
        elif age_hours < 72:
            strength += 0.2

        # Important memories replay stronger
        strength += memory.importance * 0.3

        # Emotional memories replay stronger
        strength += memory.emotion_intensity * 0.2

        # Recently accessed memories replay stronger
        if memory.last_accessed:
            hours_since_access = (datetime.now() - memory.last_accessed).total_seconds() / 3600
            if hours_since_access < 1:
                strength += 0.2

        return min(1.0, strength)

    def _simulate_sharp_wave_ripples(self, memory_count: int) -> int:
        """Simulate sharp-wave ripple events during replay"""

        # SWRs occur roughly every 1-3 memories during replay
        base_swr_rate = 0.4  # 40% chance per memory

        swr_events = 0
        for _ in range(memory_count):
            import random
            if random.random() < base_swr_rate:
                swr_events += 1

        return swr_events
