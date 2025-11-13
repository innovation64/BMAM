"""
手动测试脚本 - 直接调用巩固流程，查看详细日志
"""
import asyncio
import sys
import logging
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 只显示我们关心的日志
for logger_name in ['src.memory.memory_consolidation_pipeline',
                     'src.memory.agent_storage_proxy',
                     'src.agents.brain_regions.temporal_lobe_agent.storage']:
    logging.getLogger(logger_name).setLevel(logging.DEBUG)

async def main():
    from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
    from src.memory.memory_consolidation_pipeline import MemoryConsolidationPipeline
    from src.memory.agent_storage_proxy import AgentStorageProxy

    print("=" * 80)
    print("🔍 手动巩固测试 - 详细日志模式")
    print("=" * 80)

    # 初始化coordinator
    coordinator = BrainInspiredCoordinator()

    # 检查初始状态
    initial_hippocampus = len(coordinator.hippocampus.memories)
    initial_temporal = len(coordinator.temporal_lobe.memories)

    print(f"\n初始状态:")
    print(f"  Hippocampus: {initial_hippocampus} 条记忆")
    print(f"  TemporalLobe: {initial_temporal} 条记忆")

    # 创建巩固pipeline
    pipeline = MemoryConsolidationPipeline()

    # 创建代理
    hippocampus_proxy = AgentStorageProxy(coordinator.hippocampus, 'hippocampus')
    temporal_lobe_proxy = AgentStorageProxy(coordinator.temporal_lobe, 'temporal_lobe')

    # 获取第一条hippocampus记忆
    if coordinator.hippocampus.memories:
        test_memory = coordinator.hippocampus.memories[0]
        test_memory_id = test_memory.id

        print(f"\n测试记忆:")
        print(f"  ID: {test_memory_id[:16]}...")
        print(f"  Content: {test_memory.content[:60]}...")
        print(f"  Importance: {test_memory.importance}")

        print(f"\n{'='*80}")
        print(f"开始巩固流程...")
        print(f"{'='*80}\n")

        # 调用巩固
        result = await pipeline.consolidate_episodic_to_semantic(
            episodic_memory_id=test_memory_id,
            hippocampus_storage=hippocampus_proxy,
            temporal_lobe_storage=temporal_lobe_proxy,
            priority=0.7
        )

        print(f"\n{'='*80}")
        print(f"巩固结果:")
        print(f"  Success: {result.success}")
        print(f"  Source ID: {result.source_memory_id[:16] if result.source_memory_id else 'None'}")
        print(f"  Target ID: {result.target_memory_id[:16] if result.target_memory_id else 'None'}")
        print(f"  Metadata: {result.metadata}")
        print(f"{'='*80}\n")

        # 检查最终状态
        final_hippocampus = len(coordinator.hippocampus.memories)
        final_temporal = len(coordinator.temporal_lobe.memories)

        print(f"最终状态:")
        print(f"  Hippocampus: {final_hippocampus} 条记忆")
        print(f"  TemporalLobe: {final_temporal} 条记忆 (+{final_temporal - initial_temporal})")

        if final_temporal > initial_temporal:
            print(f"\n✅ 成功! TemporalLobe增加了 {final_temporal - initial_temporal} 条记忆")
        else:
            print(f"\n❌ 失败! TemporalLobe没有增加记忆")
            print(f"\n请查看上面的详细日志,找出问题所在:")
            print(f"  1. 检查 '🔄 Calling temporal_lobe_storage.region_store' 是否出现")
            print(f"  2. 检查 '🔵 [temporal_lobe] region_store called' 是否出现")
            print(f"  3. 检查 '🟢 [TemporalLobe] Created SemanticMemory' 是否出现")
            print(f"  4. 检查是否有任何 '❌' 错误标记")
    else:
        print(f"\n❌ Hippocampus为空,无法测试巩固")

if __name__ == '__main__':
    asyncio.run(main())
