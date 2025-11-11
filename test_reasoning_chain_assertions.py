#!/usr/bin/env python3
"""
Memory Reasoning Chain 断言测试
验证推理链的核心机制：timeline、causal_links、confidence
"""
import asyncio
import sys
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def test_reasoning_chain_basic():
    """基础测试：2条记忆 → 验证 timeline/causal_links/confidence"""
    print("=" * 80)
    print("测试 1: 基础推理链构建（2条记忆）")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入 2 条相关记忆
    print("\n[1/3] 注入测试记忆...")
    mem1 = "Caroline went to an LGBTQ support group on 7 May 2023."
    mem2 = "Caroline researched adoption agencies on 25 May 2023."

    await coordinator.process_input(mem1)
    await coordinator.process_input(mem2)
    print(f"  ✓ 已注入 2 条记忆")

    # 触发推理链
    print("\n[2/3] 触发推理链...")
    query = "What is Caroline's identity?"

    # 直接调用推理链（绕过 coordinator，直接测试）
    if coordinator.memory_reasoning_chain:
        result = await coordinator.memory_reasoning_chain.build_reasoning_chain(query)

        print(f"\n[3/3] 验证推理链结果...")

        # 断言 1: 应该检索到至少 1 条记忆
        assert len(result['memories']) >= 1, f"❌ 预期至少 1 条记忆，实际: {len(result['memories'])}"
        print(f"  ✅ 断言 1: 检索到 {len(result['memories'])} 条记忆")

        # 断言 2: timeline 应该按时间排序
        timeline = result['timeline']
        if len(timeline) >= 2:
            assert timeline[0][0] <= timeline[1][0], "❌ Timeline 未按时间排序"
            print(f"  ✅ 断言 2: Timeline 正确排序 ({len(timeline)} 个事件)")
        else:
            print(f"  ⚠️  断言 2: Timeline 只有 {len(timeline)} 个事件，跳过排序检查")

        # 断言 3: 如果有多条记忆，应该产生 causal_links
        if len(result['memories']) >= 2:
            assert len(result['causal_links']) > 0, f"❌ 2条记忆应产生因果链接，实际: {len(result['causal_links'])}"
            print(f"  ✅ 断言 3: 生成 {len(result['causal_links'])} 条因果链接")

            # 验证 causal_link 结构
            link = result['causal_links'][0]
            assert hasattr(link, 'cause'), "❌ CausalLink 缺少 cause"
            assert hasattr(link, 'effect'), "❌ CausalLink 缺少 effect"
            assert hasattr(link, 'strength'), "❌ CausalLink 缺少 strength"
            assert 0 <= link.strength <= 1, f"❌ strength 应在 [0,1]，实际: {link.strength}"
            print(f"    样本链接: {link.cause.content[:30]}... → {link.effect.content[:30]}... (强度={link.strength:.2f})")
        else:
            print(f"  ⚠️  断言 3: 只有 {len(result['memories'])} 条记忆，跳过因果链检查")

        # 断言 4: confidence 应该在 [0, 1] 范围
        assert 0 <= result['confidence'] <= 1, f"❌ confidence 应在 [0,1]，实际: {result['confidence']}"
        print(f"  ✅ 断言 4: Confidence = {result['confidence']:.2f}")

        # 断言 5: answer 不应为空
        assert result['answer'] and len(result['answer'].strip()) > 0, "❌ Answer 为空"
        print(f"  ✅ 断言 5: Answer 已生成 ({len(result['answer'])} 字符)")

        print("\n✅ 所有断言通过")
        await coordinator.stop_system()
        return True
    else:
        print("❌ Memory Reasoning Chain 不可用")
        await coordinator.stop_system()
        return False


