"""
MBTI Personality Profile
MBTI人格档案

Defines the data structure for MBTI personality profiles.
定义MBTI人格档案的数据结构。
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .types import MBTIType, CognitiveFunctionType


@dataclass
class MBTIProfile:
    """
    MBTI Personality Profile
    MBTI人格档案

    Comprehensive personality profile based on MBTI type.
    基于MBTI类型的综合人格档案。
    """

    mbti_type: MBTIType
    title: str  # e.g., "The Architect"
    description: str

    # Cognitive Function Stack (in order of preference)
    # 认知功能栈（按优先级顺序）
    dominant: CognitiveFunctionType    # Primary function - 主导功能
    auxiliary: CognitiveFunctionType   # Supporting function - 辅助功能
    tertiary: CognitiveFunctionType    # Developing function - 第三功能
    inferior: CognitiveFunctionType    # Least developed - 劣势功能

    # Core Characteristics (0.0 to 1.0)
    # 核心特征（0.0到1.0）
    traits: Dict[str, float] = field(default_factory=dict)

    # Communication Style
    # 沟通风格
    communication_style: Dict[str, Any] = field(default_factory=dict)

    # Decision Making Patterns
    # 决策模式
    decision_patterns: Dict[str, Any] = field(default_factory=dict)

    # Strengths and Weaknesses
    # 优势与劣势
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Interaction Preferences
    # 交互偏好
    interaction_style: Dict[str, float] = field(default_factory=dict)

    # Emotional Expression
    # 情感表达
    emotional_expression: Dict[str, Any] = field(default_factory=dict)

    # Values and Motivations
    # 价值观与动机
    core_values: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
