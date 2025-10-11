#!/usr/bin/env python3
"""
LoCoMo小批量测试 - 验证新架构效果

测试新功能:
1. CapabilityOrchestrator动态能力编排
2. ConditionalConstraintEngine条件约束
3. LLM驱动的约束规则推理
"""

import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator


# 选择5个代表性案例(覆盖不同类型)
SMALL_TEST_CASES = [
    # 1. Identity (身份问题)
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

    # 2. Factual (事实问题)
    {
        'id': 'F1',
        'type': 'factual',
        'learning': [
            "On 8 May 2023, Caroline attended an LGBTQ support group meeting."
        ],
        'question': "What did Caroline attend on 8 May 2023?",
        'expected': 'LGBTQ support group'
    },

    # 3. Temporal (时间计算)
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

    # 4. Multi-hop (多跳推理)
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

    # 5. Research (研究问题)
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


async def test_locomo_small():
    """小批量LoCoMo测试"""
    print("=" * 100)
    print("🧪 LoCoMo Small Batch Test - Testing New Architecture")
    print("=" * 100)
    print(f"Total test cases: {len(SMALL_TEST_CASES)}")
    print(f"Architecture: CapabilityOrchestrator + ConditionalConstraintEngine")
    print("=" * 100)

    coordinator = BrainInspiredCoordinator()

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

        # 学习阶段
        print(f"\n📚 Learning Phase:")
        for j, fact in enumerate(case['learning'], 1):
            print(f"  {j}. {fact}")
            learn_result = await coordinator.process_input(fact)
            # 兼容不同返回类型
            if hasattr(learn_result, 'routing_decision'):
                mode = learn_result.routing_decision.get('mode', 'N/A')
            else:
                mode = 'legacy'
            print(f"     ✅ Stored (mode={mode})")

        # 问答阶段
        print(f"\n❓ Question: {case['question']}")
        print(f"🎯 Expected: {case['expected']}")

        result = await coordinator.process_input(case['question'])

        # 兼容不同返回类型
        if hasattr(result, 'response'):
            answer = result.response
            mode = result.routing_decision.get('mode', 'N/A')
            capabilities = result.routing_decision.get('capabilities', [])
            confidence = result.insights.get('confidence', 0.0)
            processing_time = result.processing_time
        else:
            # Legacy string response
            answer = str(result)
            mode = 'legacy'
            capabilities = []
            confidence = 0.5
            processing_time = 0.0

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

        # 显示约束历史(如果使用了orchestrator)
        if mode == 'capability_orchestrator' and hasattr(result, 'agent_logs'):
            reasoning_chain = result.agent_logs.get('reasoning_chain', [])
            if reasoning_chain:
                print(f"\n🔗 Reasoning Chain:")
                for step in reasoning_chain[:5]:  # 显示前5步
                    print(f"  - {step}")

    # ========== 汇总结果 ==========
    print(f"\n\n{'='*100}")
    print("📊 Test Summary")
    print(f"{'='*100}")
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")

    # 按类型统计
    print(f"\n📈 Results by Type:")
    type_stats = {}
    for detail in results['details']:
        t = detail['type']
        if t not in type_stats:
            type_stats[t] = {'total': 0, 'passed': 0}
        type_stats[t]['total'] += 1
        if detail['passed']:
            type_stats[t]['passed'] += 1

    for t, stats in sorted(type_stats.items()):
        rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {t}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    # 模式统计
    print(f"\n🎯 Results by Mode:")
    mode_stats = {}
    for detail in results['details']:
        m = detail['mode']
        if m not in mode_stats:
            mode_stats[m] = {'total': 0, 'passed': 0}
        mode_stats[m]['total'] += 1
        if detail['passed']:
            mode_stats[m]['passed'] += 1

    for m, stats in sorted(mode_stats.items()):
        rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {m}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    # 失败案例
    if results['failed'] > 0:
        print(f"\n❌ Failed Cases:")
        for detail in results['details']:
            if not detail['passed']:
                print(f"  {detail['id']} ({detail['type']}): Expected '{detail['expected']}', Got '{detail['answer'][:50]}...'")

    # 平均置信度
    avg_confidence = sum(d['confidence'] for d in results['details']) / len(results['details']) if results['details'] else 0
    avg_time = sum(d['processing_time'] for d in results['details']) / len(results['details']) if results['details'] else 0

    print(f"\n📊 Performance Metrics:")
    print(f"  Average Confidence: {avg_confidence:.2f}")
    print(f"  Average Processing Time: {avg_time:.2f}s")

    print(f"\n{'='*100}")
    if results['passed'] == results['total']:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️ {results['failed']} test(s) failed")
    print(f"{'='*100}")

    return results


if __name__ == '__main__':
    asyncio.run(test_locomo_small())
