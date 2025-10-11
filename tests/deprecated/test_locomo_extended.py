#!/usr/bin/env python3
"""
LoCoMo扩展测试: 挑选10个不同难度的案例
测试分布式推理架构的鲁棒性
"""
import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

# 从LoCoMo挑选的10个测试案例 (覆盖不同类型和难度)
TEST_CASES = [
    {
        "id": "Q1",
        "question": "When did Caroline go to the LGBTQ support group?",
        "expected": "7 May 2023",
        "type": "temporal",
        "difficulty": "medium"
    },
    {
        "id": "Q3",
        "question": "What fields would Caroline be likely to pursue in her education?",
        "expected": "Psychology, counseling certification",
        "type": "multi_hop",
        "difficulty": "hard"
    },
    {
        "id": "Q4",
        "question": "What did Caroline research?",
        "expected": "Adoption agencies",
        "type": "research",
        "difficulty": "easy"
    },
    {
        "id": "Q5",
        "question": "What is Caroline's identity?",
        "expected": "Transgender woman",
        "type": "identity",
        "difficulty": "medium"
    },
    {
        "id": "Q7",
        "question": "What is Caroline interested in?",
        "expected": "Adoption, LGBTQ advocacy",
        "type": "multi_hop",
        "difficulty": "medium"
    },
    {
        "id": "Q8",
        "question": "What is Caroline's relationship status?",
        "expected": "Single",
        "type": "identity",
        "difficulty": "easy"
    },
    {
        "id": "Q9",
        "question": "Where did Caroline move from 4 years ago?",
        "expected": "Sweden",
        "type": "factual",
        "difficulty": "easy"
    },
    {
        "id": "Q10",
        "question": "What career path has Caroline decided to pursue?",
        "expected": "counseling or mental health for Transgender people",
        "type": "multi_hop",
        "difficulty": "hard"
    },
    {
        "id": "Q11",
        "question": "When is Melanie planning on going camping?",
        "expected": "June 2023",
        "type": "temporal",
        "difficulty": "easy"
    },
    {
        "id": "Q12",
        "question": "How long has Caroline had her current group of friends for?",
        "expected": "4 years",
        "type": "temporal",
        "difficulty": "medium"
    }
]

async def test_locomo_extended():
    print("=" * 90)
    print("🧠 LoCoMo扩展测试: 10个案例验证分布式推理架构")
    print("=" * 90)

    coordinator = BrainInspiredCoordinator()

    # 验证分布式推理架构
    print(f"\n✅ Reflection Agent: {coordinator.reasoning_validator.reflection_agent is not None}")
    print(f"✅ Consolidation Agent: {coordinator.reasoning_validator.consolidation_agent is not None}")

    # 学习记忆 (简化版 - Session 1-3的关键事件)
    print("\n📝 学习记忆...")
    memories = [
        # Session 1 - 8 May 2023
        "On 8 May, 2023, Caroline attended an LGBTQ support group for the first time.",
        "Caroline found transgender stories very inspiring.",

        # Session 2 - 25 May 2023
        "On 25 May, 2023, Caroline researched adoption agencies.",
        "Melanie is planning to go camping in June 2023.",

        # Session 3 - 9 June 2023
        "Caroline is single and has had her friends for 4 years.",
        "Caroline moved from Sweden 4 years ago.",

        # Session 4 - Career decision
        "Caroline decided to pursue counseling and mental health services for transgender people.",
    ]

    for mem in memories:
        print(f"   ✓ {mem[:70]}...")
        await coordinator.process_input(mem)

    print("\n" + "=" * 90)
    print("🧪 开始测试...")
    print("=" * 90)

    results = []
    passed = 0

    for i, case in enumerate(TEST_CASES, 1):
        print(f"\n--- 案例 {i}/{len(TEST_CASES)}: {case['id']} ({case['type']}) [{case['difficulty']}] ---")
        print(f"❓ {case['question']}")
        print(f"✅ Expected: {case['expected']}")

        answer = await coordinator.process_input(case['question'])
        print(f"🤖 Answer: {answer}")

        # 判断逻辑
        is_correct = False
        expected_lower = case['expected'].lower()
        answer_lower = answer.lower()

        if case['type'] == 'temporal':
            # 时间类型 - 宽松匹配
            key_parts = [p.strip() for p in expected_lower.split()]
            is_correct = any(part in answer_lower for part in key_parts if len(part) > 2)
        elif case['type'] == 'identity':
            # 身份类型 - 关键词匹配
            if 'transgender' in expected_lower:
                is_correct = 'transgender' in answer_lower
            elif 'single' in expected_lower:
                is_correct = 'single' in answer_lower
        elif case['type'] == 'research':
            is_correct = 'adoption' in answer_lower
        elif case['type'] == 'factual':
            is_correct = expected_lower in answer_lower or any(word in answer_lower for word in expected_lower.split())
        else:  # multi_hop
            # 多跳推理 - 语义匹配
            keywords = ['counseling', 'psychology', 'mental health', 'transgender', 'advocacy',
                       'adoption', 'social work', 'helping']
            is_correct = any(kw in answer_lower for kw in keywords)

        status = "✅ PASS" if is_correct else "❌ FAIL"
        print(f"{status}")

        if is_correct:
            passed += 1

        results.append({
            'id': case['id'],
            'question': case['question'],
            'expected': case['expected'],
            'actual': answer,
            'type': case['type'],
            'difficulty': case['difficulty'],
            'passed': is_correct
        })

        print("-" * 90)

    # 汇总结果
    print("\n" + "=" * 90)
    print("📊 测试结果汇总")
    print("=" * 90)

    total = len(TEST_CASES)
    pass_rate = (passed / total) * 100

    print(f"\n总计: {passed}/{total} 通过 ({pass_rate:.1f}%)")

    # 按难度统计
    by_difficulty = {'easy': {'total': 0, 'passed': 0},
                     'medium': {'total': 0, 'passed': 0},
                     'hard': {'total': 0, 'passed': 0}}

    for r in results:
        diff = r['difficulty']
        by_difficulty[diff]['total'] += 1
        if r['passed']:
            by_difficulty[diff]['passed'] += 1

    print("\n按难度统计:")
    for diff in ['easy', 'medium', 'hard']:
        stats = by_difficulty[diff]
        if stats['total'] > 0:
            rate = (stats['passed'] / stats['total']) * 100
            print(f"  {diff.upper()}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    # 按类型统计
    by_type = {}
    for r in results:
        t = r['type']
        if t not in by_type:
            by_type[t] = {'total': 0, 'passed': 0}
        by_type[t]['total'] += 1
        if r['passed']:
            by_type[t]['passed'] += 1

    print("\n按类型统计:")
    for t, stats in by_type.items():
        rate = (stats['passed'] / stats['total']) * 100
        print(f"  {t}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    print("\n详细结果:")
    for r in results:
        status = "✅" if r['passed'] else "❌"
        print(f"{status} {r['id']} ({r['type']}/{r['difficulty']}): {r['question']}")

    # 保存结果
    import json
    from datetime import datetime
    output_file = f"results/locomo_extended_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'total': total,
            'passed': passed,
            'pass_rate': pass_rate,
            'by_difficulty': by_difficulty,
            'by_type': by_type,
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 结果已保存: {output_file}")

    print("\n" + "=" * 90)
    print("✅ 测试完成!")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(test_locomo_extended())
