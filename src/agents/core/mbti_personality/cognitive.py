"""
Cognitive Function Analysis
认知功能分析

Mixin for analyzing input through MBTI cognitive functions.
用于通过MBTI认知功能分析输入的混入类。
"""

import logging
from typing import Dict, Any

from .types import CognitiveFunctionType

logger = logging.getLogger(__name__)


class CognitiveFunctionMixin:
    """
    Mixin for cognitive function analysis
    认知功能分析混入类

    Analyzes input through the lens of MBTI cognitive functions.
    通过MBTI认知功能的视角分析输入。
    """

    def _analyze_through_cognitive_functions(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze input through the lens of cognitive functions
        通过认知功能的视角分析输入

        Args:
            user_input: User's input text / 用户输入文本

        Returns:
            Dict containing cognitive analysis / 包含认知分析的字典
        """

        analysis = {
            'dominant_response': '',
            'auxiliary_support': '',
            'triggers': []
        }

        # Analyze based on dominant function
        if self.profile.dominant == CognitiveFunctionType.Ni:
            # Introverted Intuition - Pattern recognition, future implications
            # 内向直觉 - 模式识别、未来影响
            analysis['dominant_response'] = 'pattern_synthesis'
            analysis['triggers'] = ['why', 'meaning', 'future', 'pattern', 'understand']

        elif self.profile.dominant == CognitiveFunctionType.Ne:
            # Extraverted Intuition - Possibilities, connections
            # 外向直觉 - 可能性、联系
            analysis['dominant_response'] = 'possibility_exploration'
            analysis['triggers'] = ['what if', 'could', 'imagine', 'alternative', 'creative']

        elif self.profile.dominant == CognitiveFunctionType.Ti:
            # Introverted Thinking - Logical analysis, precision
            # 内向思维 - 逻辑分析、精确性
            analysis['dominant_response'] = 'logical_analysis'
            analysis['triggers'] = ['how', 'logic', 'analyze', 'precise', 'system']

        elif self.profile.dominant == CognitiveFunctionType.Te:
            # Extraverted Thinking - Efficiency, organization
            # 外向思维 - 效率、组织
            analysis['dominant_response'] = 'efficient_organization'
            analysis['triggers'] = ['efficient', 'plan', 'organize', 'achieve', 'goal']

        elif self.profile.dominant == CognitiveFunctionType.Fi:
            # Introverted Feeling - Personal values, authenticity
            # 内向情感 - 个人价值、真实性
            analysis['dominant_response'] = 'value_assessment'
            analysis['triggers'] = ['feel', 'value', 'authentic', 'personal', 'believe']

        elif self.profile.dominant == CognitiveFunctionType.Fe:
            # Extraverted Feeling - Harmony, group dynamics
            # 外向情感 - 和谐、团体动态
            analysis['dominant_response'] = 'harmony_creation'
            analysis['triggers'] = ['together', 'everyone', 'harmony', 'support', 'team']

        elif self.profile.dominant == CognitiveFunctionType.Si:
            # Introverted Sensing - Past experience, details
            # 内向感觉 - 过去经验、细节
            analysis['dominant_response'] = 'experience_recall'
            analysis['triggers'] = ['remember', 'before', 'detail', 'specific', 'tradition']

        elif self.profile.dominant == CognitiveFunctionType.Se:
            # Extraverted Sensing - Present moment, action
            # 外向感觉 - 当下时刻、行动
            analysis['dominant_response'] = 'immediate_action'
            analysis['triggers'] = ['now', 'do', 'action', 'real', 'practical']

        # Check for trigger words in input
        input_lower = user_input.lower()
        analysis['activated'] = any(trigger in input_lower for trigger in analysis['triggers'])

        return analysis

    def _determine_response_approach(self, cognitive_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        """
        Determine response approach based on personality type
        根据人格类型确定响应方式

        Args:
            cognitive_analysis: Cognitive function analysis / 认知功能分析
            context: Additional context / 额外上下文

        Returns:
            Dict defining response approach / 定义响应方式的字典
        """

        approach = {
            'style': '',
            'focus': '',
            'structure': ''
        }

        # Style based on introversion/extraversion
        # 基于内向/外向的风格
        if self.profile.mbti_type.value[0] == 'I':
            approach['style'] = 'thoughtful_measured'
        else:
            approach['style'] = 'energetic_engaging'

        # Focus based on thinking/feeling
        # 基于思维/情感的焦点
        if 'T' in self.profile.mbti_type.value:
            approach['focus'] = 'logical_objective'
        else:
            approach['focus'] = 'empathetic_personal'

        # Structure based on judging/perceiving
        # 基于判断/感知的结构
        if self.profile.mbti_type.value[-1] == 'J':
            approach['structure'] = 'organized_conclusive'
        else:
            approach['structure'] = 'flexible_exploratory'

        return approach
