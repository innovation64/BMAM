"""
Mock Object Factories
模拟对象工厂

Create test doubles for all interfaces
为所有接口创建测试替身
"""

from typing import List, Dict, Any, Optional, Callable, Awaitable
import numpy as np
from dataclasses import dataclass, field

from ..interfaces import (
    IMemorySystem,
    IMemoryRetriever,
    IMemoryStorer,
    IEmbeddingService,
    IVectorDatabase,
    IAgent,
    IMessageBus,
    IMessageHandler,
    AgentMessage,
    Memory,
    MessageHandler
)


class MockEmbeddingService(IEmbeddingService):
    """
    Mock embedding service for testing
    用于测试的模拟嵌入服务
    """

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension
        self.encode_text_calls: List[str] = []
        self.encode_batch_calls: List[List[str]] = []

    async def encode_text(self, text: str) -> np.ndarray:
        """Encode text to deterministic embedding for testing"""
        self.encode_text_calls.append(text)
        # Return deterministic embedding based on text hash
        return np.random.RandomState(hash(text) % 2**32).rand(self._dimension).astype(np.float32)

    async def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Encode multiple texts in batch"""
        self.encode_batch_calls.append(texts)
        return [await self.encode_text(text) for text in texts]

    @property
    def dimension(self) -> int:
        """Embedding vector dimension"""
        return self._dimension

    def reset(self):
        """Reset call tracking"""
        self.encode_text_calls.clear()
        self.encode_batch_calls.clear()


class MockVectorDatabase(IVectorDatabase):
    """
    Mock vector database for testing
    用于测试的模拟向量数据库
    """

    def __init__(self):
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1
        self.add_vectors_calls: List[Dict[str, Any]] = []
        self.search_calls: List[Dict[str, Any]] = []
        self.delete_calls: List[List[str]] = []

    async def add_vectors(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Add vectors to the mock database"""
        self.add_vectors_calls.append({
            'vectors': len(vectors),
            'metadata': metadata
        })

        ids = []
        for vec, meta in zip(vectors, metadata):
            vec_id = f"vec_{self._next_id}"
            self._next_id += 1
            self.vectors[vec_id] = vec
            self.metadata[vec_id] = meta
            ids.append(vec_id)
        return ids

    async def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity"""
        self.search_calls.append({
            'query_shape': query_vector.shape,
            'k': k,
            'threshold': threshold
        })

        results = []
        for vec_id, vec in self.vectors.items():
            # Cosine similarity
            similarity = float(
                np.dot(query_vector, vec) /
                (np.linalg.norm(query_vector) * np.linalg.norm(vec) + 1e-8)
            )

            if similarity >= threshold:
                result = {
                    'id': vec_id,
                    'similarity': similarity,
                    **self.metadata[vec_id]
                }
                results.append(result)

        # Sort by similarity descending
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:k]

    async def delete_vectors(self, ids: List[str]) -> int:
        """Delete vectors by IDs"""
        self.delete_calls.append(ids)

        count = 0
        for vec_id in ids:
            if vec_id in self.vectors:
                del self.vectors[vec_id]
                del self.metadata[vec_id]
                count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'total_vectors': len(self.vectors),
            'dimension': self.vectors[next(iter(self.vectors))].shape[0] if self.vectors else 0,
            'add_calls': len(self.add_vectors_calls),
            'search_calls': len(self.search_calls),
            'delete_calls': len(self.delete_calls)
        }

    def reset(self):
        """Reset mock state"""
        self.vectors.clear()
        self.metadata.clear()
        self._next_id = 1
        self.add_vectors_calls.clear()
        self.search_calls.clear()
        self.delete_calls.clear()


class MockMemorySystem(IMemorySystem):
    """
    Mock memory system for testing
    用于测试的模拟记忆系统
    """

    def __init__(self):
        self.memories: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1
        self.store_calls: List[Dict[str, Any]] = []
        self.retrieve_calls: List[Dict[str, Any]] = []
        self.search_calls: List[Dict[str, Any]] = []
        self.update_calls: List[Dict[str, Any]] = []
        self.delete_calls: List[str] = []

    async def store_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> str:
        """Store a new memory"""
        memory_id = f"mem_{self._next_id}"
        self._next_id += 1

        self.memories[memory_id] = {
            'memory_id': memory_id,
            'content': content,
            'metadata': metadata or {},
            'importance': importance,
            'embedding': None
        }

        self.store_calls.append({
            'content': content,
            'metadata': metadata,
            'importance': importance
        })

        return memory_id

    async def store_batch(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Store multiple memories in batch"""
        ids = []
        for mem in memories:
            mem_id = await self.store_memory(
                mem['content'],
                mem.get('metadata'),
                mem.get('importance', 0.5)
            )
            ids.append(mem_id)
        return ids

    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing memory"""
        self.update_calls.append({
            'memory_id': memory_id,
            'updates': updates
        })

        if memory_id in self.memories:
            self.memories[memory_id].update(updates)
            return True
        return False

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        self.delete_calls.append(memory_id)

        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False

    async def retrieve(
        self,
        query: str,
        k: int = 10,
        **filters
    ) -> List[Memory]:
        """Retrieve memories matching query"""
        self.retrieve_calls.append({
            'query': query,
            'k': k,
            'filters': filters
        })

        # Simple filtering by metadata
        results = []
        for mem in self.memories.values():
            # Check if memory matches filters
            if filters:
                match = all(
                    mem.get('metadata', {}).get(key) == value
                    for key, value in filters.items()
                )
                if not match:
                    continue

            # Convert to Memory object
            memory_obj = Memory(
                memory_id=mem['memory_id'],
                content=mem['content'],
                embedding=mem.get('embedding'),
                metadata=mem.get('metadata', {}),
                importance=mem.get('importance', 0.5),
                timestamp=mem.get('metadata', {}).get('timestamp', '')
            )
            results.append(memory_obj)

        return results[:k]

    async def retrieve_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by ID"""
        if memory_id not in self.memories:
            return None

        mem = self.memories[memory_id]
        return Memory(
            memory_id=mem['memory_id'],
            content=mem['content'],
            embedding=mem.get('embedding'),
            metadata=mem.get('metadata', {}),
            importance=mem.get('importance', 0.5),
            timestamp=mem.get('metadata', {}).get('timestamp', '')
        )

    async def retrieve_by_ids(self, memory_ids: List[str]) -> List[Memory]:
        """Retrieve multiple memories by IDs"""
        results = []
        for mem_id in memory_ids:
            mem = await self.retrieve_by_id(mem_id)
            if mem:
                results.append(mem)
        return results

    async def search_memories(
        self,
        query: str,
        search_type: str = "semantic",
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """Unified search interface"""
        self.search_calls.append({
            'query': query,
            'search_type': search_type,
            'k': k,
            'threshold': threshold,
            'filters': filters
        })

        # Return memories as dicts
        memories = await self.retrieve(query, k, **filters)
        return [
            {
                'memory_id': mem.memory_id,
                'content': mem.content,
                'metadata': mem.metadata,
                'importance': mem.importance
            }
            for mem in memories
        ]

    def get_system_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            'total_memories': len(self.memories),
            'store_calls': len(self.store_calls),
            'retrieve_calls': len(self.retrieve_calls),
            'search_calls': len(self.search_calls),
            'update_calls': len(self.update_calls),
            'delete_calls': len(self.delete_calls)
        }

    def reset(self):
        """Reset mock state"""
        self.memories.clear()
        self._next_id = 1
        self.store_calls.clear()
        self.retrieve_calls.clear()
        self.search_calls.clear()
        self.update_calls.clear()
        self.delete_calls.clear()


