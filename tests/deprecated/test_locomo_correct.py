#!/usr/bin/env python3
"""
LoCoMo正确测试 - 修复学习阶段直接存储记忆的问题

关键修正:
1. 学习阶段直接调用memory_system.store_memory(),不是process_input()
2. 问答阶段调用process_user_input()获得ProcessingResult
3. 这样避免了"在prompt里面泄漏问题答案"的问题
"""

import asyncio
import sys
from datetime import datetime
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator


# 选择5个代表性案例
SMALL_TEST_CASES = [
    {
        'id': 'I1',
        'type': 'identity',
        'learning': [
            "On 8 May 2023, Caroline attended an LGBTQ support group meeting.",
            "On 12 May 2023, Caroline went to a gender identity clinic."
        ],
        'question': "What is Caroline's gender identity?",
        'expected': 'transgender'
    },
    {
        'id': 'F1',
        'type': 'factual',
        'learning': [
            "On 8 May 2023, Caroline attended an LGBTQ support group meeting."
        ],
        'question': "What did Caroline attend on 8 May 2023?",
        'expected': 'LGBTQ support group'
    },
    {
        'id': 'T5',
        'type': 'temporal',
        'learning': [
            "On 25 May, 2023, Caroline researched adoption agencies.",
            "On 3 June, 2023, Caroline had a consultation with Dr. Anderson."
        ],
        'question': "How many days passed between Caroline researching adoption agencies and having the consultation with Dr. Anderson?",
        'expected': '9'
    },
    {
        'id': 'M2',
        'type': 'multi_hop',
        'learning': [
            "On 12 May 2023, Caroline went to a gender identity clinic.",
            "On 25 May, 2023, Caroline researched adoption agencies."
        ],
        'question': "What are Caroline's interests?",
        'expected': 'gender identity, adoption'
    },
    {
        'id': 'R1',
        'type': 'research',
        'learning': [
            "On 25 May, 2023, Caroline researched adoption agencies."
        ],
        'question': "What did Caroline research on 25 May, 2023?",
        'expected': 'adoption agencies'
    }
]


async def test_locomo_correct():
    """正确的LoCoMo测试 - 学习阶段直接存储记忆"""
    print("=" * 100)
    print("🧪 LoCoMo Correct Test - Learning Phase Stores Memory Directly")
    print("=" * 100)
    print(f"Total test cases: {len(SMALL_TEST_CASES)}")
    print(f"Key Fix: Learning events stored as memories, NOT processed as questions")
    print("=" * 100)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    results = {
        'total': len(SMALL_TEST_CASES),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    for i, case in enumerate(SMALL_TEST_CASES, 1):
        print(f"\n{'='*100}")
        print(f"Test Case {i}/{len(SMALL_TEST_CASES)}: {case['id']} ({case['type']})")
        print(f"{'='*100}")

        # ✅ 正确做法: 学习阶段直接存储记忆,不经过process_input
        print(f"\n📚 Learning Phase (Direct Memory Storage):")
        for j, fact in enumerate(case['learning'], 1):
            print(f"  {j}. {fact}")

            # 🔥 关键修正: 直接存储到memory_system,不是当作问题处理
            memory_id = await coordinator.memory_system.store_memory(
                content=fact,
                importance=0.9,
                context_tags=['learning', 'event', 'locomo_test']
            )
            print(f"     ✅ Stored as memory: {memory_id[:8]}...")

        # 问答阶段: 调用process_user_input获取完整的ProcessingResult
        print(f"\n❓ Question: {case['question']}")
        print(f"🎯 Expected: {case['expected']}")

        result = await coordinator.process_user_input(case['question'], {})

        # 现在result是ProcessingResult对象,不是字符串
        answer = result.response
        mode = result.routing_decision.get('mode', 'N/A')
        capabilities = result.routing_decision.get('capabilities', [])
        confidence = result.insights.get('confidence', 0.0)
        processing_time = result.processing_time

        print(f"\n📊 Result:")
        print(f"  Mode: {mode}")
        print(f"  Capabilities: {capabilities}")
        print(f"  Answer: {answer}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Processing Time: {processing_time:.2f}s")

        # 验证答案
        expected_lower = case['expected'].lower()
        answer_lower = answer.lower()

        # 多策略匹配
        exact_match = expected_lower in answer_lower

        # 关键词匹配(70%阈值)
        expected_keywords = [kw.strip() for kw in expected_lower.replace(',', ' ').split() if len(kw.strip()) > 2]
        keyword_matches = sum(1 for kw in expected_keywords if kw in answer_lower)
        semantic_match = len(expected_keywords) > 0 and keyword_matches >= len(expected_keywords) * 0.7

        is_correct = exact_match or semantic_match

        if is_correct:
            results['passed'] += 1
            status = "✅ PASS"
        else:
            results['failed'] += 1
            status = "❌ FAIL"

        print(f"\n{status}")
        if not is_correct:
            print(f"  Expected keywords: {expected_keywords}")
            print(f"  Matched: {keyword_matches}/{len(expected_keywords)}")

        # 记录详细结果
        results['details'].append({
            'id': case['id'],
            'type': case['type'],
            'passed': is_correct,
            'mode': mode,
            'capabilities': capabilities,
            'confidence': confidence,
            'answer': answer,
            'expected': case['expected'],
            'processing_time': processing_time
        })

    # 打印汇总
    print(f"\n{'='*100}")
    print(f"📊 Test Summary")
    print(f"{'='*100}")
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")

    # 按类型统计
    type_stats = {}
    for detail in results['details']:
        t = detail['type']
        if t not in type_stats:
            type_stats[t] = {'total': 0, 'passed': 0}
        type_stats[t]['total'] += 1
        if detail['passed']:
            type_stats[t]['passed'] += 1

    print(f"\n📈 Results by Type:")
    for t, stats in type_stats.items():
        accuracy = stats['passed'] / stats['total'] * 100
        print(f"  {t}: {stats['passed']}/{stats['total']} ({accuracy:.1f}%)")

    # 按模式统计
    mode_stats = {}
    for detail in results['details']:
        m = detail['mode']
        if m not in mode_stats:
            mode_stats[m] = {'total': 0, 'passed': 0}
        mode_stats[m]['total'] += 1
        if detail['passed']:
            mode_stats[m]['passed'] += 1

    print(f"\n🎯 Results by Mode:")
    for m, stats in mode_stats.items():
        accuracy = stats['passed'] / stats['total'] * 100
        print(f"  {m}: {stats['passed']}/{stats['total']} ({accuracy:.1f}%)")

    if results['failed'] > 0:
        print(f"\n❌ Failed Cases:")
        for detail in results['details']:
            if not detail['passed']:
                print(f"  {detail['id']} ({detail['type']}): Expected '{detail['expected']}', Got '{detail['answer'][:50]}...'")

    # 性能指标
    avg_confidence = sum(d['confidence'] for d in results['details']) / len(results['details'])
    avg_time = sum(d['processing_time'] for d in results['details']) / len(results['details'])
    print(f"\n📊 Performance Metrics:")
    print(f"  Average Confidence: {avg_confidence:.2f}")
    print(f"  Average Processing Time: {avg_time:.2f}s")

    print(f"\n{'='*100}")
    if results['failed'] == 0:
        print(f"🎉 All tests passed!")
    else:
        print(f"⚠️ {results['failed']} test(s) failed")
    print(f"{'='*100}")

    await coordinator.stop_system()


if __name__ == "__main__":
    asyncio.run(test_locomo_correct())
