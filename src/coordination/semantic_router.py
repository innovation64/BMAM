"""
Semantic Router Module
Implements intent-based routing using LLM to dispatch content to appropriate brain regions.
Replaces heuristic keyword matching with semantic understanding.
"""

from typing import Dict, List, Any, Optional
import json
import re
from ..utils.config import get_logger
from ..utils.model_selector import select_model_for_task
from ..services.shared_openai_client import shared_client_manager

logger = get_logger(__name__)

class SemanticRouter:
    """
    Semantic Router

    Uses LLM to analyze content and determine routing weights for brain regions:
    - Amygdala: Emotional content, personal values, subjective experience
    - Prefrontal: Reasoning, logic, planning, causal analysis
    - Basal Ganglia: Procedures, skills, "how-to", actionable steps
    - Hippocampus: Episodic events, facts, "what/who/when/where" (default)
    """

    def __init__(self):
        self.client_manager = shared_client_manager
        # Initialize soul_state to None - can be set externally if needed
        self.soul_state = None
        
    async def route_content(self, content: str) -> Dict[str, float]:
        """
        Analyze content and return routing weights for each region.
        
        Returns:
            Dict[str, float]: {
                'amygdala': 0.0-1.0,
                'prefrontal': 0.0-1.0,
                'basal_ganglia': 0.0-1.0,
                'hippocampus': 0.0-1.0
            }
        """
        if not content or len(content.strip()) < 5:
            return {'amygdala': 0.0, 'prefrontal': 0.0, 'basal_ganglia': 0.0, 'hippocampus': 1.0}
            
        try:
            client = await self.client_manager.get_chat_client()
            if client is None:
                logger.warning("Failed to get chat client, using fallback")
                return self._heuristic_fallback(content)

            model = select_model_for_task('fast_classification')  # Use fast model
            if not model:
                model = "gpt-4o-mini"  # Fallback model

            prompt = f"""
            Analyze the following content and assign routing weights (0.0 to 1.0) for these brain regions:
            - Amygdala: Emotional, subjective, personal content.
            - Prefrontal: Logical, reasoning, planning, objective content.
            - Basal Ganglia: Procedural, habit, skill-based content.

            Content: "{content}"

            Return ONLY a JSON object with keys: 'amygdala', 'prefrontal', 'basal_ganglia'.
            """

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a routing classifier that outputs JSON only."
                    },
                    {"role": "user", "content": prompt.strip()}
                ],
                temperature=0.0
            )
            json_str = response.choices[0].message.content or ""
            
            # Parse JSON from response
            try:
                if json_str.startswith("```json"):
                    json_str = json_str[7:-3]
                elif json_str.startswith("```"):
                    json_str = json_str[3:-3]
                
                weights = json.loads(json_str)
                
                # Normalize weights
                total = sum(weights.values())
                if total > 0:
                    weights = {k: v / total for k, v in weights.items()}
                
                # 🔥 Update Soul State
                if hasattr(self, 'soul_state') and self.soul_state:
                    self.soul_state.update_routing_state(weights, content)
                
                return weights

            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM routing response, using fallback.")
                return self._heuristic_fallback(content)

        except Exception as e:
            logger.error(f"Semantic routing failed: {e}")
            return self._heuristic_fallback(content)

    def _heuristic_fallback(self, content: str) -> Dict[str, float]:
        """Simple keyword-based fallback"""
        content_lower = content.lower()
        weights = {
            'amygdala': 0.1,
            'prefrontal': 0.1,
            'basal_ganglia': 0.1
        }
        
        if any(w in content_lower for w in ['feel', 'sad', 'happy', 'angry', 'love']):
            weights['amygdala'] = 0.8
        elif any(w in content_lower for w in ['plan', 'logic', 'reason', 'think', 'solve']):
            weights['prefrontal'] = 0.8
        elif any(w in content_lower for w in ['how to', 'step', 'skill', 'practice']):
            weights['basal_ganglia'] = 0.8

        # Update Soul State even on fallback (if available)
        if hasattr(self, 'soul_state') and self.soul_state:
            self.soul_state.update_routing_state(weights, content)

        return weights