class MockAgent(IAgent):
    """
    Mock agent for testing
    用于测试的模拟智能体
    """

    def __init__(
        self,
        agent_id: str = "mock_agent",
        brain_region: str = "mock",
        process_result: Optional[Dict[str, Any]] = None
    ):
        self._agent_id = agent_id
        self._brain_region = brain_region
        self._process_result = process_result or {'success': True, 'message': 'Processed'}
        self.messages_received: List[AgentMessage] = []
        self.initialized = False
        self.shutdown_called = False

    @property
    def agent_id(self) -> str:
        """Unique agent identifier"""
        return self._agent_id

    @property
    def brain_region(self) -> str:
        """Associated brain region"""
        return self._brain_region

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process an incoming message"""
        self.messages_received.append(message)
        result = self._process_result.copy()
        result['agent_id'] = self.agent_id
        return result

    async def initialize(self):
        """Initialize agent resources"""
        self.initialized = True

    async def shutdown(self):
        """Cleanup agent resources"""
        self.shutdown_called = True

    def reset(self):
        """Reset mock state"""
        self.messages_received.clear()
        self.initialized = False
        self.shutdown_called = False


class MockMessageBus(IMessageBus):
    """
    Mock message bus for testing
    用于测试的模拟消息总线
    """

    def __init__(self):
        self.published_messages: List[AgentMessage] = []
        self.subscribers: Dict[str, List[MessageHandler]] = {}
        self.started = False
        self.stopped = False

    async def publish(self, message: AgentMessage):
        """Publish a message to the bus"""
        self.published_messages.append(message)

        # Call subscribers
        if message.message_type in self.subscribers:
            for handler in self.subscribers[message.message_type]:
                await handler(message)

    async def subscribe(self, message_type: str, handler: MessageHandler):
        """Subscribe to messages of a specific type"""
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(handler)

    async def unsubscribe(self, message_type: str, handler: MessageHandler):
        """Unsubscribe a handler"""
        if message_type in self.subscribers:
            try:
                self.subscribers[message_type].remove(handler)
            except ValueError:
                pass

    async def start(self):
        """Start message bus processing"""
        self.started = True

    async def stop(self):
        """Stop message bus processing"""
        self.stopped = True

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            'messages_published': len(self.published_messages),
            'subscriber_count': sum(len(subs) for subs in self.subscribers.values()),
            'started': self.started,
            'stopped': self.stopped
        }

    def reset(self):
        """Reset mock state"""
        self.published_messages.clear()
        self.subscribers.clear()
        self.started = False
        self.stopped = False


# Factory functions

def create_mock_memory_system() -> MockMemorySystem:
    """
    Create a mock memory system
    创建模拟记忆系统
    """
    return MockMemorySystem()


def create_mock_agent(
    agent_id: str = "test_agent",
    brain_region: str = "test",
    process_result: Optional[Dict[str, Any]] = None
) -> MockAgent:
    """
    Create a mock agent
    创建模拟智能体
    """
    return MockAgent(agent_id=agent_id, brain_region=brain_region, process_result=process_result)


def create_mock_message_bus() -> MockMessageBus:
    """
    Create a mock message bus
    创建模拟消息总线
    """
    return MockMessageBus()


def create_mock_embedding_service(dimension: int = 1536) -> MockEmbeddingService:
    """
    Create a mock embedding service
    创建模拟嵌入服务
    """
    return MockEmbeddingService(dimension=dimension)


def create_mock_vector_database() -> MockVectorDatabase:
    """
    Create a mock vector database
    创建模拟向量数据库
    """
    return MockVectorDatabase()


def create_mock_container():
    """
    Create a container with mock components
    创建包含模拟组件的容器
    """
    from ..container import Container
    from ..config import BMAMConfig

    container = Container()

    # Register test configuration
    config = BMAMConfig.for_testing()
    container.register_instance(BMAMConfig, config)

    # Register mocks
    container.register_instance(IMemorySystem, create_mock_memory_system())
    container.register_instance(IMessageBus, create_mock_message_bus())
    container.register_instance(IEmbeddingService, create_mock_embedding_service())
    container.register_instance(IVectorDatabase, create_mock_vector_database())

    return container
