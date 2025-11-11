#!/usr/bin/env python3
"""
LoCoMo 5问题测试 - HRM版本
Tests HRM integration with LoCoMo benchmark
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# 确保正确的导入路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# LoCoMo真实数据 - Caroline的故事
LOCOMO_SESSIONS = [
    {
        'date': '2023-05-08',
        'events': [
            "On 8 May 2023, Caroline said: 'I went to a LGBTQ support group yesterday and it was so powerful.'",
            "She said: 'The transgender stories were so inspiring! I was so happy and thankful for all the support.'",
            "Caroline said: 'Gonna continue my edu and check out career options, which is pretty exciting!'",
            "She added: 'I'm keen on counseling or working in mental health - I'd love to support those with similar issues.'",
        ]
    },
    {
        'date': '2023-05-25',
        'events': [
            "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
            "She learned about social work programs focused on community advocacy.",
        ]
    },
]

LOCOMO_QUESTIONS = [
    {
        'id': 'Q1',
        'question': 'When did Caroline go to the LGBTQ support group?',
        'expected_answer': '7 May 2023',
        'keywords': ['7 may', '7th may', 'may 7']
    },
    {
        'id': 'Q2',
        'question': 'What did Caroline research?',
        'expected_answer': 'adoption agencies',
        'keywords': ['adoption', 'agencies']
    },
    {
        'id': 'Q3',
        'question': "What is Caroline's identity?",
        'expected_answer': 'transgender woman',
        'keywords': ['transgender', 'trans', 'lgbtq']
    },
    {
        'id': 'Q4',
        'question': 'What fields would Caroline be likely to pursue in her education?',
        'expected_answer': 'social work / psychology',
        'keywords': ['social work', 'psychology', 'counseling', 'mental health']
    },
    {
        'id': 'Q5',
        'question': 'What community did Caroline engage with?',
        'expected_answer': 'LGBTQ community',
        'keywords': ['lgbtq', 'transgender', 'support group']
    },
]


async def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("  真实LoCoMo 5问题测试 - HRM版本 (Caroline数据集)")
    print("="*80)

    # 创建coordinator
    print("\n正在初始化HRM-aware coordinator...")
    coordinator = BrainInspiredCoordinator()

    try:
        await coordinator.initialize()

        # 检查是否有HRM组件
        has_hrm = False
        if hasattr(coordinator, 'basal_ganglia_agent'):
            print("✅ Basal Ganglia detected (fixed-point detection)")
            has_hrm = True
        if hasattr(coordinator, 'thalamus_agent'):
            print("✅ Thalamus detected (multi-timescale)")
            has_hrm = True

        if not has_hrm:
            print("⚠️  No HRM components detected, running in standard mode")

        print("\n" + "="*80)
        print("📚 Phase 1: Learning Sessions")
        print("-"*80)

        # Phase 1: 学习sessions
        for session in LOCOMO_SESSIONS:
            date = session['date']
            print(f"\n📅 Session {LOCOMO_SESSIONS.index(session) + 1} ({date}):")

            for i, event in enumerate(session['events'], 1):
                print(f"   {i}. {event[:80]}...")

                try:
                    await coordinator.process_input(f"Remember this: {event}")
                except Exception as e:
                    print(f"   ⚠️  Error processing event: {e}")

        print("\n" + "="*80)
        print("❓ Phase 2: Answering Questions")
        print("="*80 + "\n")

        # Phase 2: 回答questions
        results = []

        for q in LOCOMO_QUESTIONS:
            print(f"[{q['id']}] {q['question']}")
            print(f"Expected: {q['expected_answer']}")

            try:
                answer_data = await coordinator.process_input(q['question'])
                answer = answer_data if isinstance(answer_data, str) else str(answer_data)

                # 检查关键词匹配
                answer_lower = answer.lower()
                matched = any(kw in answer_lower for kw in q['keywords'])

                print(f"Answer:   {answer[:100]}...")
                print(f"{'✅' if matched else '❌'} {'包含关键词' if matched else '未包含关键词'}\n")

                results.append({
                    'question_id': q['id'],
                    'question': q['question'],
                    'expected': q['expected_answer'],
                    'answer': answer,
                    'matched': matched
                })

            except Exception as e:
                print(f"❌ Error: {e}\n")
                results.append({
                    'question_id': q['id'],
                    'question': q['question'],
                    'expected': q['expected_answer'],
                    'answer': f"ERROR: {e}",
                    'matched': False
                })

        # 统计结果
        total = len(results)
        matched = sum(1 for r in results if r['matched'])
        accuracy = (matched / total * 100) if total > 0 else 0

        print("="*80)
        print("📊 测试总结")
        print("="*80)
        print(f"问题总数: {total}")
        print(f"关键词匹配: {matched}/{total} ({accuracy:.1f}%)")

        # 保存结果
        output_file = 'locomo_hrm_5q_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'mode': 'HRM-aware' if has_hrm else 'standard',
                'total_questions': total,
                'matched': matched,
                'accuracy': accuracy,
                'results': results
            }, f, ensure_ascii=False, indent=2)

        print(f"结果已保存: {output_file}")

        # HRM统计
        if hasattr(coordinator, 'forgetting_coordinator'):
            fc_stats = coordinator.forgetting_coordinator.get_stats()
            if fc_stats.get('hrm_enabled'):
                print("\n🎯 HRM Statistics:")
                print(f"   Fixed-point detections: {fc_stats.get('fixed_point_detections', 0)}")

        print()

        if accuracy < 70:
            print(f"⚠️  准确率较低: {accuracy:.1f}%")
        else:
            print(f"✅ 准确率良好: {accuracy:.1f}%")

    finally:
        # 清理
        await coordinator.stop_system()
        print("\n✅ Coordinator stopped")


if __name__ == "__main__":
    asyncio.run(main())
