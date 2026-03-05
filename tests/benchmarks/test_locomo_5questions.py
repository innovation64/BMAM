"""
LoCoMo 5问题测试 - 验证BrainNetwork混合检索
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Use relative path instead of hardcoded absolute path
_BMAM_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(_BMAM_ROOT))
os.environ['USE_BRAIN_NETWORK'] = 'true'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


# LoCoMo数据集样本 (完整5个问题)
# 注意: Session日期是8 May,但Caroline说"yesterday"去的support group,所以实际是7 May
# 基于LoCoMo官方数据集的D1:3, D1:5, D2:8等对话
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
    ("When did Caroline go to the LGBTQ support group?", "7 May 2023"),  # Session是8 May,她说yesterday
    ("What did Caroline research?", "adoption agencies"),
    ("What is Caroline's identity?", "transgender woman"),
    ("What fields would Caroline be likely to pursue in her education?", "social work / psychology"),
    ("What community did Caroline engage with?", "LGBTQ community")
]


async def main():
    print("=" * 80)
    print("🧪 LoCoMo 5-Question Test with BrainNetwork")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Phase 1: 学习sessions
    print("\n📚 Phase 1: Learning Sessions")
    print("-" * 80)

    for session_idx, session in enumerate(LOCOMO_SESSIONS, 1):
        print(f"\n📅 Session {session_idx} ({session['date']}):")
        for event_idx, event in enumerate(session['events'], 1):
            print(f"  {event_idx}. {event[:70]}...")
            result = await coordinator.process_user_input(event)
            # 不打印响应,加快速度

    print("\n✅ Learning complete")

    # Phase 2: 测试5个问题
    print("\n❓ Phase 2: Testing 5 Questions")
    print("-" * 80)

    results = []
    for i, (question, expected_answer) in enumerate(LOCOMO_QUESTIONS, 1):
        print(f"\n  Q{i}: {question}")
        print(f"  📌 Expected: {expected_answer}")

        start_time = datetime.now()
        result = await coordinator.process_user_input(question)
        elapsed = (datetime.now() - start_time).total_seconds()

        answer = result.response
        print(f"  🤖 Got: {answer[:100]}...")
        print(f"  ⏱️  Time: {elapsed:.2f}s")
        print(f"  💾 Memories: {len(result.memories_retrieved)}")

        # 简单判断正确性
        correct = expected_answer.lower() in answer.lower()
        results.append({
            'question': question,
            'expected': expected_answer,
            'got': answer,
            'correct': correct,
            'time': elapsed,
            'memories': len(result.memories_retrieved)
        })

        print(f"  {'✅' if correct else '❌'} {('CORRECT' if correct else 'WRONG')}")

    # 统计结果
    print("\n" + "=" * 80)
    print("📊 Test Summary")
    print("=" * 80)

    correct_count = sum(1 for r in results if r['correct'])
    total_count = len(results)
    accuracy = correct_count / total_count * 100

    print(f"\n✅ Correct: {correct_count}/{total_count}")
    print(f"📈 Accuracy: {accuracy:.1f}%")
    print(f"⏱️  Avg Time: {sum(r['time'] for r in results) / len(results):.2f}s")
    print(f"💾 Avg Memories: {sum(r['memories'] for r in results) / len(results):.1f}")

    print("\n详细结果:")
    for i, r in enumerate(results, 1):
        status = '✅' if r['correct'] else '❌'
        print(f"  {status} Q{i}: {r['question'][:40]}... ({r['time']:.1f}s, {r['memories']} mems)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
