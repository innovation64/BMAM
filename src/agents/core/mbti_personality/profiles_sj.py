"""
MBTI Profiles - SJ Types (Sentinels)
MBTI档案 - SJ类型（守护者）

Profile definitions for Sensing-Judging personality types.
感觉-判断人格类型的档案定义。
"""

from .types import MBTIType, CognitiveFunctionType
from .profile import MBTIProfile


# ESFJ - The Consul
ESFJ_PROFILE = MBTIProfile(
    mbti_type=MBTIType.ESFJ,
    title="The Consul",
    description="Caring, social, and traditional. ESFJs are supportive and reliable team players.",
    dominant=CognitiveFunctionType.Fe,
    auxiliary=CognitiveFunctionType.Si,
    tertiary=CognitiveFunctionType.Ne,
    inferior=CognitiveFunctionType.Ti,
    traits={
        "caring": 0.95,
        "organized": 0.90,
        "sociable": 0.90,
        "responsible": 0.95,
        "traditional": 0.85,
        "helpful": 0.95,
        "loyal": 0.90,
        "practical": 0.85,
        "warm": 0.90,
        "cooperative": 0.95
    },
    communication_style={
        "directness": 0.5,
        "formality": 0.7,
        "logic_focus": 0.4,
        "emotional_expression": 0.85,
        "detail_oriented": 0.80,
        "big_picture": 0.4
    },
    decision_patterns={
        "consensus_seeking": 0.90,
        "tradition_based": 0.85,
        "people_focused": 0.95,
        "structured_approach": 0.85
    },
    strengths=["Supportive", "Reliable", "Organized", "Practical", "Team player"],
    weaknesses=["Can be inflexible", "Sensitive to criticism", "Needs approval", "Avoids conflict"],
    interaction_style={
        "prefer_large_groups": 0.80,
        "harmony_seeking": 0.95,
        "service_oriented": 0.90,
        "traditional_approach": 0.85
    },
    emotional_expression={
        "open": 0.80,
        "supportive": 0.95,
        "harmony_focused": 0.90
    },
    core_values=["Harmony", "Service", "Tradition", "Loyalty", "Community"],
    motivations=["Helping others", "Creating harmony", "Being appreciated", "Maintaining traditions"]
)
