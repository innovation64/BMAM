"""
MBTI Personality Agent Core
MBTI人格代理核心

Core initialization and personality management.
核心初始化和人格管理。
"""

import logging
from typing import Dict, Any, List

from ...base import BrainAgent, AgentMessage, BrainRegion
from ...llm_service import LLMServiceInterface, create_llm_service

from .types import MBTIType, CognitiveFunctionType
from .factory import MBTIPersonalityFactory
from .system_prompt import SystemPromptMixin
from .cognitive import CognitiveFunctionMixin
from .response import ResponseGenerationMixin
from .interaction import InteractionTrackingMixin
from .personality_management import PersonalityManagementMixin

logger = logging.getLogger(__name__)


class MBTIPersonalityCore(
    BrainAgent,
    SystemPromptMixin,
    CognitiveFunctionMixin,
    ResponseGenerationMixin,
    InteractionTrackingMixin,
    PersonalityManagementMixin
):
    """
    MBTI-based Personality Agent Core
    基于MBTI的人格代理核心

    Implements personality behaviors based on MBTI 16 personality types
    with cognitive functions and type-specific interaction patterns.

    基于MBTI 16种人格类型实现人格行为，包含认知功能和特定类型的交互模式。
    """

    def __init__(
        self,
        mbti_type: MBTIType = MBTIType.INTJ,
        client=None,
        llm_service: LLMServiceInterface = None,
        persona_memory_agent=None,
        name: str = "AI Assistant"
    ):
        """
        Initialize MBTI Personality Agent
        初始化MBTI人格代理

        Args:
            mbti_type: MBTI personality type / MBTI人格类型
            client: OpenAI client / OpenAI客户端
            llm_service: LLM service interface / LLM服务接口
            persona_memory_agent: Memory agent / 记忆代理
            name: Agent name / 代理名称
        """
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

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process personality-related messages
        处理人格相关消息

        Args:
            message: Agent message / 代理消息

        Returns:
            Dict containing response / 包含响应的字典
        """

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