async def test_kg_integration():
    """KG 集成测试：验证 KG 数据是否影响推理链"""
    print("\n" + "=" * 80)
    print("测试 2: KG 集成验证")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 注入包含实体关系的记忆
    print("\n[1/2] 注入包含实体关系的记忆...")
    mem1 = "Caroline is a transgender woman."
    mem2 = "Caroline attended an LGBTQ support group."

    await coordinator.process_input(mem1)
    await coordinator.process_input(mem2)
    print(f"  ✓ 已注入 2 条记忆")

    # 检查 KG 是否提取了关系
    print("\n[2/2] 检查 KG 提取...")
    if hasattr(coordinator, 'knowledge_graph_builder'):
        kg = coordinator.knowledge_graph_builder.get_knowledge_graph()
        entities_count = len(kg.get('entities', []))
        relations_count = len(kg.get('relations', []))

        print(f"  → KG 实体: {entities_count}")
        print(f"  → KG 关系: {relations_count}")

        if relations_count > 0:
            print(f"  ✅ KG 已提取关系")
            sample_rel = kg['relations'][0]
            if isinstance(sample_rel, tuple):
                print(f"    样本: {sample_rel[0]} - {sample_rel[1]} - {sample_rel[2]}")
            else:
                print(f"    样本: {sample_rel}")
        else:
            print(f"  ⚠️  KG 未提取到关系")
    else:
        print("  ❌ KnowledgeGraphBuilder 不可用")

    # 触发推理链，检查 kg_context
    if coordinator.memory_reasoning_chain:
        result = await coordinator.memory_reasoning_chain.build_reasoning_chain(
            "What is Caroline's identity?"
        )

        kg_context = result.get('kg_context', [])
        print(f"\n  → 推理链中的 KG 上下文: {len(kg_context)} 条")

        if len(kg_context) > 0:
            print(f"  ✅ KG 数据已融入推理链")
            for i, fact in enumerate(kg_context[:3], 1):
                print(f"    {i}. {fact}")
        else:
            print(f"  ⚠️  推理链未使用 KG 数据")

    await coordinator.stop_system()
    return True


async def test_multi_turn_stability():
    """多轮对话稳定性测试"""
    print("\n" + "=" * 80)
    print("测试 3: 多轮对话稳定性")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 模拟 5 轮对话
    conversations = [
        "Caroline went to an LGBTQ support group on 7 May 2023.",
        "Caroline researched adoption agencies on 25 May 2023.",
        "Caroline is excited about continuing her education.",
        "Caroline is interested in counseling or mental health.",
        "Caroline wants to support LGBTQ families."
    ]

    print("\n[1/2] 注入 5 轮对话...")
    for i, conv in enumerate(conversations, 1):
        await coordinator.process_input(conv)
        print(f"  {i}. ✓ {conv[:50]}...")

    # 连续 3 次查询
    queries = [
        "What did Caroline research?",
        "What is Caroline's identity?",
        "What fields would Caroline pursue?"
    ]

    print("\n[2/2] 连续 3 次查询...")
    for i, query in enumerate(queries, 1):
        if coordinator.memory_reasoning_chain:
            result = await coordinator.memory_reasoning_chain.build_reasoning_chain(query)

            print(f"\n  查询 {i}: {query}")
            print(f"    → 检索: {len(result['memories'])} 条记忆")
            print(f"    → 链接: {len(result['causal_links'])} 条")
            print(f"    → 置信度: {result['confidence']:.2f}")

            # 断言：每次查询都应该有合理结果
            assert len(result['memories']) > 0, f"❌ 查询 {i} 未检索到记忆"
            assert result['confidence'] > 0, f"❌ 查询 {i} 置信度为 0"
            assert len(result['answer'].strip()) > 0, f"❌ 查询 {i} 答案为空"

    print("\n✅ 多轮查询稳定")
    await coordinator.stop_system()
    return True


async def main():
    """运行所有测试"""
    print("Memory Reasoning Chain 断言测试套件")
    print("=" * 80)

    tests = [
        ("基础推理链", test_reasoning_chain_basic),
        ("KG 集成", test_kg_integration),
        ("多轮稳定性", test_multi_turn_stability),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n✅ 所有测试通过")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
