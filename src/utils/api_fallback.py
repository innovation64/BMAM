#!/usr/bin/env python3
"""
Fallback implementations for when APIs are not available
"""

import re
from typing import Dict, List, Any
import json

class FallbackConditionExtractor:
    """Fallback condition extractor using pattern matching"""
    
    def __init__(self):
        # Add feedback refinement patterns
        self.feedback_patterns = [
            r"add (?:specific )?quantities? to (.+?)(?:\.|,|$)",
            r"include (?:specific )?quantities? (?:in|to) (.+?)(?:\.|,|$)",
            r"improve (?:the |this )?(.+?) by adding (.+?)(?:\.|,|$)",
            r"please (?:add|include|improve) (.+?)(?:\.|,|$)",
            r"can you (?:add|include|improve) (.+?)(?:\.|,|$)",
            r"(?:add|include) (.+?) to (?:the |this )?(.+?)(?:\.|,|$)",
            r"make (?:the |this )?(.+?) more (.+?)(?:\.|,|$)",
            r"(?:refine|improve|enhance|update) (?:the |this )?(.+?)(?:\.|,|$)"
        ]
        
        self.job_patterns = [
            r"I (?:have a |work as a |am a |do |have a secondary job as a )(.+?)(?:\.|,|$)",
            r"My (?:job|work|occupation) is (.+?)(?:\.|,|$)",
            r"I work (.+?)(?:\.|,|$)",
            r"(?:secondary job|side job|part-time job) as (.+?)(?:\.|,|$)",
            r"It's (?:pretty |really |very |quite )?(.+?) work",
            r"(?:messy|difficult|easy|hard|challenging) work",
        ]
        
        self.preference_patterns = [
            r"I (?:love|like|enjoy|prefer) (.+?)(?:\.|,|!|$)",
            r"I (?:really|absolutely) (?:love|like|enjoy) (.+?)(?:\.|,|!|$)",
        ]
        
        self.biographical_patterns = [
            r"I (?:have|am|work|live) (.+?)(?:\.|,|$)",
            r"My (.+?) (?:is|are|was|were) (.+?)(?:\.|,|$)",
            r"I (?:moved to|am from|live in) (.+?)(?:\.|,|$)",
            r"(.+?) is my (.+?)(?:\.|,|$)",
        ]
        
        self.negation_patterns = [
            r"I (?:don't|do not|don't) (?:like|want|need) (.+?)(?:\.|,|$)",
            r"I (?:dislike|hate|avoid) (.+?)(?:\.|,|$)",
            r"(?:don't|do not|not) (.+?)(?:\.|,|$)",
        ]
        
        self.temporal_patterns = [
            r"(?:last|this|next) (?:year|month|week|day) (.+?)(?:\.|,|$)",
            r"(?:recently|yesterday|today|tomorrow) (.+?)(?:\.|,|$)",
            r"(?:in|during|after|before) (.+?)(?:\.|,|$)",
        ]
    
    def extract_conditions(self, dialogue_history: List[Dict], current_query: str = "") -> Dict[str, List]:
        """Extract conditions using pattern matching"""
        
        conditions = {
            "hard_constraints": [],
            "soft_preferences": [],
            "biographical_facts": [],
            "temporal_conditions": [],
            "negations": [],
            "feedback_requests": []  # Add new category for feedback
        }
        
        # Process each turn in dialogue history
        for turn_idx, turn in enumerate(dialogue_history, 1):
            if turn.get('role') == 'user':
                content = turn.get('content', '').strip()
                if content:
                    self._extract_from_text(content, turn_idx, conditions)
        
        # Also extract from current query if provided
        if current_query:
            self._extract_from_text(current_query, len(dialogue_history) + 1, conditions)
        
        # Remove duplicates
        self._remove_duplicates(conditions)
        
        return conditions
    
    def _extract_from_text(self, text: str, source_turn: int, conditions: Dict[str, List]):
        """Extract conditions from a single text"""
        
        # Extract biographical facts (jobs, personal info)
        for pattern in self.biographical_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_biographical_content(match.group(1)):
                    conditions["biographical_facts"].append({
                        "text": match.group(0).strip().rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "high",
                        "category": "biographical_facts"
                    })
        
        # Extract job-specific information
        for pattern in self.job_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                job_info = match.group(1).strip()
                if job_info and len(job_info) > 2:
                    conditions["biographical_facts"].append({
                        "text": match.group(0).strip().rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "high",
                        "category": "biographical_facts"
                    })
        
        # Extract preferences
        for pattern in self.preference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                preference = match.group(1).strip()
                if preference and len(preference) > 2:
                    conditions["soft_preferences"].append({
                        "text": match.group(0).strip().rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "high",
                        "category": "soft_preferences"
                    })
        
        # Extract negations
        for pattern in self.negation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                negation = match.group(1).strip()
                if negation and len(negation) > 2:
                    conditions["negations"].append({
                        "text": match.group(0).strip().rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "high",
                        "category": "negations"
                    })
        
        # Extract temporal conditions
        for pattern in self.temporal_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                temporal = match.group(0).strip()
                if temporal and len(temporal) > 3:
                    conditions["temporal_conditions"].append({
                        "text": temporal.rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "medium",
                        "category": "temporal_conditions"
                    })
        
        # Extract feedback requests (add, improve, refine patterns)
        for pattern in self.feedback_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                feedback_text = match.group(0).strip()
                if feedback_text and len(feedback_text) > 5:
                    conditions["feedback_requests"].append({
                        "text": feedback_text.rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "high",
                        "category": "feedback_requests",
                        "feedback_type": self._classify_feedback_type(feedback_text)
                    })
        
        # Extract hard constraints (must, need, require)
        constraint_patterns = [
            r"I (?:must|need|require|have to) (.+?)(?:\.|,|$)",
            r"(?:must|need|require) (.+?)(?:\.|,|$)",
        ]
        
        for pattern in constraint_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                constraint = match.group(1).strip()
                if constraint and len(constraint) > 2:
                    conditions["hard_constraints"].append({
                        "text": match.group(0).strip().rstrip('.,!'),
                        "source_turn": source_turn,
                        "confidence": "high",
                        "category": "hard_constraints"
                    })
    
    def _is_biographical_content(self, text: str) -> bool:
        """Check if text contains biographical information"""
        biographical_keywords = [
            'job', 'work', 'occupation', 'plumber', 'teacher', 'doctor', 'engineer',
            'family', 'brother', 'sister', 'father', 'mother', 'children', 'child',
            'live', 'moved', 'from', 'city', 'state', 'country',
            'secondary', 'side', 'part-time', 'full-time',
            'messy', 'difficult', 'easy', 'pays well', 'challenging'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in biographical_keywords)
    
    def _remove_duplicates(self, conditions: Dict[str, List]):
        """Remove duplicate and similar conditions within each category"""
        for category in conditions:
            if not conditions[category]:
                continue
                
            unique_conditions = []
            
            for condition in conditions[category]:
                text = condition.get('text', '').lower().strip()
                if text:
                    # Check if this text is substantially different from existing ones
                    is_duplicate = False
                    for existing in unique_conditions:
                        existing_text = existing.get('text', '').lower().strip()
                        
                        # Check if one text contains the other (substring match)
                        if text in existing_text or existing_text in text:
                            # Keep the longer, more descriptive version
                            if len(text) > len(existing_text):
                                unique_conditions.remove(existing)
                                break
                            else:
                                is_duplicate = True
                                break
                    
                    if not is_duplicate:
                        unique_conditions.append(condition)
            
            conditions[category] = unique_conditions
    
    def _classify_feedback_type(self, feedback_text: str) -> str:
        """Classify the type of feedback request"""
        text_lower = feedback_text.lower()
        
        if "quantit" in text_lower:
            return "add_quantities"
        elif any(word in text_lower for word in ["improve", "enhance", "better"]):
            return "general_improvement"
        elif any(word in text_lower for word in ["add", "include"]):
            return "add_information"
        elif any(word in text_lower for word in ["refine", "update"]):
            return "refinement"
        else:
            return "general_feedback"
    
    def classify_response_style_needed(self, text: str, conversation_history: List[Dict] = None) -> str:
        """Classify what response style is needed based on query type"""
        text_lower = text.lower()
        
        # Check for feedback requests first - always detailed
        for pattern in self.feedback_patterns:
            if re.search(pattern, text_lower):
                return 'detailed'  # Feedback always needs detailed responses
        
        # Programming/technical questions need detailed responses
        technical_indicators = [
            'function', 'method', 'code', 'class', 'algorithm', 'implementation', 
            'how does', 'how would', 'explain', 'what does', 'how to', 'why does',
            'variable', 'parameter', 'return', 'api', 'library', 'framework',
            'debug', 'error', 'exception', 'syntax', 'compile', 'execute'
        ]
        if any(indicator in text_lower for indicator in technical_indicators):
            return 'detailed'
        
        # List/step-by-step requests need detailed responses 
        list_indicators = ['list', 'steps', 'guide', 'tutorial', 'instructions', 'recipe', 'plan']
        if any(indicator in text_lower for indicator in list_indicators):
            return 'detailed'
        
        # Grocery/shopping lists specifically need detailed responses
        if any(word in text_lower for word in ['grocery', 'shopping', 'ingredients', 'meal']):
            return 'detailed'
        
        # Questions asking for explanations need detailed responses
        explanation_indicators = ['explain', 'describe', 'tell me about', 'what is', 'how is', 'why is']
        if any(indicator in text_lower for indicator in explanation_indicators):
            return 'detailed'
        
        # Continuing dialogue from technical context needs detailed responses
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Check last 3 messages
            for msg in recent_messages:
                msg_content = msg.get('content', '').lower()
                if any(tech in msg_content for tech in technical_indicators):
                    return 'detailed'  # Continue technical discussions with detail
        
        # Default to simple for basic queries
        return 'simple'


class FallbackGenerator:
    """Fallback response generator"""
    
    def generate_response(self, query: str, conditions: Dict, documents: List) -> str:
        """Generate simple response based on available information"""
        
        # Try to find relevant information
        relevant_info = []
        
        # Check documents for relevant content
        for doc in documents:
            if isinstance(doc, dict):
                content = doc.get('document', {}).get('content', '')
                if content and any(word in content.lower() for word in query.lower().split()):
                    relevant_info.append(content)
        
        # Check conditions for relevant information
        if isinstance(conditions, dict):
            for category, items in conditions.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            text = item.get('text', '')
                            if text and any(word in text.lower() for word in query.lower().split()):
                                relevant_info.append(text)
        
        if relevant_info:
            # Return the most relevant information
            return relevant_info[0]
        else:
            return "I don't have specific information about that."