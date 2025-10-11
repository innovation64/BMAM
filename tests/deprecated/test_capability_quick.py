"""
🧪 快速验证可组合推理能力架构

测试3个案例:
1. 原始问题 (baseline)
2. 变种表达 (paraphrase)
3. 新型问题 (novel - causal)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'BMAM'))

from src.reasoning.capability_analyzer import CapabilityAnalyzer
from src.coordination.brain_coordinator import BrainInspiredCoordinator


async def test_quick():
    print("=" * 80)
    print("🧠 快速验证: 可组合推理能力架构")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    analyzer = CapabilityAnalyzer()

    # 学习记忆
    print("\n📝 学习记忆...")
    memories = [
        "[Context: This conversation is on 8 May, 2023]",
        "On 8 May, 2023, Caroline attended an LGBTQ support group for the first time.",
        "Caroline found transgender stories very inspiring.",
        "On 25 May, 2023, Caroline researched adoption agencies.",
        "Caroline moved from Sweden 4 years ago.",
        "Caroline decided to pursue counseling and mental health services for transgender people.",
    ]

    for mem in memories:
        await coordinator.process_input(mem)
        print(f"   ✓ {mem[:60]}...")

    print("\n" + "=" * 80)
    print("🧪 测试案例")
    print("=" * 80)

    test_cases = [
        {
            "id": "baseline",
            "question": "When did Caroline go to the LGBTQ support group?",
            "expected": "7 May 2023"
        },
        {
            "id": "paraphrase",
            "question": "Which country did Caroline relocate from?",
            "expected": "Sweden"
        },
        {
            "id": "novel_causal",
            "question": "Why might Caroline have researched adoption agencies?",
            "expected": None  # 新类型
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 案例 {i}: {case['id']} ---")
        print(f"❓ {case['question']}")

        # 能力分析
        print("\n🔍 能力分析...")
        analysis = await analyzer.analyze(case['question'])
        caps = [c['name'] for c in analysis['capabilities']]
        print(f"   检测到的能力: {caps}")
        print(f"   执行计划: {analysis['execution_plan']}")

        # 执行推理
        print("\n▶️ 执行推理...")
        answer = await coordinator.process_input(case['question'])
        print(f"   答案: {answer}")

        # 验证
        if case['expected']:
            is_correct = case['expected'].lower() in str(answer).lower()
            print(f"\n{'✅ PASS' if is_correct else '❌ FAIL'}")
        else:
            print(f"\n⚠️ 新类型问题 (无标准答案)")

    print("\n" + "=" * 80)
    print("✅ 快速测试完成")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_quick())
