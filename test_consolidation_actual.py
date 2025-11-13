"""
Test Actual Consolidation Flow
测试实际巩固流程

验证:
1. hippocampus.retrieve_memory_by_id能获取记忆
2. Consolidation pipeline能提取语义知识
3. 语义记忆被存储到Temporal Lobe
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def test_consolidation():
    print("=" * 80)
    print("实际巩固流程测试")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    print("\n✅ Coordinator初始化完成\n")

    # 存储20条记忆以触发巩固
    print("=" * 80)
    print("Step 1: 存储20条测试记忆 (触发批量巩固)")
    print("=" * 80)

    test_memories = [
        "Caroline visited the Natural History Museum on June 5, 2023",
        "She learned about dinosaur fossils and prehistoric life",
        "Caroline attended a concert at Royal Albert Hall",
        "The orchestra performed Beethoven's 9th Symphony",
        "Caroline went to a coffee shop in Shoreditch",
        "She met with friends to discuss AI research",
        "Caroline visited the Tate Modern art gallery",
        "She saw contemporary art exhibitions",
        "Caroline took the Tube to work every morning",
        "She works as a data scientist in London",
        "Caroline enjoys reading science fiction novels",
        "Her favorite author is Isaac Asimov",
        "Caroline participated in a hackathon event",
        "Her team built a machine learning project",
        "Caroline went hiking in the Lake District",
        "She enjoyed the scenic mountain views",
        "Caroline attended a tech meetup in Shoreditch",
        "They discussed latest AI developments",
        "Caroline visited the British Library",
        "She researched historical documents"
    ]

    hippocampus_count_before = len(coordinator.hippocampus.memories)
    temporal_lobe_count_before = len(coordinator.temporal_lobe.memories)

    print(f"初始状态:")
    print(f"  Hippocampus: {hippocampus_count_before} 条")
    print(f"  Temporal Lobe: {temporal_lobe_count_before} 条\n")

    for i, text in enumerate(test_memories):
        print(f"  [{i+1}/20] 存储: {text[:50]}...")
        await coordinator.process_input(text)

    hippocampus_count_after = len(coordinator.hippocampus.memories)
    temporal_lobe_count_after = len(coordinator.temporal_lobe.memories)

    print(f"\n存储后状态:")
    print(f"  Hippocampus: {hippocampus_count_after} 条 (+{hippocampus_count_after - hippocampus_count_before})")
    print(f"  Temporal Lobe: {temporal_lobe_count_after} 条 (+{temporal_lobe_count_after - temporal_lobe_count_before})")

    # Step 2: 手动触发一次巩固 (只测试最后5条记忆以节省时间)
    print("\n" + "=" * 80)
    print("Step 2: 手动触发巩固 (仅最后5条记忆)")
    print("=" * 80)

    if hasattr(coordinator, 'background_processes'):
        from src.memory.memory_consolidation_pipeline import MemoryConsolidationPipeline
        from src.memory.agent_storage_proxy import AgentStorageProxy

        temporal_before = len(coordinator.temporal_lobe.memories)
        print(f"巩固前 Temporal Lobe: {temporal_before} 条")

        # Get last 5 memory IDs for testing (to avoid slow full consolidation)
        last_5_ids = [mem.id for mem in coordinator.hippocampus.memories[-5:]]
        print(f"测试最后5条记忆: {[mid[:8] for mid in last_5_ids]}")

        try:
            pipeline = MemoryConsolidationPipeline()

            # Wrap agents in storage proxies (agents don't have region_store API)
            hippocampus_proxy = AgentStorageProxy(coordinator.hippocampus, 'hippocampus')
            temporal_lobe_proxy = AgentStorageProxy(coordinator.temporal_lobe, 'temporal_lobe')

            results = await pipeline.batch_consolidate(
                memory_ids=last_5_ids,
                consolidation_type='episodic_to_semantic',
                source_storage=hippocampus_proxy,
                target_storage=temporal_lobe_proxy,
                priority=0.7
            )
            successful = sum(1 for r in results if r.success)
            print(f"✅ 巩固执行完成: {successful}/{len(results)} 成功")
        except Exception as e:
            print(f"❌ 巩固失败: {e}")
            import traceback
            traceback.print_exc()

        temporal_after = len(coordinator.temporal_lobe.memories)
        print(f"巩固后 Temporal Lobe: {temporal_after} 条 (+{temporal_after - temporal_before})")

        if temporal_after > temporal_before:
            print(f"\n✅ 语义记忆增加了 {temporal_after - temporal_before} 条！")
            print("\n最新的语义记忆:")
            for mem in coordinator.temporal_lobe.memories[temporal_before:temporal_before+3]:
                print(f"  - {mem.content[:80]}...")
        else:
            print(f"\n⚠️  语义记忆未增加 (可能consolidation未真正执行)")

    # Step 3: 验证retrieve_memory_by_id
    print("\n" + "=" * 80)
    print("Step 3: 验证hippocampus.retrieve_memory_by_id")
    print("=" * 80)

    if len(coordinator.hippocampus.memories) > 0:
        test_id = coordinator.hippocampus.memories[-1].id
        print(f"测试ID: {test_id[:16]}...")

        mem_dict = await coordinator.hippocampus.retrieve_memory_by_id(test_id)
        if mem_dict:
            print(f"✅ retrieve_memory_by_id成功")
            print(f"  Content: {mem_dict.get('content', '')[:60]}...")
        else:
            print(f"❌ retrieve_memory_by_id返回None")

    # Summary
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    if temporal_lobe_count_after > temporal_lobe_count_before:
        print("✅ 巩固机制工作正常 - 情节记忆成功转换为语义记忆")
    else:
        print("⚠️  巩固可能未执行或未生成语义记忆")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_consolidation())
