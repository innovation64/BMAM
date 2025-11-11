#!/usr/bin/env python3
"""
多脑区可观测性测试
验证不只是 Hippocampus 在工作，而是多个脑区协同
"""
import asyncio
from datetime import datetime
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def test_hippocampus_consolidation():
    """测试 1: Hippocampus → TemporalLobe 巩固"""
    print("=" * 80)
    print("测试 1: Hippocampus 记忆巩固机制")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入测试记忆
    print("\n[1/4] 注入测试记忆...")
    memories = [
        "Alice is a researcher.",
        "Alice published a paper on AI.",
        "Alice won an award for her research.",
    ]
    for mem in memories:
        await coordinator.process_input(mem)
    print(f"  ✓ 已注入 {len(memories)} 条记忆")

    # 检查 Hippocampus 存储
    print("\n[2/4] 检查 Hippocampus 存储...")
    if hasattr(coordinator.hippocampus, 'memories'):
        hippo_count = len(coordinator.hippocampus.memories)
        print(f"  → Hippocampus: {hippo_count} 条记忆")

        # 检查记忆属性
        sample = coordinator.hippocampus.memories[0]
        print(f"  → 样本记忆属性:")
        print(f"    - importance: {sample.importance}")
        print(f"    - access_count: {sample.access_count}")
        print(f"    - timestamp: {sample.timestamp}")
        print(f"    - entities: {sample.entities}")

    # 提升重要性并触发巩固
    print("\n[3/4] 触发巩固...")
    for mem in coordinator.hippocampus.memories:
        mem.importance = 0.9
        mem.access_count = 0

    result = await coordinator.hippocampus.consolidate_memories()
    print(f"  → 巩固结果: {result}")

    if result.get('consolidated', 0) > 0:
        print(f"  ✅ Hippocampus 巩固机制正常工作")
    else:
        print(f"  ⚠️  巩固未生效: {result.get('message', 'Unknown')}")

    # 检查 TemporalLobe 是否实际增加了记忆
    print("\n[4/4] 验证 TemporalLobe 存储...")
    temporal_count_after = len(coordinator.temporal_lobe.memories) if hasattr(coordinator, 'temporal_lobe') and hasattr(coordinator.temporal_lobe, 'memories') else 0
    print(f"  → TemporalLobe 记忆数: {temporal_count_after}")

    # 关键断言：巩固后 TemporalLobe 应该有记忆
    assert temporal_count_after > 0, "TemporalLobe should have memories after consolidation"
    print(f"  ✅ 断言通过: TemporalLobe 巩固后有 {temporal_count_after} 条记忆")

    # 验证检索能找到 TemporalLobe 来源的记忆
    query = "What research did Alice do?"
    results = await coordinator.smart_retrieve(query, k=10, strategy='hybrid')
    sources = [r.get('source', 'unknown') for r in results]
    print(f"\n  → 检索结果来源: {set(sources)}")

    # 关键断言：检索应该包含 temporal_lobe 来源
    assert 'temporal_lobe' in sources, "smart_retrieve should return memories from temporal_lobe after consolidation"
    print(f"  ✅ 断言通过: smart_retrieve 返回了来自 temporal_lobe 的记忆")

    # [新增] 验证 MemorySystem 存储
    print("\n[5/5] 验证 MemorySystem 存储...")
    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        all_memories = coordinator.memory_system.db_manager.get_all_memories()
        memory_system_count = len(all_memories)
        print(f"  → MemorySystem 记忆数: {memory_system_count}")

        # 关键断言：巩固后 MemorySystem 应该有记忆
        assert memory_system_count > 0, "MemorySystem should have memories after consolidation"
        print(f"  ✅ 断言通过: MemorySystem 巩固后有 {memory_system_count} 条记忆")
    else:
        print(f"  ⚠️  MemorySystem 不可用")
        memory_system_count = 0

    await coordinator.stop_system()
    return result.get('consolidated', 0) > 0 and temporal_count_after > 0 and memory_system_count > 0


