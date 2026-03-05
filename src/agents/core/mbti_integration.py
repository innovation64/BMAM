"""
MBTI Personality System Integration
MBTI人格系统集成

Integrates MBTI personality system with the existing BMAM agent framework.
Provides seamless personality switching and enhanced interaction capabilities.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .mbti_personality import MBTIPersonalityAgent, MBTIType
from .mbti_config import MBTIConfigurationManager, MBTIPersonalitySelector
from .personality import PersonalityAgent  # Original personality agent
from ..base import BrainAgent, AgentMessage, BrainRegion

logger = logging.getLogger(__name__)


class MBTIIntegratedPersonalityAgent(BrainAgent):
    """
    Integrated MBTI Personality Agent

    Provides seamless integration between MBTI personality system
    and existing personality framework, with enhanced capabilities.
    """

    def __init__(
        self,
        client=None,
        llm_service=None,
        persona_memory_agent=None,
        config_path=None,
        name: str = "MBTI Assistant"
    ):
        super().__init__(
            agent_id="mbti_integrated_personality",
            brain_region=BrainRegion.DEFAULT_MODE,
            client=client
        )

        # Configuration management
        self.config_manager = MBTIConfigurationManager(config_path)
        self.personality_selector = MBTIPersonalitySelector(self.config_manager)

        # Current MBTI agent
        self.current_mbti_agent: Optional[MBTIPersonalityAgent] = None

        # Fallback to original personality agent
        self.fallback_agent: Optional[PersonalityAgent] = None

        # Services
        self.llm_service = llm_service
        self.persona_memory_agent = persona_memory_agent
        self.name = name

        # Session management
        self.session_stats = {
            'personality_switches': 0,
            'interactions': 0,
            'start_time': datetime.now(),
            'personality_usage': {}
        }

        # Initialize agents
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize MBTI and fallback agents"""
        try:
            # Create current MBTI agent
            self.current_mbti_agent = self.config_manager.create_personality_agent(
                client=self.client,
                llm_service=self.llm_service,
                persona_memory_agent=self.persona_memory_agent,
                name=self.name
            )

            # Create fallback agent
            self.fallback_agent = PersonalityAgent(
                client=self.client,
                llm_service=self.llm_service,
                persona_memory_agent=self.persona_memory_agent
            )

            # Initialize usage tracking
            current_type = self.current_mbti_agent.profile.mbti_type.value
            self.session_stats['personality_usage'][current_type] = 0

            logger.debug(f"Initialized MBTI system with {current_type} personality")

        except Exception as e:
            logger.error(f"Error initializing MBTI agents: {e}")
            # Fallback to original system
            self.current_mbti_agent = None

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process messages with MBTI personality system"""

        action = message.content.get('action', 'generate_response')
        self.session_stats['interactions'] += 1

        # Handle MBTI-specific actions
        if action.startswith('mbti_'):
            return await self._handle_mbti_actions(action, message.content)

        # Route to appropriate agent
        if self.current_mbti_agent:
            # Use MBTI system
            try:
                result = await self._process_with_mbti(message)

                # Update usage stats
                current_type = self.current_mbti_agent.profile.mbti_type.value
                self.session_stats['personality_usage'][current_type] += 1

                return result

            except Exception as e:
                logger.error(f"MBTI processing failed: {e}")
                # Fall back to original system
                return await self._process_with_fallback(message)

        else:
            # Use fallback system
            return await self._process_with_fallback(message)

    async def _handle_mbti_actions(self, action: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MBTI-specific actions"""

        if action == 'mbti_switch_personality':
            return await self._switch_personality(content)

        elif action == 'mbti_get_info':
            return self._get_mbti_info()

        elif action == 'mbti_get_menu':
            return self._get_personality_menu()

        elif action == 'mbti_compare_types':
            return self._compare_personality_types(content)

        elif action == 'mbti_recommend':
            return await self._recommend_personality(content)

        elif action == 'mbti_configure':
            return self._configure_mbti_settings(content)

        elif action == 'mbti_get_stats':
            return self._get_session_stats()

        elif action == 'mbti_reset':
            return self._reset_mbti_system()

        else:
            return {'error': f'Unknown MBTI action: {action}'}

    async def _process_with_mbti(self, message: AgentMessage) -> Dict[str, Any]:
        """Process message using MBTI personality system"""

        # Prepare message for MBTI agent
        mbti_message = AgentMessage(
            sender_id=message.sender_id,
            recipient_id=self.current_mbti_agent.agent_id,
            message_type=message.message_type,
            content={
                'action': 'generate_response',
                'user_input': message.content.get('user_input', ''),
                'context': message.content.get('context', {}),
                'memories': message.content.get('memories', [])
            }
        )

        # Process with MBTI agent
        result = await self.current_mbti_agent.process_message(mbti_message)

        # Add integration metadata
        result['integration_info'] = {
            'agent_type': 'mbti',
            'personality_type': self.current_mbti_agent.profile.mbti_type.value,
            'personality_title': self.current_mbti_agent.profile.title,
            'session_interaction': self.session_stats['interactions'],
            'personality_switches': self.session_stats['personality_switches']
        }

        return result

    async def _process_with_fallback(self, message: AgentMessage) -> Dict[str, Any]:
        """Process message using fallback personality system"""

        if not self.fallback_agent:
            return {
                'error': 'No personality agent available',
                'response': 'I apologize, but I\'m experiencing technical difficulties with my personality system.'
            }

        try:
            result = await self.fallback_agent.process_message(message)

            # Add integration metadata
            result['integration_info'] = {
                'agent_type': 'fallback',
                'fallback_reason': 'mbti_unavailable',
                'session_interaction': self.session_stats['interactions']
            }

            return result

        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return {
                'error': 'Personality processing failed',
                'response': 'I understand you\'re trying to communicate with me, but I\'m having some technical issues right now.'
            }

    async def _switch_personality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to a different MBTI personality type"""

        new_type = content.get('personality_type', '').upper()

        if not new_type:
            # Return menu for selection
            menu = self.personality_selector.get_personality_menu()
            return {
                'success': False,
                'message': 'Please specify a personality type',
                'menu': menu
            }

        # Validate and switch
        try:
            mbti_type = MBTIType[new_type]
            old_type = self.current_mbti_agent.profile.mbti_type.value if self.current_mbti_agent else 'None'

            # Set new personality in configuration
            success, message = self.config_manager.set_personality(new_type)

            if not success:
                return {
                    'success': False,
                    'message': message,
                    'valid_types': [t.value for t in MBTIType]
                }

            # Create new MBTI agent
            self.current_mbti_agent = self.config_manager.create_personality_agent(
                client=self.client,
                llm_service=self.llm_service,
                persona_memory_agent=self.persona_memory_agent,
                name=self.name
            )

            # Update session stats
            self.session_stats['personality_switches'] += 1
            if new_type not in self.session_stats['personality_usage']:
                self.session_stats['personality_usage'][new_type] = 0

            # Get new personality info
            personality_info = self.current_mbti_agent._get_personality_info()

            return {
                'success': True,
                'message': f'Personality switched from {old_type} to {new_type}',
                'old_type': old_type,
                'new_type': new_type,
                'personality_info': personality_info,
                'switch_count': self.session_stats['personality_switches']
            }

        except KeyError:
            return {
                'success': False,
                'message': f'Invalid personality type: {new_type}',
                'valid_types': [t.value for t in MBTIType]
            }

        except Exception as e:
            logger.error(f"Error switching personality: {e}")
            return {
                'success': False,
                'message': f'Error switching personality: {str(e)}'
            }

    def _get_mbti_info(self) -> Dict[str, Any]:
        """Get comprehensive MBTI system information"""

        info = {
            'system_status': 'active' if self.current_mbti_agent else 'fallback',
            'available_types': [t.value for t in MBTIType],
            'configuration': self.config_manager.get_configuration_summary(),
            'session_stats': self.session_stats.copy()
        }

        if self.current_mbti_agent:
            info['current_personality'] = self.current_mbti_agent._get_personality_info()

        return info

    def _get_personality_menu(self) -> Dict[str, Any]:
        """Get interactive personality selection menu"""

        menu = self.personality_selector.get_personality_menu()

        # Add session context
        menu['session_context'] = {
            'current_interactions': self.session_stats['interactions'],
            'personality_switches': self.session_stats['personality_switches'],
            'usage_stats': self.session_stats['personality_usage']
        }

        return menu

    def _compare_personality_types(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Compare different personality types"""

        type1 = content.get('type1', '').upper()
        type2 = content.get('type2', '').upper()

        if not type1 or not type2:
            return {
                'error': 'Please specify two personality types to compare',
                'example': 'Compare INTJ with ENFP'
            }

        return self.personality_selector.get_personality_comparison(type1, type2)

    async def _recommend_personality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend personality type based on user input"""

        user_input = content.get('user_input', '')
        conversation_history = content.get('conversation_history', [])

        recommendation = self.config_manager.get_personality_recommendation(
            user_input, conversation_history
        )

        # Option to auto-switch if confidence is high
        auto_switch = content.get('auto_switch', False)
        if auto_switch and recommendation['confidence'] > 0.7:
            switch_result = await self._switch_personality({
                'personality_type': recommendation['recommendation']
            })
            recommendation['auto_switched'] = switch_result['success']

        return {
            'recommendation': recommendation,
            'current_type': self.current_mbti_agent.profile.mbti_type.value if self.current_mbti_agent else 'None'
        }

    def _configure_mbti_settings(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Configure MBTI system settings"""

        settings = content.get('settings', {})

        success, message = self.config_manager.update_configuration(settings)

        if success and self.current_mbti_agent:
            # Re-apply configuration to current agent
            self.config_manager._apply_configuration_to_agent(self.current_mbti_agent)

        return {
            'success': success,
            'message': message,
            'current_config': self.config_manager.get_configuration_summary()
        }

    def _get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""

        session_duration = (datetime.now() - self.session_stats['start_time']).total_seconds()

        stats = self.session_stats.copy()
        stats['session_duration_seconds'] = session_duration
        stats['session_duration_formatted'] = f"{int(session_duration // 60)}m {int(session_duration % 60)}s"

        # Add personality distribution
        total_interactions = sum(self.session_stats['personality_usage'].values())
        if total_interactions > 0:
            stats['personality_distribution'] = {
                ptype: (count / total_interactions) * 100
                for ptype, count in self.session_stats['personality_usage'].items()
            }

        return stats

    def _reset_mbti_system(self) -> Dict[str, Any]:
        """Reset MBTI system to defaults"""

        try:
            # Reset configuration
            success = self.config_manager.reset_to_defaults()

            if success:
                # Reinitialize agents
                self._initialize_agents()

                # Reset session stats
                self.session_stats = {
                    'personality_switches': 0,
                    'interactions': 0,
                    'start_time': datetime.now(),
                    'personality_usage': {}
                }

                return {
                    'success': True,
                    'message': 'MBTI system reset to defaults',
                    'new_personality': self.current_mbti_agent.profile.mbti_type.value if self.current_mbti_agent else 'None'
                }

            else:
                return {
                    'success': False,
                    'message': 'Failed to reset MBTI system'
                }

        except Exception as e:
            logger.error(f"Error resetting MBTI system: {e}")
            return {
                'success': False,
                'message': f'Error resetting system: {str(e)}'
            }

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""

        health = {
            'timestamp': datetime.now().isoformat(),
            'mbti_agent_status': 'healthy' if self.current_mbti_agent else 'unavailable',
            'fallback_agent_status': 'healthy' if self.fallback_agent else 'unavailable',
            'config_manager_status': 'healthy' if self.config_manager else 'unavailable',
            'session_active': True,
            'errors': []
        }

        # Check agent health
        if self.current_mbti_agent:
            try:
                info = self.current_mbti_agent._get_personality_info()
                health['current_personality'] = {
                    'type': info['mbti_type'],
                    'interaction_count': info['interaction_count']
                }
            except Exception as e:
                health['errors'].append(f'MBTI agent error: {str(e)}')
                health['mbti_agent_status'] = 'error'

        # Check configuration
        try:
            config_summary = self.config_manager.get_configuration_summary()
            health['configuration_status'] = 'healthy'
        except Exception as e:
            health['errors'].append(f'Configuration error: {str(e)}')
            health['configuration_status'] = 'error'

        # Overall health
        health['overall_status'] = 'healthy' if not health['errors'] else 'degraded'

        return health


# Convenience functions for easy integration
def create_mbti_personality_system(
    client=None,
    llm_service=None,
    persona_memory_agent=None,
    config_path=None,
    initial_personality: str = "INTJ",
    name: str = "MBTI Assistant"
) -> MBTIIntegratedPersonalityAgent:
    """
    Create a complete MBTI personality system

    Args:
        client: LLM client
        llm_service: LLM service interface
        persona_memory_agent: Persona memory agent
        config_path: Configuration file path
        initial_personality: Initial MBTI type
        name: Agent name

    Returns:
        Integrated MBTI personality agent
    """

    # Create system
    system = MBTIIntegratedPersonalityAgent(
        client=client,
        llm_service=llm_service,
        persona_memory_agent=persona_memory_agent,
        config_path=config_path,
        name=name
    )

    # Set initial personality if different from default
    if initial_personality != "INTJ":
        system.config_manager.set_personality(initial_personality)
        system._initialize_agents()

    return system


def get_available_personalities() -> List[Dict[str, str]]:
    """Get list of available MBTI personalities"""

    factory = MBTIConfigurationManager()
    return factory.get_personality_options()
