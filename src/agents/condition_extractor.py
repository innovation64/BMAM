import json
from typing import Dict, Any, List, Optional
from .base import BaseAgent
import asyncio
import re

class ConditionExtractorAgent(BaseAgent):
    """Agent for extracting conditions from dialogue history using reasoning models"""
    
    def __init__(self, api_client=None, config: Optional[Dict[str, Any]] = None):
        super().__init__("ConditionExtractor", config)
        self.api_client = api_client
        self.condition_types = ["hard_constraints", "soft_preferences", "biographical_facts", "temporal_conditions", "negations", "feedback_requests"]
        
        # Set default parameters
        self.max_tokens = config.get('max_tokens', 1000) if config else 1000
        self.temperature = config.get('temperature', 0.0) if config else 0.0
        
        # Initialize API client if config is provided and no api_client passed
        if not self.api_client and config:
            self._initialize_api_client(config)
    
    def _initialize_api_client(self, config: Dict[str, Any]):
        """Initialize API client based on configuration"""
        try:
            import os
            import sys
            from pathlib import Path
            from openai import AsyncOpenAI
            
            # Add utils to path
            sys.path.append(str(Path(__file__).parent.parent))
            from utils.ensure_api import ensure_openai_api
            
            # Ensure API key is loaded
            if ensure_openai_api():
                api_key = os.getenv('OPENAI_API_KEY')
                self.api_client = AsyncOpenAI(api_key=api_key)
                self.model_name = "gpt-4o-mini"
                self.logger.info(f"✅ Using OpenAI for condition extraction")
            else:
                self.logger.warning("❌ No valid OpenAI API key found, condition extraction will use fallback")
                self.api_client = None
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize API client: {e}")
            import traceback
            traceback.print_exc()
            self.api_client = None
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract conditions from dialogue history
        
        Args:
            input_data: Should contain 'dialogue_history' and optionally 'current_query'
            
        Returns:
            Dict containing extracted and categorized conditions
        """
        dialogue_history = input_data.get('dialogue_history', [])
        current_query = input_data.get('current_query', '')
        
        # Debug logging
        self.logger.info(f"Condition extractor received - History length: {len(dialogue_history)}, Query: {current_query[:50]}...")
        if dialogue_history:
            self.logger.info(f"First history item: {dialogue_history[0]}")
        
        # Build extraction prompt
        prompt = self._build_extraction_prompt(dialogue_history, current_query)
        
        # Try API first, then fallback
        response = None
        if self.api_client:
            try:
                # Try LLM extraction first
                llm_response = await self.api_client.generate(
                    prompt=prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                response = llm_response.strip()
                self.logger.info("Using LLM-based condition extraction")
            except Exception as e:
                self.logger.warning(f"LLM extraction failed: {e}, falling back to pattern matching")
        
        # Use fallback if LLM failed or not available
        if not response:
            try:
                from utils.api_fallback import FallbackConditionExtractor
                fallback = FallbackConditionExtractor()
                conditions_dict = fallback.extract_conditions(dialogue_history, current_query)
                response = json.dumps(conditions_dict)
                self.logger.info("Using fallback condition extraction")
            except Exception as e:
                self.logger.error(f"Fallback extraction failed: {e}")
                response = json.dumps({ct: [] for ct in self.condition_types})
        
        # Parse and categorize conditions
        conditions = self._parse_conditions(response)
        if conditions is None:
            conditions = []
        categorized = self._categorize_conditions(conditions)
        if categorized is None:
            categorized = {ct: [] for ct in self.condition_types}
        
        return {
            "status": "success",
            "conditions": categorized,
            "raw_extraction": response,
            "total_conditions": sum(len(v) for v in categorized.values() if v is not None)
        }
    
    def _build_extraction_prompt(self, history: List[Dict], current_query: str) -> str:
        """Build prompt for condition extraction"""
        history_text = self._format_dialogue_history(history)
        
        prompt = f"""Analyze the following dialogue history and extract ALL types of information about the user. Extract not just preferences and constraints, but also biographical facts, personal details, jobs, hobbies, relationships, and any factual information.

Dialogue History:
{history_text}

Current Query: {current_query}

Please identify and categorize ALL information types:

1. **Hard Constraints** (must be satisfied): Requirements with words like "need", "must", "require", "have to"

2. **Soft Preferences** (likes/wants): Things the user likes, prefers, enjoys, wants, or is interested in

3. **Biographical Facts** (personal information): Jobs, occupations, family, relationships, location, education, background
   - Jobs/Work: "I work as...", "My job is...", "I have a secondary job as..."
   - Family: "My brother is...", "I have children", "My father..."
   - Location: "I live in...", "I moved to...", "I'm from..."
   - Personal details: Age, education, background, etc.

4. **Temporal Conditions** (time-related): Time-based events, schedules, deadlines, "last year", "recently", etc.

5. **Negations** (dislikes/exclusions): Things explicitly disliked or to avoid - "don't", "not", "dislike", "avoid"

EXTRACTION RULES:
- Extract factual statements like "I have a secondary job as a plumber" as biographical facts
- Capture job descriptions like "It's pretty messy work but pays well"
- Record personal details, family information, locations, hobbies
- Include both positive statements ("I love...") and factual ones ("I work as...")
- Pay attention to descriptive details like "messy", "great", "difficult"

