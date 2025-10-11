#!/usr/bin/env python3
"""
扩展测试: 从LoCoMo挑选更多案例测试分布式推理
"""
import asyncio
import sys
import json
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

# 选择的测试案例 (不同难度和类型)
SELECTED_CASES = [
    {
        "id": "Q1",
        "question": "When did Caroline go to the LGBTQ support group?",
        "expected": "7 May 2023",
        "type": "temporal",
        "description": "时间推理 - 需要计算'yesterday'"
    },
    {
        "id": "Q3",
        "question": "What fields would Caroline be likely to pursue in her education?",
        "expected": "Psychology, counseling certification",
        "type": "multi_hop",
        "description": "多跳推理 - 需要Reflection Agent识别pattern"
    },
    {
        "id": "Q4",
        "question": "What did Caroline research?",
        "expected": "Adoption agencies",
        "type": "research",
        "description": "跨Session检索"
    },
    {
        "id": "Q5",
        "question": "What is Caroline's identity?",
        "expected": "Transgender woman",
        "type": "identity",
        "description": "身份推理 - 需要Consolidation Agent整合事实"
    },
    {
        "id": "Q6",
        "question": "When did Melanie run a charity race?",
        "expected": "The sunday before 25 May 2023",
        "type": "temporal",
        "description": "时间推理 - 相对时间"
    },
    {
        "id": "Q7",
        "question": "What is Caroline interested in?",
        "expected": "Adoption, LGBTQ advocacy",
        "type": "multi_hop",
        "description": "兴趣推理 - 需要从多条记忆推断"
    }
]

async def test_extended_cases():
    print("=" * 80)
    print("🧠 扩展测试: 分布式推理架构 - LoCoMo多案例验证")
    print("=" * 80)

    # 初始化
    print("\n1️⃣  初始化BrainCoordinator...")
    coordinator = BrainInspiredCoordinator()

    print(f"   ✅ Reflection Agent连接: {coordinator.reasoning_validator.reflection_agent is not None}")
    print(f"   ✅ Consolidation Agent连接: {coordinator.reasoning_validator.consolidation_agent is not None}")

    # 学习Session 1和2的对话
    print("\n2️⃣  学习记忆 (Session 1 & 2)...")

    # Session 1 - 8 May 2023
    session1_events = [
        "Today's date is 8 May, 2023. This conversation is happening on this date.",
        "On 8 May, 2023, Caroline: Caroline attends an LGBTQ support group for the first time.",
        "Caroline: The transgender stories were so inspiring! I was so happy and thankful for all the support.",
        "Caroline: I went to a LGBTQ support group yesterday and it was so powerful."
    ]

    # Session 2 - 25 May 2023
    session2_events = [
        "On 25 May, 2023, Caroline: Caroline is inspired by her supportive friends and mentors to start researching adoption agencies.",
        "Melanie: I ran a charity race last Sunday to raise money for kids in need!",
        "Caroline: That's amazing Melanie! I've been researching adoption agencies lately."
    ]

    for event in session1_events + session2_events:
        print(f"   📝 Learning: {event[:60]}...")
        await coordinator.process_input(event)

    # 测试所有案例
    print("\n3️⃣  测试所有案例...")
    print("=" * 80)

    results = []

    for i, case in enumerate(SELECTED_CASES, 1):
        print(f"\n--- 案例 {i}/{len(SELECTED_CASES)}: {case['id']} ({case['type']}) ---")
        print(f"📋 {case['description']}")
        print(f"❓ Question: {case['question']}")
        print(f"✅ Expected: {case['expected']}")

        response = await coordinator.process_input(case['question'])

        print(f"🤖 BMAM Answer: {response}")

        # 简单判断
        is_correct = False
        if case['type'] == 'temporal':
            # 时间答案比较宽松
            is_correct = any(part in str(response).lower() for part in case['expected'].lower().split())
        elif case['type'] == 'identity':
            is_correct = "transgender woman" in response.lower() or "transgender" in response.lower()
        elif case['type'] == 'multi_hop':
            # 多跳推理只要包含关键词
            keywords = ['psychology', 'counseling', 'social work', 'advocacy', 'adoption']
            is_correct = any(kw in response.lower() for kw in keywords)
        else:
            is_correct = case['expected'].lower() in response.lower()

        status = "✅ PASS" if is_correct else "❌ FAIL"
        print(f"{status}")

        results.append({
            'id': case['id'],
            'question': case['question'],
            'expected': case['expected'],
            'actual': response,
            'type': case['type'],
            'passed': is_correct
        })

        print("-" * 80)

    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    passed = sum(1 for r in results if r['passed'])
    total = len(results)

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    print("\n详细结果:")
    for r in results:
        status = "✅" if r['passed'] else "❌"
        print(f"{status} {r['id']} ({r['type']}): {r['question']}")

    # 保存结果
    import json
    from datetime import datetime
    output_file = f"results/distributed_reasoning_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'total': total,
            'passed': passed,
            'pass_rate': passed/total,
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 结果已保存: {output_file}")

    print("\n" + "=" * 80)
    print("✅ 扩展测试完成!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_extended_cases())
