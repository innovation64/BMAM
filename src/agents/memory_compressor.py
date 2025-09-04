from typing import Dict, Any, List, Optional, Tuple
from .base import BaseAgent
from datetime import datetime, timedelta
import random

class MemoryCompressorAgent(BaseAgent):
    """Agent for compressing memory by removing or consolidating low-importance conditions"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MemoryCompressor", config)
        self.compression_strategies = {
            'importance_based': self._importance_based_compression,
            'time_decay': self._time_decay_compression,
            'access_frequency': self._access_frequency_compression,
            'semantic_clustering': self._semantic_clustering_compression,
            'hybrid': self._hybrid_compression
        }
        self.min_importance_threshold = config.get('min_importance', 0.3)
        self.time_decay_factor = config.get('time_decay_factor', 0.1)
        self.access_threshold = config.get('access_threshold', 2)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory compression requests
        
        Args:
            input_data: Should contain:
                - conditions: List of all conditions with metadata
                - target_reduction: Target reduction ratio (0-1)
                - strategy: Compression strategy to use
                - preserve_categories: Categories to preserve
        """
        conditions = input_data.get('conditions', [])
        target_reduction = input_data.get('target_reduction', 0.5)
        strategy = input_data.get('strategy', 'hybrid')
        preserve_categories = input_data.get('preserve_categories', ['hard_constraints'])
        
        if not conditions:
            return {
                "status": "success",
                "compressed": 0,
                "removed_conditions": [],
                "consolidated_conditions": []
            }
        
        # Apply compression strategy
        if strategy in self.compression_strategies:
            result = await self.compression_strategies[strategy](
                conditions, target_reduction, preserve_categories
            )
        else:
            result = await self._hybrid_compression(
                conditions, target_reduction, preserve_categories
            )
        
        return result
    
    async def _importance_based_compression(self, conditions: List[Dict[str, Any]], 
                                          target_reduction: float,
                                          preserve_categories: List[str]) -> Dict[str, Any]:
        """Compress based on importance scores"""
        # Filter out preserved categories
        compressible = [c for c in conditions if c.get('category') not in preserve_categories]
        preserved = [c for c in conditions if c.get('category') in preserve_categories]
        
        # Sort by importance score
        compressible.sort(key=lambda x: x.get('importance_score', 0.5))
        
        # Calculate how many to remove
        total_conditions = len(conditions)
        target_size = int(total_conditions * (1 - target_reduction))
        to_remove_count = len(compressible) - max(0, target_size - len(preserved))
        
        # Select conditions to remove
        to_remove = compressible[:to_remove_count]
        to_keep = compressible[to_remove_count:] + preserved
        
        return {
            "status": "success",
            "strategy": "importance_based",
            "original_count": total_conditions,
            "compressed_count": len(to_keep),
            "removed_conditions": [c['id'] for c in to_remove],
            "removed_details": to_remove,
            "compression_ratio": len(to_remove) / total_conditions if total_conditions > 0 else 0
        }
    
    async def _time_decay_compression(self, conditions: List[Dict[str, Any]], 
                                    target_reduction: float,
                                    preserve_categories: List[str]) -> Dict[str, Any]:
        """Compress based on time decay"""
        # Calculate decay scores
        current_time = datetime.now()
        
        for condition in conditions:
            if condition.get('category') in preserve_categories:
                condition['decay_score'] = float('inf')  # Never remove
            else:
                try:
                    timestamp = datetime.fromisoformat(condition.get('timestamp', ''))
                    age_days = (current_time - timestamp).days
                    # Exponential decay
                    import math
                    condition['decay_score'] = math.exp(-self.time_decay_factor * age_days)
                except:
                    condition['decay_score'] = 0.5
        
        # Sort by decay score (lower = older/less important)
        conditions.sort(key=lambda x: x.get('decay_score', 0))
        
        # Remove conditions with lowest decay scores
        target_count = int(len(conditions) * (1 - target_reduction))
        to_remove = conditions[:len(conditions) - target_count]
        to_keep = conditions[len(conditions) - target_count:]
        
        return {
            "status": "success",
            "strategy": "time_decay",
            "original_count": len(conditions),
            "compressed_count": len(to_keep),
            "removed_conditions": [c['id'] for c in to_remove if 'id' in c],
            "removed_details": to_remove,
            "compression_ratio": len(to_remove) / len(conditions) if conditions else 0
        }
    
    async def _access_frequency_compression(self, conditions: List[Dict[str, Any]], 
                                          target_reduction: float,
                                          preserve_categories: List[str]) -> Dict[str, Any]:
        """Compress based on access frequency"""
        # Filter and sort by access count
        compressible = []
        preserved = []
        
        for condition in conditions:
            if condition.get('category') in preserve_categories:
                preserved.append(condition)
            else:
                access_count = condition.get('access_count', 0)
                if access_count is not None and isinstance(access_count, (int, float)) and access_count < self.access_threshold:
                    compressible.append(condition)
                else:
                    preserved.append(condition)
        
        # Sort compressible by access count (handle None values)
        compressible.sort(key=lambda x: x.get('access_count', 0) or 0)
        
        # Calculate removal
        target_size = int(len(conditions) * (1 - target_reduction))
        to_remove_count = max(0, len(conditions) - target_size)
        to_remove = compressible[:to_remove_count]
        
        return {
            "status": "success",
            "strategy": "access_frequency",
            "original_count": len(conditions),
            "compressed_count": len(conditions) - len(to_remove),
            "removed_conditions": [c['id'] for c in to_remove if 'id' in c],
            "removed_details": to_remove,
            "low_access_removed": len(to_remove),
            "compression_ratio": len(to_remove) / len(conditions) if conditions else 0
        }
    
    async def _semantic_clustering_compression(self, conditions: List[Dict[str, Any]], 
                                             target_reduction: float,
                                             preserve_categories: List[str]) -> Dict[str, Any]:
        """Compress by clustering similar conditions"""
        # Group similar conditions
        clusters = self._cluster_conditions(conditions, preserve_categories)
        
        consolidated = []
        removed = []
        
        for cluster in clusters:
            if len(cluster) == 1:
                consolidated.append(cluster[0])
            else:
                # Merge similar conditions
                merged = self._merge_cluster(cluster)
                consolidated.append(merged)
                # Mark others as removed
                for c in cluster[1:]:
                    removed.append(c['id'] if 'id' in c else str(c))
        
        return {
            "status": "success",
            "strategy": "semantic_clustering",
            "original_count": len(conditions),
            "compressed_count": len(consolidated),
            "clusters_found": len(clusters),
            "consolidated_conditions": consolidated,
            "removed_conditions": removed,
            "compression_ratio": len(removed) / len(conditions) if conditions else 0
        }
    
    async def _hybrid_compression(self, conditions: List[Dict[str, Any]], 
                                target_reduction: float,
                                preserve_categories: List[str]) -> Dict[str, Any]:
        """Hybrid compression using multiple strategies"""
        # Calculate composite scores
        current_time = datetime.now()
        
        for condition in conditions:
            if condition.get('category') in preserve_categories:
                condition['compression_score'] = float('inf')  # Never compress
            else:
                # Importance component
                importance = condition.get('importance_score', 0.5)
                
                # Time decay component
                try:
                    timestamp = datetime.fromisoformat(condition.get('timestamp', ''))
                    age_days = (current_time - timestamp).days
                    import math
                    time_score = math.exp(-self.time_decay_factor * age_days)
                except:
                    time_score = 0.5
                
                # Access frequency component
                access_count = condition.get('access_count', 0)
                access_score = min(1.0, access_count / 10)  # Normalize to 0-1
                
                # Composite score (higher = keep)
                condition['compression_score'] = (
                    0.4 * importance +
                    0.3 * time_score +
                    0.3 * access_score
                )
        
        # Sort by compression score (handle None values)
        conditions.sort(key=lambda x: x.get('compression_score', 0) or 0)
        
        # Determine removal threshold
        target_count = int(len(conditions) * (1 - target_reduction))
        to_remove = []
        to_keep = []
        
        for i, condition in enumerate(conditions):
            if condition.get('compression_score', 0) == float('inf'):
                to_keep.append(condition)
            elif len(to_keep) < target_count:
                compression_score = condition.get('compression_score', 0)
                if compression_score is not None and compression_score < self.min_importance_threshold:
                    to_remove.append(condition)
                else:
                    to_keep.append(condition)
            else:
                to_remove.append(condition)
        
        # Try to consolidate similar conditions in to_keep
        consolidated_keep = self._consolidate_similar(to_keep)
        
        return {
            "status": "success",
            "strategy": "hybrid",
            "original_count": len(conditions),
            "compressed_count": len(consolidated_keep),
            "removed_conditions": [c['id'] for c in to_remove if 'id' in c],
            "removed_details": to_remove,
            "consolidated_count": len(to_keep) - len(consolidated_keep),
            "compression_ratio": (len(to_remove) + len(to_keep) - len(consolidated_keep)) / len(conditions) if conditions else 0,
            "compression_stats": {
                "below_threshold": sum(1 for c in to_remove if (c.get('compression_score') or 0) < self.min_importance_threshold),
                "time_decay": sum(1 for c in to_remove if (c.get('compression_score') or 0) < 0.5),
                "low_access": sum(1 for c in to_remove if (c.get('access_count') or 0) < self.access_threshold)
            }
        }
    
    def _cluster_conditions(self, conditions: List[Dict[str, Any]], 
                           preserve_categories: List[str]) -> List[List[Dict[str, Any]]]:
        """Cluster similar conditions"""
        clusters = []
        used = set()
        
        for i, cond1 in enumerate(conditions):
            if i in used or cond1.get('category') in preserve_categories:
                continue
                
            cluster = [cond1]
            used.add(i)
            
            for j, cond2 in enumerate(conditions[i+1:], i+1):
                if j in used or cond2.get('category') in preserve_categories:
                    continue
                    
                if self._are_similar(cond1, cond2):
                    cluster.append(cond2)
                    used.add(j)
            
            clusters.append(cluster)
        
        # Add unclustered preserved conditions
        for i, cond in enumerate(conditions):
            if i not in used:
                clusters.append([cond])
        
        return clusters
    
    def _are_similar(self, cond1: Dict[str, Any], cond2: Dict[str, Any]) -> bool:
        """Check if two conditions are similar enough to merge"""
        # Same category check
        if cond1.get('category') != cond2.get('category'):
            return False
        
        # Text similarity (simple word overlap)
        text1 = set(cond1.get('text', '').lower().split())
        text2 = set(cond2.get('text', '').lower().split())
        
        if not text1 or not text2:
            return False
        
        overlap = len(text1 & text2)
        union = len(text1 | text2)
        
        similarity = overlap / union if union > 0 else 0
        return similarity > 0.7
    
    def _merge_cluster(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a cluster of similar conditions"""
        # Use the most important/recent as base
        cluster.sort(key=lambda x: (x.get('importance_score', 0), x.get('source_turn', 0)), reverse=True)
        
        merged = cluster[0].copy()
        
        # Combine text if significantly different
        texts = [c.get('text', '') for c in cluster]
        unique_texts = list(set(texts))
        
        if len(unique_texts) > 1:
            merged['text'] = ' OR '.join(unique_texts[:3])  # Limit to 3
            merged['merged_from'] = [c.get('id', '') for c in cluster[1:]]
        
        # Update importance to max
        merged['importance_score'] = max(c.get('importance_score', 0) for c in cluster)
        
        # Sum access counts
        merged['access_count'] = sum(c.get('access_count', 0) for c in cluster)
        
        return merged
    
    def _consolidate_similar(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Consolidate similar conditions in a list"""
        if len(conditions) <= 1:
            return conditions
        
        consolidated = []
        used = set()
        
        for i, cond1 in enumerate(conditions):
            if i in used:
                continue
                
            similar_group = [cond1]
            
            for j, cond2 in enumerate(conditions[i+1:], i+1):
                if j not in used and self._are_similar(cond1, cond2):
                    similar_group.append(cond2)
                    used.add(j)
            
            if len(similar_group) > 1:
                consolidated.append(self._merge_cluster(similar_group))
            else:
                consolidated.append(cond1)
        
        return consolidated