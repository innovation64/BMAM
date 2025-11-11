"""
Message Bus and Background Task Management Module
Handles message queuing and background task orchestration for the BrainCoordinator
"""

import asyncio
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, Coroutine, Optional, Callable, Awaitable, List
from datetime import datetime
import json

from ..utils.config import get_logger

logger = get_logger(__name__)


class LearningLogger:
    """Append-only JSONL logger for learning and reasoning events."""

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(self, event: str, payload: Dict[str, Any]) -> None:
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'payload': payload
        }
        try:
            line = json.dumps(entry, ensure_ascii=False)
        except (TypeError, ValueError) as err:
            logger.warning(f"Failed to serialise learning log entry: {err}")
            return

        try:
            with self._lock:
                with self._log_path.open('a', encoding='utf-8') as stream:
                    stream.write(line + '\n')
        except (OSError, IOError) as err:
            logger.warning(f"Failed to persist learning log entry: {err}")


class MessageBusManager:
    """
    Manages message queue and background task processing

    IMPORTANT: This class should implement IMessageBus interface.
    Currently it doesn't inherit from the interface, causing test/production mismatch.
    TODO: Make this inherit from IMessageBus in next refactor.
    """

    def __init__(self):
        self.message_bus = asyncio.Queue()
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self._task_counter = 0
        self.is_running = False
        self._processing_task: Optional[asyncio.Task] = None
        self._subscribers: Dict[str, List[Callable[[Any], Awaitable[Any]]]] = defaultdict(list)
        self._wildcard_subscribers: List[Callable[[Any], Awaitable[Any]]] = []


    async def start(self):
        """Start message bus processing"""
        if self.is_running:
            return

        self.is_running = True
        self._processing_task = asyncio.create_task(self._process_message_bus())

    async def stop(self):
        """Stop message bus processing and cancel all tasks"""
        self.is_running = False

        # Cancel processing task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        # Cancel all agent tasks
        for task in list(self.agent_tasks.values()):
            if not task.done():
                task.cancel()

        if self.agent_tasks:
            await asyncio.gather(*self.agent_tasks.values(), return_exceptions=True)

        self.agent_tasks.clear()

    async def publish(self, message: Any) -> None:
        """Publish a message into the bus queue."""
        await self.message_bus.put(message)

    def subscribe(self, message_type: Optional[str], handler: Callable[[Any], Awaitable[Any]]) -> None:
        """
        Subscribe a handler to a message type.

        Args:
            message_type: Message type key. Use None or "*" for wildcard.
            handler: Awaitable handler that will receive the message.
        """
        if message_type in (None, "*"):
            self._wildcard_subscribers.append(handler)
        else:
            self._subscribers[message_type].append(handler)

    def unsubscribe(self, message_type: Optional[str], handler: Callable[[Any], Awaitable[Any]]) -> None:
        """Remove a handler subscription."""
        target_list = self._wildcard_subscribers if message_type in (None, "*") else self._subscribers.get(message_type, [])
        if handler in target_list:
            target_list.remove(handler)

    async def _process_message_bus(self):
        """Continuously drain the message bus and dispatch to subscribers."""
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.message_bus.get(), timeout=0.5)
                await self._dispatch_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message bus processing: {e}")

    async def _dispatch_message(self, message: Any) -> None:
        """
        Dispatch a message to the appropriate subscribers.

        Messages are expected to be dict-like with an optional 'type' key,
        but arbitrary payloads are tolerated.
        """
        message_type = None
        if isinstance(message, dict):
            message_type = message.get('type')

        handlers = list(self._wildcard_subscribers)
        if message_type and self._subscribers.get(message_type):
            handlers.extend(self._subscribers[message_type])

        if not handlers:
            logger.debug("Message bus dropped message without subscribers: %s", message_type or type(message))
            return

        for handler in handlers:
            try:
                await handler(message)
            except Exception as exc:
                logger.error("Message handler %s failed: %s", getattr(handler, "__name__", handler), exc, exc_info=True)

    def create_background_task(self, label: str, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """
        Create a labeled background task

        Args:
            label: Human-readable label for the task
            coro: Coroutine to execute

        Returns:
            Created asyncio.Task
        """
        task = asyncio.create_task(coro)
        self._task_counter += 1
        task_id = f"{label}_{self._task_counter}"
        self.agent_tasks[task_id] = task

        # Clean up when done
        def cleanup(t):
            if task_id in self.agent_tasks:
                del self.agent_tasks[task_id]

        task.add_done_callback(cleanup)

        return task

    def get_active_tasks(self) -> Dict[str, asyncio.Task]:
        """Get currently active background tasks"""
        return {k: v for k, v in self.agent_tasks.items() if not v.done()}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics (IMessageBus interface compliance)

        Implements the get_stats() method required by IMessageBus interface.

        Returns:
            Dictionary containing:
            - is_running: bool - whether the bus is actively processing
            - active_tasks: int - number of background tasks
            - subscriber_count: int - number of type-specific subscribers
            - wildcard_subscribers: int - number of wildcard subscribers
            - queue_size: int - current message queue size
            - total_subscribers: int - total number of all subscribers
        """
        return {
            'is_running': self.is_running,
            'active_tasks': len([t for t in self.agent_tasks.values() if not t.done()]),
            'subscriber_count': sum(len(handlers) for handlers in self._subscribers.values()),
            'wildcard_subscribers': len(self._wildcard_subscribers),
            'queue_size': self.message_bus.qsize(),
            'total_subscribers': sum(len(handlers) for handlers in self._subscribers.values()) + len(self._wildcard_subscribers)
        }

    def get_task_count(self) -> int:
        """Get total number of active tasks"""
        return len([v for v in self.agent_tasks.values() if not v.done()])
