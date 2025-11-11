"""
Tests for Mock Factories
模拟工厂测试

Verify that all mock objects properly implement their interfaces
验证所有模拟对象正确实现其接口
"""

import pytest
import numpy as np
from src.core.testing import (
    MockMemorySystem,
    MockAgent,
    MockMessageBus,
    MockEmbeddingService,
    MockVectorDatabase,
    create_mock_memory_system,
    create_mock_agent,
    create_mock_message_bus,
    create_mock_embedding_service,
    create_mock_vector_database,
    create_mock_container
)
from src.core.interfaces import (
    IMemorySystem,
    IAgent,
    IMessageBus,
    IEmbeddingService,
    IVectorDatabase,
    AgentMessage
)


class TestMockEmbeddingService:
    """Test MockEmbeddingService"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify mock implements IEmbeddingService"""
        mock = create_mock_embedding_service()
        assert isinstance(mock, IEmbeddingService)

    @pytest.mark.asyncio
    async def test_encode_text(self):
        """Test text encoding"""
        mock = create_mock_embedding_service(dimension=128)

        embedding = await mock.encode_text("hello world")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (128,)
        assert len(mock.encode_text_calls) == 1
        assert mock.encode_text_calls[0] == "hello world"

    @pytest.mark.asyncio
    async def test_encode_batch(self):
        """Test batch encoding"""
        mock = create_mock_embedding_service()
        texts = ["hello", "world", "test"]

        embeddings = await mock.encode_batch(texts)

        assert len(embeddings) == 3
        assert all(isinstance(e, np.ndarray) for e in embeddings)
        assert len(mock.encode_batch_calls) == 1

    def test_dimension_property(self):
        """Test dimension property"""
        mock = create_mock_embedding_service(dimension=256)
        assert mock.dimension == 256

    @pytest.mark.asyncio
    async def test_deterministic_encoding(self):
        """Test that same text produces same embedding"""
        mock = create_mock_embedding_service()

        emb1 = await mock.encode_text("test")
        emb2 = await mock.encode_text("test")

        np.testing.assert_array_equal(emb1, emb2)


class TestMockVectorDatabase:
    """Test MockVectorDatabase"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify mock implements IVectorDatabase"""
        mock = create_mock_vector_database()
        assert isinstance(mock, IVectorDatabase)

    @pytest.mark.asyncio
    async def test_add_vectors(self):
        """Test adding vectors"""
        mock = create_mock_vector_database()
        vectors = [np.random.rand(128) for _ in range(3)]
        metadata = [{'id': i} for i in range(3)]

        ids = await mock.add_vectors(vectors, metadata)

        assert len(ids) == 3
        assert all(id.startswith('vec_') for id in ids)
        assert len(mock.vectors) == 3

    @pytest.mark.asyncio
    async def test_search(self):
        """Test vector search"""
        mock = create_mock_vector_database()

        # Add some vectors
        vectors = [np.random.rand(128) for _ in range(5)]
        metadata = [{'content': f'doc{i}'} for i in range(5)]
        await mock.add_vectors(vectors, metadata)

        # Search
        query = np.random.rand(128)
        results = await mock.search(query, k=3)

        assert len(results) <= 3
        assert all('similarity' in r for r in results)
        assert all('id' in r for r in results)

    @pytest.mark.asyncio
    async def test_delete_vectors(self):
        """Test vector deletion"""
        mock = create_mock_vector_database()

        # Add vectors
        vectors = [np.random.rand(128) for _ in range(3)]
        metadata = [{'id': i} for i in range(3)]
        ids = await mock.add_vectors(vectors, metadata)

        # Delete
        count = await mock.delete_vectors([ids[0], ids[1]])

        assert count == 2
        assert len(mock.vectors) == 1

    def test_get_stats(self):
        """Test statistics"""
        mock = create_mock_vector_database()
        stats = mock.get_stats()

        assert 'total_vectors' in stats
        assert stats['total_vectors'] == 0


