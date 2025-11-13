#!/usr/bin/env python3
"""
Quick test script for TemporalLobe auto-persistence
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.brain_regions.temporal_lobe_agent.temporal_lobe_agent import TemporalLobeAgent


async def test_persistence():
    """Test TemporalLobe auto-persistence"""
    print("=" * 80)
    print("🧪 Testing TemporalLobe Auto-Persistence")
    print("=" * 80)

    # Test 1: Create agent and store some memories
    print("\n📝 Test 1: Storing memories...")
    agent = TemporalLobeAgent(capacity=100)

    # Store a few test memories
    result1 = await agent.store_memory(
        content="Caroline and Melanie discussed AI",
        entities=["Caroline", "Melanie", "AI"],
        relations=[("Caroline", "discussed_with", "Melanie")],
        importance=0.8
    )
    print(f"   Stored memory 1: {result1['memory_id'][:8]}")

    result2 = await agent.store_memory(
        content="They talked about machine learning",
        entities=["machine learning"],
        relations=[("Caroline", "talked_about", "machine learning")],
        importance=0.7
    )
    print(f"   Stored memory 2: {result2['memory_id'][:8]}")

    result3 = await agent.store_memory(
        content="The conversation happened on Tuesday",
        entities=["Tuesday"],
        importance=0.5
    )
    print(f"   Stored memory 3: {result3['memory_id'][:8]}")

    stats = agent.get_statistics()
    print(f"\n   ✅ Stored {stats['current_memories']} memories")
    print(f"   ✅ Knowledge graph: {stats['knowledge_graph']['total_triples']} triples")

    # Check database file exists
    db_path = Path("data/temporal_lobe.db")
    db_size = db_path.stat().st_size if db_path.exists() else 0
    print(f"   ✅ Database file: {db_path} ({db_size} bytes)")

    # Test 2: Create new agent and verify auto-load
    print("\n📥 Test 2: Reloading from database...")
    agent2 = TemporalLobeAgent(capacity=100)

    stats2 = agent2.get_statistics()
    print(f"   ✅ Loaded {stats2['current_memories']} memories")
    print(f"   ✅ Knowledge graph: {stats2['knowledge_graph']['total_triples']} triples")

    # Verify memories match
    if stats2['current_memories'] == stats['current_memories']:
        print("\n✅ Persistence test PASSED!")
        print(f"   - Memories persisted: {stats['current_memories']}")
        print(f"   - Memories loaded: {stats2['current_memories']}")
        print(f"   - KG triples: {stats2['knowledge_graph']['total_triples']}")
        return 0
    else:
        print("\n❌ Persistence test FAILED!")
        print(f"   - Expected: {stats['current_memories']} memories")
        print(f"   - Got: {stats2['current_memories']} memories")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_persistence())
    sys.exit(exit_code)
