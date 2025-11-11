"""
Tests for Adapters
适配器测试

Verify that all adapters properly bridge legacy implementations to interfaces
验证所有适配器正确地将遗留实现桥接到接口
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, Mock
from src.core.adapters import (
    MemorySystemAdapter,
    EmbeddingServiceAdapter,
    VectorDatabaseAdapter,
    AgentAdapter,
    BrainRegionAgentAdapter
)
from src.core.interfaces import (
    IMemorySystem,
    IEmbeddingService,
    IVectorDatabase,
    IAgent,
    AgentMessage
)


class TestMemorySystemAdapter:
    """Test MemorySystemAdapter"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify adapter implements IMemorySystem"""
        # Create a mock legacy system
        legacy = AsyncMock()
        legacy.store_memory = AsyncMock(return_value="mem_123")

        adapter = MemorySystemAdapter(legacy)
        assert isinstance(adapter, IMemorySystem)

    @pytest.mark.asyncio
    async def test_store_memory(self):
        """Test memory storage delegation"""
        legacy = AsyncMock()
        legacy.store_memory = AsyncMock(return_value="mem_123")

        adapter = MemorySystemAdapter(legacy)
        memory_id = await adapter.store_memory("Test content", importance=0.8)

        assert memory_id == "mem_123"
        legacy.store_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test search delegation"""
        legacy = AsyncMock()
        legacy.search_memories = AsyncMock(return_value=[
            {'memory_id': 'mem_1', 'content': 'Test 1'},
            {'memory_id': 'mem_2', 'content': 'Test 2'}
        ])

        adapter = MemorySystemAdapter(legacy)
        results = await adapter.search_memories("query", k=2)

        assert len(results) == 2
        legacy.search_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve(self):
        """Test retrieval delegation"""
        legacy = AsyncMock()
        legacy.search_memories = AsyncMock(return_value=[
            {
                'memory_id': 'mem_1',
                'content': 'Test',
                'metadata': {},
                'importance': 0.5,
                'timestamp': '2024-01-01'
            }
        ])

        adapter = MemorySystemAdapter(legacy)
        memories = await adapter.retrieve("query", k=1)

        assert len(memories) == 1
        assert memories[0].content == 'Test'

    def test_get_system_stats(self):
        """Test stats delegation"""
        legacy = Mock()
        legacy.get_system_stats = Mock(return_value={'total': 100})

        adapter = MemorySystemAdapter(legacy)
        stats = adapter.get_system_stats()

        assert 'total' in stats or 'adapter' in stats


class TestEmbeddingServiceAdapter:
    """Test EmbeddingServiceAdapter"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify adapter implements IEmbeddingService"""
        legacy = AsyncMock()
        legacy.encode_text = AsyncMock(return_value=np.random.rand(128))
        legacy.dimension = 128

        adapter = EmbeddingServiceAdapter(legacy)
        assert isinstance(adapter, IEmbeddingService)

    @pytest.mark.asyncio
    async def test_encode_text(self):
        """Test text encoding delegation"""
        legacy = AsyncMock()
        expected = np.random.rand(128)
        legacy.encode_text = AsyncMock(return_value=expected)

        adapter = EmbeddingServiceAdapter(legacy)
        result = await adapter.encode_text("test")

        np.testing.assert_array_equal(result, expected)
        legacy.encode_text.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_encode_batch(self):
        """Test batch encoding delegation"""
        legacy = AsyncMock()
        expected = [np.random.rand(128) for _ in range(3)]
        legacy.encode_batch = AsyncMock(return_value=expected)

        adapter = EmbeddingServiceAdapter(legacy)
        results = await adapter.encode_batch(["a", "b", "c"])

        assert len(results) == 3
        legacy.encode_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_encode_batch_fallback(self):
        """Test batch encoding fallback to sequential"""
        # Create a legacy object without encode_batch
        legacy = Mock()
        legacy.encode_text = AsyncMock(side_effect=[
            np.random.rand(128),
            np.random.rand(128)
        ])
        # Explicitly remove encode_batch attributes
        legacy.encode_batch = None
        legacy.get_embeddings = None

        adapter = EmbeddingServiceAdapter(legacy)
        results = await adapter.encode_batch(["a", "b"])

        assert len(results) == 2
        assert legacy.encode_text.call_count == 2

    def test_dimension_property(self):
        """Test dimension property"""
        legacy = Mock()
        legacy.dimension = 256

        adapter = EmbeddingServiceAdapter(legacy)
        assert adapter.dimension == 256


