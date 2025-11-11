#!/usr/bin/env python3
"""
完整巩固周期测试
验证记忆从 Hippocampus → MemorySystem → TemporalLobe 的完整流程
"""
import asyncio
from datetime import datetime, timedelta
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def main():
    print("=" * 80)
    print("完整记忆巩固周期测试")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Phase 1: 注入多条记忆（模拟多轮对话）
    print("\n[Phase 1/5] 注入测试记忆...")
    memories = [
        "Caroline went to an LGBTQ support group on 7 May 2023.",
        "Caroline researched adoption agencies on 25 May 2023.",
        "Caroline is excited about continuing her education.",
        "Caroline is interested in counseling or mental health.",
        "Caroline wants to support LGBTQ families.",
    ]

    for i, mem in enumerate(memories, 1):
        await coordinator.process_input(mem)
        print(f"  {i}/5 ✓ {mem[:50]}...")

    # Phase 2: 检查巩固前的存储分布
    print("\n[Phase 2/5] 巩固前的存储分布...")

    # Hippocampus
    hippo_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    print(f"  → Hippocampus: {hippo_count} 条记忆")

    # MemorySystem
    memory_system_count = 0
    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        try:
            all_mems = coordinator.memory_system.db_manager.get_all_memories()
            memory_system_count = len(all_mems)
            print(f"  → MemorySystem: {memory_system_count} 条记忆")
        except Exception as e:
            print(f"  → MemorySystem: 查询失败 ({e})")

    # TemporalLobe - check semantic memories
    temporal_count = 0
    if hasattr(coordinator, 'temporal_lobe') and hasattr(coordinator.temporal_lobe, 'memories'):
        temporal_count = len(coordinator.temporal_lobe.memories)
        print(f"  → TemporalLobe (语义): {temporal_count} 条记忆")

    # Phase 3: 手动提升记忆重要性（确保满足巩固条件）
    print("\n[Phase 3/5] 提升记忆重要性以满足巩固条件...")
    if hasattr(coordinator.hippocampus, 'memories'):
        for mem in coordinator.hippocampus.memories:
            mem.importance = 0.8  # 超过 0.5 阈值
            mem.access_count = 0  # 确保 < 3
        print(f"  ✓ 已将 {len(coordinator.hippocampus.memories)} 条记忆重要性设为 0.8")

    # Phase 4: 触发巩固
    print("\n[Phase 4/5] 触发记忆巩固...")
    if hasattr(coordinator.hippocampus, 'consolidate_memories'):
        result = await coordinator.hippocampus.consolidate_memories()
        print(f"  → 巩固结果: {result}")

        if 'consolidated' in result:
            print(f"  ✅ 成功巩固 {result['consolidated']} 条记忆")
        else:
            print(f"  ⚠️  巩固返回: {result}")
    else:
        print(f"  ❌ Hippocampus 没有 consolidate_memories 方法")

    # 等待异步巩固完成
    await asyncio.sleep(2)

    # Phase 5: 检查巩固后的存储分布
    print("\n[Phase 5/5] 巩固后的存储分布...")

    # Hippocampus (应该还在，因为不会删除)
    hippo_after = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    print(f"  → Hippocampus: {hippo_after} 条记忆 (变化: {hippo_after - hippo_count:+d})")

    # MemorySystem
    memory_system_after = 0
    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        try:
            all_mems = coordinator.memory_system.db_manager.get_all_memories()
            memory_system_after = len(all_mems)
            print(f"  → MemorySystem: {memory_system_after} 条记忆 (变化: {memory_system_after - memory_system_count:+d})")
        except Exception as e:
            print(f"  → MemorySystem: 查询失败 ({e})")

    # TemporalLobe
    temporal_after = 0
    if hasattr(coordinator, 'temporal_lobe') and hasattr(coordinator.temporal_lobe, 'memories'):
        temporal_after = len(coordinator.temporal_lobe.memories)
        print(f"  → TemporalLobe (语义): {temporal_after} 条记忆 (变化: {temporal_after - temporal_count:+d})")

    # Phase 6: 验证长期检索
    print("\n[Phase 6/6] 验证长期记忆检索...")
    query = "What did Caroline research?"

    # 使用 smart_retrieve 查看来源分布
    results = await coordinator.smart_retrieve(query, k=10)
    print(f"  → smart_retrieve 返回: {len(results)} 条记忆")

    # 统计来源
    sources = {}
    for r in results:
        source = r.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1

    print(f"  → 来源分布:")
    for source, count in sources.items():
        print(f"    - {source}: {count} 条")

    # 使用 Memory Reasoning Chain 验证跨存储检索
    if coordinator.memory_reasoning_chain:
        print(f"\n  → 测试 Memory Reasoning Chain 长期检索...")
        result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(
            query, max_memories=20
        )
        print(f"    - 检索记忆数: {len(result.memories)}")
        print(f"    - 因果链接数: {len(result.causal_links)}")
        print(f"    - KG 上下文: {len(result.kg_context)}")
        print(f"    - 置信度: {result.confidence:.2f}")

        # 检查记忆来源分布
        memory_sources = {}
        for mem in result.memories:
            source = mem.source
            memory_sources[source] = memory_sources.get(source, 0) + 1

        if memory_sources:
            print(f"    - 记忆来源:")
            for source, count in memory_sources.items():
                print(f"      • {source}: {count} 条")

    # 结论
    print("\n" + "=" * 80)
    print("测试结论")
    print("=" * 80)

    consolidation_worked = (temporal_after > temporal_count) or (memory_system_after > memory_system_count)

    if consolidation_worked:
        print("✅ 巩固成功:")
        print(f"  - TemporalLobe 增加: {temporal_after - temporal_count} 条")
        print(f"  - MemorySystem 增加: {memory_system_after - memory_system_count} 条")
    else:
        print("⚠️  巩固可能未生效:")
        print(f"  - TemporalLobe 变化: {temporal_after - temporal_count}")
        print(f"  - MemorySystem 变化: {memory_system_after - memory_system_count}")
        print(f"\n  诊断:")
        print(f"  1. 检查记忆是否满足巩固条件 (importance > 0.5, access_count < 3)")
        print(f"  2. 检查 TemporalLobe 连接是否正常")
        print(f"  3. 检查是否有异步错误")

    long_term_retrieval_works = len(sources) > 1 or 'temporal_lobe' in sources or 'memory_system' in sources

    if long_term_retrieval_works:
        print(f"\n✅ 长期检索正常: 从多个来源检索 ({list(sources.keys())})")
    else:
        print(f"\n⚠️  长期检索可能仅依赖短期记忆: {list(sources.keys())}")

    await coordinator.stop_system()

if __name__ == "__main__":
    asyncio.run(main())
