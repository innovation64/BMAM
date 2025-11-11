"""
MBTI Types and Cognitive Functions
MBTI类型与认知功能

Defines the 16 MBTI personality types and 8 cognitive functions.
定义16种MBTI人格类型和8种认知功能。
"""

from enum import Enum


class MBTIType(Enum):
    """
    MBTI 16 Personality Types
    MBTI 16种人格类型
    """
    INTJ = "INTJ"  # Architect - 建筑师
    INTP = "INTP"  # Thinker - 思考者
    ENTJ = "ENTJ"  # Commander - 指挥官
    ENTP = "ENTP"  # Debater - 辩论家
    INFJ = "INFJ"  # Advocate - 提倡者
    INFP = "INFP"  # Mediator - 调停者
    ENFJ = "ENFJ"  # Protagonist - 主人公
    ENFP = "ENFP"  # Campaigner - 竞选者
    ISTJ = "ISTJ"  # Logistician - 物流师
    ISFJ = "ISFJ"  # Defender - 守卫者
    ESTJ = "ESTJ"  # Executive - 总经理
    ESFJ = "ESFJ"  # Consul - 执政官
    ISTP = "ISTP"  # Virtuoso - 鉴赏家
    ISFP = "ISFP"  # Adventurer - 探险家
    ESTP = "ESTP"  # Entrepreneur - 企业家
    ESFP = "ESFP"  # Entertainer - 表演者


class CognitiveFunctionType(Enum):
    """
    Cognitive Functions in MBTI
    MBTI中的认知功能

    These are the 8 cognitive functions that make up personality:
    这些是构成人格的8种认知功能：
    - Extraverted (Outward-focused) / 外向（关注外部）
    - Introverted (Inward-focused) / 内向（关注内部）
    """
    # Intuition Functions - 直觉功能
    Ne = "Extraverted Intuition"  # 外向直觉 - Possibilities, connections
    Ni = "Introverted Intuition"  # 内向直觉 - Patterns, insights

    # Sensing Functions - 感觉功能
    Se = "Extraverted Sensing"    # 外向感觉 - Present moment, action
    Si = "Introverted Sensing"    # 内向感觉 - Past experience, details

    # Thinking Functions - 思维功能
    Te = "Extraverted Thinking"   # 外向思维 - Efficiency, organization
    Ti = "Introverted Thinking"   # 内向思维 - Logical analysis, precision

    # Feeling Functions - 情感功能
    Fe = "Extraverted Feeling"    # 外向情感 - Harmony, group dynamics
    Fi = "Introverted Feeling"    # 内向情感 - Personal values, authenticity
