"""
Message Bus Interfaces
消息总线接口

Defines contracts for message passing
定义消息传递的契约
"""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Any, Dict
from .agent_interface import AgentMessage


MessageHandler = Callable[[AgentMessage], Awaitable[Any]]


class IMessageBus(ABC):
    """
    Message Bus Interface
    消息总线接口

    Handles asynchronous message passing between components
    处理组件之间的异步消息传递
    """

    @abstractmethod
    async def publish(self, message: AgentMessage):
        """
        Publish a message to the bus
        向总线发布消息

        Args:
            message: Message to publish / 要发布的消息
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        message_type: str,
        handler: MessageHandler
    ):
        """
        Subscribe to messages of a specific type
        订阅特定类型的消息

        Args:
            message_type: Type of messages to receive / 要接收的消息类型
            handler: Async handler function / 异步处理函数
        """
        pass

    @abstractmethod
    async def unsubscribe(
        self,
        message_type: str,
        handler: MessageHandler
    ):
        """
        Unsubscribe a handler
        取消订阅处理器
        """
        pass

    @abstractmethod
    async def start(self):
        """
        Start message bus processing
        启动消息总线处理
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Stop message bus processing
        停止消息总线处理
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics
        获取消息总线统计信息
        """
        pass


class IMessageHandler(ABC):
    """
    Message Handler Interface
    消息处理器接口

    Components that handle messages implement this
    处理消息的组件实现此接口
    """

    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> Any:
        """
        Handle an incoming message
        处理传入消息

        Args:
            message: Message to handle / 要处理的消息

        Returns:
            Handler result / 处理器结果
        """
        pass

    @property
    @abstractmethod
    def handled_message_types(self) -> list[str]:
        """
        List of message types this handler processes
        此处理器处理的消息类型列表
        """
        pass
