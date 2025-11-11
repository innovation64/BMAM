"""
Forgetting Agent Module
遗忘智能体模块 - 对应前额叶抑制网络
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


from .core import ForgettingAgentCore
from ....memory.memory_item import MemoryItem


class InterferenceMixin:
    """记忆干扰消除和冲突解决功能"""
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
    
