"""
Forgetting Agent
遗忘智能体 - 对应前额叶抑制网络
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class ForgettingAgent(BrainAgent):
    """
    Forgetting Agent (Prefrontal Inhibition Network)
    
    核心概念：遗忘
    对应脑区：前额叶抑制网络
    主要功能：主动遗忘，记忆清理，干扰消除
    """
    
    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="forgetting",
            brain_region=BrainRegion.INHIBITION,
            system_prompt="""You are the forgetting and memory management system of a brain-inspired AI.
            Your role is to:
            1. Manage memory decay through passive forgetting processes
            2. Perform active forgetting and memory suppression when needed
            3. Resolve interference between conflicting memories
            4. Maintain optimal memory capacity through selective pruning
            5. Implement adaptive forgetting strategies based on memory value"""
        )
        
        # External services
        self.db_manager = db_manager
        
        # Forgetting parameters
        self.forgetting_threshold = 0.2  # Memories below this importance are candidates for forgetting
        self.capacity_limit = 10000  # Maximum active memories (soft limit)
        self.interference_threshold = 0.7  # Threshold for detecting memory interference
        
        # Forgetting strategies
        self.forgetting_strategies = {
            'passive_decay': self._apply_ebbinghaus_forgetting,
            'active_suppression': self._active_memory_suppression,
            'interference_resolution': self._resolve_memory_interference,
            'capacity_management': self._manage_memory_capacity,
            'contextual_forgetting': self._contextual_forgetting,
            'emotional_suppression': self._emotional_memory_suppression
        }
        
        # Forgetting curves and parameters
        self.ebbinghaus_params = {
            'initial_strength': 1.0,
            'decay_constant': 0.1,
            'time_constant': 24.0  # hours
        }
        
        # Statistics
        self.memories_forgotten = 0
        self.decay_applications = 0
        self.active_suppressions = 0
        self.interferences_resolved = 0
        
        # Suppression history (to avoid over-suppression)
        self.suppression_history = {}
        
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process forgetting and memory management requests"""
        action = message.content.get('action')
        
        if action == 'passive_decay':
            return await self._apply_passive_decay()
        elif action == 'active_forgetting':
            return await self._active_forgetting(message.content['memory_ids'])
        elif action == 'interference_resolution':
            return await self._resolve_interference(message.content['conflicting_memories'])
        elif action == 'capacity_management':
            return await self._manage_memory_capacity()
        elif action == 'selective_forgetting':
            return await self._selective_forgetting(message.content['criteria'])
        elif action == 'forgetting_analysis':
            return await self._analyze_forgetting_patterns()
        elif action == 'memory_pruning':
            return await self._intelligent_memory_pruning()
        elif action == 'trauma_suppression':
            return await self._suppress_traumatic_memories(message.content.get('memory_ids', []))
        
        return {'error': f'Unknown forgetting action: {action}'}
    
    async def _apply_passive_decay(self) -> Dict[str, Any]:
        """Apply passive forgetting through time-based decay (Ebbinghaus curve)"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memories = self.db_manager.load_memories_by_criteria()
        
        decay_results = {
            'total_processed': len(memories),
            'significant_decay': 0,
            'marked_for_forgetting': 0,
            'memories_deactivated': 0,
            'average_retention': 0.0
        }
        
        retention_scores = []
        
        for memory in memories:
            # Calculate time elapsed since last access or creation
            last_time = memory.last_accessed or memory.timestamp
            time_elapsed_hours = (datetime.now() - last_time).total_seconds() / 3600
            
            # Apply Ebbinghaus forgetting curve
            retention = self._calculate_retention_score(memory, time_elapsed_hours)
            retention_scores.append(retention)
            
            # Apply decay to memory importance
            old_importance = memory.importance
            new_importance = old_importance * retention
            
            # Apply additional decay factors
            decay_factors = self._calculate_decay_factors(memory)
            final_importance = new_importance * decay_factors['compound_factor']
            
            memory.importance = max(0.01, final_importance)  # Minimum importance
            
            # Track significant decay
            if abs(old_importance - memory.importance) > 0.2:
                decay_results['significant_decay'] += 1
            
            # Mark for forgetting if below threshold
            if memory.importance < self.forgetting_threshold:
                memory.metadata['marked_for_forgetting'] = True
                memory.metadata['forgetting_reason'] = 'passive_decay'
                memory.metadata['decay_timestamp'] = datetime.now().isoformat()
                decay_results['marked_for_forgetting'] += 1
                
                # Deactivate if critically low and not protected
                if (memory.importance < 0.05 and 
                    memory.consolidation_level < 2 and 
                    not memory.metadata.get('protected', False)):
                    
                    memory.metadata['deactivated'] = True
                    decay_results['memories_deactivated'] += 1
                    self.memories_forgotten += 1
            
            # Save updated memory
            self.db_manager.save_memory(memory)
        
        # Calculate statistics
        decay_results['average_retention'] = sum(retention_scores) / len(retention_scores) if retention_scores else 0
        decay_results['forgetting_rate'] = decay_results['marked_for_forgetting'] / len(memories) if memories else 0
        
        self.decay_applications += 1
        
        return {
            'passive_decay_complete': True,
            'decay_cycle': self.decay_applications,
            'results': decay_results,
            'ebbinghaus_params': self.ebbinghaus_params
        }
    
    async def _apply_ebbinghaus_forgetting(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Apply Ebbinghaus forgetting curve to decay memories naturally"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Load memories that might be affected by decay
        all_memories = self.db_manager.load_memories_by_criteria()
        
        if not all_memories:
            return {
                'ebbinghaus_forgetting_complete': True,
                'memories_processed': 0,
                'message': 'No memories to process for decay'
            }
        
        decay_results = []
        
        for memory in all_memories:
            # Calculate time since creation and last access
            hours_since_creation = (datetime.now() - memory.timestamp).total_seconds() / 3600
            hours_since_access = 0
            if memory.last_accessed:
                hours_since_access = (datetime.now() - memory.last_accessed).total_seconds() / 3600
            
            # Apply Ebbinghaus forgetting curve: R = e^(-t/S)
            # R = retention, t = time, S = strength factor
            import math
            strength_factor = max(1.0, memory.importance * 10)  # Higher importance = slower decay
            
            # Calculate retention based on creation time
            creation_retention = math.exp(-hours_since_creation / strength_factor)
            
            # Calculate retention based on last access (resets the curve)
            access_retention = 1.0
            if memory.last_accessed:
                access_retention = math.exp(-hours_since_access / strength_factor)
            
            # Take the maximum (last access resets forgetting)
            current_retention = max(creation_retention, access_retention)
            
            # Apply forgetting if retention is below current importance
            original_importance = memory.importance
            if current_retention < memory.importance:
                # Reduce importance based on forgetting curve
                new_importance = max(0.0, memory.importance * current_retention)
                memory.importance = new_importance
                
                # Increase decay rate
                memory.decay_rate = min(1.0, memory.decay_rate + 0.1)
                
                # Save updated memory
                self.db_manager.save_memory(memory)
                
                decay_results.append({
                    'memory_id': memory.id,
                    'original_importance': original_importance,
                    'new_importance': new_importance,
                    'retention_rate': current_retention,
                    'hours_since_creation': hours_since_creation,
                    'hours_since_access': hours_since_access,
                    'decayed': True
                })
            else:
                decay_results.append({
                    'memory_id': memory.id,
                    'importance': memory.importance,
                    'retention_rate': current_retention,
                    'decayed': False
                })
        
        # Count how many memories were significantly decayed
        decayed_count = len([r for r in decay_results if r.get('decayed', False)])
        
        return {
            'ebbinghaus_forgetting_complete': True,
            'memories_processed': len(all_memories),
            'memories_decayed': decayed_count,
            'decay_rate': decayed_count / len(all_memories) if all_memories else 0,
            'time_window_hours': time_window_hours,
            'results': decay_results
        }
    
    async def _active_memory_suppression(self, suppression_targets: List[str]) -> Dict[str, Any]:
        """Actively suppress specific memories or memory patterns"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        if not suppression_targets:
            return {
                'active_suppression_complete': True,
                'memories_processed': 0,
                'message': 'No suppression targets specified'
            }
        
        suppression_results = []
        
        for target in suppression_targets:
            # Load memory by ID or find by content pattern
            if target.startswith('mem_'):
                # Direct memory ID
                memory = self.db_manager.load_memory(target)
                if memory:
                    memories_to_suppress = [memory]
                else:
                    memories_to_suppress = []
            else:
                # Content pattern - find matching memories
                all_memories = self.db_manager.load_memories_by_criteria()
                memories_to_suppress = [
                    m for m in all_memories 
                    if target.lower() in m.content.lower()
                ]
            
            for memory in memories_to_suppress:
                # Apply suppression by reducing importance and access
                original_importance = memory.importance
                memory.importance = max(0.1, memory.importance * 0.3)  # Significant reduction
                memory.decay_rate = min(1.0, memory.decay_rate + 0.3)  # Increase decay
                
                # Mark as suppressed
                if 'suppressed' not in memory.tags:
                    memory.tags.append('suppressed')
                
                # Reduce consolidation level
                memory.consolidation_level = max(0, memory.consolidation_level - 1)
                
                # Save updated memory
                self.db_manager.save_memory(memory)
                
                suppression_results.append({
                    'memory_id': memory.id,
                    'target': target,
                    'original_importance': original_importance,
                    'new_importance': memory.importance,
                    'suppression_strength': (original_importance - memory.importance) / original_importance if original_importance > 0 else 0,
                    'suppressed': True
                })
        
        successful_suppressions = len([r for r in suppression_results if r.get('suppressed', False)])
        
        return {
            'active_suppression_complete': True,
            'targets_processed': len(suppression_targets),
            'memories_suppressed': successful_suppressions,
            'suppression_effectiveness': successful_suppressions / len(suppression_targets) if suppression_targets else 0,
            'results': suppression_results
        }
    
    async def _resolve_memory_interference(self, similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """Resolve interference between similar memories"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Load all memories for interference analysis
        all_memories = self.db_manager.load_memories_by_criteria()
        
        if len(all_memories) < 2:
            return {
                'interference_resolution_complete': True,
                'memories_processed': len(all_memories),
                'message': 'Insufficient memories for interference analysis'
            }
        
        interference_pairs = []
        resolution_results = []
        
        # Find interfering memory pairs
        for i, memory1 in enumerate(all_memories):
            for memory2 in all_memories[i+1:]:
                similarity = self._calculate_memory_similarity(memory1, memory2)
                
                if similarity > similarity_threshold:
                    interference_pairs.append({
                        'memory1': memory1,
                        'memory2': memory2,
                        'similarity': similarity,
                        'interference_strength': similarity * min(memory1.importance, memory2.importance)
                    })
        
        # Resolve interference for each pair
        for pair in interference_pairs:
            memory1, memory2 = pair['memory1'], pair['memory2']
            
            # Determine which memory to weaken
            if memory1.importance > memory2.importance:
                stronger_memory, weaker_memory = memory1, memory2
            elif memory2.importance > memory1.importance:
                stronger_memory, weaker_memory = memory2, memory1
            else:
                # Equal importance - weaken the older one
                if memory1.timestamp < memory2.timestamp:
                    stronger_memory, weaker_memory = memory2, memory1
                else:
                    stronger_memory, weaker_memory = memory1, memory2
            
            # Apply interference resolution
            original_weak_importance = weaker_memory.importance
            
            # Weaken the less important/older memory
            interference_factor = pair['similarity'] * 0.5
            weaker_memory.importance *= (1.0 - interference_factor)
            weaker_memory.decay_rate = min(1.0, weaker_memory.decay_rate + interference_factor * 0.3)
            
            # Slightly strengthen the dominant memory
            stronger_memory.importance = min(1.0, stronger_memory.importance * (1.0 + interference_factor * 0.1))
            
            # Save updated memories
            self.db_manager.save_memory(weaker_memory)
            self.db_manager.save_memory(stronger_memory)
            
            resolution_results.append({
                'stronger_memory_id': stronger_memory.id,
                'weaker_memory_id': weaker_memory.id,
                'similarity': pair['similarity'],
                'interference_strength': pair['interference_strength'],
                'weaker_original_importance': original_weak_importance,
                'weaker_new_importance': weaker_memory.importance,
                'importance_reduction': original_weak_importance - weaker_memory.importance
            })
        
        return {
            'interference_resolution_complete': True,
            'memories_analyzed': len(all_memories),
            'interference_pairs_found': len(interference_pairs),
            'interference_pairs_resolved': len(resolution_results),
            'similarity_threshold': similarity_threshold,
            'results': resolution_results
        }
    
    async def _manage_memory_capacity(self, target_capacity: int = None) -> Dict[str, Any]:
        """Manage memory capacity by removing low-importance memories"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        if target_capacity is None:
            target_capacity = self.capacity_limit
        
        # Load all memories and sort by importance
        all_memories = self.db_manager.load_memories_by_criteria()
        
        if len(all_memories) <= target_capacity:
            return {
                'capacity_management_complete': True,
                'current_count': len(all_memories),
                'target_capacity': target_capacity,
                'message': 'Memory count within capacity limits'
            }
        
        # Sort memories by composite score (importance, access frequency, age)
        scored_memories = []
        for memory in all_memories:
            # Calculate composite retention score
            age_penalty = min(0.3, (datetime.now() - memory.timestamp).days * 0.01)
            access_boost = min(0.3, memory.access_frequency * 0.05)
            consolidation_boost = memory.consolidation_level * 0.1
            
            retention_score = (
                memory.importance * 0.4 +
                access_boost +
                consolidation_boost -
                age_penalty -
                memory.decay_rate * 0.2
            )
            
            scored_memories.append({
                'memory': memory,
                'retention_score': retention_score
            })
        
        # Sort by retention score (highest first)
        scored_memories.sort(key=lambda x: x['retention_score'], reverse=True)
        
        # Keep top memories, remove the rest
        memories_to_keep = scored_memories[:target_capacity]
        memories_to_remove = scored_memories[target_capacity:]
        
        removal_results = []
        
        for item in memories_to_remove:
            memory = item['memory']
            
            # Mark for removal (could implement soft deletion)
            original_importance = memory.importance
            memory.importance = 0.0
            memory.decay_rate = 1.0
            if 'forgotten' not in memory.tags:
                memory.tags.append('forgotten')
            
            # Save updated memory (or implement actual deletion)
            self.db_manager.save_memory(memory)
            
            removal_results.append({
                'memory_id': memory.id,
                'retention_score': item['retention_score'],
                'original_importance': original_importance,
                'removal_reason': 'capacity_management'
            })
        
        return {
            'capacity_management_complete': True,
            'original_count': len(all_memories),
            'target_capacity': target_capacity,
            'memories_kept': len(memories_to_keep),
            'memories_removed': len(memories_to_remove),
            'removal_results': removal_results
        }
    
    async def _contextual_forgetting(self, context_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Forget memories based on contextual criteria"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Load memories and filter by context
        all_memories = self.db_manager.load_memories_by_criteria()
        contextual_candidates = []
        
        for memory in all_memories:
            should_forget = False
            
            # Check various contextual criteria
            if 'time_range' in context_criteria:
                time_range = context_criteria['time_range']
                if time_range['start'] <= memory.timestamp <= time_range['end']:
                    should_forget = True
            
            if 'emotion_state' in context_criteria:
                target_emotion = context_criteria['emotion_state']
                if memory.emotional_context.get('dominant_emotion') == target_emotion:
                    should_forget = True
            
            if 'memory_type' in context_criteria:
                if memory.memory_type in context_criteria['memory_type']:
                    should_forget = True
            
            if 'importance_below' in context_criteria:
                if memory.importance < context_criteria['importance_below']:
                    should_forget = True
            
            if should_forget:
                contextual_candidates.append(memory)
        
        # Apply contextual forgetting
        forgetting_results = []
        
        for memory in contextual_candidates:
            original_importance = memory.importance
            
            # Apply forgetting based on context strength
            context_strength = context_criteria.get('forgetting_strength', 0.5)
            memory.importance *= (1.0 - context_strength)
            memory.decay_rate = min(1.0, memory.decay_rate + context_strength * 0.4)
            
            # Add contextual tag
            if 'contextual_forgotten' not in memory.tags:
                memory.tags.append('contextual_forgotten')
            
            # Save updated memory
            self.db_manager.save_memory(memory)
            
            forgetting_results.append({
                'memory_id': memory.id,
                'original_importance': original_importance,
                'new_importance': memory.importance,
                'context_strength': context_strength,
                'context_match': True
            })
        
        return {
            'contextual_forgetting_complete': True,
            'total_memories': len(all_memories),
            'contextual_candidates': len(contextual_candidates),
            'memories_forgotten': len(forgetting_results),
            'context_criteria': context_criteria,
            'results': forgetting_results
        }
    
    async def _emotional_memory_suppression(self, emotion_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Suppress memories based on emotional criteria"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Default to suppressing negative high-intensity emotions
        target_emotions = emotion_criteria.get('target_emotions', ['anxiety', 'sadness', 'anger'])
        intensity_threshold = emotion_criteria.get('intensity_threshold', 0.7)
        suppression_strength = emotion_criteria.get('suppression_strength', 0.6)
        
        # Load memories and find emotional candidates
        all_memories = self.db_manager.load_memories_by_criteria()
        emotional_candidates = []
        
        for memory in all_memories:
            if memory.emotion_intensity >= intensity_threshold:
                dominant_emotion = memory.emotional_context.get('dominant_emotion', 'neutral')
                if dominant_emotion in target_emotions:
                    emotional_candidates.append(memory)
        
        if not emotional_candidates:
            return {
                'emotional_suppression_complete': True,
                'memories_processed': len(all_memories),
                'message': 'No memories meet emotional suppression criteria'
            }
        
        suppression_results = []
        
        for memory in emotional_candidates:
            original_importance = memory.importance
            original_emotion_intensity = memory.emotion_intensity
            
            # Apply emotional suppression
            memory.importance *= (1.0 - suppression_strength)
            memory.decay_rate = min(1.0, memory.decay_rate + suppression_strength * 0.3)
            
            # Reduce emotional intensity
            memory.emotion_intensity *= (1.0 - suppression_strength * 0.5)
            
            # Add suppression tag
            if 'emotionally_suppressed' not in memory.tags:
                memory.tags.append('emotionally_suppressed')
            
            # Save updated memory
            self.db_manager.save_memory(memory)
            
            suppression_results.append({
                'memory_id': memory.id,
                'original_importance': original_importance,
                'new_importance': memory.importance,
                'original_emotion_intensity': original_emotion_intensity,
                'new_emotion_intensity': memory.emotion_intensity,
                'dominant_emotion': memory.emotional_context.get('dominant_emotion'),
                'suppression_applied': True
            })
        
        return {
            'emotional_suppression_complete': True,
            'total_memories': len(all_memories),
            'emotional_candidates': len(emotional_candidates),
            'memories_suppressed': len(suppression_results),
            'target_emotions': target_emotions,
            'intensity_threshold': intensity_threshold,
            'suppression_strength': suppression_strength,
            'results': suppression_results
        }
    
    async def _active_forgetting(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Actively suppress specific memories (directed forgetting)"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        suppression_results = {
            'attempted': len(memory_ids),
            'suppressed': [],
            'failed': [],
            'protected': []
        }
        
        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if not memory:
                suppression_results['failed'].append({
                    'memory_id': memory_id,
                    'reason': 'Memory not found'
                })
                continue
            
            # Check if memory is protected from suppression
            if self._is_memory_protected(memory):
                suppression_results['protected'].append({
                    'memory_id': memory_id,
                    'reason': self._get_protection_reason(memory)
                })
                continue
            
            # Apply active suppression
            suppression_success = self._apply_active_suppression(memory)
            
            if suppression_success:
                # Record suppression
                self.suppression_history[memory_id] = {
                    'timestamp': datetime.now(),
                    'original_importance': memory.importance,
                    'suppression_strength': suppression_success['strength']
                }
                
                suppression_results['suppressed'].append({
                    'memory_id': memory_id,
                    'suppression_strength': suppression_success['strength'],
                    'new_importance': memory.importance,
                    'method': suppression_success['method']
                })
                
                self.active_suppressions += 1
            else:
                suppression_results['failed'].append({
                    'memory_id': memory_id,
                    'reason': 'Suppression failed'
                })
        
        return {
            'active_forgetting_complete': True,
            'results': suppression_results,
            'total_suppressions': self.active_suppressions
        }
    
    async def _resolve_interference(self, conflicting_memories: List[str]) -> Dict[str, Any]:
        """Resolve interference between conflicting memories"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memories = []
        for memory_id in conflicting_memories:
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                memories.append(memory)
        
        if len(memories) < 2:
            return {'error': 'Need at least 2 memories to resolve interference'}
        
        # Analyze interference patterns
        interference_analysis = self._analyze_memory_interference(memories)
        
        # Determine resolution strategy
        resolution_strategy = self._select_resolution_strategy(interference_analysis)
        
        # Apply resolution
        resolution_results = await self._apply_interference_resolution(
            memories, 
            resolution_strategy
        )
        
        self.interferences_resolved += 1
        
        return {
            'interference_resolved': True,
            'conflicting_memories': len(memories),
            'interference_analysis': interference_analysis,
            'resolution_strategy': resolution_strategy,
            'results': resolution_results,
            'total_resolutions': self.interferences_resolved
        }
    
    async def _manage_memory_capacity(self) -> Dict[str, Any]:
        """Manage memory capacity through intelligent pruning"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        all_memories = self.db_manager.load_memories_by_criteria()
        active_memories = [m for m in all_memories if not m.metadata.get('deactivated', False)]
        
        capacity_status = {
            'total_memories': len(all_memories),
            'active_memories': len(active_memories),
            'capacity_limit': self.capacity_limit,
            'utilization': len(active_memories) / self.capacity_limit,
            'action_needed': len(active_memories) > self.capacity_limit
        }
        
        if not capacity_status['action_needed']:
            return {
                'capacity_management_complete': True,
                'status': capacity_status,
                'action_taken': 'none_needed'
            }
        
        # Calculate pruning targets
        excess_memories = len(active_memories) - self.capacity_limit
        safety_margin = int(self.capacity_limit * 0.1)  # 10% safety margin
        target_to_prune = excess_memories + safety_margin
        
        # Identify pruning candidates
        pruning_candidates = self._identify_pruning_candidates(active_memories, target_to_prune)
        
        # Execute pruning
        pruning_results = await self._execute_memory_pruning(pruning_candidates)
        
        return {
            'capacity_management_complete': True,
            'status': capacity_status,
            'pruning_target': target_to_prune,
            'pruning_results': pruning_results
        }
    
    async def _selective_forgetting(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Perform selective forgetting based on specific criteria"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Load memories matching criteria
        memories = self.db_manager.load_memories_by_criteria()
        
        # Filter based on criteria
        candidates = self._filter_memories_by_criteria(memories, criteria)
        
        # Apply selective forgetting
        forgetting_results = {
            'candidates_identified': len(candidates),
            'forgotten_memories': [],
            'preserved_memories': [],
            'criteria_used': criteria
        }
        
        for memory in candidates:
            # Evaluate if memory should be forgotten
            forget_score = self._calculate_forgetting_score(memory, criteria)
            
            if forget_score > 0.6:  # High forget score
                # Apply forgetting
                self._apply_selective_forgetting_to_memory(memory, criteria)
                forgetting_results['forgotten_memories'].append({
                    'memory_id': memory.id,
                    'forget_score': forget_score,
                    'reason': self._get_forgetting_reason(criteria)
                })
                
                self.db_manager.save_memory(memory)
                
            else:
                forgetting_results['preserved_memories'].append(memory.id)
        
        return {
            'selective_forgetting_complete': True,
            'results': forgetting_results
        }
    
    async def _analyze_forgetting_patterns(self) -> Dict[str, Any]:
        """Analyze system-wide forgetting patterns and effectiveness"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        all_memories = self.db_manager.load_memories_by_criteria()
        forgotten_memories = [m for m in all_memories if m.metadata.get('marked_for_forgetting', False)]
        deactivated_memories = [m for m in all_memories if m.metadata.get('deactivated', False)]
        
        patterns = {
            'forgetting_statistics': {
                'total_memories': len(all_memories),
                'forgotten_memories': len(forgotten_memories),
                'deactivated_memories': len(deactivated_memories),
                'forgetting_rate': len(forgotten_memories) / len(all_memories) if all_memories else 0,
                'deactivation_rate': len(deactivated_memories) / len(all_memories) if all_memories else 0
            },
            'forgetting_by_type': self._analyze_forgetting_by_type(forgotten_memories),
            'forgetting_by_age': self._analyze_forgetting_by_age(forgotten_memories),
            'forgetting_by_importance': self._analyze_forgetting_by_importance(forgotten_memories),
            'retention_curves': self._calculate_retention_curves(all_memories)
        }
        
        # Generate insights
        insights = self._generate_forgetting_insights(patterns)
        
        return {
            'analysis_complete': True,
            'patterns': patterns,
            'insights': insights,
            'system_stats': {
                'decay_applications': self.decay_applications,
                'active_suppressions': self.active_suppressions,
                'interferences_resolved': self.interferences_resolved,
                'total_forgotten': self.memories_forgotten
            }
        }
    
    async def _intelligent_memory_pruning(self) -> Dict[str, Any]:
        """Perform intelligent memory pruning using multiple criteria"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        all_memories = self.db_manager.load_memories_by_criteria()
        
        # Multi-criteria pruning evaluation
        pruning_scores = []
        
        for memory in all_memories:
            score = self._calculate_intelligent_pruning_score(memory)
            pruning_scores.append((memory, score))
        
        # Sort by pruning score (higher = more likely to prune)
        pruning_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Determine pruning threshold
        pruning_threshold = self._determine_adaptive_pruning_threshold(pruning_scores)
        
        # Execute intelligent pruning
        pruning_results = {
            'evaluated_memories': len(all_memories),
            'pruned_memories': [],
            'preserved_memories': [],
            'pruning_threshold': pruning_threshold
        }
        
        for memory, score in pruning_scores:
            if score > pruning_threshold and not self._is_memory_protected(memory):
                # Prune memory
                memory.metadata['intelligently_pruned'] = True
                memory.metadata['pruning_score'] = score
                memory.metadata['pruning_timestamp'] = datetime.now().isoformat()
                memory.importance *= 0.1  # Severely reduce importance
                
                pruning_results['pruned_memories'].append({
                    'memory_id': memory.id,
                    'pruning_score': score,
                    'pruning_reasons': self._get_pruning_reasons(memory, score)
                })
                
                self.db_manager.save_memory(memory)
                
            else:
                pruning_results['preserved_memories'].append(memory.id)
        
        return {
            'intelligent_pruning_complete': True,
            'results': pruning_results
        }
    
    async def _suppress_traumatic_memories(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Apply special suppression techniques for traumatic memories"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        suppression_results = {
            'attempted': len(memory_ids),
            'suppressed': [],
            'containment_applied': []
        }
        
        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if not memory:
                continue
            
            # Apply trauma-specific suppression
            if memory.stress_marker or 'trauma' in memory.emotion_tags:
                # Containment rather than complete suppression
                containment_result = self._apply_trauma_containment(memory)
                
                suppression_results['containment_applied'].append({
                    'memory_id': memory_id,
                    'containment_level': containment_result['level'],
                    'accessibility_reduced': containment_result['accessibility_reduction']
                })
                
                self.db_manager.save_memory(memory)
                
            else:
                # Regular suppression for non-traumatic memories
                suppression_success = self._apply_active_suppression(memory)
                if suppression_success:
                    suppression_results['suppressed'].append(memory_id)
        
        return {
            'trauma_suppression_complete': True,
            'results': suppression_results
        }
    
    def _calculate_retention_score(self, memory: MemoryItem, time_elapsed_hours: float) -> float:
        """Calculate retention score using Ebbinghaus forgetting curve"""
        
        # Base Ebbinghaus curve: R(t) = e^(-t/τ)
        # Where τ is the time constant
        base_retention = math.exp(-time_elapsed_hours / self.ebbinghaus_params['time_constant'])
        
        # Adjust for memory-specific factors
        
        # Consolidation level affects retention
        consolidation_boost = memory.consolidation_level / 3.0 * 0.3
        
        # Importance affects retention
        importance_boost = memory.importance * 0.2
        
        # Access frequency affects retention (spaced repetition effect)
        access_boost = min(0.3, memory.access_frequency * 0.05)
        
        # Emotional intensity affects retention
        emotion_boost = memory.emotion_intensity * 0.15
        
        # Final retention score
        retention = base_retention + consolidation_boost + importance_boost + access_boost + emotion_boost
        
        return min(1.0, max(0.01, retention))
    
    def _calculate_decay_factors(self, memory: MemoryItem) -> Dict[str, float]:
        """Calculate additional decay factors beyond basic Ebbinghaus curve"""
        
        factors = {
            'interference_factor': 1.0,
            'stress_factor': 1.0,
            'context_factor': 1.0,
            'association_factor': 1.0,
            'compound_factor': 1.0
        }
        
        # Interference decay (memories with many similar memories decay faster)
        if len(memory.associations) > 10:
            factors['interference_factor'] = 0.9
        
        # Stress affects consolidation and retention
        if memory.stress_marker:
            factors['stress_factor'] = 1.1  # Stress can enhance memory
        
        # Context-dependent decay
        if len(memory.context_tags) == 0:
            factors['context_factor'] = 0.9  # Memories without context decay faster
        
        # Association strength affects retention
        if len(memory.associations) == 0:
            factors['association_factor'] = 0.8  # Isolated memories decay faster
        
        # Compound all factors
        factors['compound_factor'] = (
            factors['interference_factor'] *
            factors['stress_factor'] *
            factors['context_factor'] *
            factors['association_factor']
        )
        
        return factors
    
    def _is_memory_protected(self, memory: MemoryItem) -> bool:
        """Check if memory is protected from forgetting/suppression"""
        
        # Protected if explicitly marked
        if memory.metadata.get('protected', False):
            return True
        
        # Protected if highly consolidated
        if memory.consolidation_level >= 3:
            return True
        
        # Protected if very high importance
        if memory.importance > 0.9:
            return True
        
        # Protected if it's an insight or abstract learning
        if 'insight' in memory.context_tags or 'abstract' in memory.context_tags:
            return True
        
        # Protected if it's a traumatic memory that needs special handling
        if memory.stress_marker and memory.emotion_intensity > 0.8:
            return True
        
        return False
    
    def _get_protection_reason(self, memory: MemoryItem) -> str:
        """Get the reason why a memory is protected"""
        
        if memory.metadata.get('protected', False):
            return 'Explicitly protected'
        elif memory.consolidation_level >= 3:
            return 'Highly consolidated'
        elif memory.importance > 0.9:
            return 'Critical importance'
        elif 'insight' in memory.context_tags:
            return 'Insight memory'
        elif memory.stress_marker and memory.emotion_intensity > 0.8:
            return 'Traumatic memory requiring special handling'
        else:
            return 'Unknown protection reason'
    
    def _apply_active_suppression(self, memory: MemoryItem) -> Dict[str, Any]:
        """Apply active suppression to a memory"""
        
        # Calculate suppression strength based on memory properties
        base_suppression = 0.7
        
        # Easier to suppress recent, non-consolidated memories
        if memory.consolidation_level == 0:
            suppression_strength = base_suppression + 0.2
        elif memory.consolidation_level == 1:
            suppression_strength = base_suppression
        else:
            suppression_strength = base_suppression - 0.3
        
        # Harder to suppress important memories
        importance_resistance = memory.importance * 0.4
        suppression_strength -= importance_resistance
        
        # Harder to suppress emotional memories
        emotion_resistance = memory.emotion_intensity * 0.2
        suppression_strength -= emotion_resistance
        
        # Apply suppression if strength is sufficient
        if suppression_strength > 0.3:
            # Reduce importance dramatically
            memory.importance *= (1.0 - suppression_strength) * 0.5
            
            # Increase decay rate
            memory.decay_rate = min(0.95, memory.decay_rate + suppression_strength * 0.5)
            
            # Mark as suppressed
            memory.metadata['actively_suppressed'] = True
            memory.metadata['suppression_strength'] = suppression_strength
            memory.metadata['suppression_timestamp'] = datetime.now().isoformat()
            
            self.db_manager.save_memory(memory)
            
            return {
                'success': True,
                'strength': suppression_strength,
                'method': 'active_suppression',
                'new_importance': memory.importance
            }
        
        return None
    
    def _analyze_memory_interference(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze interference patterns between memories"""
        
        interference_analysis = {
            'interference_pairs': [],
            'interference_types': [],
            'overall_interference': 0.0
        }
        
        # Check pairwise interference
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                mem1, mem2 = memories[i], memories[j]
                
                interference_score = self._calculate_interference_score(mem1, mem2)
                
                if interference_score > self.interference_threshold:
                    interference_type = self._classify_interference_type(mem1, mem2)
                    
                    interference_analysis['interference_pairs'].append({
                        'memory1_id': mem1.id,
                        'memory2_id': mem2.id,
                        'interference_score': interference_score,
                        'interference_type': interference_type
                    })
                    
                    interference_analysis['interference_types'].append(interference_type)
        
        # Calculate overall interference
        if interference_analysis['interference_pairs']:
            total_score = sum(pair['interference_score'] for pair in interference_analysis['interference_pairs'])
            interference_analysis['overall_interference'] = total_score / len(interference_analysis['interference_pairs'])
        
        return interference_analysis
    
    def _calculate_interference_score(self, mem1: MemoryItem, mem2: MemoryItem) -> float:
        """Calculate interference score between two memories"""
        
        score = 0.0
        
        # Content similarity (using simple word overlap)
        words1 = set(mem1.content.lower().split())
        words2 = set(mem2.content.lower().split())
        
        if words1 and words2:
            overlap = len(words1 & words2)
            union = len(words1 | words2)
            content_similarity = overlap / union if union > 0 else 0
            score += content_similarity * 0.4
        
        # Context overlap
        context1 = set(mem1.context_tags)
        context2 = set(mem2.context_tags)
        
        if context1 and context2:
            context_overlap = len(context1 & context2) / len(context1 | context2)
            score += context_overlap * 0.3
        
        # Temporal proximity
        if mem1.timestamp and mem2.timestamp:
            time_diff = abs((mem1.timestamp - mem2.timestamp).total_seconds())
            if time_diff < 3600:  # Within 1 hour
                score += 0.3
            elif time_diff < 86400:  # Within 1 day
                score += 0.2
        
        return min(1.0, score)
    
    def _classify_interference_type(self, mem1: MemoryItem, mem2: MemoryItem) -> str:
        """Classify the type of interference between memories"""
        
        # Simple classification based on dominant similarity
        content_sim = len(set(mem1.content.lower().split()) & set(mem2.content.lower().split()))
        context_sim = len(set(mem1.context_tags) & set(mem2.context_tags))
        
        if content_sim > context_sim:
            return 'content_interference'
        elif context_sim > 0:
            return 'context_interference'
        else:
            return 'temporal_interference'
    
    def _select_resolution_strategy(self, interference_analysis: Dict[str, Any]) -> str:
        """Select appropriate strategy for resolving interference"""
        
        if not interference_analysis['interference_pairs']:
            return 'no_action_needed'
        
        # Count interference types
        type_counts = {}
        for interference_type in interference_analysis['interference_types']:
            type_counts[interference_type] = type_counts.get(interference_type, 0) + 1
        
        # Select strategy based on dominant interference type
        dominant_type = max(type_counts, key=type_counts.get) if type_counts else 'general'
        
        strategy_map = {
            'content_interference': 'merge_similar_memories',
            'context_interference': 'separate_by_context',
            'temporal_interference': 'temporal_disambiguation',
            'general': 'importance_based_resolution'
        }
        
        return strategy_map.get(dominant_type, 'importance_based_resolution')
    
    async def _apply_interference_resolution(self, memories: List[MemoryItem], strategy: str) -> Dict[str, Any]:
        """Apply the selected interference resolution strategy"""
        
        resolution_results = {
            'strategy_applied': strategy,
            'memories_modified': [],
            'memories_suppressed': []
        }
        
        if strategy == 'importance_based_resolution':
            # Sort by importance and suppress less important conflicting memories
            memories.sort(key=lambda m: m.importance, reverse=True)
            
            # Keep the most important, suppress others
            for memory in memories[1:]:
                memory.importance *= 0.6  # Reduce importance
                memory.metadata['interference_suppressed'] = True
                memory.metadata['dominant_memory'] = memories[0].id
                
                self.db_manager.save_memory(memory)
                
                resolution_results['memories_suppressed'].append(memory.id)
            
            resolution_results['memories_modified'].append(memories[0].id)
        
        elif strategy == 'merge_similar_memories':
            # Merge highly similar memories (simplified implementation)
            if len(memories) >= 2:
                primary_memory = memories[0]
                
                # Combine content and context
                combined_content = primary_memory.content
                for memory in memories[1:]:
                    combined_content += f" [MERGED: {memory.content}]"
                    memory.metadata['merged_into'] = primary_memory.id
                    memory.importance *= 0.1  # Severely reduce importance
                    
                    self.db_manager.save_memory(memory)
                    resolution_results['memories_suppressed'].append(memory.id)
                
                primary_memory.content = combined_content
                primary_memory.metadata['merged_memories'] = [m.id for m in memories[1:]]
                
                self.db_manager.save_memory(primary_memory)
                resolution_results['memories_modified'].append(primary_memory.id)
        
        # Other strategies would be implemented similarly
        
        return resolution_results
    
    def _identify_pruning_candidates(self, memories: List[MemoryItem], target_count: int) -> List[Tuple[MemoryItem, float]]:
        """Identify memories that are candidates for pruning"""
        
        candidates = []
        
        for memory in memories:
            # Calculate pruning priority (higher = more likely to prune)
            priority = self._calculate_pruning_priority(memory)
            candidates.append((memory, priority))
        
        # Sort by priority (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[:target_count]
    
    def _calculate_pruning_priority(self, memory: MemoryItem) -> float:
        """Calculate pruning priority for a memory"""
        
        priority = 0.0
        
        # Low importance increases pruning priority
        priority += (1.0 - memory.importance) * 0.4
        
        # Old, unaccessed memories have higher priority
        if memory.last_accessed:
            days_since_access = (datetime.now() - memory.last_accessed).days
            priority += min(0.3, days_since_access / 100)
        else:
            priority += 0.2  # Never accessed
        
        # Low consolidation level increases priority
        priority += (1.0 - memory.consolidation_level / 3.0) * 0.2
        
        # High decay rate increases priority
        priority += memory.decay_rate * 0.1
        
        # Isolated memories (no associations) have higher priority
        if not memory.associations:
            priority += 0.1
        
        return min(1.0, priority)
    
    async def _execute_memory_pruning(self, candidates: List[Tuple[MemoryItem, float]]) -> Dict[str, Any]:
        """Execute memory pruning on selected candidates"""
        
        pruning_results = {
            'candidates_processed': len(candidates),
            'memories_pruned': [],
            'memories_archived': []
        }
        
        for memory, priority in candidates:
            if not self._is_memory_protected(memory):
                if priority > 0.8:  # High priority - complete pruning
                    memory.metadata['pruned'] = True
                    memory.metadata['pruning_priority'] = priority
                    memory.metadata['pruning_timestamp'] = datetime.now().isoformat()
                    memory.importance = 0.01
                    
                    pruning_results['memories_pruned'].append(memory.id)
                    
                elif priority > 0.6:  # Medium priority - archiving
                    memory.metadata['archived'] = True
                    memory.metadata['archive_priority'] = priority
                    memory.importance *= 0.3
                    
                    pruning_results['memories_archived'].append(memory.id)
                
                self.db_manager.save_memory(memory)
        
        return pruning_results
    
    def _filter_memories_by_criteria(self, memories: List[MemoryItem], criteria: Dict[str, Any]) -> List[MemoryItem]:
        """Filter memories based on forgetting criteria"""
        
        filtered = []
        
        for memory in memories:
            matches = True
            
            # Age criteria
            if 'max_age_days' in criteria:
                age_days = (datetime.now() - memory.timestamp).days
                if age_days < criteria['max_age_days']:
                    matches = False
            
            # Importance criteria
            if 'max_importance' in criteria:
                if memory.importance > criteria['max_importance']:
                    matches = False
            
            # Access criteria
            if 'max_access_frequency' in criteria:
                if memory.access_frequency > criteria['max_access_frequency']:
                    matches = False
            
            # Context criteria
            if 'exclude_contexts' in criteria:
                if any(ctx in memory.context_tags for ctx in criteria['exclude_contexts']):
                    matches = False
            
            # Memory type criteria
            if 'memory_types' in criteria:
                if memory.memory_type not in criteria['memory_types']:
                    matches = False
            
            if matches:
                filtered.append(memory)
        
        return filtered
    
    def _calculate_forgetting_score(self, memory: MemoryItem, criteria: Dict[str, Any]) -> float:
        """Calculate forgetting score based on criteria"""
        
        score = 0.0
        
        # Age factor
        if 'age_weight' in criteria:
            age_days = (datetime.now() - memory.timestamp).days
            age_score = min(1.0, age_days / 365)  # Normalize to year
            score += age_score * criteria['age_weight']
        
        # Importance factor (inverse)
        if 'importance_weight' in criteria:
            importance_score = 1.0 - memory.importance
            score += importance_score * criteria['importance_weight']
        
        # Access frequency factor (inverse)
        if 'access_weight' in criteria:
            access_score = 1.0 - min(1.0, memory.access_frequency / 10)
            score += access_score * criteria['access_weight']
        
        return min(1.0, score)
    
    def _apply_selective_forgetting_to_memory(self, memory: MemoryItem, criteria: Dict[str, Any]):
        """Apply selective forgetting to a specific memory"""
        
        # Reduce importance based on criteria
        importance_reduction = criteria.get('importance_reduction', 0.5)
        memory.importance *= (1.0 - importance_reduction)
        
        # Increase decay rate
        decay_increase = criteria.get('decay_increase', 0.3)
        memory.decay_rate = min(0.95, memory.decay_rate + decay_increase)
        
        # Mark as selectively forgotten
        memory.metadata['selectively_forgotten'] = True
        memory.metadata['forgetting_criteria'] = criteria
        memory.metadata['selective_forgetting_timestamp'] = datetime.now().isoformat()
    
    def _get_forgetting_reason(self, criteria: Dict[str, Any]) -> str:
        """Get human-readable forgetting reason from criteria"""
        
        reasons = []
        
        if 'max_age_days' in criteria:
            reasons.append(f"older than {criteria['max_age_days']} days")
        
        if 'max_importance' in criteria:
            reasons.append(f"importance below {criteria['max_importance']}")
        
        if 'memory_types' in criteria:
            reasons.append(f"memory type in {criteria['memory_types']}")
        
        return '; '.join(reasons) if reasons else 'selective forgetting criteria'
    
    def _calculate_intelligent_pruning_score(self, memory: MemoryItem) -> float:
        """Calculate intelligent pruning score using multiple factors"""
        
        score = 0.0
        
        # Base factors
        score += (1.0 - memory.importance) * 0.3
        score += memory.decay_rate * 0.2
        score += (1.0 - memory.consolidation_level / 3.0) * 0.2
        
        # Access patterns
        if memory.last_accessed:
            days_since_access = (datetime.now() - memory.last_accessed).days
            score += min(0.2, days_since_access / 100)
        else:
            score += 0.1
        
        # Network position
        if not memory.associations:
            score += 0.1  # Isolated memories
        elif len(memory.associations) > 10:
            score -= 0.05  # Hub memories are valuable
        
        return min(1.0, max(0.0, score))
    
    def _determine_adaptive_pruning_threshold(self, pruning_scores: List[Tuple[MemoryItem, float]]) -> float:
        """Determine adaptive pruning threshold based on score distribution"""
        
        if not pruning_scores:
            return 0.5
        
        scores = [score for _, score in pruning_scores]
        
        # Use percentile-based threshold
        scores.sort()
        threshold_index = int(len(scores) * 0.8)  # 80th percentile
        
        return scores[threshold_index] if threshold_index < len(scores) else 0.5
    
    def _get_pruning_reasons(self, memory: MemoryItem, score: float) -> List[str]:
        """Get reasons why a memory is being pruned"""
        
        reasons = []
        
        if memory.importance < 0.3:
            reasons.append('low importance')
        
        if memory.decay_rate > 0.7:
            reasons.append('high decay rate')
        
        if memory.consolidation_level == 0:
            reasons.append('unconsolidated')
        
        if not memory.associations:
            reasons.append('isolated memory')
        
        if memory.last_accessed:
            days_since_access = (datetime.now() - memory.last_accessed).days
            if days_since_access > 90:
                reasons.append(f'not accessed for {days_since_access} days')
        else:
            reasons.append('never accessed')
        
        return reasons
    
    def _apply_trauma_containment(self, memory: MemoryItem) -> Dict[str, Any]:
        """Apply specialized containment for traumatic memories"""
        
        # Trauma memories need special handling - containment rather than suppression
        containment_level = 'moderate'
        accessibility_reduction = 0.4
        
        if memory.emotion_intensity > 0.9:
            containment_level = 'high'
            accessibility_reduction = 0.7
        elif memory.emotion_intensity > 0.7:
            containment_level = 'moderate'
            accessibility_reduction = 0.5
        else:
            containment_level = 'low'
            accessibility_reduction = 0.3
        
        # Apply containment
        memory.metadata['trauma_contained'] = True
        memory.metadata['containment_level'] = containment_level
        memory.metadata['containment_timestamp'] = datetime.now().isoformat()
        
        # Reduce accessibility but maintain memory integrity
        memory.importance *= (1.0 - accessibility_reduction)
        
        # Don't increase decay rate for trauma memories - they need to be preserved
        # but made less accessible
        
        return {
            'level': containment_level,
            'accessibility_reduction': accessibility_reduction
        }
    
    # Analysis methods for forgetting patterns
    
    def _analyze_forgetting_by_type(self, forgotten_memories: List[MemoryItem]) -> Dict[str, int]:
        """Analyze forgetting patterns by memory type"""
        
        type_counts = {}
        for memory in forgotten_memories:
            mem_type = memory.memory_type
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        return type_counts
    
    def _analyze_forgetting_by_age(self, forgotten_memories: List[MemoryItem]) -> Dict[str, int]:
        """Analyze forgetting patterns by age"""
        
        age_buckets = {'recent': 0, 'medium': 0, 'old': 0}
        
        for memory in forgotten_memories:
            age_days = (datetime.now() - memory.timestamp).days
            
            if age_days < 7:
                age_buckets['recent'] += 1
            elif age_days < 30:
                age_buckets['medium'] += 1
            else:
                age_buckets['old'] += 1
        
        return age_buckets
    
    def _analyze_forgetting_by_importance(self, forgotten_memories: List[MemoryItem]) -> Dict[str, int]:
        """Analyze forgetting patterns by importance level"""
        
        importance_buckets = {'low': 0, 'medium': 0, 'high': 0}
        
        for memory in forgotten_memories:
            if memory.importance < 0.3:
                importance_buckets['low'] += 1
            elif memory.importance < 0.7:
                importance_buckets['medium'] += 1
            else:
                importance_buckets['high'] += 1
        
        return importance_buckets
    
    def _calculate_retention_curves(self, memories: List[MemoryItem]) -> Dict[str, List[float]]:
        """Calculate retention curves for different memory types"""
        
        # Group memories by type
        memory_types = {}
        for memory in memories:
            mem_type = memory.memory_type
            if mem_type not in memory_types:
                memory_types[mem_type] = []
            memory_types[mem_type].append(memory)
        
        # Calculate retention curves
        retention_curves = {}
        
        for mem_type, type_memories in memory_types.items():
            curve = []
            
            # Sample retention at different time points
            for hours in [1, 24, 168, 720, 8760]:  # 1h, 1d, 1w, 1m, 1y
                retentions = []
                
                for memory in type_memories:
                    time_elapsed = (datetime.now() - memory.timestamp).total_seconds() / 3600
                    if time_elapsed >= hours:
                        retention = self._calculate_retention_score(memory, hours)
                        retentions.append(retention)
                
                avg_retention = sum(retentions) / len(retentions) if retentions else 1.0
                curve.append(avg_retention)
            
            retention_curves[mem_type] = curve
        
        return retention_curves
    
    def _generate_forgetting_insights(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate insights from forgetting patterns"""
        
        insights = []
        
        stats = patterns['forgetting_statistics']
        
        # Overall forgetting rate insight
        if stats['forgetting_rate'] > 0.3:
            insights.append(f"High forgetting rate detected: {stats['forgetting_rate']:.1%}")
        elif stats['forgetting_rate'] < 0.1:
            insights.append(f"Low forgetting rate: {stats['forgetting_rate']:.1%} - system may benefit from more aggressive pruning")
        
        # Memory type insights
        type_patterns = patterns['forgetting_by_type']
        if type_patterns:
            most_forgotten_type = max(type_patterns, key=type_patterns.get)
            insights.append(f"Most forgotten memory type: {most_forgotten_type}")
        
        # Age-based insights
        age_patterns = patterns['forgetting_by_age']
        if age_patterns['recent'] > age_patterns['old']:
            insights.append("Unusual pattern: more recent memories being forgotten than old ones")
        
        return insights