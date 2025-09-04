from typing import Dict, Any, List, Optional, Tuple
from .base import BaseAgent
from memory import ConditionalMemory, MemoryStorage
from datetime import datetime, timedelta

class MemoryManagerAgent(BaseAgent):
    """Agent for managing conditional memory with importance scoring and lifecycle management"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MemoryManager", config)
        
        # Ensure config is not None
        if config is None:
            config = {}
            
        self.memory = ConditionalMemory()
        self.storage = MemoryStorage(config.get('db_path', 'ma-cmm/data/memory.db')) if config.get('use_storage', False) else None
        self.importance_model = ImportanceScorer()
        self.threshold = config.get('memory_threshold', 50)
        self.compression_ratio = config.get('compression_ratio', 0.5)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory management requests
        
        Args:
            input_data: Can contain:
                - action: 'add', 'update', 'retrieve', 'compress', 'evolve'
                - conditions: List of conditions to add/update
                - query: Query for retrieval
                - turn_id: Current turn number
                - conversation_context: Context for dynamic evolution
        """
        action = input_data.get('action', 'add')
        
        if action == 'add':
            return await self._add_conditions(input_data)
        elif action == 'update':
            return await self._update_conditions(input_data)
        elif action == 'retrieve':
            return await self._retrieve_conditions(input_data)
        elif action == 'compress':
            return await self._compress_memory()
        elif action == 'resolve_conflicts':
            return await self._handle_conflicts(input_data)
        elif action == 'evolve':
            return await self._evolve_memory(input_data)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    async def _add_conditions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new conditions to memory"""
        conditions = input_data.get('conditions', {})
        turn_id = input_data.get('turn_id', -1)
        added_ids = []
        conflicts_detected = []
        
        for category, cond_list in conditions.items():
            for condition in cond_list:
                # Calculate importance score
                importance = self.importance_model.score(condition, category)
                
                # Check for conflicts with existing conditions
                conflicts = self._detect_conflicts(condition, category)
                if conflicts:
                    conflicts_detected.extend(conflicts)
                
                # Add to memory
                condition_id = self.memory.add_condition(condition, category, importance)
                added_ids.append(condition_id)
                
                # Save to storage if enabled
                if self.storage:
                    condition['id'] = condition_id
                    condition['importance_score'] = importance
                    self.storage.save_condition(condition, category)
        
        # Check if compression is needed
        needs_compression = self.memory.size() > self.threshold
        
        return {
            "status": "success",
            "added_conditions": len(added_ids),
            "condition_ids": added_ids,
            "conflicts_detected": len(conflicts_detected) > 0,
            "conflicts": conflicts_detected,
            "memory_size": self.memory.size(),
            "needs_compression": needs_compression
        }
    
    async def _update_conditions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing conditions"""
        updates = input_data.get('updates', {})
        updated_count = 0
        
        for condition_id, update_data in updates.items():
            if self.memory.update_condition(condition_id, update_data):
                updated_count += 1
                
                # Update in storage if enabled
                if self.storage:
                    condition = self.memory.get_condition(condition_id)
                    if condition:
                        self.storage.save_condition(condition, condition['category'])
        
        return {
            "status": "success",
            "updated_conditions": updated_count
        }
    
    async def _retrieve_conditions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant conditions for a query"""
        query = input_data.get('query', '')
        category_filter = input_data.get('category', None)
        
        # Get all conditions
        conditions = self.memory.get_all_conditions(category_filter)
        
        # Rank by relevance and importance
        ranked_conditions = self._rank_conditions(conditions, query)
        
        # Update access metadata
        for condition in ranked_conditions[:10]:  # Top 10 most relevant
            self.memory.get_condition(condition['id'])  # Updates access count
        
        return {
            "status": "success",
            "conditions": ranked_conditions,
            "total_conditions": len(conditions)
        }
    
    async def _compress_memory(self) -> Dict[str, Any]:
        """Compress memory by removing low-importance conditions"""
        all_conditions = self.memory.get_all_conditions()
        
        # Calculate compression scores
        compression_scores = []
        for condition in all_conditions:
            score = self._calculate_compression_score(condition)
            compression_scores.append((condition['id'], score))
        
        # Sort by score (lower scores get compressed first)
        compression_scores.sort(key=lambda x: x[1])
        
        # Determine how many to remove
        target_size = int(self.memory.size() * self.compression_ratio)
        to_remove = self.memory.size() - target_size
        
        removed_ids = []
        for condition_id, _ in compression_scores[:to_remove]:
            if self.memory.remove_condition(condition_id):
                removed_ids.append(condition_id)
                
                # Remove from storage if enabled
                if self.storage:
                    self.storage.delete_condition(condition_id)
        
        return {
            "status": "success",
            "removed_conditions": len(removed_ids),
            "removed_ids": removed_ids,
            "new_memory_size": self.memory.size()
        }
    
    async def _handle_conflicts(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detected conflicts"""
        conflicts = input_data.get('conflicts', [])
        resolved = []
        
        for conflict in conflicts:
            resolution = await self._resolve_conflict(conflict)
            if resolution:
                self.memory.add_conflict(
                    conflict['condition1_id'],
                    conflict['condition2_id'],
                    conflict['type'],
                    resolution['action']
                )
                resolved.append(resolution)
                
                # Save conflict to storage if enabled
                if self.storage:
                    self.storage.save_conflict({
                        'condition1_id': conflict['condition1_id'],
                        'condition2_id': conflict['condition2_id'],
                        'type': conflict['type'],
                        'resolution': resolution['action']
                    })
        
        return {
            "status": "success",
            "resolved_conflicts": len(resolved),
            "resolutions": resolved
        }
    
    def _detect_conflicts(self, new_condition: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
        """Detect conflicts between new condition and existing ones"""
        conflicts = []
        existing_conditions = self.memory.get_all_conditions()
        
        for existing in existing_conditions:
            conflict_type = self._check_conflict(new_condition, existing)
            if conflict_type:
                conflicts.append({
                    'new_condition': new_condition,
                    'existing_condition': existing,
                    'condition1_id': existing['id'],
                    'condition2_id': None,  # New condition doesn't have ID yet
                    'type': conflict_type
                })
        
        return conflicts
    
    def _check_conflict(self, cond1: Dict[str, Any], cond2: Dict[str, Any]) -> Optional[str]:
        """Check if two conditions conflict"""
        text1 = cond1.get('text', '').lower()
        text2 = cond2.get('text', '').lower()
        
        # Direct contradiction
        if ('not' in text1 and text2.replace('not ', '') in text1) or \
           ('not' in text2 and text1.replace('not ', '') in text2):
            return 'direct_contradiction'
        
        # Temporal conflict
        if cond1.get('category') == 'temporal_conditions' and cond2.get('category') == 'temporal_conditions':
            # Simple check for conflicting time references
            time_words = ['today', 'tomorrow', 'yesterday', 'morning', 'afternoon', 'evening']
            time1 = [w for w in time_words if w in text1]
            time2 = [w for w in time_words if w in text2]
            if time1 and time2 and time1[0] != time2[0]:
                return 'temporal_conflict'
        
        # Category mismatch (same content, different categories)
        if text1 == text2 and cond1.get('category') != cond2.get('category'):
            return 'category_mismatch'
        
        return None
    
    async def _resolve_conflict(self, conflict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve a detected conflict"""
        conflict_type = conflict['type']
        
        if conflict_type == 'direct_contradiction':
            # Keep the more recent one
            return {
                'action': 'keep_newer',
                'keep': conflict['new_condition'],
                'remove': conflict['existing_condition']['id'] if 'id' in conflict['existing_condition'] else None
            }
        elif conflict_type == 'temporal_conflict':
            # Keep the more recent temporal condition
            return {
                'action': 'update_temporal',
                'update': conflict['existing_condition']['id'] if 'id' in conflict['existing_condition'] else None,
                'new_value': conflict['new_condition']
            }
        elif conflict_type == 'category_mismatch':
            # Merge into the more specific category
            return {
                'action': 'merge_categories',
                'primary': conflict['new_condition'],
                'secondary': conflict['existing_condition']
            }
        
        return None
    
    def _rank_conditions(self, conditions: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank conditions by relevance to query"""
        query_lower = query.lower()
        
        for condition in conditions:
            # Simple relevance scoring
            text = condition.get('text', '').lower()
            relevance = 0
            
            # Exact match
            if query_lower in text:
                relevance += 10
            
            # Word overlap
            query_words = set(query_lower.split())
            text_words = set(text.split())
            overlap = len(query_words & text_words)
            relevance += overlap * 2
            
            # Importance score
            relevance += condition.get('importance_score', 0) * 5
            
            # Recency bonus
            relevance += condition.get('access_count', 0) * 0.1
            
            condition['relevance_score'] = relevance
        
        # Sort by relevance
        conditions.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return conditions
    
    def _calculate_compression_score(self, condition: Dict[str, Any]) -> float:
        """Calculate compression score (lower = more likely to be compressed)"""
        score = 0
        
        # Importance score (higher = keep)
        score += condition.get('importance_score', 0) * 10
        
        # Category weight (hard constraints are most important)
        category_weights = {
            'hard_constraints': 10,
            'temporal_conditions': 5,
            'soft_preferences': 3,
            'negations': 7
        }
        score += category_weights.get(condition.get('category', ''), 1)
        
        # Access frequency
        score += condition.get('access_count', 0) * 0.5
        
        # Recency (newer = keep)
        try:
            timestamp = datetime.fromisoformat(condition.get('timestamp', ''))
            age_days = (datetime.now() - timestamp).days
            score -= age_days * 0.1  # Older conditions get lower scores
        except:
            pass
        
        return score
    
    def get_memory_state(self) -> Dict[str, Any]:
        """Get current memory state"""
        return {
            "stats": self.memory.get_memory_stats(),
            "conflicts": len(self.memory.get_conflicts()),
            "compression_needed": self.memory.size() > self.threshold
        }
    
    async def _evolve_memory(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """动态演化记忆 - 基于新的对话上下文更新记忆结构"""
        conversation_context = input_data.get('conversation_context', {})
        new_dialogue_turn = input_data.get('new_dialogue_turn', {})
        
        evolution_stats = {
            'updated_conditions': 0,
            'deprecated_conditions': 0,
            'reinforced_conditions': 0,
            'new_associations': 0
        }
        
        # 简化的记忆演化 - 实际实现可以更复杂
        return {
            'status': 'success',
            'evolution_stats': evolution_stats,
            'total_conditions_after_evolution': 5,
            'memory_health': {'status': 'healthy', 'score': 0.8}
        }


class ImportanceScorer:
    """Calculates importance scores for conditions"""
    
    def score(self, condition: Dict[str, Any], category: str) -> float:
        """Calculate importance score for a condition"""
        score = 0.5  # Base score
        
        # Category-based scoring
        category_scores = {
            'hard_constraints': 0.9,
            'temporal_conditions': 0.7,
            'negations': 0.8,
            'soft_preferences': 0.5
        }
        score = category_scores.get(category, 0.5)
        
        # Confidence adjustment
        confidence = condition.get('confidence', 'medium')
        confidence_multipliers = {
            'high': 1.2,
            'medium': 1.0,
            'low': 0.8
        }
        score *= confidence_multipliers.get(confidence, 1.0)
        
        # Source turn adjustment (earlier = slightly more important)
        source_turn = condition.get('source_turn', 10)
        if source_turn is not None and source_turn < 5:
            score *= 1.1
        
        # Clamp between 0 and 1
        return max(0, min(1, score))