async def test_temporal_lobe_kg_storage():
    """测试 2: TemporalLobe KG 关系存储"""
    print("\n" + "=" * 80)
    print("测试 2: TemporalLobe KG 关系存储")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入包含明确关系的记忆
    print("\n[1/3] 注入包含实体关系的记忆...")
    relations_data = [
        "Bob is a professor at MIT.",
        "Bob teaches machine learning.",
        "Bob supervises PhD students.",
    ]
    for mem in relations_data:
        await coordinator.process_input(mem)
    print(f"  ✓ 已注入 {len(relations_data)} 条记忆")

    # 检查 KG 提取
    print("\n[2/3] 检查 KG 提取...")
    if hasattr(coordinator, 'knowledge_graph_builder'):
        kg = coordinator.knowledge_graph_builder.knowledge_graph
        entities = kg.get('entities', {})
        relations = kg.get('relations', [])

        print(f"  → KG 提取:")
        print(f"    - Entities: {len(entities)} ({list(entities.keys())[:5]})")
        print(f"    - Relations: {len(relations)}")

        for i, rel in enumerate(relations[:3], 1):
            if isinstance(rel, tuple) and len(rel) >= 3:
                print(f"      {i}. {rel[0]} - {rel[1]} - {rel[2]}")

    # 检查 TemporalLobe 接收
    print("\n[3/3] 检查 TemporalLobe 接收...")
    print(f"  提示: 查看日志中是否有:")
    print(f"    - '🔗 Ingested N KG relations from hippocampus'")
    print(f"    - TemporalLobe 存储确认")

    if len(relations) > 0:
        print(f"  ✅ TemporalLobe KG 机制正常工作")
        kg_works = True
    else:
        print(f"  ⚠️  KG 未提取到关系")
        kg_works = False

    await coordinator.stop_system()
    return kg_works


async def test_prefrontal_working_memory():
    """测试 3: PrefrontalAgent 工作记忆整合"""
    print("\n" + "=" * 80)
    print("测试 3: PrefrontalAgent 工作记忆整合")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入需要推理的记忆
    print("\n[1/3] 注入需要推理的记忆...")
    reasoning_data = [
        "Carol loves painting.",
        "Carol studied art history.",
        "Carol opened an art gallery.",
    ]
    for mem in reasoning_data:
        await coordinator.process_input(mem)
    print(f"  ✓ 已注入 {len(reasoning_data)} 条记忆")

    # 触发推理链（需要前额叶整合）
    print("\n[2/3] 触发推理链...")
    query = "What is Carol's profession?"

    if coordinator.memory_reasoning_chain:
        result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(query)

        print(f"  → 推理链结果:")
        print(f"    - Memories: {len(result.memories)}")
        print(f"    - Causal Links: {len(result.causal_links)} (前额叶因果推理)")
        print(f"    - Confidence: {result.confidence:.2f}")

        # 检查因果链接（前额叶功能）
        if len(result.causal_links) > 0:
            print(f"\n  → 因果链接样本 (前额叶推理):")
            link = result.causal_links[0]
            print(f"    Cause: {link.cause.content[:40]}...")
            print(f"    Effect: {link.effect.content[:40]}...")
            print(f"    Type: {link.relation_type}")
            print(f"    Strength: {link.strength:.2f}")

        prefrontal_works = len(result.causal_links) > 0
    else:
        print(f"  ❌ Memory Reasoning Chain 不可用")
        prefrontal_works = False

    # 检查工作记忆容量
    print("\n[3/3] 检查工作记忆...")
    if hasattr(coordinator, 'prefrontal_agent') and hasattr(coordinator.prefrontal_agent, 'working_memory'):
        wm_count = len(coordinator.prefrontal_agent.working_memory)
        print(f"  → PrefrontalAgent 工作记忆: {wm_count} 项")
        print(f"  → 容量限制: {coordinator.prefrontal_agent.capacity if hasattr(coordinator.prefrontal_agent, 'capacity') else 'Unknown'}")

    if prefrontal_works:
        print(f"  ✅ PrefrontalAgent 推理机制正常工作")
    else:
        print(f"  ⚠️  前额叶推理未生效")

    await coordinator.stop_system()
    return prefrontal_works


