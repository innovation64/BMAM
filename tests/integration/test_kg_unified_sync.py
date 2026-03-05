"""
Integration Test: KG Unification - Verify add_to_graph() Syncs to NetworkX
集成测试：验证 add_to_graph() 同步到 NetworkX

Tests the fix for the dual KG system issue where add_to_graph() was only
updating the memory dict and not syncing to the unified NetworkX graph.
"""

import pytest
import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.memory.knowledge_graph import LightweightKnowledgeGraph
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder


@pytest.fixture
def test_kg_dir(tmp_path):
    """Create temporary KG directory"""
    kg_dir = tmp_path / "test_kg_sync"
    kg_dir.mkdir(exist_ok=True)
    yield kg_dir
    # Cleanup
    if kg_dir.exists():
        shutil.rmtree(kg_dir)


@pytest.fixture
def unified_kg(test_kg_dir):
    """Create unified NetworkX KG"""
    kg = LightweightKnowledgeGraph(save_dir=str(test_kg_dir))
    return kg


@pytest.fixture
def kg_builder_with_unified(unified_kg):
    """Create KG builder with unified KG instance"""
    builder = KnowledgeGraphBuilder(
        llm_client=None,  # No LLM needed for this test
        use_spacy=False,  # Disable spaCy for faster test
        kg_instance=unified_kg
    )
    return builder


class TestKGUnifiedSync:
    """Test KG synchronization between memory dict and NetworkX"""

    def test_add_to_graph_syncs_to_networkx(self, kg_builder_with_unified, unified_kg):
        """
        Test that add_to_graph() syncs to NetworkX

        Before Fix:
        - add_to_graph() only updated memory dict
        - NetworkX graph remained empty

        After Fix:
        - add_to_graph() updates both memory dict AND NetworkX
        - Data is consistent across both systems
        """
        # Prepare test data
        entities = [
            {'name': 'Caroline', 'type': 'Person', 'mentions': 1},
            {'name': 'Sweden', 'type': 'Location', 'mentions': 1}
        ]
        relations = [
            {'source': 'Caroline', 'relation': 'researches', 'target': 'adoption'},
            {'source': 'adoption', 'relation': 'located_at', 'target': 'Sweden'}
        ]

        # Get initial stats
        initial_nx_stats = unified_kg.get_statistics()
        print(f"\n📊 Initial NetworkX stats: {initial_nx_stats}")

        # Add to graph (this should sync to NetworkX)
        kg_builder_with_unified.add_to_graph(entities, relations)

        # Verify memory dict has data
        memory_stats = kg_builder_with_unified.get_statistics()
        print(f"📊 Memory Dict stats: {memory_stats}")
        assert memory_stats['total_entities'] == 2, "Memory dict should have 2 entities"
        assert memory_stats['total_relations'] == 2, "Memory dict should have 2 relations"

        # ✅ Verify NetworkX has data (THIS IS THE FIX)
        nx_stats_full = unified_kg.get_statistics()
        print(f"📊 NetworkX stats after sync: {nx_stats_full}")

        # Extract basic stats (nested under 'basic')
        basic_stats = nx_stats_full.get('basic', {})

        # NetworkX should have at least 3 nodes (Caroline, adoption, Sweden)
        node_count = basic_stats.get('total_nodes', 0)
        assert node_count >= 3, \
            f"NetworkX should have at least 3 nodes, got {node_count}"

        # NetworkX should have at least 2 edges
        edge_count = basic_stats.get('total_edges', 0)
        assert edge_count >= 2, \
            f"NetworkX should have at least 2 edges, got {edge_count}"

        # Verify specific nodes exist
        caroline_node = unified_kg.get_node('Caroline')
        assert caroline_node is not None, "Caroline node should exist in NetworkX"
        assert caroline_node.entity_type == 'person', "Caroline should be a person"

        sweden_node = unified_kg.get_node('Sweden')
        assert sweden_node is not None, "Sweden node should exist in NetworkX"
        assert sweden_node.entity_type == 'location', "Sweden should be a location"

        print("✅ Test PASSED: add_to_graph() successfully syncs to NetworkX")

    def test_add_to_graph_without_unified_kg(self):
        """
        Test that add_to_graph() still works without unified KG (legacy mode)

        This ensures backward compatibility.
        """
        # Create builder WITHOUT unified KG
        builder = KnowledgeGraphBuilder(
            llm_client=None,
            use_spacy=False,
            kg_instance=None  # No unified KG
        )

        entities = [{'name': 'Test', 'type': 'Concept', 'mentions': 1}]
        relations = []

        # Should work without error (but only update memory dict)
        builder.add_to_graph(entities, relations)

        # Memory dict should have data
        stats = builder.get_statistics()
        assert stats['total_entities'] == 1
        assert stats['total_relations'] == 0

        print("✅ Test PASSED: Backward compatibility maintained")

    def test_multiple_adds_accumulate(self, kg_builder_with_unified, unified_kg):
        """
        Test that multiple add_to_graph() calls accumulate in both systems
        """
        # First batch
        entities1 = [{'name': 'Alice', 'type': 'Person', 'mentions': 1}]
        relations1 = []
        kg_builder_with_unified.add_to_graph(entities1, relations1)

        stats1_full = unified_kg.get_statistics()
        print(f"After batch 1: {stats1_full}")
        stats1 = stats1_full.get('basic', {})

        # Second batch
        entities2 = [{'name': 'Bob', 'type': 'Person', 'mentions': 1}]
        relations2 = [{'source': 'Alice', 'relation': 'knows', 'target': 'Bob'}]
        kg_builder_with_unified.add_to_graph(entities2, relations2)

        stats2_full = unified_kg.get_statistics()
        print(f"After batch 2: {stats2_full}")
        stats2 = stats2_full.get('basic', {})

        # Should have accumulated
        assert stats2.get('total_nodes', 0) > stats1.get('total_nodes', 0)
        assert stats2.get('total_edges', 0) > stats1.get('total_edges', 0)

        # Verify both nodes exist
        assert unified_kg.get_node('Alice') is not None
        assert unified_kg.get_node('Bob') is not None

        # Verify edge exists
        neighbors = unified_kg.get_neighbors('Alice')
        assert 'Bob' in neighbors

        print("✅ Test PASSED: Multiple adds accumulate correctly")

    def test_duplicate_entities_merge_mentions(self, kg_builder_with_unified, unified_kg):
        """
        Test that duplicate entities merge their mention counts
        """
        # Add entity first time
        entities1 = [{'name': 'Carol', 'type': 'Person', 'mentions': 1}]
        kg_builder_with_unified.add_to_graph(entities1, [])

        # Add same entity second time
        entities2 = [{'name': 'Carol', 'type': 'Person', 'mentions': 1}]
        kg_builder_with_unified.add_to_graph(entities2, [])

        # Memory dict should merge mentions
        memory_stats = kg_builder_with_unified.get_statistics()
        assert memory_stats['total_entities'] == 1, "Should have 1 unique entity"

        carol_memory = kg_builder_with_unified.knowledge_graph['entities']['Carol']
        assert carol_memory['mentions'] == 2, "Mentions should be merged (1+1=2)"

        # NetworkX should also reflect this (may create multiple nodes or update)
        carol_node = unified_kg.get_node('Carol')
        assert carol_node is not None

        print("✅ Test PASSED: Duplicate entities handled correctly")


