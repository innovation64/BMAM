"""
Agent Adapter
智能体适配器

Base adapter for existing agents to IAgent interface
现有智能体到IAgent接口的基础适配器
"""

from typing import Dict, Any
import logging
from abc import ABC

from ..interfaces import IAgent, AgentMessage

logger = logging.getLogger(__name__)


class AgentAdapter(IAgent):
    """
    Base adapter for legacy agents to IAgent interface
    遗留智能体到IAgent接口的基础适配器

    Bridges legacy agent implementations with the new interface contract.
    桥接遗留智能体实现与新接口契约。

    This adapter provides a base class for adapting existing agent
    implementations to conform to the IAgent interface.

    Example:
        from src.agents.brain_regions import HippocampusAgent
        from src.core.adapters import AgentAdapter

        class HippocampusAdapter(AgentAdapter):
            pass

        legacy_agent = HippocampusAgent(...)
        adapted_agent = HippocampusAdapter(legacy_agent, "hippocampus", "hippocampus")

        # Now works with IAgent interface
        result = await adapted_agent.process_message(message)
    """

    def __init__(
        self,
        legacy_agent,
        agent_id: str,
        brain_region: str
    ):
        """
        Initialize adapter with legacy agent

        Args:
            legacy_agent: Legacy agent instance
            agent_id: Unique agent identifier
            brain_region: Associated brain region
        """
        self._legacy = legacy_agent
        self._agent_id = agent_id
        self._brain_region = brain_region
        logger.debug(
            f"AgentAdapter initialized: {agent_id} ({brain_region}) "
            f"with {type(legacy_agent).__name__}"
        )

    @property
    def agent_id(self) -> str:
        """Unique agent identifier"""
        return self._agent_id

    @property
    def brain_region(self) -> str:
        """Associated brain region"""
        return self._brain_region

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process an incoming message

        Args:
            message: Agent message to process

        Returns:
            Processing result dictionary
        """
        try:
            # Try different method names that legacy agents might use
            if hasattr(self._legacy, 'process_message') and callable(getattr(self._legacy, 'process_message', None)):
                return await self._legacy.process_message(message)
            elif hasattr(self._legacy, 'process') and callable(getattr(self._legacy, 'process', None)):
                return await self._legacy.process(message)
            elif hasattr(self._legacy, 'handle_message') and callable(getattr(self._legacy, 'handle_message', None)):
                return await self._legacy.handle_message(message)
            elif hasattr(self._legacy, 'activate') and callable(getattr(self._legacy, 'activate', None)):
                # Some agents use activate method
                result = await self._legacy.activate(
                    message.content.get('input', ''),
                    message.content
                )
                return {
                    'success': True,
                    'agent_id': self.agent_id,
                    'result': result
                }
            else:
                # Try synchronous version
                if hasattr(self._legacy, 'process_sync') and callable(getattr(self._legacy, 'process_sync', None)):
                    result = self._legacy.process_sync(message)
                    return result
                else:
                    logger.warning(
                        f"Legacy agent {type(self._legacy).__name__} has no compatible process method"
                    )
                    return {
                        'success': False,
                        'agent_id': self.agent_id,
                        'error': 'No compatible process method'
                    }
        except Exception as e:
            logger.error(f"Error processing message in {self.agent_id}: {e}")
            return {
                'success': False,
                'agent_id': self.agent_id,
                'error': str(e)
            }

    async def initialize(self):
        """
        Initialize agent resources

        Calls legacy initialization if available
        """
        try:
            if hasattr(self._legacy, 'initialize'):
                await self._legacy.initialize()
            elif hasattr(self._legacy, 'init'):
                await self._legacy.init()
            elif hasattr(self._legacy, 'setup'):
                await self._legacy.setup()
            else:
                # Try synchronous version
                if hasattr(self._legacy, 'initialize_sync'):
                    self._legacy.initialize_sync()
                else:
                    logger.debug(f"Agent {self.agent_id} has no initialization method")
        except Exception as e:
            logger.error(f"Error initializing agent {self.agent_id}: {e}")
            raise

    async def shutdown(self):
        """
        Cleanup agent resources

        Calls legacy cleanup if available
        """
        try:
            if hasattr(self._legacy, 'shutdown'):
                await self._legacy.shutdown()
            elif hasattr(self._legacy, 'cleanup'):
                await self._legacy.cleanup()
            elif hasattr(self._legacy, 'close'):
                await self._legacy.close()
            else:
                # Try synchronous version
                if hasattr(self._legacy, 'shutdown_sync'):
                    self._legacy.shutdown_sync()
                else:
                    logger.debug(f"Agent {self.agent_id} has no shutdown method")
        except Exception as e:
            logger.error(f"Error shutting down agent {self.agent_id}: {e}")
            raise

    @property
    def legacy_agent(self):
        """Access to underlying legacy agent for advanced operations"""
        return self._legacy


class BrainRegionAgentAdapter(AgentAdapter):
    """
    Specialized adapter for brain region agents
    大脑区域智能体的专用适配器

    Provides additional handling for brain region specific methods
    为大脑区域特定方法提供额外处理
    """

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process message with brain region specific handling

        Args:
            message: Agent message to process

        Returns:
            Processing result dictionary
        """
        try:
            # Brain region agents often have specific activation patterns
            if hasattr(self._legacy, 'activate'):
                # Extract input from message
                user_input = message.content.get('user_input', '')
                context = message.content.get('context', {})

                # Call activate method
                result = await self._legacy.activate(user_input, context)

                # Format result
                return {
                    'success': True,
                    'agent_id': self.agent_id,
                    'brain_region': self.brain_region,
                    'result': result,
                    'message_type': message.message_type
                }
            else:
                # Fall back to parent implementation
                return await super().process_message(message)
        except Exception as e:
            logger.error(f"Error processing message in brain region {self.brain_region}: {e}")
            return {
                'success': False,
                'agent_id': self.agent_id,
                'brain_region': self.brain_region,
                'error': str(e)
            }
