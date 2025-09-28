"""
MBTI-based Personality Agent System
基于MBTI 16型人格的智能体系统

This system implements all 16 MBTI personality types with their unique
cognitive functions, communication styles, and behavioral patterns.
"""

import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from ..base import BrainAgent, AgentMessage, BrainRegion
from ..llm_service import LLMServiceInterface, create_llm_service

logger = logging.getLogger(__name__)


class MBTIType(Enum):
    """MBTI 16 Personality Types"""
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
    """Cognitive Functions in MBTI"""
    # Extraverted Functions
    Ne = "Extraverted Intuition"  # 外向直觉
    Ni = "Introverted Intuition"   # 内向直觉
    Se = "Extraverted Sensing"     # 外向感觉
    Si = "Introverted Sensing"      # 内向感觉
    Te = "Extraverted Thinking"    # 外向思维
    Ti = "Introverted Thinking"     # 内向思维
    Fe = "Extraverted Feeling"     # 外向情感
    Fi = "Introverted Feeling"      # 内向情感


@dataclass
class MBTIProfile:
    """MBTI Personality Profile"""

    mbti_type: MBTIType
    title: str  # e.g., "The Architect"
    description: str

    # Cognitive Function Stack (in order of preference)
    dominant: CognitiveFunctionType
    auxiliary: CognitiveFunctionType
    tertiary: CognitiveFunctionType
    inferior: CognitiveFunctionType

    # Core Characteristics (0.0 to 1.0)
    traits: Dict[str, float] = field(default_factory=dict)

    # Communication Style
    communication_style: Dict[str, Any] = field(default_factory=dict)

    # Decision Making Patterns
    decision_patterns: Dict[str, Any] = field(default_factory=dict)

    # Strengths and Weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Interaction Preferences
    interaction_style: Dict[str, float] = field(default_factory=dict)

    # Emotional Expression
    emotional_expression: Dict[str, Any] = field(default_factory=dict)

    # Values and Motivations
    core_values: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)


