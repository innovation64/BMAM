#!/usr/bin/env python3
"""
KG 可观测性测试 - 追踪 KG 数据流
验证 KG 数据是否真的影响推理链
"""
import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def main():
    print("=" * 80)
    print("KG 可观测性测试")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入包含明确实体关系的记忆
    print("\n[1/4] 注入包含实体关系的记忆...")
    mem1 = "Caroline is a transgender woman."
    mem2 = "Caroline attended an LGBTQ support group."

    await coordinator.process_input(mem1)
    await coordinator.process_input(mem2)
    print(f"  ✓ 已注入 2 条记忆")

    # 检查 1: KnowledgeGraphBuilder 的内部存储
    print("\n[2/4] 检查 KnowledgeGraphBuilder 内部存储...")
    if hasattr(coordinator, 'knowledge_graph_builder'):
        kb = coordinator.knowledge_graph_builder

        # 检查 legacy storage
        if hasattr(kb, 'knowledge_graph'):
            kg_data = kb.knowledge_graph
            entities = kg_data.get('entities', {})
            relations = kg_data.get('relations', [])

            print(f"  → Legacy KG 存储:")
            print(f"    - Entities: {len(entities)} ({list(entities.keys())[:5]})")
            print(f"    - Relations: {len(relations)}")
            for i, rel in enumerate(relations[:3], 1):
                if isinstance(rel, tuple):
                    print(f"      {i}. {rel[0]} - {rel[1]} - {rel[2]}")
                else:
                    print(f"      {i}. {rel}")

        # 检查 unified KG
        if kb.kg:
            print(f"  → Unified KG: 已启用 (类型={type(kb.kg).__name__})")
        else:
            print(f"  ⚠️  Unified KG: 未启用 (使用 legacy 存储)")

    # 检查 2: MemoryReasoningChain 的 KG 引用
    print("\n[3/4] 检查 MemoryReasoningChain 的 KG 引用...")
    if hasattr(coordinator, 'memory_reasoning_chain') and coordinator.memory_reasoning_chain:
        mrc = coordinator.memory_reasoning_chain

        if hasattr(mrc, 'kg') and mrc.kg:
            print(f"  → MRC.kg: {type(mrc.kg).__name__}")

            # 手动测试 _retrieve_from_kg
            print(f"\n  测试 _retrieve_from_kg()...")

            # 创建模拟记忆片段
            from src.reasoning.memory_reasoning_chain import MemoryFragment
            from datetime import datetime

            test_memory = MemoryFragment(
                id="test",
                content="Caroline is a transgender woman",
                timestamp=datetime.now(),
                source="test",
                entities=['Caroline', 'transgender woman']
            )

            kg_facts = await mrc._retrieve_from_kg(
                query="What is Caroline's identity?",
                memories=[test_memory]
            )

            print(f"    → 检索到 {len(kg_facts)} 条 KG facts")
            for i, fact in enumerate(kg_facts[:3], 1):
                print(f"      {i}. {fact}")

        else:
            print(f"  ❌ MRC.kg 未设置")

    # 检查 3: 完整推理链中的 KG 上下文
    print("\n[4/4] 检查完整推理链中的 KG 上下文...")
    if coordinator.memory_reasoning_chain:
        result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(
            "What is Caroline's identity?",
            include_kg=True
        )

        print(f"  → 推理链检索:")
        print(f"    - Memories: {len(result.memories)}")
        print(f"    - Causal Links: {len(result.causal_links)}")
        print(f"    - KG Context: {len(result.kg_context)}")
        print(f"    - Confidence: {result.confidence:.2f}")

        if len(result.kg_context) > 0:
            print(f"\n  ✅ KG 数据已融入推理链:")
            for i, fact in enumerate(result.kg_context[:5], 1):
                print(f"    {i}. {fact}")
        else:
            print(f"\n  ⚠️  KG 数据未融入推理链")
            print(f"  诊断:")

            # 诊断原因
            if not hasattr(coordinator.memory_reasoning_chain, 'kg') or not coordinator.memory_reasoning_chain.kg:
                print(f"    - MRC.kg 未设置")

            if hasattr(coordinator, 'knowledge_graph_builder'):
                if not coordinator.knowledge_graph_builder.knowledge_graph['relations']:
                    print(f"    - KG 没有 relations 数据")
                else:
                    print(f"    - KG 有 {len(coordinator.knowledge_graph_builder.knowledge_graph['relations'])} 条 relations")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

    await coordinator.stop_system()

if __name__ == "__main__":
    asyncio.run(main())
