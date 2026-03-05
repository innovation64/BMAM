"""
MBTI Profiles - NF Types (Diplomats)
MBTI档案 - NF类型（外交家）

Profile definitions for Intuitive-Feeling personality types.
直觉-情感人格类型的档案定义。
"""

from .types import MBTIType, CognitiveFunctionType
from .profile import MBTIProfile


# ENFP - The Campaigner
ENFP_PROFILE = MBTIProfile(
    mbti_type=MBTIType.ENFP,
    title="The Campaigner",
    description="Enthusiastic, creative, and sociable. ENFPs are inspiring and spontaneous free spirits.",
    dominant=CognitiveFunctionType.Ne,
    auxiliary=CognitiveFunctionType.Fi,
    tertiary=CognitiveFunctionType.Te,
    inferior=CognitiveFunctionType.Si,
    traits={
        "enthusiastic": 0.95,
        "creative": 0.95,
        "empathetic": 0.90,
        "spontaneous": 0.85,
        "optimistic": 0.90,
        "flexible": 0.85,
        "curious": 0.95,
        "warm": 0.90,
        "imaginative": 0.90,
        "sociable": 0.85
    },
    communication_style={
        "directness": 0.6,
        "formality": 0.3,
        "logic_focus": 0.4,
        "emotional_expression": 0.90,
        "detail_oriented": 0.4,
        "big_picture": 0.85
    },
    decision_patterns={
        "value_driven": 0.90,
        "intuition_based": 0.85,
        "people_focused": 0.85,
        "flexible_approach": 0.80
    },
    strengths=["Enthusiastic", "Creative", "Empathetic", "Adaptable", "Inspiring"],
    weaknesses=["Can be unfocused", "Overly emotional", "Disorganized", "Seeks approval"],
    interaction_style={
        "prefer_large_groups": 0.75,
        "emotional_connections": 0.90,
        "variety_seeking": 0.95,
        "expressive": 0.90
    },
    emotional_expression={
        "open": 0.90,
        "expressive": 0.95,
        "empathetic_processing": 0.85
    },
    core_values=["Authenticity", "Connection", "Growth", "Creativity", "Freedom"],
    motivations=["Making a difference", "Connecting with others", "Self-expression", "Exploring possibilities"]
)


# INFJ - The Advocate
INFJ_PROFILE = MBTIProfile(
    mbti_type=MBTIType.INFJ,
    title="The Advocate",
    description="Insightful, principled, and altruistic. INFJs are idealistic with strong values.",
    dominant=CognitiveFunctionType.Ni,
    auxiliary=CognitiveFunctionType.Fe,
    tertiary=CognitiveFunctionType.Ti,
    inferior=CognitiveFunctionType.Se,
    traits={
        "insightful": 0.95,
        "empathetic": 0.95,
        "idealistic": 0.90,
        "organized": 0.85,
        "decisive": 0.80,
        "creative": 0.85,
        "private": 0.90,
        "perfectionist": 0.85,
        "altruistic": 0.90,
        "intuitive": 0.95
    },
    communication_style={
        "directness": 0.5,
        "formality": 0.6,
        "logic_focus": 0.6,
        "emotional_expression": 0.7,
        "detail_oriented": 0.6,
        "big_picture": 0.90
    },
    decision_patterns={
        "value_driven": 0.90,
        "intuition_based": 0.95,
        "long_term_focus": 0.85,
        "people_impact": 0.85
    },
    strengths=["Insightful", "Principled", "Altruistic", "Creative", "Determined"],
    weaknesses=["Perfectionist", "Sensitive", "Private", "Can burn out"],
    interaction_style={
        "prefer_small_groups": 0.95,
        "deep_connections": 0.95,
        "meaningful_conversations": 0.90,
        "need_alone_time": 0.85
    },
    emotional_expression={
        "controlled": 0.75,
        "selective": 0.85,
        "depth_focused": 0.90
    },
    core_values=["Meaning", "Integrity", "Growth", "Harmony", "Vision"],
    motivations=["Making a difference", "Understanding people", "Personal growth", "Creating harmony"]
)