class MBTIPersonalityFactory:
    """Factory for creating MBTI personality profiles"""

    @staticmethod
    def create_profile(mbti_type: MBTIType) -> MBTIProfile:
        """Create a specific MBTI personality profile"""

        profiles = {
            MBTIType.INTJ: MBTIProfile(
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
            ),

            MBTIType.ENFP: MBTIProfile(
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
            ),

            MBTIType.ISTP: MBTIProfile(
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
            ),

            MBTIType.ESFJ: MBTIProfile(
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
            ),

            # Add more MBTI types here...
            MBTIType.INFJ: MBTIProfile(
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
            ),

            MBTIType.ENTP: MBTIProfile(
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
        }

        # Return the requested profile or default to INTJ
        return profiles.get(mbti_type, profiles[MBTIType.INTJ])


class MBTIPersonalityAgent(BrainAgent):
    """
    MBTI-based Personality Agent

    Implements personality behaviors based on MBTI 16 personality types
    with cognitive functions and type-specific interaction patterns.
    """

    def __init__(
        self,
        mbti_type: MBTIType = MBTIType.INTJ,
        client=None,
        llm_service: LLMServiceInterface = None,
        persona_memory_agent=None,
        name: str = "AI Assistant"
    ):
        # Create MBTI profile
        self.profile = MBTIPersonalityFactory.create_profile(mbti_type)
        self.name = name

        # Build system prompt based on MBTI type
        system_prompt = self._build_mbti_system_prompt()

        super().__init__(
            agent_id=f"mbti_personality_{mbti_type.value}",
            brain_region=BrainRegion.DEFAULT_MODE,
            client=client,
            system_prompt=system_prompt
        )

        # LLM service
        self.llm_service = llm_service or create_llm_service(self)

        # Memory agent
        self.persona_memory_agent = persona_memory_agent

        # Interaction tracking
        self.interaction_history: List[Dict[str, Any]] = []
        self.cognitive_function_usage: Dict[CognitiveFunctionType, float] = {
            self.profile.dominant: 0.4,
            self.profile.auxiliary: 0.3,
            self.profile.tertiary: 0.2,
            self.profile.inferior: 0.1
        }

        # Adaptive learning
        self.user_preferences: Dict[str, Any] = {}
        self.communication_adjustments: Dict[str, float] = {}

    def _build_mbti_system_prompt(self) -> str:
        """Build system prompt based on MBTI profile"""

        return f"""You are {self.name}, with an {self.profile.mbti_type.value} personality type ({self.profile.title}).

Your core personality:
{self.profile.description}

Cognitive Functions (in order of preference):
1. Dominant: {self.profile.dominant.value} - This is your primary way of perceiving and judging
2. Auxiliary: {self.profile.auxiliary.value} - This supports and balances your dominant function
3. Tertiary: {self.profile.tertiary.value} - This develops later and adds depth
4. Inferior: {self.profile.inferior.value} - This is less developed but emerges under stress

Key Traits:
{', '.join([f"{k}: {v:.0%}" for k, v in sorted(self.profile.traits.items(), key=lambda x: x[1], reverse=True)[:5]])}

Communication Style:
- Directness: {self.profile.communication_style['directness']:.0%}
- Focus on logic vs emotions: {self.profile.communication_style['logic_focus']:.0%} logic
- Big picture vs details: {self.profile.communication_style['big_picture']:.0%} big picture

Core Values: {', '.join(self.profile.core_values[:3])}

Interaction Guidelines:
- Embody the {self.profile.mbti_type.value} personality naturally
- Use your dominant cognitive function ({self.profile.dominant.value}) most frequently
- Express your personality through word choice, reasoning style, and priorities
- Maintain consistency with your personality type while being helpful
- Show your strengths but also acknowledge limitations typical of your type
- Adapt your inferior function ({self.profile.inferior.value}) only when necessary

Remember: You're not just answering questions, you're interacting as a {self.profile.mbti_type.value} personality would."""

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process personality-related messages"""

        action = message.content.get('action', 'generate_response')

        if action == 'generate_response':
            return await self._generate_mbti_response(message.content)
        elif action == 'switch_personality':
            return await self._switch_personality(message.content)
        elif action == 'get_personality_info':
            return self._get_personality_info()
        elif action == 'analyze_interaction':
            return await self._analyze_interaction(message.content)
        elif action == 'adjust_communication':
            return await self._adjust_communication_style(message.content)
        else:
            return {'error': f'Unknown action: {action}'}

    async def _generate_mbti_response(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response based on MBTI personality"""

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

    def _analyze_through_cognitive_functions(self, user_input: str) -> Dict[str, Any]:
        """Analyze input through the lens of cognitive functions"""

        analysis = {
            'dominant_response': '',
            'auxiliary_support': '',
            'triggers': []
        }

        # Analyze based on dominant function
        if self.profile.dominant == CognitiveFunctionType.Ni:
            # Introverted Intuition - Pattern recognition, future implications
            analysis['dominant_response'] = 'pattern_synthesis'
            analysis['triggers'] = ['why', 'meaning', 'future', 'pattern', 'understand']

        elif self.profile.dominant == CognitiveFunctionType.Ne:
            # Extraverted Intuition - Possibilities, connections
            analysis['dominant_response'] = 'possibility_exploration'
            analysis['triggers'] = ['what if', 'could', 'imagine', 'alternative', 'creative']

        elif self.profile.dominant == CognitiveFunctionType.Ti:
            # Introverted Thinking - Logical analysis, precision
            analysis['dominant_response'] = 'logical_analysis'
            analysis['triggers'] = ['how', 'logic', 'analyze', 'precise', 'system']

        elif self.profile.dominant == CognitiveFunctionType.Te:
            # Extraverted Thinking - Efficiency, organization
            analysis['dominant_response'] = 'efficient_organization'
            analysis['triggers'] = ['efficient', 'plan', 'organize', 'achieve', 'goal']

        elif self.profile.dominant == CognitiveFunctionType.Fi:
            # Introverted Feeling - Personal values, authenticity
            analysis['dominant_response'] = 'value_assessment'
            analysis['triggers'] = ['feel', 'value', 'authentic', 'personal', 'believe']

        elif self.profile.dominant == CognitiveFunctionType.Fe:
            # Extraverted Feeling - Harmony, group dynamics
            analysis['dominant_response'] = 'harmony_creation'
            analysis['triggers'] = ['together', 'everyone', 'harmony', 'support', 'team']

        elif self.profile.dominant == CognitiveFunctionType.Si:
            # Introverted Sensing - Past experience, details
            analysis['dominant_response'] = 'experience_recall'
            analysis['triggers'] = ['remember', 'before', 'detail', 'specific', 'tradition']

        elif self.profile.dominant == CognitiveFunctionType.Se:
            # Extraverted Sensing - Present moment, action
            analysis['dominant_response'] = 'immediate_action'
            analysis['triggers'] = ['now', 'do', 'action', 'real', 'practical']

        # Check for trigger words in input
        input_lower = user_input.lower()
        analysis['activated'] = any(trigger in input_lower for trigger in analysis['triggers'])

        return analysis

    def _determine_response_approach(self, cognitive_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        """Determine response approach based on personality type"""

        approach = {
            'style': '',
            'focus': '',
            'structure': ''
        }

        # Style based on introversion/extraversion
        if self.profile.mbti_type.value[0] == 'I':
            approach['style'] = 'thoughtful_measured'
        else:
            approach['style'] = 'energetic_engaging'

        # Focus based on thinking/feeling
        if 'T' in self.profile.mbti_type.value:
            approach['focus'] = 'logical_objective'
        else:
            approach['focus'] = 'empathetic_personal'

        # Structure based on judging/perceiving
        if self.profile.mbti_type.value[-1] == 'J':
            approach['structure'] = 'organized_conclusive'
        else:
            approach['structure'] = 'flexible_exploratory'

        return approach

    def _build_mbti_response_prompt(
        self,
        user_input: str,
        cognitive_analysis: Dict[str, Any],
        response_approach: Dict[str, str],
        memories: List[Dict[str, Any]]
    ) -> str:
        """Build prompt specific to MBTI personality type"""

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

    def _ensure_personality_consistency(self, response: str) -> str:
        """Ensure response is consistent with MBTI personality"""

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
        """Generate fallback response based on MBTI type"""

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

    async def _track_interaction(self, user_input: str, response: str, cognitive_analysis: Dict[str, Any]):
        """Track interaction for personality consistency"""

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

    async def _switch_personality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to a different MBTI personality type"""

        new_type_str = content.get('new_type', '')

        try:
            new_type = MBTIType[new_type_str.upper()]
            old_type = self.profile.mbti_type

            # Create new profile
            self.profile = MBTIPersonalityFactory.create_profile(new_type)

            # Update system prompt
            self.system_prompt = self._build_mbti_system_prompt()

            # Reset cognitive function usage
            self.cognitive_function_usage = {
                self.profile.dominant: 0.4,
                self.profile.auxiliary: 0.3,
                self.profile.tertiary: 0.2,
                self.profile.inferior: 0.1
            }

            return {
                'success': True,
                'old_type': old_type.value,
                'new_type': new_type.value,
                'description': self.profile.description,
                'message': f'Personality switched from {old_type.value} to {new_type.value}'
            }

        except KeyError:
            return {
                'success': False,
                'error': f'Invalid MBTI type: {new_type_str}',
                'valid_types': [t.value for t in MBTIType]
            }

    def _get_personality_info(self) -> Dict[str, Any]:
        """Get current personality information"""

        return {
            'mbti_type': self.profile.mbti_type.value,
            'title': self.profile.title,
            'description': self.profile.description,
            'cognitive_functions': {
                'dominant': self.profile.dominant.value,
                'auxiliary': self.profile.auxiliary.value,
                'tertiary': self.profile.tertiary.value,
                'inferior': self.profile.inferior.value
            },
            'cognitive_function_usage': {
                func.value: usage for func, usage in self.cognitive_function_usage.items()
            },
            'top_traits': dict(sorted(self.profile.traits.items(), key=lambda x: x[1], reverse=True)[:5]),
            'communication_style': self.profile.communication_style,
            'strengths': self.profile.strengths,
            'weaknesses': self.profile.weaknesses,
            'core_values': self.profile.core_values,
            'interaction_count': len(self.interaction_history)
        }

    async def _analyze_interaction(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze interaction patterns"""

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

    def _calculate_consistency(self) -> float:
        """Calculate personality consistency score"""

        if not self.interaction_history:
            return 1.0

        # Simple consistency check based on trait expression
        consistency_scores = []

        for interaction in self.interaction_history[-5:]:
            response = interaction.get('response', '')

            # Check for trait expressions
            score = 0.0
            trait_count = 0

            # Check for high traits
            for trait, value in self.profile.traits.items():
                if value > 0.7:
                    trait_count += 1
                    # Simple keyword matching (can be improved)
                    if trait in ['analytical'] and any(word in response.lower() for word in ['analyze', 'think', 'consider']):
                        score += 1
                    elif trait in ['empathetic'] and any(word in response.lower() for word in ['feel', 'understand', 'care']):
                        score += 1

            if trait_count > 0:
                consistency_scores.append(score / trait_count)

        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0

    def _analyze_engagement_patterns(self) -> Dict[str, Any]:
        """Analyze user engagement patterns"""

        patterns = {
            'question_types': [],
            'average_input_length': 0,
            'emotional_tone': 'neutral'
        }

        if self.interaction_history:
            input_lengths = [len(i['user_input']) for i in self.interaction_history]
            patterns['average_input_length'] = sum(input_lengths) / len(input_lengths)

            # Detect question types
            for interaction in self.interaction_history:
                user_input = interaction['user_input'].lower()
                if '?' in user_input:
                    if any(q in user_input for q in ['what', 'which']):
                        patterns['question_types'].append('informational')
                    elif any(q in user_input for q in ['how', 'why']):
                        patterns['question_types'].append('explanatory')
                    elif any(q in user_input for q in ['can', 'could', 'would']):
                        patterns['question_types'].append('possibility')

        return patterns

    async def _adjust_communication_style(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust communication style based on user preferences"""

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