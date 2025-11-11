"""
Agent Lifecycle Management Module
Handles agent activation, deactivation, and task creation
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .clean_agent_system import AgentMessage
from ..agents.agent_buffer_system import agent_buffer_system
from ..utils.config import get_logger

logger = get_logger(__name__)


class AgentLifecycleManager:
    """Manages agent activation, deactivation, and lifecycle"""

    def __init__(self, agents: Dict[str, Any], processing_stats: Dict[str, Any],
                 pattern_getter_fn, phrases_checker_fn):
        """
        Initialize Agent Lifecycle Manager

        Args:
            agents: Dictionary of agent instances
            processing_stats: Reference to processing statistics dict
            pattern_getter_fn: Function to get query patterns
            phrases_checker_fn: Function to check phrases in text
        """
        self.agents = agents
        self.processing_stats = processing_stats
        self._get_query_patterns = pattern_getter_fn
        self._phrases_in_text = phrases_checker_fn


    async def activate_agent(self, agent_id: str, message: AgentMessage) -> Dict[str, Any]:
        """
        Activate specific agent with message and use buffer system

        Args:
            agent_id: Agent identifier
            message: AgentMessage to send to the agent

        Returns:
            Dict with agent processing result
        """
        if agent_id not in self.agents:
            return {'error': f'Agent {agent_id} not found'}

        try:
            agent = self.agents[agent_id]
            self.processing_stats['agent_activations'][agent_id] += 1

            # Read agent's current buffer state
            try:
                buffer_content = await agent_buffer_system.read_buffer(agent_id)
                # Add ONLY essential buffer data to avoid infinite nesting
                if hasattr(message, 'content') and isinstance(message.content, dict):
                    # Only pass essential data, not the entire buffer including recent_inputs
                    essential_data = {}
                    for key, value in buffer_content.items():
                        if key not in ['recent_inputs', 'recent_exchanges', 'recent_outputs']:
                            essential_data[key] = value
                    message.content['buffer_data'] = essential_data
            except (asyncio.CancelledError, asyncio.TimeoutError) as buffer_e:
                logger.warning(f"Failed to read buffer for {agent_id}: {buffer_e}")

            # Process the message
            result = await agent.process_message(message)

            # Update agent buffer with processing results
            try:
                # Sanitize function for JSON serialization
                def sanitize_for_json(obj):
                    if isinstance(obj, dict):
                        return {k: sanitize_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [sanitize_for_json(item) for item in obj]
                    elif hasattr(obj, '__dict__'):
                        return str(obj)  # Convert objects to string representation
                    elif isinstance(obj, (str, int, float, bool)) or obj is None:
                        return obj
                    else:
                        return str(obj)  # Convert everything else to string

                # Store ONLY the original message content, not the enriched version
                original_content = {k: v for k, v in message.content.items() if k != 'buffer_data'}
                await agent_buffer_system.write_buffer(
                    agent_id,
                    'recent_inputs',
                    {
                        'message': sanitize_for_json(original_content),
                        'timestamp': datetime.now().isoformat(),
                        'sender': message.sender
                    },
                    append=True
                )

                # Store processing results if available - sanitize for JSON
                if result and not result.get('error'):
                    await agent_buffer_system.write_buffer(
                        agent_id,
                        'recent_outputs',
                        {
                            'result': sanitize_for_json(result),
                            'timestamp': datetime.now().isoformat(),
                            'processing_success': True
                        },
                        append=True
                    )
            except (asyncio.CancelledError, asyncio.TimeoutError) as buffer_e:
                logger.warning(f"Failed to write buffer for {agent_id}: {buffer_e}")

            return result

        except (asyncio.TimeoutError) as e:
            logger.error(f"Error activating agent {agent_id}: {e}")
            return {'error': str(e)}

    def map_agent_name(self, agent_name: str) -> Optional[str]:
        """
        Map Chinese agent names to agent IDs

        Args:
            agent_name: Agent name (possibly in Chinese)

        Returns:
            Mapped agent ID or normalized name
        """
        name_mapping = {
            '记忆存储智能体': 'long_term_memory',
            '记忆检索智能体': 'memory_retrieval',
            '对话智能体': 'conversation',
            '反思智能体': 'reflection',
            '规划智能体': 'action_execution',
            '工具调用智能体': 'action_execution',
            '记忆巩固智能体': 'consolidation',
            '遗忘智能体': 'forgetting'
        }
        return name_mapping.get(agent_name, agent_name.lower().replace(' ', '_'))

    def classify_task_type(self, user_input: str, default_language: str,
                          task_type_keywords_fn) -> str:
        """
        Classify task type for routing decisions

        Args:
            user_input: User input text
            default_language: Default language code
            task_type_keywords_fn: Function to get task type keywords

        Returns:
            Task type classification
        """
        storage_keywords = task_type_keywords_fn('memory_storage', default_language)
        retrieval_keywords = task_type_keywords_fn('memory_retrieval', default_language)
        tool_keywords = task_type_keywords_fn('tool_execution', default_language)
        reflection_keywords = task_type_keywords_fn('reflection', default_language)
        lower_input = user_input.lower()

        if self._phrases_in_text(storage_keywords, lower_input):
            return 'memory_storage'
        if self._phrases_in_text(retrieval_keywords, lower_input):
            return 'memory_retrieval'
        if self._phrases_in_text(tool_keywords, lower_input):
            return 'tool_execution'
        if self._phrases_in_text(reflection_keywords, lower_input):
            return 'reflection'
        return 'conversation'

    def contains_user_preference(self, user_input: str) -> bool:
        """检测用户输入是否包含偏好表达"""
        indicators = self._get_query_patterns('preference_indicators')
        return self._phrases_in_text(indicators, user_input)

    def requires_stress_analysis(self, user_input: str) -> bool:
        """
        判断是否需要进行压力/威胁分析

        Args:
            user_input: User input text

        Returns:
            True if stress analysis is required
        """
        # Skip stress analysis for simple greetings and preferences
        greeting_patterns = self._get_query_patterns('greeting_patterns')
        if self._phrases_in_text(greeting_patterns, user_input):
            return False

        # Skip for preference expressions (they're usually positive)
        if self.contains_user_preference(user_input):
            return False

        # Require stress analysis for potentially emotional content
        stress_indicators = self._get_query_patterns('stress_indicators')

        # Also analyze longer inputs (might contain complex emotions)
        return self._phrases_in_text(stress_indicators, user_input) or len(user_input) > 50

    async def create_primary_agent_task(self, agent_id: str, user_input: str,
                                       context: Dict) -> Dict[str, Any]:
        """
        Create appropriate task for primary agent

        Args:
            agent_id: Agent identifier
            user_input: User input text
            context: Execution context

        Returns:
            Agent processing result
        """
        if agent_id == 'long_term_memory':
            return await self.activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'store_long_term',
                        'memory': {
                            'content': user_input,
                            'importance': 0.7,
                            'emotion_tags': ['neutral'],
                            'context_tags': ['user_input']
                        }
                    }
                )
            )
        elif agent_id == 'personality':
            return await self.activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'update_preferences',
                        'preferences': user_input,
                        'context': context
                    }
                )
            )
        elif agent_id == 'conversation':
            return await self.activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'generate_response',
                        'user_input': user_input,
                        'context': context
                    }
                )
            )
        else:
            # Default generic task
            return await self.activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'process',
                        'input': user_input,
                        'context': context
                    }
                )
            )

    def should_consider_long_term(self, user_input: str, context: Dict) -> bool:
        """
        Determine if long-term memory should be considered

        Args:
            user_input: User input text
            context: Execution context

        Returns:
            True if long-term memory should be accessed
        """
        # 检查是否有明确的记忆请求
        memory_request_patterns = self._get_query_patterns('memory_request_patterns')
        if self._phrases_in_text(memory_request_patterns, user_input):
            return True

        # 检查上下文中的标志
        if context.get('force_long_term', False):
            return True

        # 检查是否为复杂查询(长度>30)
        if len(user_input) > 30:
            return True

        return False

    def has_explicit_memory_request(self, user_input: str) -> bool:
        """
        Check if input has explicit memory request

        Args:
            user_input: User input text

        Returns:
            True if explicit memory request detected
        """
        memory_request_patterns = self._get_query_patterns('memory_request_patterns')
        return self._phrases_in_text(memory_request_patterns, user_input.lower())
