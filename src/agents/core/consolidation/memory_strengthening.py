"""
Memory Strengthening Mixin
记忆强化模块 - 记忆巩固和关联增强
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ...base import BrainRegion

logger = logging.getLogger(__name__)


class MemoryStrengtheningMixin:
    """记忆强化Mixin - 处理记忆巩固和强化"""

    async def _consolidate_single_memory(self, memory_id: str, urgency: str = 'normal') -> Dict[str, Any]:
        """Consolidate a single memory from short-term to long-term"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': f'Memory {memory_id} not found'}

        # Evaluate consolidation factors
        consolidation_factors = self._evaluate_consolidation_factors(memory)

        if consolidation_factors['should_consolidate']:
            # Perform consolidation process
            old_level = memory.consolidation_level
            old_region = memory.brain_region

            # Update consolidation level (Synaptic -> Systems consolidation)
            memory.consolidation_level = min(3, memory.consolidation_level + 1)

            # Move to appropriate brain region based on consolidation level
            if memory.consolidation_level >= 2:
                memory.brain_region = BrainRegion.NEOCORTEX  # Systems consolidation

            # Update memory properties
            memory.importance = min(1.0, memory.importance + consolidation_factors['importance_boost'])
            memory.decay_rate = max(0.01, memory.decay_rate * 0.8)  # Reduce forgetting
            memory.last_consolidated = datetime.now()

            # Strengthen related associations
            strengthened_associations = await self._strengthen_associations(memory)

            # Save consolidated memory
            self.db_manager.save_memory(memory)
            self.memories_consolidated += 1

            return {
                'consolidated': True,
                'memory_id': memory_id,
                'old_level': old_level,
                'new_level': memory.consolidation_level,
                'old_region': old_region,
                'new_region': memory.brain_region,
                'factors': consolidation_factors,
                'strengthened_associations': strengthened_associations,
                'consolidation_type': urgency
            }
        else:
            return {
                'consolidated': False,
                'memory_id': memory_id,
                'reason': consolidation_factors.get('reason', 'Insufficient consolidation factors'),
                'factors': consolidation_factors
            }

    async def _immediate_consolidation(self, memory_ids: List[str] = None) -> Dict[str, Any]:
        """Execute immediate consolidation for urgent memories"""

        if not memory_ids:
            # Auto-select high priority memories
            if not self.db_manager:
                return {'error': 'Database manager not available'}

            # Load memories that need immediate consolidation
            all_memories = self.db_manager.load_memories_by_criteria()
            immediate_candidates = []

            for memory in all_memories:
                factors = self._evaluate_consolidation_factors(memory)
                if factors['consolidation_score'] > 0.8:
                    immediate_candidates.append(memory)

            # Sort by importance and take top candidates
            immediate_candidates.sort(key=lambda m: m.importance, reverse=True)
            memory_ids = [m.id for m in immediate_candidates[:5]]

        if not memory_ids:
            return {
                'immediate_consolidation_complete': True,
                'memories_processed': 0,
                'message': 'No memories require immediate consolidation'
            }

        consolidation_results = []

        for memory_id in memory_ids:
            result = await self._consolidate_single_memory(memory_id, urgency='immediate')
            consolidation_results.append(result)

        successful = len([r for r in consolidation_results if r.get('consolidated')])

        return {
            'immediate_consolidation_complete': True,
            'memories_processed': len(memory_ids),
            'memories_consolidated': successful,
            'success_rate': successful / len(memory_ids) if memory_ids else 0,
            'results': consolidation_results
        }

    async def _delayed_consolidation(self, delay_hours: int = 6) -> Dict[str, Any]:
        """Execute delayed consolidation after specified delay"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # Find memories that are ready for delayed consolidation
        all_memories = self.db_manager.load_memories_by_criteria()
        delayed_candidates = []

        cutoff_time = datetime.now() - timedelta(hours=delay_hours)

        for memory in all_memories:
            if memory.timestamp < cutoff_time and memory.consolidation_level < 2:
                factors = self._evaluate_consolidation_factors(memory)
                if 0.6 <= factors['consolidation_score'] <= 0.8:
                    delayed_candidates.append({
                        'memory': memory,
                        'score': factors['consolidation_score']
                    })

        if not delayed_candidates:
            return {
                'delayed_consolidation_complete': True,
                'memories_processed': 0,
                'message': f'No memories ready for delayed consolidation after {delay_hours} hours'
            }

        # Sort by consolidation score
        delayed_candidates.sort(key=lambda x: x['score'], reverse=True)

        consolidation_results = []

        for candidate in delayed_candidates[:10]:  # Process top 10
            result = await self._consolidate_single_memory(candidate['memory'].id, urgency='delayed')
            consolidation_results.append(result)

        successful = len([r for r in consolidation_results if r.get('consolidated')])

        return {
            'delayed_consolidation_complete': True,
            'memories_processed': len(consolidation_results),
            'memories_consolidated': successful,
            'success_rate': successful / len(consolidation_results) if consolidation_results else 0,
            'delay_hours': delay_hours,
            'results': consolidation_results
        }

    def _evaluate_consolidation_factors(self, memory) -> Dict[str, Any]:
        """Evaluate factors determining consolidation readiness"""

        factors = {
            'importance_factor': memory.importance,
            'access_factor': min(1.0, memory.access_frequency / 5.0),
            'emotion_factor': memory.emotion_intensity,
            'time_factor': 0.5,  # Base time factor
            'stress_factor': 0.1 if memory.stress_marker else 0.0,
            'consolidation_score': 0.0,
            'should_consolidate': False,
            'importance_boost': 0.0,
            'reason': ''
        }

        # Age factor (recent memories get boost, but need some time)
        age_hours = (datetime.now() - memory.timestamp).total_seconds() / 3600

        if 1 <= age_hours < 24:  # Sweet spot for consolidation
            factors['time_factor'] = 0.9
        elif 24 <= age_hours < 72:  # Still good
            factors['time_factor'] = 0.7
        elif age_hours < 1:  # Too recent
            factors['time_factor'] = 0.3
        else:  # Older memories
            factors['time_factor'] = 0.4

        # Access recency factor
        recency_factor = 0.5
        if memory.last_accessed:
            hours_since_access = (datetime.now() - memory.last_accessed).total_seconds() / 3600
            if hours_since_access < 1:
                recency_factor = 1.0
            elif hours_since_access < 24:
                recency_factor = 0.8
            elif hours_since_access < 72:
                recency_factor = 0.6

        # Calculate overall consolidation score
        factors['consolidation_score'] = (
            factors['importance_factor'] * 0.3 +
            factors['access_factor'] * 0.25 +
            factors['emotion_factor'] * 0.2 +
            factors['time_factor'] * 0.15 +
            recency_factor * 0.1
        )

        # Apply stress enhancement (stress hormones enhance consolidation)
        if factors['stress_factor'] > 0:
            factors['consolidation_score'] *= 1.2

        factors['should_consolidate'] = factors['consolidation_score'] >= self.consolidation_threshold

        if factors['should_consolidate']:
            factors['importance_boost'] = min(0.2, factors['consolidation_score'] - self.consolidation_threshold)
            factors['reason'] = 'Meets consolidation criteria'
        else:
            factors['reason'] = f"Score {factors['consolidation_score']:.2f} below threshold {self.consolidation_threshold}"

        return factors

    async def _strengthen_associations(self, memory) -> int:
        """Strengthen associations during consolidation"""

        if not self.db_manager:
            return 0

        strengthened = 0

        # Strengthen bidirectional associations
        for assoc_id in memory.associations[:5]:  # Top 5 associations
            assoc_memory = self.db_manager.load_memory(assoc_id)
            if assoc_memory:
                # Add reverse association if not exists
                if memory.id not in assoc_memory.associations:
                    assoc_memory.associations.append(memory.id)
                    self.db_manager.save_memory(assoc_memory)
                    strengthened += 1

        return strengthened

    async def _system_consolidation(self) -> Dict[str, Any]:
        """System-wide consolidation process (slow consolidation)"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        self.consolidation_cycles += 1

        # Find candidate memories for consolidation
        candidates = self.db_manager.load_memories_by_criteria(
            consolidation_level=1,  # Weakly consolidated
            min_importance=self.consolidation_threshold
        )

        # Also consider recently accessed memories
        recent_candidates = self.db_manager.load_memories_by_criteria(
            consolidation_level=0  # New memories
        )

        # Filter recent candidates by access pattern
        filtered_recent = [
            mem for mem in recent_candidates
            if mem.last_accessed and
            (datetime.now() - mem.last_accessed).days < 2 and
            mem.access_frequency > 1
        ]

        all_candidates = candidates + filtered_recent

        consolidated_memories = []
        failed_consolidations = []

        for memory in all_candidates:
            # Check consolidation criteria
            time_since_creation = datetime.now() - memory.timestamp
            time_since_access = datetime.now() - (memory.last_accessed or memory.timestamp)

            should_consolidate = (
                (time_since_access.days < 7 and memory.importance > 0.7) or
                (memory.access_frequency > 3) or
                (memory.emotion_intensity > 0.8) or  # Emotional enhancement
                (time_since_creation.days > 1 and memory.importance > 0.8)  # High importance memories
            )

            if should_consolidate:
                result = await self._consolidate_single_memory(memory.id)
                if result.get('consolidated'):
                    consolidated_memories.append(result)
                else:
                    failed_consolidations.append(result)

        # Perform memory replay for strengthening
        if consolidated_memories:
            replay_ids = [mem['memory_id'] for mem in consolidated_memories[:10]]  # Top 10
            replay_result = await self._memory_replay(replay_ids)
        else:
            replay_result = {'replayed_memories': 0}

        return {
            'system_consolidation_complete': True,
            'cycle_number': self.consolidation_cycles,
            'candidates_processed': len(all_candidates),
            'consolidated_count': len(consolidated_memories),
            'failed_count': len(failed_consolidations),
            'consolidation_rate': len(consolidated_memories) / len(all_candidates) if all_candidates else 0,
            'replay_result': replay_result,
            'consolidated_memories': [mem['memory_id'] for mem in consolidated_memories]
        }

    async def _evaluate_consolidation_candidates(self) -> Dict[str, Any]:
        """Evaluate which memories are ready for consolidation"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # Load memories that might need consolidation
        all_memories = self.db_manager.load_memories_by_criteria()

        candidates = {
            'immediate': [],    # Ready for immediate consolidation
            'delayed': [],      # Ready for delayed consolidation
            'sleep': [],        # Best consolidated during sleep
            'replay': []        # Need replay strengthening first
        }

        for memory in all_memories:
            if memory.consolidation_level >= 3:
                continue  # Already fully consolidated

            factors = self._evaluate_consolidation_factors(memory)

            if factors['consolidation_score'] > 0.8:
                candidates['immediate'].append({
                    'memory_id': memory.id,
                    'score': factors['consolidation_score'],
                    'factors': factors
                })
            elif factors['consolidation_score'] > 0.6:
                if memory.emotion_intensity > 0.6:
                    candidates['sleep'].append({
                        'memory_id': memory.id,
                        'score': factors['consolidation_score'],
                        'factors': factors
                    })
                else:
                    candidates['delayed'].append({
                        'memory_id': memory.id,
                        'score': factors['consolidation_score'],
                        'factors': factors
                    })
            elif factors['consolidation_score'] > 0.4:
                candidates['replay'].append({
                    'memory_id': memory.id,
                    'score': factors['consolidation_score'],
                    'factors': factors
                })

        # Sort each category by score
        for category in candidates.values():
            category.sort(key=lambda x: x['score'], reverse=True)

        return {
            'evaluation_complete': True,
            'total_memories_evaluated': len(all_memories),
            'candidates': candidates,
            'summary': {
                'immediate': len(candidates['immediate']),
                'delayed': len(candidates['delayed']),
                'sleep': len(candidates['sleep']),
                'replay': len(candidates['replay'])
            }
        }
