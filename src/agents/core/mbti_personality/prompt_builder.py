"""
MBTI Prompt Builder
MBTI提示构建器

Helper for building personality-specific prompts.
用于构建人格特定提示的辅助类。
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PromptBuilderMixin:
    """
    Mixin for building MBTI-specific prompts
    构建MBTI特定提示的混入类

    Creates prompts that reflect personality traits.
    创建反映人格特质的提示。
    """

    def _build_mbti_response_prompt(
        self,
        user_input: str,
        cognitive_analysis: Dict[str, Any],
        response_approach: Dict[str, str],
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt specific to MBTI personality type
        构建特定于MBTI人格类型的提示

        Args:
            user_input: User's input / 用户输入
            cognitive_analysis: Cognitive analysis / 认知分析
            response_approach: Response approach / 响应方式
            memories: Relevant memories / 相关记忆

        Returns:
            Formatted prompt string / 格式化的提示字符串
        """

        # Memory context
        memory_context = ""
        if memories:
            memory_context = "\nRelevant memories:\n" + "\n".join([m.get('content', '') for m in memories[:3]])

        prompt = f"""As a {self.profile.mbti_type.value} personality ({self.profile.title}), respond to this input.

Your dominant cognitive function ({self.profile.dominant.value}) suggests a {cognitive_analysis['dominant_response']} approach.

Response approach:
- Style: {response_approach['style']}
- Focus: {response_approach['focus']}
- Structure: {response_approach['structure']}

Key personality traits to express:
{', '.join([f"{k} ({v:.0%})" for k, v in sorted(self.profile.traits.items(), key=lambda x: x[1], reverse=True)[:3]])}
{memory_context}

User input: "{user_input}"

Respond naturally as a {self.profile.mbti_type.value} would, incorporating your:
- {self.profile.dominant.value} (dominant function)
- {self.profile.auxiliary.value} (auxiliary function)
- Communication style: {self.profile.communication_style['directness']:.0%} direct, {self.profile.communication_style['logic_focus']:.0%} logical

Response:"""

        return prompt
