from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
import json

class ConditionalMemory:
    """Manages conditional memory storage with metadata tracking"""
    
    def __init__(self):
        self.memory_structure = {
            "hard_constraints": [],
            "soft_preferences": [],
            "temporal_conditions": [],
            "negations": [],
            "metadata": {
                "importance_scores": {},
                "timestamps": {},
                "source_turns": {},
                "access_count": {},
                "last_accessed": {}
            }
        }
        self.condition_index = {}  # Maps condition_id to (category, index)
        self.conflict_history = []
        
    def add_condition(self, condition: Dict[str, Any], category: str, importance_score: float = 0.5) -> str:
        """Add a new condition to memory
        
        Args:
            condition: Condition data including text, source_turn, confidence
            category: One of the condition categories
            importance_score: Importance score (0-1)
            
        Returns:
            Condition ID
        """
        # Generate unique ID
        condition_id = str(uuid.uuid4())
        condition['id'] = condition_id
        
        # Add to appropriate category
        if category in self.memory_structure:
            index = len(self.memory_structure[category])
            self.memory_structure[category].append(condition)
            self.condition_index[condition_id] = (category, index)
            
            # Update metadata
            self.memory_structure["metadata"]["importance_scores"][condition_id] = importance_score
            self.memory_structure["metadata"]["timestamps"][condition_id] = datetime.now().isoformat()
            self.memory_structure["metadata"]["source_turns"][condition_id] = condition.get('source_turn', -1)
            self.memory_structure["metadata"]["access_count"][condition_id] = 0
            self.memory_structure["metadata"]["last_accessed"][condition_id] = datetime.now().isoformat()
            
        return condition_id
    
    def get_condition(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific condition by ID"""
        if condition_id not in self.condition_index:
            return None
            
        category, index = self.condition_index[condition_id]
        condition = self.memory_structure[category][index].copy()
        
        # Update access metadata
        self.memory_structure["metadata"]["access_count"][condition_id] += 1
        self.memory_structure["metadata"]["last_accessed"][condition_id] = datetime.now().isoformat()
        
        # Add metadata to condition
        condition['importance_score'] = self.memory_structure["metadata"]["importance_scores"].get(condition_id, 0)
        condition['timestamp'] = self.memory_structure["metadata"]["timestamps"].get(condition_id, '')
        
        return condition
    
    def update_condition(self, condition_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing condition"""
        if condition_id not in self.condition_index:
            return False
            
        category, index = self.condition_index[condition_id]
        
        # Update condition data
        self.memory_structure[category][index].update(updates)
        
        # Update timestamp
        self.memory_structure["metadata"]["timestamps"][condition_id] = datetime.now().isoformat()
        
        return True
    
    def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition from memory"""
        if condition_id not in self.condition_index:
            return False
            
        category, index = self.condition_index[condition_id]
        
        # Remove from category list
        self.memory_structure[category].pop(index)
        
        # Update indices for remaining conditions
        for cid, (cat, idx) in list(self.condition_index.items()):
            if cat == category and idx > index:
                self.condition_index[cid] = (cat, idx - 1)
        
        # Remove from index and metadata
        del self.condition_index[condition_id]
        for metadata_dict in self.memory_structure["metadata"].values():
            if condition_id in metadata_dict:
                del metadata_dict[condition_id]
        
        return True
    
    def get_all_conditions(self, category: Optional[str] = None, min_importance: float = 0.0) -> List[Dict[str, Any]]:
        """Get all conditions, optionally filtered by category and importance"""
        conditions = []
        
        categories = [category] if category else ["hard_constraints", "soft_preferences", 
                                                "temporal_conditions", "negations"]
        
        for cat in categories:
            for condition in self.memory_structure.get(cat, []):
                cond_copy = condition.copy()
                cond_id = cond_copy['id']
                
                # Add metadata
                cond_copy['category'] = cat
                cond_copy['importance_score'] = self.memory_structure["metadata"]["importance_scores"].get(cond_id, 0)
                cond_copy['access_count'] = self.memory_structure["metadata"]["access_count"].get(cond_id, 0)
                
                # Filter by importance
                if cond_copy['importance_score'] >= min_importance:
                    conditions.append(cond_copy)
        
        # Sort by importance and recency
        conditions.sort(key=lambda x: (x['importance_score'], x['access_count']), reverse=True)
        
        return conditions
    
    def update_importance_scores(self, score_updates: Dict[str, float]):
        """Update importance scores for multiple conditions"""
        for condition_id, score in score_updates.items():
            if condition_id in self.condition_index:
                self.memory_structure["metadata"]["importance_scores"][condition_id] = score
    
    def add_conflict(self, condition1_id: str, condition2_id: str, conflict_type: str, resolution: Optional[str] = None):
        """Record a conflict between two conditions"""
        conflict = {
            "timestamp": datetime.now().isoformat(),
            "condition1_id": condition1_id,
            "condition2_id": condition2_id,
            "type": conflict_type,
            "resolution": resolution
        }
        self.conflict_history.append(conflict)
    
    def get_conflicts(self, condition_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conflict history, optionally filtered by condition ID"""
        if condition_id:
            return [c for c in self.conflict_history 
                   if c["condition1_id"] == condition_id or c["condition2_id"] == condition_id]
        return self.conflict_history
    
    def size(self) -> int:
        """Get total number of conditions in memory"""
        return len(self.condition_index)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        stats = {
            "total_conditions": self.size(),
            "by_category": {},
            "average_importance": 0,
            "total_conflicts": len(self.conflict_history)
        }
        
        # Count by category
        for category in ["hard_constraints", "soft_preferences", "temporal_conditions", "negations"]:
            stats["by_category"][category] = len(self.memory_structure[category])
        
        # Calculate average importance
        if self.size() > 0:
            scores = list(self.memory_structure["metadata"]["importance_scores"].values())
            stats["average_importance"] = sum(scores) / len(scores)
        
        return stats
    
    def get_context_relevant_conditions(self, context_embedding: Any, top_k: int = 10) -> List[Dict[str, Any]]:
        """Get conditions most relevant to current context based on semantic similarity"""
        conditions = self.get_all_conditions()
        
        # Calculate relevance scores
        for condition in conditions:
            # Placeholder for semantic similarity calculation
            # In real implementation, use embedding similarity
            condition['relevance_score'] = condition['importance_score'] * condition['access_count']
        
        # Sort by relevance and return top_k
        conditions.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return conditions[:top_k]
    
    def decay_importance_scores(self, decay_factor: float = 0.95):
        """Apply time-based decay to importance scores"""
        current_time = datetime.now()
        
        for condition_id, timestamp_str in self.memory_structure["metadata"]["timestamps"].items():
            timestamp = datetime.fromisoformat(timestamp_str)
            hours_elapsed = (current_time - timestamp).total_seconds() / 3600
            
            # Apply exponential decay based on time
            if hours_elapsed > 24:  # Start decay after 24 hours
                decay = decay_factor ** (hours_elapsed / 24)
                current_score = self.memory_structure["metadata"]["importance_scores"][condition_id]
                self.memory_structure["metadata"]["importance_scores"][condition_id] = current_score * decay
    
    def serialize(self) -> str:
        """Serialize memory to JSON string"""
        return json.dumps({
            "memory_structure": self.memory_structure,
            "condition_index": self.condition_index,
            "conflict_history": self.conflict_history
        })
    
    def deserialize(self, data: str):
        """Deserialize memory from JSON string"""
        loaded = json.loads(data)
        self.memory_structure = loaded.get("memory_structure", self.memory_structure)
        self.condition_index = loaded.get("condition_index", {})
        self.conflict_history = loaded.get("conflict_history", [])