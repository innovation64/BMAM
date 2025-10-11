#!/usr/bin/env python3
"""
测试条件约束引擎 - ConditionalConstraintEngine

测试场景:
1. 时间问题需要插入日期提取
2. 记忆不足时跳过能力
3. 低置信度触发备选路径
"""

import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')


async def test_constraint_engine():
    """测试条件约束引擎"""
    from src.reasoning.conditional_constraint_engine import ConditionalConstraintEngine

    print("=" * 80)
    print("🧪 Testing ConditionalConstraintEngine")
    print("=" * 80)

    engine = ConditionalConstraintEngine()

    # ========== 测试场景1: 时间计算需要先提取日期 ==========
    print("\n📋 Test 1: Temporal calculation should insert fact_extraction")
    print("-" * 80)

    capabilities_1 = [
        {'name': 'temporal_calculation', 'priority': 1, 'reason': 'Calculate time difference'}
    ]

    memories_1 = [
        {'content': 'On May 25, Caroline researched adoption agencies'},
        {'content': 'On June 3, Caroline had a consultation'}
    ]

    constraints_1 = await engine.analyze_constraints(
        query="How many days passed between researching and consultation?",
        capabilities=capabilities_1,
        memories=memories_1,
        intermediate_results={}
    )

    print(f"✅ LLM generated {len(constraints_1)} constraints:")
    for c in constraints_1:
        print(f"   - {c.get('name')}: {c.get('action')} ({c.get('reason', 'N/A')[:60]}...)")

    # 应用约束
    modified_caps_1 = engine.apply_constraints(capabilities_1, constraints_1)
    print(f"\n📋 Original capabilities: {[c['name'] for c in capabilities_1]}")
    print(f"📋 Modified capabilities: {[c['name'] for c in modified_caps_1]}")

    # ========== 测试场景2: 记忆为空时跳过能力 ==========
    print("\n\n📋 Test 2: No memories should skip memory-dependent capabilities")
    print("-" * 80)

    capabilities_2 = [
        {'name': 'fact_extraction', 'priority': 1, 'reason': 'Extract facts'},
        {'name': 'temporal_calculation', 'priority': 2, 'reason': 'Calculate time'}
    ]

    memories_2 = []  # 空记忆

    constraints_2 = await engine.analyze_constraints(
        query="What did Caroline do?",
        capabilities=capabilities_2,
        memories=memories_2,
        intermediate_results={}
    )

    print(f"✅ LLM generated {len(constraints_2)} constraints:")
    for c in constraints_2:
        print(f"   - {c.get('name')}: {c.get('action')} ({c.get('reason', 'N/A')[:60]}...)")

    modified_caps_2 = engine.apply_constraints(capabilities_2, constraints_2)
    print(f"\n📋 Original capabilities: {[c['name'] for c in capabilities_2]}")
    print(f"📋 Modified capabilities: {[c['name'] for c in modified_caps_2]}")

    # ========== 测试场景3: 低置信度触发备选路径 ==========
    print("\n\n📋 Test 3: Low confidence should activate alternative capability")
    print("-" * 80)

    capabilities_3 = [
        {'name': 'identity_inference', 'priority': 1, 'reason': 'Infer identity'}
    ]

    memories_3 = [
        {'content': 'Caroline attended a support group'}
    ]

    # 模拟低置信度结果
    intermediate_3 = {
        'fact_extraction': {'answer': 'unclear', 'confidence': 0.2}  # 低置信度
    }

    constraints_3 = await engine.analyze_constraints(
        query="What is Caroline's gender identity?",
        capabilities=capabilities_3,
        memories=memories_3,
        intermediate_results=intermediate_3
    )

    print(f"✅ LLM generated {len(constraints_3)} constraints:")
    for c in constraints_3:
        print(f"   - {c.get('name')}: {c.get('action')} ({c.get('reason', 'N/A')[:60]}...)")

    modified_caps_3 = engine.apply_constraints(capabilities_3, constraints_3)
    print(f"\n📋 Original capabilities: {[c['name'] for c in capabilities_3]}")
    print(f"📋 Modified capabilities: {[c['name'] for c in modified_caps_3]}")

    # ========== 检查执行历史 ==========
    print("\n\n📊 Constraint Execution History:")
    print("-" * 80)
    history = engine.get_execution_history()
    for i, entry in enumerate(history, 1):
        print(f"{i}. {entry['constraint']}: {entry['action']}")
        print(f"   Reason: {entry['reason'][:80]}...")

    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_constraint_engine())