class TestMockMemorySystem:
    """Test MockMemorySystem"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify mock implements IMemorySystem"""
        mock = create_mock_memory_system()
        assert isinstance(mock, IMemorySystem)

    @pytest.mark.asyncio
    async def test_store_memory(self):
        """Test memory storage"""
        mock = create_mock_memory_system()

        memory_id = await mock.store_memory(
            "Test content",
            metadata={'type': 'test'},
            importance=0.8
        )

        assert memory_id.startswith('mem_')
        assert len(mock.memories) == 1
        assert len(mock.store_calls) == 1

    @pytest.mark.asyncio
    async def test_retrieve_by_id(self):
        """Test retrieval by ID"""
        mock = create_mock_memory_system()

        memory_id = await mock.store_memory("Test content")
        memory = await mock.retrieve_by_id(memory_id)

        assert memory is not None
        assert memory.memory_id == memory_id
        assert memory.content == "Test content"

    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test memory search"""
        mock = create_mock_memory_system()

        # Store some memories
        await mock.store_memory("First", metadata={'type': 'test'})
        await mock.store_memory("Second", metadata={'type': 'test'})
        mock.store_calls.clear()  # Reset call tracking

        # Search
        results = await mock.search_memories("query", k=5)

        assert len(results) <= 5
        assert len(mock.search_calls) == 1

    @pytest.mark.asyncio
    async def test_update_memory(self):
        """Test memory update"""
        mock = create_mock_memory_system()

        memory_id = await mock.store_memory("Original")
        success = await mock.update_memory(memory_id, {'importance': 0.9})

        assert success is True
        assert len(mock.update_calls) == 1

    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """Test memory deletion"""
        mock = create_mock_memory_system()

        memory_id = await mock.store_memory("To delete")
        success = await mock.delete_memory(memory_id)

        assert success is True
        assert memory_id not in mock.memories

    def test_get_system_stats(self):
        """Test system statistics"""
        mock = create_mock_memory_system()
        stats = mock.get_system_stats()

        assert 'total_memories' in stats
        assert 'store_calls' in stats


class TestMockAgent:
    """Test MockAgent"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify mock implements IAgent"""
        mock = create_mock_agent()
        assert isinstance(mock, IAgent)

    def test_properties(self):
        """Test agent properties"""
        mock = create_mock_agent("test_id", "test_region")

        assert mock.agent_id == "test_id"
        assert mock.brain_region == "test_region"

    @pytest.mark.asyncio
    async def test_process_message(self):
        """Test message processing"""
        mock = create_mock_agent()
        message = AgentMessage(
            sender="test",
            receiver=mock.agent_id,
            message_type="request",
            content={'data': 'test'}
        )

        result = await mock.process_message(message)

        assert result['success'] is True
        assert result['agent_id'] == mock.agent_id
        assert len(mock.messages_received) == 1

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test agent initialization"""
        mock = create_mock_agent()

        await mock.initialize()

        assert mock.initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test agent shutdown"""
        mock = create_mock_agent()

        await mock.shutdown()

        assert mock.shutdown_called is True


class TestMockMessageBus:
    """Test MockMessageBus"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify mock implements IMessageBus"""
        mock = create_mock_message_bus()
        assert isinstance(mock, IMessageBus)

    @pytest.mark.asyncio
    async def test_publish(self):
        """Test message publishing"""
        mock = create_mock_message_bus()
        message = AgentMessage(
            sender="test",
            receiver="agent",
            message_type="request",
            content={}
        )

        await mock.publish(message)

        assert len(mock.published_messages) == 1

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """Test subscription"""
        mock = create_mock_message_bus()
        received = []

        async def handler(msg):
            received.append(msg)

        await mock.subscribe("test_type", handler)

        # Publish message
        message = AgentMessage(
            sender="test",
            receiver="agent",
            message_type="test_type",
            content={}
        )
        await mock.publish(message)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop"""
        mock = create_mock_message_bus()

        await mock.start()
        assert mock.started is True

        await mock.stop()
        assert mock.stopped is True

    def test_get_stats(self):
        """Test statistics"""
        mock = create_mock_message_bus()
        stats = mock.get_stats()

        assert 'messages_published' in stats
        assert 'subscriber_count' in stats


class TestMockContainer:
    """Test mock container factory"""

    def test_create_mock_container(self):
        """Test container creation"""
        container = create_mock_container()

        # Verify all components are registered
        from src.core.config import BMAMConfig
        config = container.resolve(BMAMConfig)
        assert config is not None

        memory = container.resolve(IMemorySystem)
        assert isinstance(memory, MockMemorySystem)

        bus = container.resolve(IMessageBus)
        assert isinstance(bus, MockMessageBus)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
