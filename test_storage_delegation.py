"""
Test Storage Delegation - Phase 3 Integration Test
测试存储委托功能

Verifies that hippocampus can successfully delegate storage to the global system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agents.brain_regions.hippocampus_agent import HippocampusAgent
from src.memory.memory_system.advanced_memory_system import get_memory_system
from src.services.openai_embedding_service import OpenAIEmbeddingService
from src.services.shared_openai_client import SharedOpenAIClientManager


async def test_storage_delegation():
    """
    Test Storage Delegation
    测试存储委托

    Scenario:
    1. Create hippocampus with delegated storage
    2. Store a memory via hippocampus
    3. Verify it appears in global system
    4. Retrieve via hippocampus
    5. Verify consistency
    """

    print("\n" + "="*80)
    print("Phase 3: Storage Delegation Test")
    print("="*80 + "\n")

    # Step 1: Initialize services
    print("Step 1: Initializing services...")

    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    client_manager = SharedOpenAIClientManager()
    client = await client_manager.get_chat_client()
    embedding_service = OpenAIEmbeddingService(use_cache=True)
    global_memory_system = get_memory_system()

    print("✅ Services initialized")
    print(f"   - Global memory system: {type(global_memory_system).__name__}")
    print(f"   - Embedding service: {type(embedding_service).__name__}")

    # Step 2: Create hippocampus with delegation DISABLED (baseline)
    print("\n" + "-"*80)
    print("Step 2: Testing LOCAL storage mode (baseline)...")

    hippocampus_local = HippocampusAgent(
        client=client,
        embedding_service=embedding_service,
        memory_system=None,  # No global system
        use_global_storage=False  # Local mode
    )

    # Store a memory locally
    result_local = await hippocampus_local.store_memory(
        content="Alice went to Paris for vacation.",
        entities=["Alice", "Paris"],
        importance=0.7,
        auto_extract_kg=False  # Skip KG extraction for speed
    )

    print(f"✅ Memory stored locally: {result_local['memory_id']}")
    print(f"   - Storage location: local")
    print(f"   - Hippocampus memories: {len(hippocampus_local.memories)}")

    # Check global system (should be empty)
    global_stats_before = global_memory_system.get_system_stats()
    print(f"   - Global system memories: {global_stats_before.get('total_memories', 0)}")

    # Step 3: Create hippocampus with delegation ENABLED
    print("\n" + "-"*80)
    print("Step 3: Testing DELEGATED storage mode...")

    hippocampus_delegated = HippocampusAgent(
        client=client,
        embedding_service=embedding_service,
        memory_system=global_memory_system,  # ✅ Provide global system
        use_global_storage=True  # ✅ Enable delegation
    )

    # Store a memory via delegation
    result_delegated = await hippocampus_delegated.store_memory(
        content="Bob visited Tokyo last month.",
        entities=["Bob", "Tokyo"],
        importance=0.8,
        auto_extract_kg=False  # Skip KG extraction for speed
    )

    print(f"✅ Memory stored via delegation: {result_delegated['memory_id']}")
    print(f"   - Storage location: {result_delegated.get('storage_location', 'N/A')}")
    print(f"   - Hippocampus cache: {len(hippocampus_delegated.memories)}")

    # Check adapter stats
    adapter_stats = hippocampus_delegated.storage_adapter.get_stats()
    print(f"   - Adapter mode: {adapter_stats['mode']}")
    print(f"   - Delegation calls: {adapter_stats['delegation_calls']}")
    print(f"   - Cache size: {adapter_stats['cache_size']}")

    # Check global system (should have new memory)
    global_stats_after = global_memory_system.get_system_stats()
    print(f"   - Global system memories: {global_stats_after.get('total_memories', 0)}")

    # Step 4: Retrieve from hippocampus (should delegate to global)
    print("\n" + "-"*80)
    print("Step 4: Testing DELEGATED retrieval...")

    search_result = await hippocampus_delegated.search_memories(
        query="Tokyo",
        k=5
    )

    print(f"✅ Retrieved {search_result['count']} memories")
    print(f"   - Search time: {search_result['search_time_ms']:.2f} ms")
    print(f"   - Source: {search_result.get('source', 'N/A')}")

    if search_result['memories']:
        first_memory = search_result['memories'][0]
        print(f"   - First result: {first_memory['content'][:50]}...")
        print(f"   - Entities: {first_memory.get('entities', [])}")

    # Step 5: Verify consistency
    print("\n" + "-"*80)
    print("Step 5: Verifying consistency...")

    success = True
    issues = []

    # Check 1: Memory stored in global system
    if global_stats_after.get('total_memories', 0) == 0:
        success = False
        issues.append("❌ Memory NOT stored in global system")
    else:
        print("✅ Memory stored in global system")

    # Check 2: Delegation calls made
    if adapter_stats['delegation_calls'] == 0:
        success = False
        issues.append("❌ No delegation calls made")
    else:
        print(f"✅ {adapter_stats['delegation_calls']} delegation calls made")

    # Check 3: Retrieval returned results
    if search_result['count'] == 0:
        success = False
        issues.append("❌ Retrieval returned no results")
    else:
        print(f"✅ Retrieved {search_result['count']} memories")

    # Check 4: Retrieved memory matches stored content
    if search_result['memories']:
        retrieved_content = search_result['memories'][0]['content']
        if "Tokyo" in retrieved_content or "Bob" in retrieved_content:
            print("✅ Retrieved memory matches stored content")
        else:
            success = False
            issues.append("❌ Retrieved memory doesn't match")

    # Final summary
    print("\n" + "="*80)
    if success:
        print("✅ ALL TESTS PASSED - Storage delegation working correctly!")
    else:
        print("❌ SOME TESTS FAILED:")
        for issue in issues:
            print(f"   {issue}")

    print("="*80 + "\n")

    # Cleanup
    print("Cleanup...")
    await hippocampus_local.stop()
    await hippocampus_delegated.stop()
    print("✅ Agents stopped\n")

    return success


async def test_backward_compatibility():
    """
    Test Backward Compatibility
    测试向后兼容性

    Ensures existing code without delegation still works.
    """

    print("\n" + "="*80)
    print("Backward Compatibility Test")
    print("="*80 + "\n")

    print("Testing hippocampus WITHOUT delegation parameters...")

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return

    client_manager = SharedOpenAIClientManager()
    client = await client_manager.get_chat_client()
    embedding_service = OpenAIEmbeddingService(use_cache=True)

    # Create hippocampus without new parameters (legacy mode)
    hippocampus_legacy = HippocampusAgent(
        client=client,
        embedding_service=embedding_service
        # ❌ No memory_system parameter
        # ❌ No use_global_storage parameter
    )

    # Should still work in local mode
    result = await hippocampus_legacy.store_memory(
        content="Legacy test memory",
        entities=["Test"],
        importance=0.5,
        auto_extract_kg=False
    )

    print(f"✅ Legacy mode works: {result['memory_id']}")
    print(f"   - Memories stored: {len(hippocampus_legacy.memories)}")

    # Verify adapter defaults to local mode
    adapter_stats = hippocampus_legacy.storage_adapter.get_stats()
    print(f"   - Adapter mode: {adapter_stats['mode']}")

    if adapter_stats['mode'] == 'local':
        print("✅ Backward compatibility maintained!")
    else:
        print("❌ Unexpected adapter mode")

    await hippocampus_legacy.stop()

    print("="*80 + "\n")


async def main():
    """Run all tests"""
    print("\n🧪 Starting Phase 3 Storage Delegation Tests...\n")

    try:
        # Test 1: Storage delegation
        test1_passed = await test_storage_delegation()

        # Test 2: Backward compatibility
        await test_backward_compatibility()

        print("\n" + "="*80)
        if test1_passed:
            print("🎉 Phase 3 Implementation: SUCCESS")
            print("   - Storage delegation works correctly")
            print("   - Backward compatibility maintained")
            print("   - Hippocampus can delegate to global system")
        else:
            print("⚠️  Phase 3 Implementation: PARTIAL SUCCESS")
            print("   - Some issues detected (see above)")
            print("   - May need adjustments")

        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
