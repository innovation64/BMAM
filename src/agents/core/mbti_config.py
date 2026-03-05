"""
MBTI Personality Configuration System
MBTI人格配置系统

Provides configuration management for MBTI personality types,
user preferences, and personality switching functionality.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .mbti_personality import MBTIType, MBTIPersonalityAgent, MBTIPersonalityFactory

logger = logging.getLogger(__name__)


class PersonalityMode(Enum):
    """Personality operation modes"""
    FIXED = "fixed"  # 固定人格模式
    ADAPTIVE = "adaptive"  # 自适应模式
    CONTEXTUAL = "contextual"  # 情境适应模式
    USER_CHOICE = "user_choice"  # 用户选择模式


@dataclass
class MBTIConfiguration:
    """MBTI personality configuration"""

    # Current personality settings
    current_personality: str = "INTJ"
    personality_mode: str = "fixed"

    # User preferences
    allow_personality_switching: bool = True
    remember_personality_choice: bool = True
    auto_detect_preference: bool = False

    # Interaction settings
    personality_adaptation_threshold: int = 10
    consistency_enforcement: float = 0.8

    # Communication adjustments
    formality_adjustment: float = 0.0
    directness_adjustment: float = 0.0
    emotion_expression_adjustment: float = 0.0

    # Advanced settings
    cognitive_function_emphasis: Dict[str, float] = None
    custom_traits_override: Dict[str, float] = None

    # Session management
    session_personality_memory: bool = True
    cross_session_learning: bool = True

    def __post_init__(self):
        if self.cognitive_function_emphasis is None:
            self.cognitive_function_emphasis = {}
        if self.custom_traits_override is None:
            self.custom_traits_override = {}


class MBTIConfigurationManager:
    """Manages MBTI personality configuration"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/mbti_personality.json")
        self.config = MBTIConfiguration()
        self.available_personalities = list(MBTIType)
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # Update configuration
                for key, value in config_data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)

                logger.info(f"Loaded MBTI configuration from {self.config_path}")
            else:
                logger.info("No existing configuration found, using defaults")
        except Exception as e:
            logger.error(f"Error loading MBTI configuration: {e}")

    def save_configuration(self):
        """Save current configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)

            logger.info(f"Saved MBTI configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving MBTI configuration: {e}")

    def get_personality_options(self) -> List[Dict[str, str]]:
        """Get available personality options with descriptions"""
        options = []

        for mbti_type in MBTIType:
            profile = MBTIPersonalityFactory.create_profile(mbti_type)
            options.append({
                'type': mbti_type.value,
                'title': profile.title,
                'description': profile.description,
                'traits': list(profile.traits.keys())[:3]
            })

        return options

    def set_personality(self, personality_type: str) -> Tuple[bool, str]:
        """Set current personality type"""
        try:
            mbti_type = MBTIType[personality_type.upper()]
            self.config.current_personality = mbti_type.value

            if self.config.remember_personality_choice:
                self.save_configuration()

            return True, f"Personality set to {mbti_type.value}"
        except KeyError:
            return False, f"Invalid personality type: {personality_type}"

    def get_current_personality(self) -> MBTIType:
        """Get current personality type"""
        try:
            return MBTIType[self.config.current_personality]
        except KeyError:
            logger.warning(f"Invalid current personality: {self.config.current_personality}")
            return MBTIType.INTJ

    def create_personality_agent(
        self,
        client=None,
        llm_service=None,
        persona_memory_agent=None,
        name: str = "AI Assistant"
    ) -> MBTIPersonalityAgent:
        """Create personality agent with current configuration"""

        current_type = self.get_current_personality()

        agent = MBTIPersonalityAgent(
            mbti_type=current_type,
            client=client,
            llm_service=llm_service,
            persona_memory_agent=persona_memory_agent,
            name=name
        )

        # Apply configuration adjustments
        self._apply_configuration_to_agent(agent)

        return agent

    def _apply_configuration_to_agent(self, agent: MBTIPersonalityAgent):
        """Apply configuration adjustments to agent"""

        # Apply communication adjustments
        if self.config.formality_adjustment != 0:
            current_formality = agent.profile.communication_style.get('formality', 0.5)
            new_formality = max(0, min(1, current_formality + self.config.formality_adjustment))
            agent.profile.communication_style['formality'] = new_formality

        if self.config.directness_adjustment != 0:
            current_directness = agent.profile.communication_style.get('directness', 0.5)
            new_directness = max(0, min(1, current_directness + self.config.directness_adjustment))
            agent.profile.communication_style['directness'] = new_directness

        if self.config.emotion_expression_adjustment != 0:
            current_emotion = agent.profile.communication_style.get('emotional_expression', 0.5)
            new_emotion = max(0, min(1, current_emotion + self.config.emotion_expression_adjustment))
            agent.profile.communication_style['emotional_expression'] = new_emotion

        # Apply custom trait overrides
        for trait, value in self.config.custom_traits_override.items():
            if trait in agent.profile.traits:
                agent.profile.traits[trait] = max(0, min(1, value))

    def update_configuration(self, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update configuration with new settings"""
        try:
            updated_fields = []

            for key, value in updates.items():
                if hasattr(self.config, key):
                    old_value = getattr(self.config, key)
                    setattr(self.config, key, value)
                    updated_fields.append(f"{key}: {old_value} -> {value}")
                else:
                    logger.warning(f"Unknown configuration field: {key}")

            if updated_fields:
                self.save_configuration()
                return True, f"Updated: {', '.join(updated_fields)}"
            else:
                return False, "No valid fields to update"

        except Exception as e:
            return False, f"Error updating configuration: {e}"

    def get_personality_recommendation(self, user_input: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Recommend personality type based on user input and history"""

        if not self.config.auto_detect_preference:
            return {
                'recommendation': self.config.current_personality,
                'confidence': 1.0,
                'reason': 'Auto-detection disabled'
            }

        # Simple recommendation logic based on keywords and patterns
        recommendations = {}

        user_input_lower = user_input.lower()

        # Keyword-based analysis
        keyword_patterns = {
            MBTIType.INTJ: ['strategy', 'plan', 'efficient', 'analyze', 'system', 'future'],
            MBTIType.ENFP: ['creative', 'possibility', 'inspire', 'people', 'idea', 'imagine'],
            MBTIType.ISTP: ['practical', 'hands-on', 'fix', 'tool', 'problem', 'work'],
            MBTIType.ESFJ: ['help', 'support', 'team', 'harmony', 'care', 'together'],
            MBTIType.INFJ: ['meaning', 'purpose', 'understand', 'insight', 'growth', 'vision'],
            MBTIType.ENTP: ['debate', 'challenge', 'innovative', 'possibility', 'logic', 'argue']
        }

        for personality, keywords in keyword_patterns.items():
            score = sum(1 for keyword in keywords if keyword in user_input_lower)
            if score > 0:
                recommendations[personality] = score / len(keywords)

        # Conversation style analysis
        if conversation_history:
            # Analyze communication patterns
            total_messages = len(conversation_history)
            question_count = sum(1 for msg in conversation_history if '?' in msg.get('content', ''))

            # High question ratio might indicate curious types (NT, NF)
            if question_count / total_messages > 0.3:
                for personality in [MBTIType.ENTP, MBTIType.INFJ, MBTIType.ENFP]:
                    recommendations[personality] = recommendations.get(personality, 0) + 0.2

        # Find best recommendation
        if recommendations:
            best_personality = max(recommendations.keys(), key=lambda k: recommendations[k])
            confidence = recommendations[best_personality]

            return {
                'recommendation': best_personality.value,
                'confidence': min(confidence, 0.8),  # Cap confidence
                'reason': f'Based on keyword analysis and communication patterns',
                'alternatives': sorted(
                    [(k.value, v) for k, v in recommendations.items() if k != best_personality],
                    key=lambda x: x[1],
                    reverse=True
                )[:2]
            }

        # Default to current personality
        return {
            'recommendation': self.config.current_personality,
            'confidence': 0.1,
            'reason': 'No clear patterns detected, using current setting'
        }

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get current configuration summary"""

        current_profile = MBTIPersonalityFactory.create_profile(self.get_current_personality())

        return {
            'current_personality': {
                'type': self.config.current_personality,
                'title': current_profile.title,
                'description': current_profile.description
            },
            'mode': self.config.personality_mode,
            'settings': {
                'allow_switching': self.config.allow_personality_switching,
                'remember_choice': self.config.remember_personality_choice,
                'auto_detect': self.config.auto_detect_preference,
                'adaptation_threshold': self.config.personality_adaptation_threshold
            },
            'adjustments': {
                'formality': self.config.formality_adjustment,
                'directness': self.config.directness_adjustment,
                'emotion_expression': self.config.emotion_expression_adjustment
            },
            'custom_overrides': {
                'traits': self.config.custom_traits_override,
                'cognitive_functions': self.config.cognitive_function_emphasis
            }
        }

    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self.config = MBTIConfiguration()
            self.save_configuration()
            logger.info("Configuration reset to defaults")
            return True
        except Exception as e:
            logger.error(f"Error resetting configuration: {e}")
            return False


class MBTIPersonalitySelector:
    """Interactive personality selector for users"""

    def __init__(self, config_manager: MBTIConfigurationManager):
        self.config_manager = config_manager

    def get_personality_menu(self) -> Dict[str, Any]:
        """Get personality selection menu"""

        options = self.config_manager.get_personality_options()
        current = self.config_manager.get_current_personality()

        return {
            'title': 'Select Your MBTI Personality Type',
            'description': 'Choose the personality type that best matches how you want the AI to interact',
            'current': current.value,
            'options': options,
            'categories': {
                'Analysts (NT)': ['INTJ', 'INTP', 'ENTJ', 'ENTP'],
                'Diplomats (NF)': ['INFJ', 'INFP', 'ENFJ', 'ENFP'],
                'Sentinels (SJ)': ['ISTJ', 'ISFJ', 'ESTJ', 'ESFJ'],
                'Explorers (SP)': ['ISTP', 'ISFP', 'ESTP', 'ESFP']
            }
        }

    def select_personality_interactive(self, preference: str = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Interactive personality selection"""

        if preference:
            # Direct selection
            success, message = self.config_manager.set_personality(preference)
            if success:
                agent = self.config_manager.create_personality_agent()
                return True, message, agent.get_personality_info()
            else:
                return False, message, {}

        # Return menu for selection
        menu = self.get_personality_menu()
        return True, "Please select a personality type", menu

    def get_personality_comparison(self, type1: str, type2: str) -> Dict[str, Any]:
        """Compare two personality types"""

        try:
            profile1 = MBTIPersonalityFactory.create_profile(MBTIType[type1.upper()])
            profile2 = MBTIPersonalityFactory.create_profile(MBTIType[type2.upper()])

            return {
                'comparison': {
                    type1: {
                        'title': profile1.title,
                        'description': profile1.description,
                        'strengths': profile1.strengths[:3],
                        'communication_style': profile1.communication_style,
                        'dominant_function': profile1.dominant.value
                    },
                    type2: {
                        'title': profile2.title,
                        'description': profile2.description,
                        'strengths': profile2.strengths[:3],
                        'communication_style': profile2.communication_style,
                        'dominant_function': profile2.dominant.value
                    }
                },
                'key_differences': self._identify_key_differences(profile1, profile2)
            }

        except KeyError as e:
            return {'error': f'Invalid personality type: {e}'}

    def _identify_key_differences(self, profile1, profile2) -> List[str]:
        """Identify key differences between two profiles"""

        differences = []

        # Communication style differences
        comm_diff = []
        for key in ['directness', 'formality', 'logic_focus']:
            if key in profile1.communication_style and key in profile2.communication_style:
                diff = abs(profile1.communication_style[key] - profile2.communication_style[key])
                if diff > 0.3:
                    comm_diff.append(f"{key}: {profile1.communication_style[key]:.1f} vs {profile2.communication_style[key]:.1f}")

        if comm_diff:
            differences.extend([f"Communication: {diff}" for diff in comm_diff[:2]])

        # Cognitive function differences
        if profile1.dominant != profile2.dominant:
            differences.append(f"Different dominant functions: {profile1.dominant.value} vs {profile2.dominant.value}")

        # Trait differences
        trait_diff = []
        for trait in profile1.traits:
            if trait in profile2.traits:
                diff = abs(profile1.traits[trait] - profile2.traits[trait])
                if diff > 0.3:
                    trait_diff.append(f"{trait}: {profile1.traits[trait]:.1f} vs {profile2.traits[trait]:.1f}")

        differences.extend([f"Traits: {diff}" for diff in trait_diff[:2]])

        return differences[:5]  # Return top 5 differences