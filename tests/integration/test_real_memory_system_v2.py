"""
Real Integration Tests for Memory System V2
记忆系统V2真实集成测试

Tests with REAL components (OpenAI, FAISS, Database) - NO MOCKS
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.core.config import BMAMConfig, MemorySystemConfig
from src.core.container import Container as DependencyContainer
from src.memory.memory_system.registration import (
    create_memory_system,
    register_memory_system_components
)
from src.memory.memory_system.memory_system_v2 import AdvancedMemorySystemV2


@pytest.fixture
def test_config() -> BMAMConfig:
    """Test configuration"""
    return BMAMConfig.for_testing()


@pytest.fixture
def real_container() -> DependencyContainer:
    """Real DI container with real components"""
    container = DependencyContainer()
    register_memory_system_components(container)
    return container


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_real_storage(test_config):
    """
    Test V2 memory system with REAL storage
    使用真实存储测试V2记忆系统
    """
    # Create system with real components
    memory = create_memory_system(config=test_config.memory)

    # Store real memory
    memory_id = await memory.store_memory("Test memory content for integration")

    assert memory_id is not None
    assert isinstance(memory_id, str)
    assert len(memory_id) > 0

    print(f"✓ Stored memory with ID: {memory_id}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_real_retrieval(test_config):
    """
    Test V2 memory system with REAL retrieval
    使用真实检索测试V2记忆系统
    """
    memory = create_memory_system(config=test_config.memory)

    # Store test memories
    test_contents = [
        "Artificial intelligence is the future of technology",
        "Machine learning algorithms can learn from data",
        "Neural networks mimic the human brain structure",
        "Deep learning uses multiple layers of neurons",
        "Python is a popular programming language for AI"
    ]

    stored_ids = []
    for content in test_contents:
        memory_id = await memory.store_memory(content)
        stored_ids.append(memory_id)

    print(f"✓ Stored {len(stored_ids)} test memories")

    # Retrieve with real embeddings and FAISS search
    results = await memory.retrieve_memories("artificial intelligence", k=3)

    assert len(results) > 0
    assert len(results) <= 3

    # Verify results have expected structure
    for result in results:
        assert 'content' in result or 'memory' in result
        assert 'similarity_score' in result or 'score' in result

    print(f"✓ Retrieved {len(results)} relevant memories")
    print(f"  Top result: {str(results[0])[:100]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_real_semantic_search(test_config):
    """
    Test V2 with REAL semantic search
    使用真实语义搜索测试V2
    """
    memory = create_memory_system(config=test_config.memory)

    # Store domain-specific memories
    await memory.store_memory("The hippocampus is crucial for forming new memories")
    await memory.store_memory("The prefrontal cortex controls executive functions")
    await memory.store_memory("The amygdala processes emotional responses")
    await memory.store_memory("Neurons communicate through synaptic connections")

    # Search with semantic similarity (should find brain-related content)
    results = await memory.search_memories(
        "brain memory formation",
        search_type="semantic",
        k=2
    )

    assert len(results) > 0
    print(f"✓ Semantic search returned {len(results)} results")

    # Results should be relevant to brain/memory
    for i, result in enumerate(results):
        print(f"  Result {i+1}: {str(result)[:80]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_real_hybrid_search(test_config):
    """
    Test V2 with REAL hybrid search
    使用真实混合搜索测试V2
    """
    memory = create_memory_system(config=test_config.memory)

    # Store memories with metadata
    await memory.store_memory(
        "Meeting with team about project roadmap",
        metadata={'type': 'meeting', 'importance': 0.8}
    )
    await memory.store_memory(
        "Personal note: remember to buy groceries",
        metadata={'type': 'personal', 'importance': 0.3}
    )
    await memory.store_memory(
        "Project deadline is next Friday",
        metadata={'type': 'meeting', 'importance': 0.9}
    )

    # Hybrid search: semantic + metadata filter
    results = await memory.search_memories(
        "project meeting",
        search_type="hybrid",
        k=5,
        metadata_filter={'type': 'meeting'}
    )

    assert len(results) > 0
    print(f"✓ Hybrid search returned {len(results)} filtered results")

    # All results should have 'meeting' type
    for result in results:
        if 'metadata' in result:
            assert result['metadata'].get('type') == 'meeting'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_lazy_initialization(test_config):
    """
    Test that V2 has no initialization side effects
    测试V2没有初始化副作用
    """
    # Creating system should NOT trigger initialization
    memory = create_memory_system(config=test_config.memory)

    # Check it's created but not initialized
    assert hasattr(memory, '_initialized')
    assert memory._initialized == False

    print("✓ Memory system created without initialization")

    # First operation should trigger initialization
    memory_id = await memory.store_memory("Test lazy initialization")

    # Now it should be initialized
    assert memory._initialized == True
    assert memory_id is not None

    print("✓ Lazy initialization triggered on first use")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_stats(test_config):
    """
    Test V2 system statistics
    测试V2系统统计
    """
    memory = create_memory_system(config=test_config.memory)

    # Store some memories
    for i in range(5):
        await memory.store_memory(f"Test memory {i}")

    # Get stats
    stats = memory.get_system_stats()

    assert stats is not None
    assert isinstance(stats, dict)

    print(f"✓ System stats: {stats}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_large_batch(test_config):
    """
    Test V2 with large batch of memories
    使用大批量记忆测试V2
    """
    memory = create_memory_system(config=test_config.memory)

    # Store 50 memories
    batch_size = 50
    print(f"Storing {batch_size} memories...")

    for i in range(batch_size):
        await memory.store_memory(f"Batch memory {i}: Some content about topic {i % 10}")

    print(f"✓ Stored {batch_size} memories")

    # Search should work efficiently
    results = await memory.retrieve_memories("topic 5", k=10)

    assert len(results) > 0
    assert len(results) <= 10

    print(f"✓ Retrieved {len(results)} results from {batch_size} memories")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_container_resolution(real_container):
    """
    Test resolving memory system from DI container
    测试从DI容器解析记忆系统
    """
    from src.core.interfaces.memory_interface import IMemorySystem

    # Resolve from container
    memory = real_container.resolve(IMemorySystem)

    assert memory is not None
    assert isinstance(memory, AdvancedMemorySystemV2)

    # Should work normally
    memory_id = await memory.store_memory("Container resolution test")
    assert memory_id is not None

    print("✓ Memory system resolved from DI container")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_system_v2_concurrent_operations(test_config):
    """
    Test V2 with concurrent operations
    使用并发操作测试V2
    """
    memory = create_memory_system(config=test_config.memory)

    # Store memories concurrently
    async def store_memory(i: int) -> str:
        return await memory.store_memory(f"Concurrent memory {i}")

    # Create 10 concurrent store operations
    tasks = [store_memory(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert all(r is not None for r in results)

    print(f"✓ Completed 10 concurrent store operations")

    # Concurrent retrieval
    async def retrieve_memories(query: str) -> List[Dict]:
        return await memory.retrieve_memories(query, k=5)

    queries = ["memory", "concurrent", "test"]
    results = await asyncio.gather(*[retrieve_memories(q) for q in queries])

    assert len(results) == 3
    print(f"✓ Completed 3 concurrent retrieve operations")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
