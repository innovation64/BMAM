#!/usr/bin/env python3
"""
存储生命周期验证 - 检查记忆在三层存储中的分布
"""
import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def main():
    print("=" * 80)
    print("三层存储生命周期验证")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 存入测试记忆
    print("\n[1/3] 存入测试记忆...")
    test_input = "Caroline went to an LGBTQ support group on 7 May 2023."
    await coordinator.process_input(test_input)
    print(f"  ✓ 存储完成")

    # 检查各层存储
    print("\n[2/3] 检查各层存储...")

    # Layer 1: Hippocampus (短期情节记忆)
    if hasattr(coordinator, 'hippocampus') and hasattr(coordinator.hippocampus, 'memories'):
        hippo_count = len(coordinator.hippocampus.memories)
        print(f"  → Hippocampus (短期): {hippo_count} 条记忆")
        if hippo_count > 0:
            sample = coordinator.hippocampus.memories[0]
            print(f"    样本: {sample.content[:60] if hasattr(sample, 'content') else str(sample)[:60]}")
    else:
        print(f"  → Hippocampus: 无法访问 memories 列表")

    # Layer 2: MemorySystem (长期FAISS存储)
    if hasattr(coordinator, 'memory_system'):
        if hasattr(coordinator.memory_system, 'db_manager'):
            try:
                all_mems = await coordinator.memory_system.db_manager.get_all_memories()
                print(f"  → MemorySystem (长期): {len(all_mems)} 条记忆")
                if len(all_mems) > 0:
                    sample = all_mems[0]
                    content = sample.get('content', str(sample))[:60]
                    print(f"    样本: {content}")
            except Exception as e:
                print(f"  → MemorySystem: 查询失败 ({e})")
        else:
            print(f"  → MemorySystem: 无 db_manager")
    else:
        print(f"  → MemorySystem: 不存在")

    # Layer 3: TemporalLobe (知识图谱/语义记忆)
    if hasattr(coordinator, 'temporal_lobe'):
        if hasattr(coordinator.temporal_lobe, 'relations'):
            rel_count = len(coordinator.temporal_lobe.relations)
            print(f"  → TemporalLobe (知识图谱): {rel_count} 条关系")
            if rel_count > 0:
                sample = coordinator.temporal_lobe.relations[0]
                print(f"    样本关系: {sample}")
        else:
            print(f"  → TemporalLobe: 无法访问 relations")
    else:
        print(f"  → TemporalLobe: 不存在")

    # 检索验证
    print("\n[3/3] 检索验证...")
    query = "When did Caroline go to the support group?"
    results = await coordinator.smart_retrieve(query, k=5)
    print(f"  → smart_retrieve 返回: {len(results)} 条记忆")
    for i, mem in enumerate(results[:3], 1):
        source = mem.get('source', 'unknown')
        content = mem.get('content', str(mem))[:50]
        print(f"    {i}. [{source}] {content}")

    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)

    await coordinator.stop_system()

if __name__ == "__main__":
    asyncio.run(main())
