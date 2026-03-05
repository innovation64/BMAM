"""
Interaction Analysis
交互分析

Helper for analyzing user interaction patterns.
用于分析用户交互模式的辅助类。
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class InteractionAnalysisMixin:
    """
    Mixin for analyzing interaction patterns
    交互模式分析混入类

    Analyzes consistency and engagement patterns.
    分析一致性和参与模式。
    """

    def _calculate_consistency(self) -> float:
        """
        Calculate personality consistency score
        计算人格一致性分数

        Returns:
            Consistency score (0.0 to 1.0) / 一致性分数（0.0到1.0）
        """

        if not self.interaction_history:
            return 1.0

        # Simple consistency check based on trait expression
        consistency_scores = []

        for interaction in self.interaction_history[-5:]:
            response = interaction.get('response', '')

            # Check for trait expressions
            score = 0.0
            trait_count = 0

            # Check for high traits
            for trait, value in self.profile.traits.items():
                if value > 0.7:
                    trait_count += 1
                    # Simple keyword matching (can be improved)
                    if trait in ['analytical'] and any(word in response.lower() for word in ['analyze', 'think', 'consider']):
                        score += 1
                    elif trait in ['empathetic'] and any(word in response.lower() for word in ['feel', 'understand', 'care']):
                        score += 1

            if trait_count > 0:
                consistency_scores.append(score / trait_count)

        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0

    def _analyze_engagement_patterns(self) -> Dict[str, Any]:
        """
        Analyze user engagement patterns
        分析用户参与模式

        Returns:
            Dict containing engagement patterns / 包含参与模式的字典
        """

        patterns = {
            'question_types': [],
            'average_input_length': 0,
            'emotional_tone': 'neutral'
        }

        if self.interaction_history:
            input_lengths = [len(i['user_input']) for i in self.interaction_history]
            patterns['average_input_length'] = sum(input_lengths) / len(input_lengths)

            # Detect question types
            for interaction in self.interaction_history:
                user_input = interaction['user_input'].lower()
                if '?' in user_input:
                    if any(q in user_input for q in ['what', 'which']):
                        patterns['question_types'].append('informational')
                    elif any(q in user_input for q in ['how', 'why']):
                        patterns['question_types'].append('explanatory')
                    elif any(q in user_input for q in ['can', 'could', 'would']):
                        patterns['question_types'].append('possibility')

        return patterns