Output ONLY a valid JSON object in this exact format:
{{
  "hard_constraints": [
    {{"text": "condition text", "source_turn": 1, "confidence": "high", "category": "hard_constraints"}}
  ],
  "soft_preferences": [
    {{"text": "preference text", "source_turn": 2, "confidence": "medium", "category": "soft_preferences"}}
  ],
  "biographical_facts": [
    {{"text": "personal fact", "source_turn": 3, "confidence": "high", "category": "biographical_facts"}}
  ],
  "temporal_conditions": [
    {{"text": "time condition", "source_turn": 4, "confidence": "medium", "category": "temporal_conditions"}}
  ],
  "negations": [
    {{"text": "exclusion", "source_turn": 5, "confidence": "high", "category": "negations"}}
  ]
}}

If no information is found in a category, use an empty array []."""
        
        return prompt
    
    def _format_dialogue_history(self, history: List[Dict]) -> str:
        """Format dialogue history for prompt"""
        formatted = []
        for i, turn in enumerate(history):
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            formatted.append(f"Turn {i+1} [{role}]: {content}")
        return "\n".join(formatted)
    
    async def _call_reasoning_api(self, prompt: str) -> str:
        """Call reasoning API (OpenAI)"""
        if not self.api_client:
            self.logger.error("No API client in _call_reasoning_api")
            return json.dumps({ct: [] for ct in self.condition_types})
        
        try:
            # Use OpenAI API
            response = await self.api_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            return json.dumps({ct: [] for ct in self.condition_types})
    
    def _mock_extraction(self, history: List[Dict], current_query: str) -> str:
        """Mock extraction for testing without API"""
        conditions = {
            "hard_constraints": [],
            "soft_preferences": [],
            "temporal_conditions": [],
            "negations": []
        }
        
        # Simple rule-based extraction for testing
        for i, turn in enumerate(history):
            if turn.get('role') == 'user':
                content = turn.get('content', '').lower()
                
                # Check for negations first (highest priority)
                if any(pattern in content for pattern in ["don't", "do not", 'not', 'never', 'without', 'except', 'avoid', 'exclude']):
                    conditions["negations"].append({
                        "text": turn.get('content'),
                        "source_turn": i + 1,
                        "confidence": "high"
                    })
                
                # Hard constraints (must, need, require)
                elif any(word in content for word in ['must', 'need', 'require']):
                    conditions["hard_constraints"].append({
                        "text": turn.get('content'),
                        "source_turn": i + 1,
                        "confidence": "high"
                    })
                
                # Soft preferences (prefer, like, want)
                elif any(word in content for word in ['prefer', 'like', 'want', 'interested']):
                    conditions["soft_preferences"].append({
                        "text": turn.get('content'),
                        "source_turn": i + 1,
                        "confidence": "medium"
                    })
                
                # Temporal conditions
                elif any(word in content for word in ['today', 'tomorrow', 'week', 'month', 'time']):
                    conditions["temporal_conditions"].append({
                        "text": turn.get('content'),
                        "source_turn": i + 1,
                        "confidence": "medium"
                    })
                
                # Additional soft preferences for other patterns  
                elif any(word in content for word in ['should', 'would like', 'looking for']):
                    conditions["soft_preferences"].append({
                        "text": turn.get('content'),
                        "source_turn": i + 1,
                        "confidence": "medium"
                    })
        
        return json.dumps(conditions, ensure_ascii=False)
    
    def _parse_conditions(self, response: str) -> List[Dict[str, Any]]:
        """Parse conditions from API response"""
        try:
            if not response or response.strip() == "":
                return []
                
            if isinstance(response, str):
                # Try multiple JSON extraction approaches
                response = response.strip()
                
                # First, try to parse the entire response as JSON
                try:
                    data = json.loads(response)
                except json.JSONDecodeError:
                    # Try to extract JSON block from response
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            # Try to find JSON between code blocks
                            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                            if json_match:
                                data = json.loads(json_match.group(1))
                            else:
                                self.logger.warning(f"Could not parse JSON from response: {response[:200]}...")
                                data = {}
                    else:
                        data = {}
            else:
                data = response
            
            conditions = []
            for category in self.condition_types:
                if category in data and isinstance(data[category], list):
                    for cond in data[category]:
                        if isinstance(cond, dict):
                            cond['category'] = category
                            conditions.append(cond)
            
            return conditions
        except Exception as e:
            self.logger.error(f"Failed to parse conditions: {e}")
            return []
    
    def _categorize_conditions(self, conditions: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Categorize conditions by type"""
        categorized = {ct: [] for ct in self.condition_types}
        
        if conditions is not None:
            for condition in conditions:
                if condition is not None:
                    category = condition.get('category', 'soft_preferences')
                    if category in categorized:
                        categorized[category].append(condition)
        
        return categorized
    
    async def extract_conditions(self, dialogue_history: List[Dict[str, str]], current_query: str = "") -> List[Dict[str, Any]]:
        """
        Extract conditions from dialogue history and current query
        
        Args:
            dialogue_history: List of dialogue turns
            current_query: Current user query
            
        Returns:
            List of extracted conditions
        """
        try:
            # Use the process method
            input_data = {
                'dialogue_history': dialogue_history,
                'current_query': current_query
            }
            
            result = await self.process(input_data)
            
            # Flatten categorized conditions into a single list
            conditions = []
            categorized_conditions = result.get('conditions', {})
            
            for category, cond_list in categorized_conditions.items():
                if cond_list:
                    for condition in cond_list:
                        condition['type'] = category  # Ensure type is set
                        conditions.append(condition)
            
            return conditions
            
        except Exception as e:
            self.logger.error(f"Error in extract_conditions: {str(e)}")
            return []