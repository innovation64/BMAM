#!/usr/bin/env python3
"""
最小验证脚本 - 测试 MemoryCoordinator 检索
目标：确认在 LoCoMo 测试场景下，coordinator.retrieve_memories() 返回什么
"""
import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def main():
    print("=" * 80)
    print("最小 Memory Retrieval 验证")
    print("=" * 80)

    # 1. 初始化 coordinator
    print("\n[1/4] 初始化 BrainInspiredCoordinator...")
    coordinator = BrainInspiredCoordinator()

    # 2. 存入一条测试记忆
    print("\n[2/4] 存入测试记忆...")
    test_input = "Caroline went to an LGBTQ support group on 7 May 2023."
    result = await coordinator.process_input(test_input)
    print(f"  ✓ 存储结果: {result[:100] if isinstance(result, str) else 'Success'}")

    # 3. 使用 smart_retrieve 检索
    print("\n[3/4] 使用 smart_retrieve 检索...")
    query = "When did Caroline go to the support group?"
    memories = await coordinator.smart_retrieve(query, k=5)
    print(f"  → smart_retrieve 返回: {len(memories)} 条记忆")
    for i, mem in enumerate(memories[:3], 1):
        content = mem.get('content', str(mem))[:60]
        source = mem.get('source', 'unknown')
        print(f"    {i}. [{source}] {content}")

    # 4. 使用 MemoryCoordinator.smart_retrieve 检索
    print("\n[4/4] 使用 MemoryCoordinator.smart_retrieve 检索...")
    if hasattr(coordinator, 'memory_coordinator'):
        mc_memories = await coordinator.memory_coordinator.smart_retrieve(
            query=query,
            k=5,
            strategy='hybrid'
        )
        print(f"  → MemoryCoordinator 返回: {len(mc_memories)} 条记忆")
        for i, mem in enumerate(mc_memories[:3], 1):
            content = mem.get('content', str(mem))[:60]
            source = mem.get('source', 'unknown')
            print(f"    {i}. [{source}] {content}")
    else:
        print("  ✗ MemoryCoordinator 不可用")

    # 5. 直接检查各存储层
    print("\n[5/5] 直接检查各存储层...")

    # Hippocampus
    if hasattr(coordinator, 'hippocampus'):
        from src.agents.brain_regions.hippocampus_agent.storage import HippocampusStorage
        if isinstance(coordinator.hippocampus, HippocampusStorage) or hasattr(coordinator.hippocampus, 'memories'):
            hippo_count = len(getattr(coordinator.hippocampus, 'memories', []))
            print(f"  → Hippocampus: {hippo_count} 条记忆")
        else:
            print(f"  → Hippocampus: 类型={type(coordinator.hippocampus).__name__}")

    # MemorySystem
    if hasattr(coordinator, 'memory_system'):
        if hasattr(coordinator.memory_system, 'db_manager'):
            # Try to get count from database
            try:
                all_mems = await coordinator.memory_system.db_manager.get_all_memories()
                print(f"  → MemorySystem DB: {len(all_mems)} 条记忆")
            except:
                print(f"  → MemorySystem: DB 查询失败")
        else:
            print(f"  → MemorySystem: 类型={type(coordinator.memory_system).__name__}")

    # TemporalLobe
    if hasattr(coordinator, 'temporal_lobe'):
        if hasattr(coordinator.temporal_lobe, 'memories'):
            tl_count = len(coordinator.temporal_lobe.memories)
            print(f"  → TemporalLobe: {tl_count} 条记忆")
        else:
            print(f"  → TemporalLobe: 类型={type(coordinator.temporal_lobe).__name__}")

    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)

    await coordinator.stop_system()

if __name__ == "__main__":
    asyncio.run(main())