class TestVectorDatabaseAdapter:
    """Test VectorDatabaseAdapter"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify adapter implements IVectorDatabase"""
        legacy = AsyncMock()
        legacy.add_vectors = AsyncMock(return_value=["id1", "id2"])

        adapter = VectorDatabaseAdapter(legacy)
        assert isinstance(adapter, IVectorDatabase)

    @pytest.mark.asyncio
    async def test_add_vectors(self):
        """Test vector addition delegation"""
        legacy = AsyncMock()
        expected_ids = ["vec_1", "vec_2"]
        legacy.add_vectors = AsyncMock(return_value=expected_ids)

        adapter = VectorDatabaseAdapter(legacy)
        vectors = [np.random.rand(128) for _ in range(2)]
        metadata = [{'id': i} for i in range(2)]

        ids = await adapter.add_vectors(vectors, metadata)

        assert ids == expected_ids
        legacy.add_vectors.assert_called_once()

    @pytest.mark.asyncio
    async def test_search(self):
        """Test search delegation"""
        legacy = AsyncMock()
        expected_results = [
            {'id': 'vec_1', 'similarity': 0.9},
            {'id': 'vec_2', 'similarity': 0.8}
        ]
        legacy.search = AsyncMock(return_value=expected_results)

        adapter = VectorDatabaseAdapter(legacy)
        query = np.random.rand(128)

        results = await adapter.search(query, k=2)

        assert len(results) == 2
        assert results[0]['similarity'] == 0.9

    @pytest.mark.asyncio
    async def test_delete_vectors(self):
        """Test vector deletion delegation"""
        legacy = AsyncMock()
        legacy.delete_vectors = AsyncMock(return_value=2)

        adapter = VectorDatabaseAdapter(legacy)
        count = await adapter.delete_vectors(["vec_1", "vec_2"])

        assert count == 2
        legacy.delete_vectors.assert_called_once()

    def test_get_stats(self):
        """Test stats delegation"""
        legacy = Mock()
        legacy.get_stats = Mock(return_value={'total_vectors': 100})

        adapter = VectorDatabaseAdapter(legacy)
        stats = adapter.get_stats()

        assert 'total_vectors' in stats or 'adapter' in stats


class TestAgentAdapter:
    """Test AgentAdapter"""

    @pytest.mark.asyncio
    async def test_implements_interface(self):
        """Verify adapter implements IAgent"""
        legacy = AsyncMock()
        adapter = AgentAdapter(legacy, "test_id", "test_region")
        assert isinstance(adapter, IAgent)

    def test_properties(self):
        """Test agent properties"""
        legacy = Mock()
        adapter = AgentAdapter(legacy, "test_id", "test_region")

        assert adapter.agent_id == "test_id"
        assert adapter.brain_region == "test_region"

    @pytest.mark.asyncio
    async def test_process_message(self):
        """Test message processing delegation"""
        legacy = AsyncMock()
        expected_result = {'success': True, 'data': 'result'}
        legacy.process_message = AsyncMock(return_value=expected_result)

        adapter = AgentAdapter(legacy, "test_id", "test_region")
        message = AgentMessage(
            sender="test",
            receiver="test_id",
            message_type="request",
            content={}
        )

        result = await adapter.process_message(message)

        assert result == expected_result
        legacy.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_activate(self):
        """Test message processing via activate method"""
        # Create legacy object without process_message
        legacy = Mock()
        legacy.activate = AsyncMock(return_value={'output': 'test'})
        # Explicitly remove process_message attributes
        legacy.process_message = None
        legacy.process = None
        legacy.handle_message = None

        adapter = AgentAdapter(legacy, "test_id", "test_region")
        message = AgentMessage(
            sender="test",
            receiver="test_id",
            message_type="request",
            content={'input': 'test input'}
        )

        result = await adapter.process_message(message)

        assert result['success'] is True
        assert 'result' in result
        legacy.activate.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialization delegation"""
        legacy = AsyncMock()
        legacy.initialize = AsyncMock()

        adapter = AgentAdapter(legacy, "test_id", "test_region")
        await adapter.initialize()

        legacy.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test shutdown delegation"""
        legacy = AsyncMock()
        legacy.shutdown = AsyncMock()

        adapter = AgentAdapter(legacy, "test_id", "test_region")
        await adapter.shutdown()

        legacy.shutdown.assert_called_once()


class TestBrainRegionAgentAdapter:
    """Test BrainRegionAgentAdapter"""

    @pytest.mark.asyncio
    async def test_specialized_processing(self):
        """Test brain region specific processing"""
        legacy = AsyncMock()
        legacy.activate = AsyncMock(return_value={'output': 'test'})

        adapter = BrainRegionAgentAdapter(legacy, "hippocampus", "hippocampus")
        message = AgentMessage(
            sender="test",
            receiver="hippocampus",
            message_type="request",
            content={'user_input': 'test', 'context': {}}
        )

        result = await adapter.process_message(message)

        assert result['success'] is True
        assert result['brain_region'] == 'hippocampus'
        legacy.activate.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
