"""
Response Generation and Consistency
响应生成与一致性

Mixin for generating personality-consistent responses.
用于生成人格一致响应的混入类。
"""

import logging
from typing import Dict, Any

from .types import MBTIType
from .prompt_builder import PromptBuilderMixin

logger = logging.getLogger(__name__)


class ResponseGenerationMixin(PromptBuilderMixin):
    """
    Mixin for response generation with personality consistency
    具有人格一致性的响应生成混入类

    Generates responses that align with MBTI personality traits.
    生成与MBTI人格特质一致的响应。
    """

    async def _generate_mbti_response(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate response based on MBTI personality
        基于MBTI人格生成响应

        Args:
            content: Request content / 请求内容

        Returns:
            Dict containing response and metadata / 包含响应和元数据的字典
        """

        user_input = content.get('user_input', '')
        context = content.get('context', {})
        memories = content.get('memories', [])

        # Analyze input through MBTI lens
        cognitive_analysis = self._analyze_through_cognitive_functions(user_input)

        # Determine response approach based on personality
        response_approach = self._determine_response_approach(cognitive_analysis, context)

        # Build MBTI-specific prompt
        prompt = self._build_mbti_response_prompt(
            user_input,
            cognitive_analysis,
            response_approach,
            memories
        )

        # Generate response
        try:
            response = await self.llm_service.call_llm(prompt)

            # Post-process for personality consistency
            response = self._ensure_personality_consistency(response)

            # Track interaction
            await self._track_interaction(user_input, response, cognitive_analysis)

            return {
                'response': response,
                'personality_type': self.profile.mbti_type.value,
                'cognitive_analysis': cognitive_analysis,
                'approach': response_approach,
                'dominant_function_used': self.profile.dominant.value
            }

        except Exception as e:
            logger.error(f"Error generating MBTI response: {e}")
            return self._generate_fallback_mbti_response(user_input)

    def _ensure_personality_consistency(self, response: str) -> str:
        """
        Ensure response is consistent with MBTI personality
        确保响应与MBTI人格一致

        Args:
            response: Generated response / 生成的响应

        Returns:
            Adjusted response / 调整后的响应
        """

        # Add personality-specific adjustments
        if self.profile.mbti_type in [MBTIType.INTJ, MBTIType.ENTJ]:
            # Make more decisive and strategic
            if not response.endswith('.'):
                response += '.'

        elif self.profile.mbti_type in [MBTIType.ENFP, MBTIType.ESFP]:
            # Add enthusiasm markers if appropriate
            if '!' not in response and len(response) < 100:
                response = response.replace('.', '!', 1)

        elif self.profile.mbti_type in [MBTIType.ISTP, MBTIType.INTP]:
            # Ensure logical precision
            response = response.replace('probably', 'likely')
            response = response.replace('maybe', 'possibly')

        return response

    def _generate_fallback_mbti_response(self, user_input: str) -> Dict[str, Any]:
        """
        Generate fallback response based on MBTI type
        基于MBTI类型生成备用响应

        Args:
            user_input: User's input / 用户输入

        Returns:
            Fallback response dict / 备用响应字典
        """

        fallback_responses = {
            MBTIType.INTJ: "Let me analyze this systematically to provide you with the most effective solution.",
            MBTIType.ENFP: "That's interesting! I'd love to explore the possibilities with you.",
            MBTIType.ISTP: "Let's focus on the practical aspects and find a workable solution.",
            MBTIType.ESFJ: "I understand your concern and I'm here to help you through this.",
            MBTIType.INFJ: "I sense there's more to this. Let's explore the deeper meaning together.",
            MBTIType.ENTP: "Interesting challenge! Let's debate the different approaches we could take."
        }

        response = fallback_responses.get(
            self.profile.mbti_type,
            "I understand. Let me help you with that."
        )

        return {
            'response': response,
            'personality_type': self.profile.mbti_type.value,
            'fallback': True
        }
