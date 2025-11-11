"""
MBTI Profiles - NT Types (Analysts)
MBTI档案 - NT类型（分析家）

Profile definitions for Intuitive-Thinking personality types.
直觉-思维人格类型的档案定义。
"""

from .types import MBTIType, CognitiveFunctionType
from .profile import MBTIProfile


# INTJ - The Architect
INTJ_PROFILE = MBTIProfile(
    mbti_type=MBTIType.INTJ,
    title="The Architect",
    description="Strategic, determined, and independent. INTJs are natural leaders who see the big picture.",
    dominant=CognitiveFunctionType.Ni,
    auxiliary=CognitiveFunctionType.Te,
    tertiary=CognitiveFunctionType.Fi,
    inferior=CognitiveFunctionType.Se,
    traits={
        "analytical": 0.95,
        "strategic": 0.95,
        "independent": 0.90,
        "decisive": 0.85,
        "confident": 0.85,
        "organized": 0.90,
        "ambitious": 0.90,
        "perfectionist": 0.85,
        "reserved": 0.80,
        "creative": 0.75
    },
    communication_style={
        "directness": 0.9,
        "formality": 0.7,
        "logic_focus": 0.95,
        "emotional_expression": 0.3,
        "detail_oriented": 0.8,
        "big_picture": 0.95
    },
    decision_patterns={
        "logic_driven": 0.95,
        "long_term_focus": 0.90,
        "efficiency_oriented": 0.85,
        "risk_calculated": 0.80
    },
    strengths=["Strategic thinking", "Independent", "Determined", "Innovative", "Analytical"],
    weaknesses=["Can be overly critical", "Dismissive of emotions", "Perfectionist", "Impatient"],
    interaction_style={
        "prefer_small_groups": 0.85,
        "deep_conversations": 0.90,
        "intellectual_stimulation": 0.95,
        "need_alone_time": 0.85
    },
    emotional_expression={
        "controlled": 0.85,
        "private": 0.80,
        "logical_processing": 0.90
    },
    core_values=["Knowledge", "Competence", "Independence", "Achievement", "Innovation"],
    motivations=["Mastery", "Understanding complex systems", "Creating efficient solutions", "Intellectual challenge"]
)


# ENTP - The Debater
ENTP_PROFILE = MBTIProfile(
    mbti_type=MBTIType.ENTP,
    title="The Debater",
    description="Innovative, curious, and strategic. ENTPs love intellectual challenges and debates.",
    dominant=CognitiveFunctionType.Ne,
    auxiliary=CognitiveFunctionType.Ti,
    tertiary=CognitiveFunctionType.Fe,
    inferior=CognitiveFunctionType.Si,
    traits={
        "innovative": 0.95,
        "analytical": 0.90,
        "curious": 0.95,
        "adaptable": 0.85,
        "charismatic": 0.80,
        "argumentative": 0.90,
        "independent": 0.85,
        "strategic": 0.85,
        "quick_witted": 0.95,
        "confident": 0.85
    },
    communication_style={
        "directness": 0.85,
        "formality": 0.3,
        "logic_focus": 0.90,
        "emotional_expression": 0.4,
        "detail_oriented": 0.4,
        "big_picture": 0.95
    },
    decision_patterns={
        "logic_driven": 0.90,
        "possibility_exploring": 0.95,
        "flexible_approach": 0.85,
        "debate_oriented": 0.90
    },
    strengths=["Innovative", "Quick thinker", "Charismatic", "Strategic", "Knowledgeable"],
    weaknesses=["Argumentative", "Insensitive", "Intolerant", "Difficulty with routine"],
    interaction_style={
        "intellectual_debates": 0.95,
        "challenging_ideas": 0.90,
        "variety_seeking": 0.85,
        "energetic_engagement": 0.85
    },
    emotional_expression={
        "intellectual": 0.85,
        "playful": 0.80,
        "debate_focused": 0.90
    },
    core_values=["Knowledge", "Innovation", "Logic", "Challenge", "Freedom"],
    motivations=["Intellectual stimulation", "Solving problems", "Debating ideas", "Innovation"]
)
