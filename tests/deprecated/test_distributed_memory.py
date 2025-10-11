"""
测试分布式记忆系统
验证每个脑区存储不同类型的记忆
"""

import asyncio
import sys
import os

# Add BMAM to path
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.brain.distributed_memory import get_distributed_memory


async def test_distributed_memory():
    print("=" * 80)
    print("🧠 测试分布式记忆系统")
    print("=" * 80)

    # 获取分布式记忆系统
    dm = get_distributed_memory()

    print("\n📝 Phase 1: 存储不同类型的记忆")
    print("-" * 80)

    # 1. 存储情景记忆到海马体
    episodic_id = dm.store_memory(
        content="On 8 May 2023, Caroline attended an LGBTQ support group for the first time.",
        memory_type='episodic',
        metadata={'person': 'Caroline', 'event': 'LGBTQ support group', 'date': '2023-05-08'}
    )
    print(f"✅ Episodic memory stored: {episodic_id}")

    # 2. 存储语义记忆到颞叶
    semantic_id = dm.store_memory(
        content="Caroline is a transgender woman interested in social justice.",
        memory_type='semantic',
        metadata={'person': 'Caroline', 'fact': 'identity'}
    )
    print(f"✅ Semantic memory stored: {semantic_id}")

    # 3. 存储工作记忆到前额叶
    working_id = dm.store_memory(
        content="Current task: Answer questions about Caroline",
        memory_type='working',
        metadata={'task': 'QA', 'status': 'active'}
    )
    print(f"✅ Working memory stored: {working_id}")

    # 4. 存储情绪记忆到杏仁核
    emotional_id = dm.store_memory(
        content="Caroline felt empowered and supported at the LGBTQ group.",
        memory_type='emotional',
        metadata={'person': 'Caroline', 'emotion': 'empowered'}
    )
    print(f"✅ Emotional memory stored: {emotional_id}")

    print("\n🔍 Phase 2: 从不同脑区检索记忆")
    print("-" * 80)

    # 测试单脑区检索
    hippocampus_memories = dm.retrieve_from_region('hippocampus', query='Caroline', k=5)
    print(f"\n🧠 海马体 (Hippocampus - Episodic):")
    print(f"   Found {len(hippocampus_memories)} memories")
    for mem in hippocampus_memories:
        print(f"   - {mem['content'][:60]}...")

    temporal_memories = dm.retrieve_from_region('temporal', query='Caroline', k=5)
    print(f"\n🧠 颞叶 (Temporal - Semantic):")
    print(f"   Found {len(temporal_memories)} memories")
    for mem in temporal_memories:
        print(f"   - {mem['content'][:60]}...")

    print("\n🌐 Phase 3: 多脑区并行检索 (Multi-Region Retrieval)")
    print("-" * 80)

    multi_results = dm.multi_region_retrieval(
        query='Caroline LGBTQ',
        regions=['hippocampus', 'temporal', 'amygdala'],
        k_per_region=2
    )

    for region_name, memories in multi_results.items():
        print(f"\n📍 {region_name.upper()}: {len(memories)} memories")
        for mem in memories:
            print(f"   [{mem['type']}] {mem['content'][:50]}...")

    print("\n📊 Phase 4: 系统统计")
    print("-" * 80)

    stats = dm.get_statistics()
    print(f"\n总记忆数: {stats['total_memories']}")
    print(f"\n各脑区统计:")
    for region_name, region_stats in stats['regions'].items():
        print(f"  {region_name:15} | Type: {region_stats['memory_type']:12} | Size: {region_stats['size']:3}/{region_stats['capacity']:4} ({region_stats['utilization']:5}) | Access: {region_stats['access_count']}")

    print("\n💾 Phase 5: 记忆巩固 (Consolidation)")
    print("-" * 80)

    # 将工作记忆巩固到长期记忆
    longterm_id = dm.consolidate_to_longterm(working_id, target_type='semantic')
    if longterm_id:
        print(f"✅ Consolidated working memory → semantic: {longterm_id}")

    # 再次查看统计
    stats_after = dm.get_statistics()
    print(f"\n巩固后:")
    print(f"  Working memory: {stats['regions']['prefrontal']['size']} → {stats_after['regions']['prefrontal']['size']} (removed)")
    print(f"  Semantic memory: {stats['regions']['temporal']['size']} → {stats_after['regions']['temporal']['size']} (added)")

    print("\n" + "=" * 80)
    print("✅ 分布式记忆系统测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_distributed_memory())
