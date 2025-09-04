from typing import Dict, Any, List, Optional, Tuple
from .base import BaseAgent
import re
from datetime import datetime

class ConflictResolverAgent(BaseAgent):
    """Agent for detecting and resolving conflicts between conditions using reasoning"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ConflictResolver", config)
        self.api_client = None
        self.conflict_types = [
            'direct_contradiction',
            'temporal_conflict', 
            'logical_inconsistency',
            'priority_conflict',
            'scope_overlap'
        ]
        self.resolution_strategies = {
            'direct_contradiction': self._resolve_direct_contradiction,
            'temporal_conflict': self._resolve_temporal_conflict,
            'logical_inconsistency': self._resolve_logical_inconsistency,
            'priority_conflict': self._resolve_priority_conflict,
            'scope_overlap': self._resolve_scope_overlap
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process conflict resolution requests
        
        Args:
            input_data: Should contain:
                - conflicts: List of detected conflicts
                - memory_state: Current memory state
                - use_reasoning: Whether to use reasoning API
        """
        conflicts = input_data.get('conflicts', [])
        memory_state = input_data.get('memory_state', {})
        use_reasoning = input_data.get('use_reasoning', True)
        
        resolutions = []
        
        for conflict in conflicts:
            # Analyze conflict type if not provided
            if 'type' not in conflict:
                conflict['type'] = await self._analyze_conflict_type(conflict, use_reasoning)
            
            # Resolve conflict
            resolution = await self._resolve_conflict(conflict, memory_state, use_reasoning)
            if resolution:
                resolutions.append(resolution)
        
        return {
            "status": "success",
            "resolved_conflicts": len(resolutions),
            "resolutions": resolutions,
            "unresolved": len(conflicts) - len(resolutions)
        }
    
    async def _analyze_conflict_type(self, conflict: Dict[str, Any], use_reasoning: bool) -> str:
        """Analyze and determine the type of conflict"""
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        if use_reasoning and self.api_client:
            # Use reasoning API for complex analysis
            prompt = self._build_analysis_prompt(cond1, cond2)
            try:
                response = await self.api_client.generate(prompt)
                conflict_type = self._parse_conflict_type(response)
                return conflict_type
            except:
                pass
        
        # Fallback to rule-based analysis
        return self._rule_based_conflict_detection(cond1, cond2)
    
    async def _resolve_conflict(self, conflict: Dict[str, Any], memory_state: Dict[str, Any], 
                              use_reasoning: bool) -> Optional[Dict[str, Any]]:
        """Resolve a conflict based on its type"""
        conflict_type = conflict.get('type', 'unknown')
        
        # Use specific resolution strategy
        if conflict_type in self.resolution_strategies:
            resolution = await self.resolution_strategies[conflict_type](conflict, memory_state)
        else:
            # Use reasoning for unknown conflict types
            if use_reasoning and self.api_client:
                resolution = await self._reasoning_based_resolution(conflict, memory_state)
            else:
                resolution = self._default_resolution(conflict)
        
        if resolution:
            resolution['conflict_id'] = conflict.get('id', '')
            resolution['timestamp'] = datetime.now().isoformat()
            resolution['conflict_type'] = conflict_type
        
        return resolution
    
    def _build_analysis_prompt(self, cond1: Dict[str, Any], cond2: Dict[str, Any]) -> str:
        """Build prompt for conflict type analysis"""
        return f"""<think>
Analyze the relationship between these two conditions:

Condition 1:
- Text: {cond1.get('text', '')}
- Category: {cond1.get('category', '')}
- Source Turn: {cond1.get('source_turn', '')}

Condition 2:
- Text: {cond2.get('text', '')}
- Category: {cond2.get('category', '')}
- Source Turn: {cond2.get('source_turn', '')}

Determine if these conditions conflict and identify the type:
1. direct_contradiction: Conditions directly oppose each other
2. temporal_conflict: Time-based inconsistency
3. logical_inconsistency: Logically incompatible
4. priority_conflict: Different priority levels for same aspect
5. scope_overlap: Overlapping but potentially compatible

Provide the conflict type and explanation.
</think>

Conflict analysis:"""
    
    def _rule_based_conflict_detection(self, cond1: Dict[str, Any], cond2: Dict[str, Any]) -> str:
        """Rule-based conflict type detection"""
        text1 = cond1.get('text', '').lower()
        text2 = cond2.get('text', '').lower()
        cat1 = cond1.get('category', '')
        cat2 = cond2.get('category', '')
        
        # Direct contradiction
        negation_words = ['not', 'no', 'never', 'without', "don't", "doesn't", "won't"]
        if any(neg in text1 for neg in negation_words) and any(neg in text2 for neg in negation_words):
            # Check if they negate the same thing
            clean1 = re.sub(r'\b(' + '|'.join(negation_words) + r')\b', '', text1).strip()
            clean2 = re.sub(r'\b(' + '|'.join(negation_words) + r')\b', '', text2).strip()
            if clean1 == clean2:
                return 'direct_contradiction'
        
        # Temporal conflict
        time_indicators = ['today', 'tomorrow', 'yesterday', 'morning', 'afternoon', 
                          'evening', 'night', 'week', 'month', 'year']
        if any(time in text1 for time in time_indicators) and any(time in text2 for time in time_indicators):
            if cat1 == 'temporal_conditions' or cat2 == 'temporal_conditions':
                return 'temporal_conflict'
        
        # Priority conflict
        if cat1 == 'hard_constraints' and cat2 == 'soft_preferences':
            if self._check_same_topic(text1, text2):
                return 'priority_conflict'
        
        # Scope overlap
        if self._check_partial_overlap(text1, text2):
            return 'scope_overlap'
        
        return 'logical_inconsistency'
    
    def _check_same_topic(self, text1: str, text2: str) -> bool:
        """Check if two texts refer to the same topic"""
        # Simple word overlap check
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on', 'at'}
        words1 -= common_words
        words2 -= common_words
        
        overlap = len(words1 & words2)
        return overlap >= min(len(words1), len(words2)) * 0.3
    
    def _check_partial_overlap(self, text1: str, text2: str) -> bool:
        """Check if texts have partial overlap"""
        return self._check_same_topic(text1, text2) and text1 != text2
    
    async def _resolve_direct_contradiction(self, conflict: Dict[str, Any], 
                                          memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve direct contradictions"""
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        # Resolution strategies:
        # 1. Recency: Keep the more recent condition
        # 2. Source reliability: Prefer explicit user statements
        # 3. Category priority: Hard constraints > negations > soft preferences
        
        # Check recency
        turn1 = cond1.get('source_turn', 0)
        turn2 = cond2.get('source_turn', 0)
        
        if turn2 > turn1:  # cond2 is more recent
            return {
                'action': 'replace',
                'keep_condition_id': cond2.get('id'),
                'remove_condition_id': cond1.get('id'),
                'reason': 'More recent condition takes precedence'
            }
        else:
            return {
                'action': 'replace',
                'keep_condition_id': cond1.get('id'),
                'remove_condition_id': cond2.get('id'),
                'reason': 'More recent condition takes precedence'
            }
    
    async def _resolve_temporal_conflict(self, conflict: Dict[str, Any], 
                                       memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve temporal conflicts"""
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        # For temporal conflicts, we can often merge or update
        return {
            'action': 'update_temporal',
            'condition_id': cond1.get('id'),
            'new_temporal_value': cond2.get('text'),
            'reason': 'Updated temporal constraint to most recent specification'
        }
    
    async def _resolve_logical_inconsistency(self, conflict: Dict[str, Any], 
                                           memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve logical inconsistencies"""
        # This requires more complex reasoning
        # For now, use category priority
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        priority_order = ['hard_constraints', 'negations', 'temporal_conditions', 'soft_preferences']
        
        cat1_priority = priority_order.index(cond1.get('category', 'soft_preferences'))
        cat2_priority = priority_order.index(cond2.get('category', 'soft_preferences'))
        
        if cat1_priority < cat2_priority:
            return {
                'action': 'keep_higher_priority',
                'keep_condition_id': cond1.get('id'),
                'remove_condition_id': cond2.get('id'),
                'reason': f"Hard constraint takes precedence over {cond2.get('category')}"
            }
        else:
            return {
                'action': 'keep_higher_priority',
                'keep_condition_id': cond2.get('id'),
                'remove_condition_id': cond1.get('id'),
                'reason': f"Hard constraint takes precedence over {cond1.get('category')}"
            }
    
    async def _resolve_priority_conflict(self, conflict: Dict[str, Any], 
                                       memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve priority conflicts"""
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        # Convert soft preference to hard constraint if user insists
        if cond1.get('category') == 'hard_constraints':
            return {
                'action': 'upgrade_priority',
                'condition_id': cond2.get('id'),
                'new_category': 'hard_constraints',
                'reason': 'User expressed this as a hard requirement'
            }
        else:
            return {
                'action': 'upgrade_priority',
                'condition_id': cond1.get('id'),
                'new_category': 'hard_constraints',
                'reason': 'User expressed this as a hard requirement'
            }
    
    async def _resolve_scope_overlap(self, conflict: Dict[str, Any], 
                                   memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve scope overlaps"""
        # For overlapping scopes, we can often merge or clarify
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        return {
            'action': 'merge',
            'primary_condition_id': cond2.get('id'),  # Keep more recent
            'merge_from_id': cond1.get('id'),
            'merged_text': f"{cond1.get('text', '')} AND {cond2.get('text', '')}",
            'reason': 'Merged overlapping conditions for clarity'
        }
    
    async def _reasoning_based_resolution(self, conflict: Dict[str, Any], 
                                        memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use reasoning API for complex conflict resolution"""
        prompt = f"""<think>
Given this conflict between conditions:
{conflict}

And the current memory state:
{memory_state}

Determine the best resolution strategy. Consider:
1. User intent and preferences
2. Temporal ordering
3. Explicit vs implicit statements
4. Category priorities

Provide a resolution with action and reasoning.
</think>

Resolution:"""
        
        try:
            response = await self.api_client.generate(prompt)
            return self._parse_resolution(response)
        except:
            return self._default_resolution(conflict)
    
    def _default_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Default resolution when other methods fail"""
        cond1 = conflict.get('condition1', {})
        cond2 = conflict.get('condition2', {})
        
        # Default: keep more recent
        if cond2.get('source_turn', 0) > cond1.get('source_turn', 0):
            return {
                'action': 'keep_recent',
                'keep_condition_id': cond2.get('id'),
                'remove_condition_id': cond1.get('id'),
                'reason': 'Defaulting to more recent condition'
            }
        else:
            return {
                'action': 'keep_recent',
                'keep_condition_id': cond1.get('id'),
                'remove_condition_id': cond2.get('id'),
                'reason': 'Defaulting to more recent condition'
            }
    
    def _parse_conflict_type(self, response: str) -> str:
        """Parse conflict type from API response"""
        response_lower = response.lower()
        
        for conflict_type in self.conflict_types:
            if conflict_type.replace('_', ' ') in response_lower:
                return conflict_type
        
        return 'logical_inconsistency'  # Default
    
    def _parse_resolution(self, response: str) -> Dict[str, Any]:
        """Parse resolution from API response"""
        # Simple parsing - in production, use more robust parsing
        resolution = {
            'action': 'resolve',
            'details': response,
            'reason': 'Resolved using reasoning model'
        }
        
        return resolution
    
    async def resolve_conflicts(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve conflicts between conditions
        
        Args:
            conditions: List of conditions that may have conflicts
            
        Returns:
            List of resolved conditions
        """
        try:
            # Use the process method to handle conflict resolution
            input_data = {
                'conditions': conditions,
                'memory_state': {}
            }
            
            result = await self.process(input_data)
            
            # Return the resolved conditions
            if result.get('status') == 'success':
                return result.get('resolved_conditions', conditions)
            else:
                # If resolution failed, return original conditions
                return conditions
                
        except Exception as e:
            self.logger.error(f"Error in resolve_conflicts: {str(e)}")
            # Return original conditions if error occurs
            return conditions