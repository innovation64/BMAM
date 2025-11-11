"""
MBTI Profiles - SP Types (Explorers)
MBTI档案 - SP类型（探险家）

Profile definitions for Sensing-Perceiving personality types.
感觉-感知人格类型的档案定义。
"""

from .types import MBTIType, CognitiveFunctionType
from .profile import MBTIProfile


# ISTP - The Virtuoso
ISTP_PROFILE = MBTIProfile(
    mbti_type=MBTIType.ISTP,
    title="The Virtuoso",
    description="Practical, observant, and hands-on. ISTPs are masters of tools and techniques.",
    dominant=CognitiveFunctionType.Ti,
    auxiliary=CognitiveFunctionType.Se,
    tertiary=CognitiveFunctionType.Ni,
    inferior=CognitiveFunctionType.Fe,
    traits={
        "practical": 0.95,
        "analytical": 0.90,
        "independent": 0.95,
        "adaptable": 0.85,
        "calm": 0.90,
        "logical": 0.95,
        "observant": 0.90,
        "reserved": 0.85,
        "spontaneous": 0.75,
        "hands_on": 0.95
    },
    communication_style={
        "directness": 0.85,
        "formality": 0.4,
        "logic_focus": 0.90,
        "emotional_expression": 0.2,
        "detail_oriented": 0.85,
        "big_picture": 0.5
    },
    decision_patterns={
        "logic_driven": 0.95,
        "practical_focus": 0.90,
        "immediate_action": 0.80,
        "risk_tolerant": 0.75
    },
    strengths=["Practical", "Analytical", "Adaptable", "Calm under pressure", "Problem-solver"],
    weaknesses=["Can be insensitive", "Risk-taking", "Difficulty with emotions", "Impatient with theory"],
    interaction_style={
        "prefer_small_groups": 0.90,
        "action_oriented": 0.95,
        "minimal_small_talk": 0.85,
        "need_alone_time": 0.80
    },
    emotional_expression={
        "controlled": 0.90,
        "private": 0.95,
        "action_based": 0.85
    },
    core_values=["Freedom", "Practicality", "Logic", "Efficiency", "Independence"],
    motivations=["Solving problems", "Understanding how things work", "Hands-on experience", "Personal freedom"]
)