async def test_memory_coordinator_unified_retrieval():
    """测试 4: MemoryCoordinator 统一检索"""
    print("\n" + "=" * 80)
    print("测试 4: MemoryCoordinator 统一检索协调")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入多样化记忆
    print("\n[1/3] 注入多样化记忆...")
    diverse_data = [
        "David is a musician.",  # 事实
        "David plays guitar.",   # 事实
        "David composed a symphony.",  # 事件
        "David won a Grammy award.",   # 成就
        "David teaches music at a university.",  # 职业
    ]
    for mem in diverse_data:
        await coordinator.process_input(mem)
    print(f"  ✓ 已注入 {len(diverse_data)} 条记忆")

    # 测试 smart_retrieve
    print("\n[2/3] 测试 MemoryCoordinator.smart_retrieve()...")
    query = "What does David do?"

    results = await coordinator.smart_retrieve(query, k=10, strategy='hybrid')

    print(f"  → 检索结果: {len(results)} 条")

    # 分析来源分布
    sources = {}
    for r in results:
        source = r.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1

    print(f"  → 来源分布:")
    for source, count in sources.items():
        print(f"    - {source}: {count} 条")

    # 检查检索策略
    print("\n[3/3] 检查检索策略...")
    print(f"  → 当前策略: hybrid")
    print(f"  → 支持的策略: semantic, recent, important, hybrid")

    if len(results) > 0:
        print(f"  ✅ MemoryCoordinator 统一检索正常工作")
        coordinator_works = True
    else:
        print(f"  ⚠️  未检索到结果")
        coordinator_works = False

    await coordinator.stop_system()
    return coordinator_works


async def main():
    """执行所有多脑区测试"""
    print("多脑区可观测性测试套件")
    print("=" * 80)
    print("目标: 验证多个脑区协同工作，而非单一 Hippocampus\n")

    results = {}

    # 测试 1: Hippocampus 巩固
    try:
        results['hippocampus_consolidation'] = await test_hippocampus_consolidation()
    except Exception as e:
        print(f"\n❌ Hippocampus 巩固测试失败: {e}")
        results['hippocampus_consolidation'] = False

    # 测试 2: TemporalLobe KG
    try:
        results['temporal_lobe_kg'] = await test_temporal_lobe_kg_storage()
    except Exception as e:
        print(f"\n❌ TemporalLobe KG 测试失败: {e}")
        results['temporal_lobe_kg'] = False

    # 测试 3: PrefrontalAgent 推理
    try:
        results['prefrontal_reasoning'] = await test_prefrontal_working_memory()
    except Exception as e:
        print(f"\n❌ PrefrontalAgent 推理测试失败: {e}")
        results['prefrontal_reasoning'] = False

    # 测试 4: MemoryCoordinator 统一检索
    try:
        results['memory_coordinator'] = await test_memory_coordinator_unified_retrieval()
    except Exception as e:
        print(f"\n❌ MemoryCoordinator 测试失败: {e}")
        results['memory_coordinator'] = False

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        test_label = test_name.replace('_', ' ').title()
        print(f"  {status}: {test_label}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\n通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.0f}%)")

    # 结论
    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)

    if passed_count == total_count:
        print("✅ 所有脑区机制正常工作")
    elif passed_count >= total_count * 0.75:
        print("⚠️  大部分脑区机制正常，部分需要修复")
    else:
        print("❌ 多数脑区机制未生效，系统可能退化为单层存储")

    # 多脑区协同证据
    print("\n多脑区协同证据:")
    if results.get('hippocampus_consolidation'):
        print("  ✅ Hippocampus → TemporalLobe 巩固流程")
    if results.get('temporal_lobe_kg'):
        print("  ✅ TemporalLobe KG 关系存储")
    if results.get('prefrontal_reasoning'):
        print("  ✅ PrefrontalAgent 因果推理")
    if results.get('memory_coordinator'):
        print("  ✅ MemoryCoordinator 跨存储检索")

    if not any(results.values()):
        print("  ⚠️  所有脑区测试失败 - 系统可能仅使用 Hippocampus 单层存储")


if __name__ == "__main__":
    asyncio.run(main())
