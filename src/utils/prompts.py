from typing import Dict, List, Any, Optional

class PromptTemplates:
    """Collection of prompt templates for different agents"""
    
    @staticmethod
    def condition_extraction_prompt(dialogue_history: List[Dict], current_query: str) -> str:
        """Template for condition extraction"""
        history_text = "\n".join([
            f"Turn {i+1} [{turn.get('role', 'user')}]: {turn.get('content', '')}"
            for i, turn in enumerate(dialogue_history)
        ])
        
        return f"""<think>
Analyze the following dialogue history and current query to extract all conditions, constraints, and preferences.

Dialogue History:
{history_text}

Current Query: {current_query}

I need to identify and categorize:
1. Hard Constraints (must be satisfied): Requirements that the user explicitly demands or insists upon
2. Soft Preferences (should be satisfied if possible): Things the user prefers but are not mandatory
3. Temporal Conditions (time-related): Any time-based requirements or constraints
4. Negations (must be excluded): Things the user explicitly doesn't want or wants to avoid

For each condition, I should provide:
- The condition text (exact phrase or paraphrased requirement)
- The source turn number where it appeared
- Confidence level (high/medium/low) based on how explicitly it was stated
- Any relevant context that clarifies the condition

Let me analyze each turn:
{self._analyze_turns_for_extraction(dialogue_history, current_query)}
</think>

Based on my analysis, here are the extracted conditions in JSON format:

{{
  "hard_constraints": [
    // Conditions that MUST be satisfied
  ],
  "soft_preferences": [
    // Conditions that SHOULD be satisfied if possible
  ],
  "temporal_conditions": [
    // Time-related conditions
  ],
  "negations": [
    // Things to avoid or exclude
  ]
}}"""
    
    @staticmethod
    def _analyze_turns_for_extraction(dialogue_history: List[Dict], current_query: str) -> str:
        """Helper to analyze turns for condition extraction"""
        analysis = []
        all_turns = dialogue_history + [{"role": "user", "content": current_query}]
        
        for i, turn in enumerate(all_turns):
            if turn.get('role') == 'user':
                content = turn.get('content', '')
                analysis.append(f"""
Turn {i+1}: "{content}"
- Look for explicit requirements (must, need, require, have to)
- Look for preferences (want, like, prefer, interested in)
- Look for temporal references (today, tomorrow, by X date, etc.)
- Look for negations (don't, not, never, without, avoid, except)
- Consider context from previous turns""")
        
        return "\n".join(analysis)
    
    @staticmethod
    def conflict_analysis_prompt(condition1: Dict[str, Any], condition2: Dict[str, Any]) -> str:
        """Template for conflict analysis"""
        return f"""<think>
I need to analyze the relationship between these two conditions to determine if they conflict:

Condition 1:
- Text: "{condition1.get('text', '')}"
- Category: {condition1.get('category', '')}
- Source Turn: {condition1.get('source_turn', '')}
- Confidence: {condition1.get('confidence', '')}

Condition 2:
- Text: "{condition2.get('text', '')}"
- Category: {condition2.get('category', '')}
- Source Turn: {condition2.get('source_turn', '')}
- Confidence: {condition2.get('confidence', '')}

Types of conflicts to check for:
1. Direct Contradiction: Conditions explicitly oppose each other (e.g., "I want X" vs "I don't want X")
2. Temporal Conflict: Time-based inconsistency (e.g., "today" vs "tomorrow" for same task)
3. Logical Inconsistency: Conditions that cannot be satisfied simultaneously
4. Priority Conflict: Same topic with different urgency levels (hard constraint vs preference)
5. Scope Overlap: Overlapping but potentially incompatible requirements

Let me check each type:
- Do they directly contradict each other?
- Are there temporal inconsistencies?
- Can both be logically satisfied?
- Do they have different priority levels for the same topic?
- Do they overlap in scope but differ in specifics?
</think>

Conflict Analysis Result:
Type: [conflict_type]
Explanation: [detailed explanation of the conflict]
Severity: [low/medium/high]
Recommendation: [suggested resolution approach]"""
    
    @staticmethod
    def conflict_resolution_prompt(conflict: Dict[str, Any], memory_state: Dict[str, Any]) -> str:
        """Template for conflict resolution"""
        return f"""<think>
I need to resolve this conflict between conditions:

Conflict Details:
{conflict}

Current Memory State:
- Total conditions: {len(memory_state.get('conditions', []))}
- Hard constraints: {len([c for c in memory_state.get('conditions', []) if c.get('category') == 'hard_constraints'])}
- Soft preferences: {len([c for c in memory_state.get('conditions', []) if c.get('category') == 'soft_preferences'])}

Resolution Strategies to Consider:
1. Recency: Keep the more recent condition (user changed their mind)
2. Priority: Hard constraints override preferences
3. Specificity: More specific conditions override general ones
4. User intent: Try to understand what the user really wants
5. Merge: Combine compatible aspects of both conditions
6. Clarify: Ask user for clarification (if interactive)

Factors to consider:
- Which condition was stated more recently?
- Which has higher importance/priority?
- Can they be merged or modified to be compatible?
- What would best serve the user's intent?
</think>

Resolution Strategy:
Action: [keep_first/keep_second/merge/modify/ask_clarification]
Reasoning: [explanation of why this resolution is best]
Implementation: [specific steps to implement the resolution]"""
    
    @staticmethod
    def generation_prompt(query: str, documents: List[Dict[str, Any]], 
                         conditions: List[Dict[str, Any]], 
                         conversation_history: List[Dict[str, Any]]) -> str:
        """Template for response generation"""
        # Format conversation history
        history_text = ""
        if conversation_history:
            recent_history = conversation_history[-5:]  # Last 5 turns
            history_text = "\n".join([
                f"{turn.get('role', 'user').upper()}: {turn.get('content', '')}"
                for turn in recent_history
            ])
        
        # Format conditions by category
        conditions_text = ""
        if conditions:
            by_category = {}
            for condition in conditions:
                category = condition.get('category', 'other')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(condition.get('text', ''))
            
            if 'hard_constraints' in by_category:
                conditions_text += f"\nMUST SATISFY (Hard Constraints):\n"
                conditions_text += "\n".join([f"- {text}" for text in by_category['hard_constraints']])
            
            if 'soft_preferences' in by_category:
                conditions_text += f"\nSHOULD CONSIDER (Preferences):\n"
                conditions_text += "\n".join([f"- {text}" for text in by_category['soft_preferences'][:5]])
            
            if 'temporal_conditions' in by_category:
                conditions_text += f"\nTIME-RELATED:\n"
                conditions_text += "\n".join([f"- {text}" for text in by_category['temporal_conditions']])
            
            if 'negations' in by_category:
                conditions_text += f"\nAVOID/EXCLUDE:\n"
                conditions_text += "\n".join([f"- {text}" for text in by_category['negations']])
        
        # Format documents
        documents_text = ""
        if documents:
            documents_text = "\n=== RELEVANT INFORMATION ===\n"
            for i, doc_data in enumerate(documents[:5]):  # Top 5 documents
                doc = doc_data.get('document', {})
                metadata = doc_data.get('metadata', {})
                title = metadata.get('title', f"Document {i+1}")
                content = doc.get('text', doc.get('content', str(doc)))
                
                if len(content) > 500:
                    content = content[:500] + "..."
                
                documents_text += f"\n[{title}]\n{content}\n"
        
        return f"""You are an AI assistant that provides helpful, accurate responses while adhering to user preferences and constraints. Consider the conversation history, retrieved documents, and user conditions when generating your response.

{f"=== CONVERSATION HISTORY ===\n{history_text}" if history_text else ""}

{f"=== USER CONDITIONS & PREFERENCES ==={conditions_text}" if conditions_text else ""}

{documents_text}

=== CURRENT QUERY ===
{query}

=== INSTRUCTIONS ===
Please provide a comprehensive response that:
1. Directly addresses the user's query
2. Satisfies all hard constraints (if any)
3. Considers user preferences when possible
4. Uses information from the provided documents (if any)
5. Maintains consistency with conversation history
6. Avoids content that violates user exclusions
7. Is helpful, accurate, and well-structured

Response:"""
    
    @staticmethod
    def memory_compression_prompt(conditions: List[Dict[str, Any]], target_reduction: float) -> str:
        """Template for memory compression decision making"""
        return f"""<think>
I need to compress the memory by removing approximately {target_reduction*100:.0f}% of conditions while preserving the most important ones.

Current Conditions ({len(conditions)} total):
{PromptTemplates._format_conditions_for_compression(conditions)}

Compression Strategy:
1. Always preserve hard constraints (highest priority)
2. Consider importance scores and access frequency
3. Consider recency (newer conditions often more relevant)
4. Look for redundant or overlapping conditions that can be merged
5. Remove low-confidence, rarely accessed conditions first

Factors to evaluate for each condition:
- Category (hard constraints > negations > temporal > preferences)
- Importance score
- Access frequency
- Recency
- Confidence level
- Redundancy with other conditions
</think>

Compression Recommendations:
[Provide specific recommendations for which conditions to remove, merge, or keep]"""
    
    @staticmethod
    def _format_conditions_for_compression(conditions: List[Dict[str, Any]]) -> str:
        """Helper to format conditions for compression analysis"""
        formatted = []
        for i, condition in enumerate(conditions[:20]):  # Limit to first 20 for prompt length
            formatted.append(f"""
{i+1}. "{condition.get('text', '')[:100]}{'...' if len(condition.get('text', '')) > 100 else ''}"
   - Category: {condition.get('category', '')}
   - Importance: {condition.get('importance_score', 0):.2f}
   - Access Count: {condition.get('access_count', 0)}
   - Source Turn: {condition.get('source_turn', '')}
   - Confidence: {condition.get('confidence', '')}""")
        
        if len(conditions) > 20:
            formatted.append(f"\n... and {len(conditions) - 20} more conditions")
        
        return "\n".join(formatted)