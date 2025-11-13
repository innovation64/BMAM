"""
Batch Consolidation Load Test
测试批量巩固（5-10条记忆）以验证proxy逻辑在负载下的稳定性
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_consolidation_pipeline import MemoryConsolidationPipeline
from src.memory.agent_storage_proxy import AgentStorageProxy

async def main():
    print("=" * 80)
    print("Batch Consolidation Load Test (10 memories)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Store 10 test memories
    print("\n📝 Storing 10 test memories...")
    test_inputs = [
        "Caroline visited the British Museum",
        "She studied ancient Egyptian artifacts",
        "Caroline had coffee at a London cafe",
        "She met her colleague David there",
        "They discussed AI safety research",
        "Caroline took notes on transformer architectures",
        "She walked through Hyde Park afterward",
        "The weather was sunny and pleasant",
        "Caroline bought a book at Waterstones",
        "It was about cognitive neuroscience"
    ]

    for i, text in enumerate(test_inputs):
        await coordinator.process_input(text)
        print(f"  [{i+1}/10] Stored: {text[:50]}...")

    print(f"\n✅ Hippocampus now has {len(coordinator.hippocampus.memories)} memories")

    # Get last 10 memory IDs
    last_10_ids = [mem.id for mem in coordinator.hippocampus.memories[-10:]]
    print(f"📋 Selected 10 IDs for consolidation: {[mid[:8] for mid in last_10_ids]}")

    # Prepare pipeline and proxies
    pipeline = MemoryConsolidationPipeline()
    hippocampus_proxy = AgentStorageProxy(coordinator.hippocampus, 'hippocampus')
    temporal_lobe_proxy = AgentStorageProxy(coordinator.temporal_lobe, 'temporal_lobe')

    # Check counts before consolidation
    temporal_before = len(coordinator.temporal_lobe.memories)
    kg_triples_before = len(coordinator.temporal_lobe.kg.get_all_triples()) if hasattr(coordinator.temporal_lobe, 'kg') else 0

    print(f"\n📊 Before consolidation:")
    print(f"  Temporal Lobe memories: {temporal_before}")
    print(f"  KG triples: {kg_triples_before}")

    # Run batch consolidation
    print(f"\n🔄 Running batch consolidation...")
    results = await pipeline.batch_consolidate(
        memory_ids=last_10_ids,
        consolidation_type='episodic_to_semantic',
        source_storage=hippocampus_proxy,
        target_storage=temporal_lobe_proxy,
        priority=0.7
    )

    # Check results
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    print(f"\n✅ Consolidation complete: {successful}/{len(results)} successful, {failed} failed")

    # Check counts after consolidation
    temporal_after = len(coordinator.temporal_lobe.memories)
    kg_triples_after = len(coordinator.temporal_lobe.kg.get_all_triples()) if hasattr(coordinator.temporal_lobe, 'kg') else 0

    print(f"\n📊 After consolidation:")
    print(f"  Temporal Lobe memories: {temporal_after} (+{temporal_after - temporal_before})")
    print(f"  KG triples: {kg_triples_after} (+{kg_triples_after - kg_triples_before})")

    # Show sample semantic memories
    if temporal_after > temporal_before:
        print(f"\n📚 Sample semantic memories created:")
        new_memories = coordinator.temporal_lobe.memories[temporal_before:temporal_before+3]
        for mem in new_memories:
            print(f"  - [{mem.memory_subtype}] {mem.content[:80]}...")

    # Validation
    print("\n" + "=" * 80)
    print("Validation Results:")
    print("=" * 80)

    if successful == len(results):
        print("✅ ALL consolidations successful!")
    elif successful > 0:
        print(f"⚠️  Partial success: {successful}/{len(results)}")
    else:
        print("❌ All consolidations failed!")

    if temporal_after > temporal_before:
        print(f"✅ Temporal Lobe grew by {temporal_after - temporal_before} memories")
    else:
        print("❌ No new semantic memories created")

    if kg_triples_after > kg_triples_before:
        print(f"✅ KG grew by {kg_triples_after - kg_triples_before} triples")

    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
