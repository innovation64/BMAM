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


class PruningMixin:
    """智能修剪和选择性遗忘功能"""
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
        
