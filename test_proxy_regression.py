"""
Regression Test for AgentStorageProxy ID-based Retrieval
防止future"silent zero"失败的回归测试

Tests that region_retrieve() correctly honors ID filters and returns targeted memories
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.memory.agent_storage_proxy import AgentStorageProxy
from src.memory.memory_item import MemoryItem
from datetime import datetime

async def test_proxy_id_retrieval_with_retrieve_memory_by_id():
    """Test ID retrieval when agent has retrieve_memory_by_id method"""
    # Mock agent with retrieve_memory_by_id
    mock_agent = MagicMock()
    mock_agent.retrieve_memory_by_id = AsyncMock()

    # Setup test data
    test_id = "test-memory-123"
    test_memory_dict = {
        'id': test_id,
        'content': 'Test memory content',
        'memory_type': 'episodic',
        'timestamp': datetime.now().isoformat(),
        'importance': 0.8,
        'emotion_tags': ['happy'],
        'metadata': {'entities': ['test'], 'relations': []}
    }

    mock_agent.retrieve_memory_by_id.return_value = test_memory_dict

    # Create proxy
    proxy = AgentStorageProxy(mock_agent, 'test_region')

    # Test retrieval with ID filter
    results = await proxy.region_retrieve(
        query='',
        filters={'id': test_id},
        k=1
    )

    # Assertions
    assert len(results) == 1, "Should return exactly 1 memory"
    assert isinstance(results[0], MemoryItem), "Should return MemoryItem object"
    assert results[0].id == test_id, f"Memory ID should match: {results[0].id} != {test_id}"
    assert results[0].content == 'Test memory content'

    # Verify mock was called correctly
    mock_agent.retrieve_memory_by_id.assert_called_once_with(test_id)

    print("✅ Test passed: ID retrieval via retrieve_memory_by_id works")


async def test_proxy_id_retrieval_with_memory_dict():
    """Test ID retrieval when agent only has memory_dict"""
    # Mock agent with memory_dict but no retrieve_memory_by_id
    mock_agent = MagicMock()
    test_id = "dict-memory-456"

    test_memory = MemoryItem(
        id=test_id,
        content='Dict memory content',
        memory_type='semantic',
        timestamp=datetime.now(),
        importance=0.9,
        emotion_tags=[],
        metadata={}
    )

    mock_agent.memory_dict = {test_id: test_memory}

    # Create proxy (no retrieve_memory_by_id)
    proxy = AgentStorageProxy(mock_agent, 'test_region')

    # Test retrieval
    results = await proxy.region_retrieve(
        query='',
        filters={'id': test_id},
        k=1
    )

    # Assertions
    assert len(results) == 1, "Should return exactly 1 memory"
    assert results[0] == test_memory, "Should return the MemoryItem from dict"
    assert results[0].id == test_id

    print("✅ Test passed: ID retrieval via memory_dict works")


async def test_proxy_id_retrieval_not_found():
    """Test ID retrieval when memory doesn't exist"""
    mock_agent = MagicMock()
    mock_agent.retrieve_memory_by_id = AsyncMock(return_value=None)

    proxy = AgentStorageProxy(mock_agent, 'test_region')

    # Try to retrieve non-existent memory
    results = await proxy.region_retrieve(
        query='',
        filters={'id': 'nonexistent-id'},
        k=1
    )

    # Should return empty list, NOT raise exception
    assert results == [], "Should return empty list for non-existent ID"

    print("✅ Test passed: Non-existent ID returns empty list (not exception)")


async def test_proxy_semantic_search_fallback():
    """Test that semantic search still works when no ID filter"""
    mock_agent = MagicMock()
    mock_agent.search_memories = AsyncMock()

    mock_agent.search_memories.return_value = {
        'results': [
            {
                'id': 'semantic-1',
                'content': 'Semantic result 1',
                'memory_type': 'semantic',
                'timestamp': datetime.now().isoformat(),
                'importance': 0.7,
                'emotion_tags': [],
                'metadata': {}
            }
        ]
    }

    proxy = AgentStorageProxy(mock_agent, 'test_region')

    # Query without ID filter (semantic search)
    results = await proxy.region_retrieve(
        query='test query',
        filters=None,
        k=5
    )

    assert len(results) == 1
    assert results[0].id == 'semantic-1'

    # Verify search_memories was called (not retrieve_memory_by_id)
    mock_agent.search_memories.assert_called_once()

    print("✅ Test passed: Semantic search fallback works")


async def main():
    """Run all regression tests"""
    print("=" * 80)
    print("AgentStorageProxy Regression Tests")
    print("=" * 80)

    tests = [
        ("ID Retrieval via retrieve_memory_by_id", test_proxy_id_retrieval_with_retrieve_memory_by_id),
        ("ID Retrieval via memory_dict", test_proxy_id_retrieval_with_memory_dict),
        ("Non-existent ID Handling", test_proxy_id_retrieval_not_found),
        ("Semantic Search Fallback", test_proxy_semantic_search_fallback)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{'─' * 80}")
        print(f"Running: {name}")
        print(f"{'─' * 80}")
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'=' * 80}")

    if failed == 0:
        print("✅ All regression tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
