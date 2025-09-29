"""
Consolidation Agent
记忆巩固智能体 - 对应海马体-新皮层回路
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class ConsolidationAgent(BrainAgent):
    """
    Consolidation Agent (Hippocampus-Neocortex Circuit)
    
    核心概念：巩固
    对应脑区：海马体-新皮层回路
    主要功能：短期转长期，记忆重播，系统巩固
    """
    
    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="consolidation",
            brain_region=BrainRegion.HIPPOCAMPUS,
            system_prompt="""You are the memory consolidation system of a brain-inspired AI.
            Your role is to:
            1. Transform memories from short-term to long-term storage
            2. Perform memory replay for strengthening connections
            3. Execute system consolidation processes
            4. Manage sleep-like consolidation periods
            5. Evaluate and prioritize memories for consolidation"""
        )
        
        # External services
        self.db_manager = db_manager
        
        # Consolidation parameters
        self.consolidation_threshold = 0.6
        self.replay_buffer = []
        self.replay_capacity = 50
        
        # Consolidation strategies
        self.strategies = {
            'immediate': self._immediate_consolidation,
            'delayed': self._delayed_consolidation,
            'sleep': self._sleep_consolidation,
            'replay': self._replay_consolidation
        }
        
        # Statistics
        self.consolidation_cycles = 0
        self.memories_consolidated = 0
        self.replay_events = 0
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process consolidation requests"""
        action = message.content.get('action')

        if action == 'consolidate_memory':
            return await self._consolidate_single_memory(message.content['memory_id'])
        elif action == 'system_consolidation':
            return await self._system_consolidation()
        elif action == 'memory_replay':
            return await self._memory_replay(message.content.get('memory_ids', []))
        elif action == 'sleep_consolidation':
            return await self._sleep_consolidation()
        elif action == 'evaluate_consolidation':
            return await self._evaluate_consolidation_candidates()
        elif action == 'batch_consolidation':
            return await self._batch_consolidation(message.content.get('batch_size', 10))
        elif action == 'process_chunked_queue':
            return await self._process_chunked_text_queue()
        elif action == 'consolidate_preference':
            return await self._consolidate_preference(message.content)

        return {'error': f'Unknown consolidation action: {action}'}
    
    async def _consolidate_single_memory(self, memory_id: str) -> Dict[str, Any]:
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
                'consolidation_type': 'single'
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
    
    async def _batch_consolidation(self, batch_size: int = 10) -> Dict[str, Any]:
        """Process a batch of memories for consolidation"""
        
        # First evaluate candidates
        evaluation = await self._evaluate_consolidation_candidates()
        
        if 'error' in evaluation:
            return evaluation
        
        # Process immediate candidates first
        immediate_candidates = evaluation['candidates']['immediate'][:batch_size]
        
        batch_results = []
        
        for candidate in immediate_candidates:
            result = await self._consolidate_single_memory(candidate['memory_id'])
            batch_results.append(result)
        
        # If we have room, process delayed candidates
        remaining_capacity = batch_size - len(batch_results)
        if remaining_capacity > 0:
            delayed_candidates = evaluation['candidates']['delayed'][:remaining_capacity]
            
            for candidate in delayed_candidates:
                result = await self._consolidate_single_memory(candidate['memory_id'])
                batch_results.append(result)
        
        successful_consolidations = [r for r in batch_results if r.get('consolidated')]
        
        return {
            'batch_consolidation_complete': True,
            'batch_size': batch_size,
            'processed': len(batch_results),
            'successful': len(successful_consolidations),
            'success_rate': len(successful_consolidations) / len(batch_results) if batch_results else 0,
            'results': batch_results
        }
    
    def _evaluate_consolidation_factors(self, memory: MemoryItem) -> Dict[str, Any]:
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
    
    def _calculate_replay_strength(self, memory: MemoryItem) -> float:
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
    
    async def _strengthen_associations(self, memory: MemoryItem) -> int:
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

    async def _process_chunked_text_queue(self) -> Dict[str, Any]:
        """Process queued chunked text segments for consolidation - now handles ALL segments"""
        from ...agents.agent_buffer_system import agent_buffer_system
        from ...memory.memory_system import memory_system

        try:
            # Read buffer content
            buffer_content = await agent_buffer_system.read_buffer('consolidation')
            chunked_queue = buffer_content.get('chunked_text_queue', [])

            if not chunked_queue:
                return {'processed': 0, 'message': 'No chunked text in queue'}

            processed_batches = 0
            stored_segments = 0
            processed_segments = 0

            # Process each entry (now potentially batched)
            for entry in chunked_queue:
                try:
                    overview = entry.get('overview', {})
                    segments = entry.get('segments', [])
                    entry_type = entry.get('type', 'chunked_text')

                    # Determine storage worthiness
                    storage_priority = overview.get('storage_priority', 'low')
                    batch_number = entry.get('batch_number', 1)
                    total_segments = entry.get('total_segments', len(segments))

                    logger.debug(f"Processing {entry_type} batch {batch_number} with {len(segments)} segments")

                    # Store segments based on priority and batch position
                    should_store = self._should_store_batch(storage_priority, batch_number, total_segments)

                    if should_store:
                        # Store ALL segments in this batch (no truncation)
                        for seg in segments:
                            try:
                                # Adjust importance based on segment position and batch
                                importance = self._calculate_segment_importance(
                                    seg, storage_priority, batch_number, total_segments
                                )

                                memory_id = await memory_system.store_memory(
                                    content=seg['summary'],
                                    memory_type='episodic',
                                    importance=importance,
                                    context_tags=['chunked_text', 'consolidation_processed', 'complete_set'],
                                    metadata={
                                        'segment_index': seg['index'],
                                        'batch_number': batch_number,
                                        'total_segments': total_segments,
                                        'parent_theme': overview.get('theme', ''),
                                        'keywords': seg.get('keywords', []),
                                        'processing_method': seg.get('processing_method', 'local'),
                                        'storage_priority': storage_priority,
                                        'consolidated_at': datetime.now().isoformat()
                                    }
                                )

                                if memory_id:
                                    stored_segments += 1

                                processed_segments += 1

                            except Exception as seg_error:
                                logger.warning(f"Failed to store segment {seg.get('index', '?')}: {seg_error}")
                                processed_segments += 1  # Count as processed even if failed
                                continue
                    else:
                        # Even if not storing, count as processed
                        processed_segments += len(segments)
                        logger.debug(f"Skipped storing batch {batch_number} (priority: {storage_priority})")

                    processed_batches += 1

                except Exception as entry_error:
                    logger.warning(f"Failed to process chunked text entry: {entry_error}")
                    continue

            # Clear the processed queue
            await agent_buffer_system.write_buffer(
                'consolidation',
                'chunked_text_queue',
                []
            )

            logger.info(f"Processed {processed_batches} batches ({processed_segments} segments total), stored {stored_segments} segments")

            return {
                'processed_batches': processed_batches,
                'processed_segments': processed_segments,
                'stored_segments': stored_segments,
                'storage_rate': stored_segments / processed_segments if processed_segments > 0 else 0,
                'status': 'completed'
            }

        except Exception as e:
            logger.error(f"Failed to process chunked text queue: {e}")
            return {'error': str(e)}

    def _should_store_batch(self, storage_priority: str, batch_number: int, total_segments: int) -> bool:
        """Determine if a batch should be stored based on priority and position"""
        if storage_priority == 'high':
            return True  # Store all batches for high priority
        elif storage_priority == 'medium':
            # Store first 3 batches (up to 15 segments)
            return batch_number <= 3
        else:  # low priority
            # Store only first batch (up to 5 segments)
            return batch_number == 1

    def _calculate_segment_importance(self, segment: Dict, priority: str, batch_number: int, total_segments: int) -> float:
        """Calculate importance score for a segment based on position and priority"""
        base_importance = {
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }.get(priority, 0.3)

        # Reduce importance for later batches
        batch_penalty = (batch_number - 1) * 0.1
        importance = max(0.2, base_importance - batch_penalty)

        # First few segments get slight boost
        segment_index = segment.get('index', 0)
        if segment_index < 3:
            importance += 0.1

        return min(1.0, importance)

    async def _consolidate_preference(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate user preference information"""
        try:
            # Apply preference boost
            importance_boost = content.get('importance_boost', 0.2)

            # This is primarily a preference consolidation marker
            # The actual preference storage happens in background in brain_coordinator

            return {
                'preference_consolidation_triggered': True,
                'importance_boost_applied': importance_boost,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to consolidate preference: {e}")
            return {'error': str(e)}