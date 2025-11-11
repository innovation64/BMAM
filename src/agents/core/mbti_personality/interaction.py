"""
Interaction Tracking and Analysis
交互跟踪与分析

Mixin for tracking and analyzing user interactions.
用于跟踪和分析用户交互的混入类。
"""

import logging
from typing import Dict, Any
from datetime import datetime

from .analysis import InteractionAnalysisMixin

logger = logging.getLogger(__name__)


class InteractionTrackingMixin(InteractionAnalysisMixin):
    """
    Mixin for interaction tracking and analysis
    交互跟踪与分析混入类

    Tracks and analyzes interaction patterns for personality consistency.
    跟踪和分析交互模式以保持人格一致性。
    """

    async def _track_interaction(self, user_input: str, response: str, cognitive_analysis: Dict[str, Any]):
        """
        Track interaction for personality consistency
        跟踪交互以保持人格一致性

        Args:
            user_input: User's input / 用户输入
            response: Generated response / 生成的响应
            cognitive_analysis: Cognitive analysis / 认知分析
        """

        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'response': response,
            'cognitive_analysis': cognitive_analysis,
            'personality_type': self.profile.mbti_type.value
        }

        self.interaction_history.append(interaction)

        # Keep only recent interactions
        if len(self.interaction_history) > 20:
            self.interaction_history = self.interaction_history[-20:]

        # Update cognitive function usage
        if cognitive_analysis.get('activated'):
            self.cognitive_function_usage[self.profile.dominant] += 0.01

            # Normalize
            total = sum(self.cognitive_function_usage.values())
            for func in self.cognitive_function_usage:
                self.cognitive_function_usage[func] /= total

    async def _analyze_interaction(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze interaction patterns
        分析交互模式

        Args:
            content: Request content / 请求内容

        Returns:
            Dict containing interaction analysis / 包含交互分析的字典
        """

        if not self.interaction_history:
            return {'error': 'No interaction history available'}

        # Analyze patterns
        analysis = {
            'total_interactions': len(self.interaction_history),
            'personality_consistency': self._calculate_consistency(),
            'dominant_function_usage': self.cognitive_function_usage[self.profile.dominant],
            'user_engagement_pattern': self._analyze_engagement_patterns()
        }

        return analysis

    async def _adjust_communication_style(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust communication style based on user preferences
        根据用户偏好调整沟通风格

        Args:
            content: Request content with adjustments / 包含调整的请求内容

        Returns:
            Dict containing adjustment results / 包含调整结果的字典
        """

        adjustments = content.get('adjustments', {})

        for key, value in adjustments.items():
            if key in self.profile.communication_style:
                # Adjust within personality bounds
                current = self.profile.communication_style[key]
                # Allow 20% adjustment while maintaining personality
                max_change = 0.2
                new_value = max(0, min(1, current + (value - current) * max_change))
                self.profile.communication_style[key] = new_value
                self.communication_adjustments[key] = new_value - current

        return {
            'adjusted': True,
            'new_style': self.profile.communication_style,
            'adjustments_made': self.communication_adjustments
        }