@pytest.mark.asyncio
class TestHippocampusKGPersistence:
    """Test that Hippocampus memory storage persists to unified NetworkX KG"""

    async def test_hippocampus_stores_to_unified_kg(self, test_kg_dir):
        """
        Integration test: Hippocampus → KG Builder → NetworkX

        This tests the full pipeline:
        1. Hippocampus stores memory
        2. Calls kg_builder.add_to_graph()
        3. Data syncs to NetworkX
        """
        from src.agents.brain_regions.hippocampus_agent.core import HippocampusAgentCore
        from src.memory.knowledge_graph import LightweightKnowledgeGraph
        from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

        # Setup unified KG
        kg = LightweightKnowledgeGraph(save_dir=str(test_kg_dir))
        kg_builder = KnowledgeGraphBuilder(
            llm_client=None,
            use_spacy=False,
            kg_instance=kg
        )

        # Create Hippocampus with unified KG
        hippocampus = HippocampusAgentCore(
            capacity=1000,
            kg_builder=kg_builder
        )

        # Store memory with entities
        result = await hippocampus.store_memory(
            content="Caroline researched adoption agencies in Sweden",
            entities=['Caroline', 'Sweden', 'adoption'],
            importance=0.8,
            auto_extract_kg=True
        )

        print(f"\n📝 Memory stored: {result['memory_id']}")
        print(f"📊 Entities extracted: {result['entities_extracted']}")
        print(f"📊 Relations extracted: {result['relations_extracted']}")

        # Verify memory dict has data
        memory_stats = kg_builder.get_statistics()
        print(f"📊 Memory Dict stats: {memory_stats}")

        # ✅ Verify NetworkX has data (THIS IS THE KEY TEST)
        nx_stats_full = kg.get_statistics()
        print(f"📊 NetworkX stats: {nx_stats_full}")

        # Should have nodes and edges
        basic_stats = nx_stats_full.get('basic', {})
        assert basic_stats.get('total_nodes', 0) > 0, \
            "NetworkX should have nodes after Hippocampus storage"

        # Check if entities exist in NetworkX
        if 'Caroline' in result['entities_extracted']:
            caroline = kg.get_node('Caroline')
            if caroline:
                print(f"✅ Found Caroline in NetworkX: {caroline}")

        print("✅ Test PASSED: Hippocampus successfully persists to NetworkX")


@pytest.mark.integration
class TestKGPersistence:
    """Test KG persistence to disk"""

    def test_networkx_persists_to_disk(self, test_kg_dir, unified_kg):
        """Test that NetworkX KG persists to disk files"""

        # Add some data
        unified_kg.add_node('Test1', 'concept', 'Test Node 1')
        unified_kg.add_node('Test2', 'concept', 'Test Node 2')
        unified_kg.add_edge('Test1', 'Test2', 'related_to')

        # Save to disk
        unified_kg.save_graph()

        # Check files exist
        nodes_file = Path(test_kg_dir) / 'nodes.json'
        edges_file = Path(test_kg_dir) / 'edges.json'

        assert nodes_file.exists(), "nodes.json should be created"
        assert edges_file.exists(), "edges.json should be created"

        # Load from disk into new instance (loads automatically in __init__)
        kg2 = LightweightKnowledgeGraph(save_dir=str(test_kg_dir))

        stats_full = kg2.get_statistics()
        basic_stats = stats_full.get('basic', {})
        assert basic_stats.get('total_nodes', 0) >= 2, \
            f"Expected at least 2 nodes after reload, got {basic_stats.get('total_nodes', 0)}"
        assert basic_stats.get('total_edges', 0) >= 1, \
            f"Expected at least 1 edge after reload, got {basic_stats.get('total_edges', 0)}"

        print("✅ Test PASSED: NetworkX persists to disk correctly")


if __name__ == '__main__':
    """Run tests directly"""
    print("=" * 80)
    print("KG Unification Sync Tests")
    print("=" * 80)

    pytest.main([__file__, '-v', '-s'])
