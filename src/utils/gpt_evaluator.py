"""
GPT Score Evaluator for MA-CMM Framework

This module implements GPT-based evaluation metrics for assessing:
- Condition satisfaction
- Response relevance  
- Dialogue coherence
- Information accuracy
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import openai
from openai import AsyncOpenAI
import numpy as np

from .config import ConfigManager


class GPTEvaluator:
    """GPT-based evaluator for response quality assessment"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize GPT evaluator"""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client
        api_key = self.config['api'].get('openai_api_key')
        base_url = self.config['api'].get('openai_base_url', 'https://api.openai.com/v1')
        
        if not api_key:
            raise ValueError("OpenAI API key not found in config. Set OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # GPT Score configuration
        self.gpt_config = self.config['experiment']['gpt_score']
        self.model = self.gpt_config.get('model', 'gpt-4o-mini')
        self.temperature = self.gpt_config.get('temperature', 0.1)
        self.max_tokens = self.gpt_config.get('max_tokens', 500)
        self.evaluation_aspects = self.gpt_config.get('evaluation_aspects', [])
        
    async def evaluate_response(
        self,
        dialogue_history: List[Dict[str, str]],
        current_query: str,
        generated_response: str,
        reference_response: str,
        conditions: List[Dict[str, Any]] = None,
        context_info: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """
        Evaluate a generated response using GPT Score
        
        Args:
            dialogue_history: Previous dialogue turns
            current_query: Current user query
            generated_response: System generated response
            reference_response: Ground truth response
            conditions: Extracted conditions
            context_info: Additional context information
            
        Returns:
            Dictionary of evaluation scores
        """
        
        try:
            scores = {}
            
            # Evaluate each aspect
            for aspect in self.evaluation_aspects:
                score = await self._evaluate_aspect(
                    aspect,
                    dialogue_history,
                    current_query,
                    generated_response,
                    reference_response,
                    conditions,
                    context_info
                )
                scores[f'gpt_{aspect}'] = score
            
            # Calculate overall GPT score
            scores['gpt_overall'] = np.mean(list(scores.values()))
            
            return scores
            
        except Exception as e:
            self.logger.error(f"Error in GPT evaluation: {str(e)}")
            return {f'gpt_{aspect}': 0.0 for aspect in self.evaluation_aspects + ['overall']}
    
    async def _evaluate_aspect(
        self,
        aspect: str,
        dialogue_history: List[Dict[str, str]],
        current_query: str,
        generated_response: str,
        reference_response: str,
        conditions: List[Dict[str, Any]] = None,
        context_info: Dict[str, Any] = None
    ) -> float:
        """Evaluate a specific aspect using GPT"""
        
        # Build evaluation prompt based on aspect
        prompt = self._build_evaluation_prompt(
            aspect,
            dialogue_history,
            current_query,
            generated_response,
            reference_response,
            conditions,
            context_info
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert evaluator for conversational AI systems. Provide precise numerical scores between 0 and 1."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract score from response
            score_text = response.choices[0].message.content.strip()
            score = self._extract_score(score_text)
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error evaluating {aspect}: {str(e)}")
            return 0.0
    
    def _build_evaluation_prompt(
        self,
        aspect: str,
        dialogue_history: List[Dict[str, str]],
        current_query: str,
        generated_response: str,
        reference_response: str,
        conditions: List[Dict[str, Any]] = None,
        context_info: Dict[str, Any] = None
    ) -> str:
        """Build evaluation prompt for specific aspect"""
        
        # Format dialogue history
        history_text = self._format_dialogue_history(dialogue_history)
        
        # Format conditions
        conditions_text = self._format_conditions(conditions) if conditions else "No explicit conditions extracted."
        
        base_prompt = f"""
## Dialogue History:
{history_text}

## Current Query:
{current_query}

## Generated Response:
{generated_response}

## Reference Response:
{reference_response}

## Extracted Conditions:
{conditions_text}
"""
        
        if aspect == "condition_satisfaction":
            prompt = base_prompt + """
## Task: Evaluate Condition Satisfaction

Evaluate how well the generated response satisfies the user's conditions and constraints mentioned in the dialogue history.

Consider:
1. Does the response respect hard constraints (must-have requirements)?
2. Does it address soft preferences when possible?
3. Does it handle temporal conditions appropriately?
4. Does it avoid violating negation conditions (things user doesn't want)?

Rate on a scale of 0.0 to 1.0:
- 0.0: Violates or ignores most conditions
- 0.5: Partially satisfies some conditions
- 1.0: Fully satisfies all relevant conditions

Score (0.0-1.0):"""
        
        elif aspect == "response_relevance":
            prompt = base_prompt + """
## Task: Evaluate Response Relevance

Evaluate how relevant and appropriate the generated response is to the current query and dialogue context.

Consider:
1. Does the response directly address the user's question?
2. Is it contextually appropriate given the dialogue history?
3. Does it provide useful and relevant information?
4. Is the level of detail appropriate?

Rate on a scale of 0.0 to 1.0:
- 0.0: Completely irrelevant or off-topic
- 0.5: Somewhat relevant but missing key points
- 1.0: Highly relevant and comprehensive

Score (0.0-1.0):"""
        
        elif aspect == "dialogue_coherence":
            prompt = base_prompt + """
## Task: Evaluate Dialogue Coherence

Evaluate how well the generated response maintains coherence with the previous dialogue flow.

Consider:
1. Does the response logically follow from previous exchanges?
2. Is the tone and style consistent with the conversation?
3. Does it reference relevant information from dialogue history?
4. Does it maintain conversational continuity?

Rate on a scale of 0.0 to 1.0:
- 0.0: Completely incoherent or contradictory
- 0.5: Somewhat coherent but with gaps
- 1.0: Perfectly coherent and well-connected

Score (0.0-1.0):"""
        
        elif aspect == "information_accuracy":
            prompt = base_prompt + """
## Task: Evaluate Information Accuracy

Evaluate the factual accuracy and consistency of the generated response compared to the reference response and dialogue context.

Consider:
1. Is the factual information correct?
2. Is it consistent with information provided in the dialogue?
3. Does it avoid hallucinations or false claims?
4. How does it compare to the reference response in terms of accuracy?

Rate on a scale of 0.0 to 1.0:
- 0.0: Contains significant factual errors or hallucinations
- 0.5: Mostly accurate with minor inconsistencies
- 1.0: Completely accurate and consistent

Score (0.0-1.0):"""
        
        else:
            # Generic evaluation prompt
            prompt = base_prompt + f"""
## Task: Evaluate {aspect.replace('_', ' ').title()}

Evaluate the generated response for {aspect.replace('_', ' ')}.

Rate on a scale of 0.0 to 1.0 where:
- 0.0: Poor quality
- 0.5: Average quality
- 1.0: Excellent quality

Score (0.0-1.0):"""
        
        return prompt
    
    def _format_dialogue_history(self, dialogue_history: List[Dict[str, str]]) -> str:
        """Format dialogue history for evaluation prompt"""
        if not dialogue_history:
            return "No previous dialogue history."
        
        formatted = []
        for i, turn in enumerate(dialogue_history):
            role = turn.get('role', 'unknown')
            content = turn.get('content', '')
            formatted.append(f"Turn {i+1} ({role}): {content}")
        
        return "\n".join(formatted)
    
    def _format_conditions(self, conditions: List[Dict[str, Any]]) -> str:
        """Format conditions for evaluation prompt"""
        if not conditions:
            return "No explicit conditions found."
        
        formatted = []
        for i, condition in enumerate(conditions):
            condition_type = condition.get('type', 'unknown')
            description = condition.get('description', 'No description')
            importance = condition.get('importance', 'unknown')
            
            formatted.append(f"{i+1}. Type: {condition_type}")
            formatted.append(f"   Description: {description}")
            formatted.append(f"   Importance: {importance}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _extract_score(self, score_text: str) -> float:
        """Extract numerical score from GPT response"""
        try:
            # Try to find a decimal number in the response
            import re
            
            # Look for patterns like "0.8", "0.75", "1.0", etc.
            score_pattern = r'\b([0-1](?:\.\d+)?)\b'
            matches = re.findall(score_pattern, score_text)
            
            if matches:
                score = float(matches[0])
                # Ensure score is between 0 and 1
                return max(0.0, min(1.0, score))
            
            # If no decimal found, look for percentages
            percent_pattern = r'(\d+)%'
            percent_matches = re.findall(percent_pattern, score_text)
            
            if percent_matches:
                percent = float(percent_matches[0])
                return max(0.0, min(1.0, percent / 100.0))
            
            # Default to 0.5 if no score found
            self.logger.warning(f"Could not extract score from: {score_text}")
            return 0.5
            
        except Exception as e:
            self.logger.error(f"Error extracting score: {str(e)}")
            return 0.0
    
    async def batch_evaluate(
        self,
        evaluation_data: List[Dict[str, Any]],
        batch_size: int = 5
    ) -> List[Dict[str, float]]:
        """
        Evaluate multiple responses in batches to avoid rate limits
        
        Args:
            evaluation_data: List of evaluation data dictionaries
            batch_size: Number of evaluations per batch
            
        Returns:
            List of evaluation score dictionaries
        """
        
        results = []
        
        for i in range(0, len(evaluation_data), batch_size):
            batch = evaluation_data[i:i + batch_size]
            
            # Process batch
            batch_tasks = []
            for data in batch:
                task = self.evaluate_response(
                    dialogue_history=data.get('dialogue_history', []),
                    current_query=data.get('current_query', ''),
                    generated_response=data.get('generated_response', ''),
                    reference_response=data.get('reference_response', ''),
                    conditions=data.get('conditions', []),
                    context_info=data.get('context_info', {})
                )
                batch_tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch evaluation error: {str(result)}")
                    # Add default scores for failed evaluation
                    default_scores = {f'gpt_{aspect}': 0.0 for aspect in self.evaluation_aspects + ['overall']}
                    results.append(default_scores)
                else:
                    results.append(result)
            
            # Add delay between batches to respect rate limits
            await asyncio.sleep(1)
            
            self.logger.info(f"Completed batch {i//batch_size + 1}/{(len(evaluation_data) + batch_size - 1)//batch_size}")
        
        return results


async def main():
    """Test GPT evaluator"""
    evaluator = GPTEvaluator()
    
    # Test evaluation
    test_data = {
        'dialogue_history': [
            {'role': 'user', 'content': 'I want to learn about machine learning, but I prefer hands-on tutorials.'},
            {'role': 'assistant', 'content': 'I can help you with that! Hands-on learning is a great approach.'}
        ],
        'current_query': 'Can you recommend some practical ML projects for beginners?',
        'generated_response': 'Here are some great beginner ML projects: 1) Iris flower classification 2) House price prediction 3) Movie recommendation system. These all include step-by-step tutorials.',
        'reference_response': 'For hands-on ML learning, I recommend starting with: 1) Iris dataset classification 2) Boston housing prices prediction 3) Basic recommendation systems.',
        'conditions': [
            {
                'type': 'soft_preference',
                'description': 'User prefers hands-on tutorials',
                'importance': 'high'
            }
        ]
    }
    
    scores = await evaluator.evaluate_response(**test_data)
    
    print("GPT Evaluation Scores:")
    for aspect, score in scores.items():
        print(f"  {aspect}: {score:.3f}")


if __name__ == "__main__":
    asyncio.run(main())