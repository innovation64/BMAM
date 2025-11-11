#!/usr/bin/env python3
"""
真实LoCoMo 5问题测试 - 使用重构后的coordinator
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
    }
]

LOCOMO_QUESTIONS = [
    ("When did Caroline go to the LGBTQ support group?", "7 May 2023"),
    ("What did Caroline research?", "adoption agencies"),
    ("What is Caroline's identity?", "transgender woman"),
    ("What fields would Caroline be likely to pursue in her education?", "social work / psychology"),
    ("What community did Caroline engage with?", "LGBTQ community")
]


async def main():
    print("=" * 80)
    print("  真实LoCoMo 5问题测试 (Caroline数据集)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Phase 1: 学习sessions
    print("\n📚 Phase 1: Learning Sessions")
    print("-" * 80)

    for session_idx, session in enumerate(LOCOMO_SESSIONS, 1):
        print(f"\n📅 Session {session_idx} ({session['date']}):")
        for event_idx, event in enumerate(session['events'], 1):
            print(f"   {event_idx}. {event[:80]}...")
            await coordinator.process_input(event)

    # Phase 2: 回答问题
    print("\n" + "=" * 80)
    print("❓ Phase 2: Answering Questions")
    print("=" * 80)

    results = []
    correct = 0

    for q_idx, (question, expected) in enumerate(LOCOMO_QUESTIONS, 1):
        print(f"\n[Q{q_idx}] {question}")
        print(f"Expected: {expected}")

        answer = await coordinator.process_input(question)
        print(f"Answer:   {answer[:150]}...")

        # 简单判断（实际应该用LLM评判）
        is_correct = any(keyword.lower() in answer.lower() for keyword in expected.split('/'))

        if is_correct:
            print("✅ 包含关键词")
            correct += 1
        else:
            print("❌ 未包含关键词")

        results.append({
            'question': question,
            'expected': expected,
            'answer': answer,
            'keyword_match': is_correct
        })

    # 保存结果
    output_file = "locomo_real_5q_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'total_questions': len(LOCOMO_QUESTIONS),
            'keyword_matches': correct,
            'results': results
        }, f, ensure_ascii=False, indent=2)

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    accuracy = correct / len(LOCOMO_QUESTIONS) * 100
    print(f"问题总数: {len(LOCOMO_QUESTIONS)}")
    print(f"关键词匹配: {correct}/{len(LOCOMO_QUESTIONS)} ({accuracy:.1f}%)")
    print(f"结果已保存: {output_file}")

    if accuracy >= 80:
        print(f"\n🎉 测试通过！准确率 {accuracy:.1f}% >= 80%")
        return 0
    else:
        print(f"\n⚠️  准确率较低: {accuracy:.1f}%")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
