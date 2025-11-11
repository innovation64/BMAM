"""
Quick Verification Script: Test KG Synchronization Fix
快速验证脚本：测试知识图谱同步修复

Run this to verify that add_to_graph() now syncs to NetworkX.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.memory.knowledge_graph import LightweightKnowledgeGraph
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder


def test_kg_sync():
    """Test that add_to_graph() syncs to NetworkX"""

    print("\n" + "=" * 80)
    print("KG Synchronization Verification Test")
    print("=" * 80)

    # Setup
    print("\n1️⃣ Setting up unified KG...")
    kg_dir = Path("data/test_kg_verification")
    kg_dir.mkdir(parents=True, exist_ok=True)

    kg = LightweightKnowledgeGraph(save_dir=str(kg_dir))
    kg_builder = KnowledgeGraphBuilder(
        llm_client=None,
        use_spacy=False,
        kg_instance=kg
    )

    print(f"   ✅ KG directory: {kg_dir}")
    print(f"   ✅ KG builder initialized with unified KG: {kg_builder.kg is not None}")

    # Test data
    print("\n2️⃣ Preparing test data...")
    entities = [
        {'name': 'Caroline', 'type': 'Person', 'mentions': 1},
        {'name': 'Sweden', 'type': 'Location', 'mentions': 1},
        {'name': 'adoption', 'type': 'Concept', 'mentions': 1}
    ]
    relations = [
        {'source': 'Caroline', 'relation': 'researches', 'target': 'adoption'},
        {'source': 'adoption', 'relation': 'located_at', 'target': 'Sweden'}
    ]

    print(f"   📊 Entities: {len(entities)}")
    print(f"   📊 Relations: {len(relations)}")

    # Get initial stats
    print("\n3️⃣ Initial state...")
    initial_nx = kg.get_statistics()
    # NetworkX stats are nested under 'basic'
    basic_stats = initial_nx.get('basic', {})
    print(f"   📊 NetworkX: {basic_stats.get('total_nodes', 0)} nodes, {basic_stats.get('total_edges', 0)} edges")

    # Add to graph (THIS SHOULD NOW SYNC)
    print("\n4️⃣ Calling add_to_graph()...")
    print("   ⏳ This should sync to both memory dict AND NetworkX...")
    kg_builder.add_to_graph(entities, relations)

    # Check memory dict
    print("\n5️⃣ Verifying memory dict...")
    memory_stats = kg_builder.get_statistics()
    print(f"   📊 Memory Dict: {memory_stats['total_entities']} entities, {memory_stats['total_relations']} relations")

    # Check NetworkX (THE CRITICAL TEST)
    print("\n6️⃣ Verifying NetworkX (THE FIX)...")
    nx_stats_full = kg.get_statistics()
    nx_stats = nx_stats_full.get('basic', {})
    print(f"   📊 NetworkX: {nx_stats.get('total_nodes', 0)} nodes, {nx_stats.get('total_edges', 0)} edges")

    # Verify sync worked
    print("\n7️⃣ Verification Results...")

    success = True

    # Check 1: Memory dict should have data
    if memory_stats['total_entities'] >= 3:
        print("   ✅ Memory Dict: Has entities (expected)")
    else:
        print(f"   ❌ Memory Dict: Missing entities (got {memory_stats['total_entities']}, expected >=3)")
        success = False

    # Check 2: NetworkX should also have data (THIS IS THE FIX)
    node_count = nx_stats.get('total_nodes', 0)
    edge_count = nx_stats.get('total_edges', 0)

    if node_count >= 3:
        print("   ✅ NetworkX: Has nodes (FIXED!)")
    else:
        print(f"   ❌ NetworkX: Still empty (got {node_count} nodes)")
        print("   ⚠️  Fix may not be working!")
        success = False

    if edge_count >= 2:
        print("   ✅ NetworkX: Has edges (FIXED!)")
    else:
        print(f"   ❌ NetworkX: No edges (got {edge_count} edges)")
        success = False

    # Check 3: Verify specific nodes
    print("\n8️⃣ Checking specific nodes...")
    caroline = kg.get_node('Caroline')
    if caroline:
        print(f"   ✅ Caroline found: type={caroline.entity_type}")
    else:
        print("   ❌ Caroline not found in NetworkX")
        success = False

    sweden = kg.get_node('Sweden')
    if sweden:
        print(f"   ✅ Sweden found: type={sweden.entity_type}")
    else:
        print("   ❌ Sweden not found in NetworkX")
        success = False

    # Check 4: Query relationships
    print("\n9️⃣ Checking relationships...")
    if caroline:
        try:
            neighbors = kg.get_neighbors('Caroline')
            print(f"   📊 Caroline's neighbors: {len(neighbors)}")
            for n_id in neighbors[:5]:  # Show first 5
                print(f"      - {n_id}")
        except Exception as e:
            print(f"   ⚠️  Could not query neighbors: {e}")

    # Final result
    print("\n" + "=" * 80)
    if success:
        print("✅ SUCCESS: KG Synchronization is WORKING!")
        print("\nWhat's fixed:")
        print("  • add_to_graph() now syncs to NetworkX")
        print("  • Both memory dict and NetworkX have data")
        print("  • Entities and relations are accessible in NetworkX")
        print("\nYou can now use NetworkX KG in reasoning chains!")
    else:
        print("❌ FAILURE: KG Synchronization NOT working")
        print("\nPlease check:")
        print("  1. Is the fix applied to knowledge_graph_builder.py?")
        print("  2. Are there any errors in the logs?")
        print("  3. Is kg_instance being passed to KnowledgeGraphBuilder?")

    print("=" * 80)

    return success


def test_without_unified_kg():
    """Test backward compatibility - without unified KG"""

    print("\n" + "=" * 80)
    print("Backward Compatibility Test (No Unified KG)")
    print("=" * 80)

    # Create builder WITHOUT unified KG
    kg_builder = KnowledgeGraphBuilder(
        llm_client=None,
        use_spacy=False,
        kg_instance=None  # No unified KG
    )

    print(f"   KG instance: {kg_builder.kg}")
    print("   Expected: Should work in legacy mode (memory dict only)")

    entities = [{'name': 'Test', 'type': 'Concept', 'mentions': 1}]
    kg_builder.add_to_graph(entities, [])

    stats = kg_builder.get_statistics()
    print(f"   Memory Dict: {stats['total_entities']} entities")

    if stats['total_entities'] == 1:
        print("   ✅ Backward compatibility maintained")
        return True
    else:
        print("   ❌ Backward compatibility broken")
        return False


if __name__ == '__main__':
    print("\n🔬 KG Synchronization Verification")
    print("This script tests the fix for the dual KG system issue.\n")

    # Test 1: With unified KG (the fix)
    test1_pass = test_kg_sync()

    # Test 2: Without unified KG (backward compatibility)
    test2_pass = test_without_unified_kg()

    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Test 1 (KG Sync):            {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (Backward Compat):    {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print("=" * 80)

    if test1_pass and test2_pass:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("1. Run full integration tests: pytest tests/integration/test_kg_unified_sync.py")
        print("2. Update coordinator to use unified KG")
        print("3. Verify in real Hippocampus memory storage")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nPlease review the errors above and check the fix.")
        sys.exit(1)
