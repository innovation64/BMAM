"""
Agent System Interfaces
智能体系统接口

Defines contracts for agent operations
定义智能体操作的契约
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentMessage:
    """
    Standardized agent message format
    标准化的智能体消息格式
    """
    sender: str
    receiver: str
    message_type: str
    content: Dict[str, Any]
    priority: str = "medium"
    timestamp: str = None
    correlation_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.correlation_id is None:
            import uuid
            self.correlation_id = str(uuid.uuid4())


class IAgent(ABC):
    """
    Base Agent Interface
    基础智能体接口

    All agents must implement this interface
    所有智能体必须实现此接口
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """
        Unique agent identifier
        唯一智能体标识符
        """
        pass

    @property
    @abstractmethod
    def brain_region(self) -> str:
        """
        Associated brain region
        关联的大脑区域
        """
        pass

    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process an incoming message
        处理传入消息

        Args:
            message: Agent message to process / 要处理的智能体消息

        Returns:
            Processing result dictionary / 处理结果字典
        """
        pass

    @abstractmethod
    async def initialize(self):
        """
        Initialize agent resources
        初始化智能体资源
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """
        Cleanup agent resources
        清理智能体资源
        """
        pass


class IAgentActivator(ABC):
    """
    Agent Activation Interface
    智能体激活接口

    Handles agent lifecycle and activation
    处理智能体生命周期和激活
    """

    @abstractmethod
    async def activate_agent(
        self,
        agent_id: str,
        message: AgentMessage
    ) -> Dict[str, Any]:
        """
        Activate an agent with a message
        使用消息激活智能体

        Args:
            agent_id: Agent identifier / 智能体标识符
            message: Message to process / 要处理的消息

        Returns:
            Agent response / 智能体响应
        """
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[IAgent]:
        """
        Get agent by ID
        通过ID获取智能体
        """
        pass

    @abstractmethod
    def get_all_agents(self) -> Dict[str, IAgent]:
        """
        Get all registered agents
        获取所有已注册的智能体
        """
        pass

    @abstractmethod
    async def initialize_agents(self):
        """
        Initialize all agents
        初始化所有智能体
        """
        pass

    @abstractmethod
    async def shutdown_agents(self):
        """
        Shutdown all agents
        关闭所有智能体
        """
        pass
