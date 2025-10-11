"""
简化的LoCoMo测试 - 直接测试核心功能
"""

import asyncio
import json
import sys
from datetime import datetime

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from evaluation.llm_judge_locomo import LoCoMoLLMJudge


# 简化的测试数据（从locomo10.json提取）
SESSIONS = [
    "On 8 May 2023, Caroline said: 'I went to a LGBTQ support group yesterday and it was so powerful.'",
    "On 8 May 2023, Caroline said: 'The transgender stories were so inspiring!'",
    "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
]

QUESTIONS = [
    {
        'question': 'When did Caroline go to the LGBTQ support group?',
        'answer': '7 May 2023',
        'id': 'Q1'
    },
    {
        'question': "What is Caroline's identity?",
        'answer': 'transgender woman',
        'id': 'Q2'
    },
    {
        'question': 'What did Caroline research?',
        'answer': 'adoption agencies',
        'id': 'Q3'
    },
    {
        'question': 'What community did Caroline engage with?',
        'answer': 'LGBTQ community',
        'id': 'Q4'
    },
    {
        'question': 'What fields would Caroline pursue?',
        'answer': 'psychology',
        'id': 'Q5'
    }
]


async def main():
    print("=" * 80)
    print("🧪 LoCoMo Simple Test (5 Questions)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    judge = LoCoMoLLMJudge()

    # Phase 1: 学习
    print("\n📚 Phase 1: Learning Sessions")
    for i, session in enumerate(SESSIONS, 1):
        print(f"  {i}. {session[:60]}...")
        try:
            result = await coordinator.process_user_input(session)
            print(f"     ✓ Stored")
        except Exception as e:
            print(f"     ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return

    print("\n✅ Learning complete\n")

    # Phase 2: 测试
    print("❓ Phase 2: Testing Questions")
    print("-" * 80)

    results = []

    for i, qa in enumerate(QUESTIONS, 1):
        print(f"\n{qa['id']}: {qa['question']}")
        print(f"  📌 Gold: {qa['answer']}")

        try:
            start = datetime.now()
            result = await coordinator.process_user_input(qa['question'])
            elapsed = (datetime.now() - start).total_seconds()

            answer = result.response
            memories = len(result.memories_retrieved) if result.memories_retrieved else 0

            print(f"  🤖 Answer: {answer[:80]}..." if len(answer) > 80 else f"  🤖 Answer: {answer}")
            print(f"  ⏱️  {elapsed:.2f}s | 💾 {memories} memories")

            # LLM Judge
            judgment = await judge.judge_answer(qa['question'], qa['answer'], answer)
            is_correct = judgment['correct']

            print(f"  {'✅' if is_correct else '❌'} LLM Judge: {judgment['label']}")

            results.append({
                'id': qa['id'],
                'correct': is_correct,
                'time': elapsed,
                'memories': memories
            })

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'id': qa['id'],
                'correct': False,
                'time': 0,
                'memories': 0,
                'error': str(e)
            })

    # 统计
    print("\n" + "=" * 80)
    print("📊 Results Summary")
    print("=" * 80)

    correct = sum(1 for r in results if r['correct'])
    total = len(results)
    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"\n✅ Accuracy: {correct}/{total} = {accuracy:.1f}%")

    avg_time = sum(r['time'] for r in results) / total if total > 0 else 0
    avg_mem = sum(r['memories'] for r in results) / total if total > 0 else 0

    print(f"⏱️  Avg Time: {avg_time:.2f}s")
    print(f"💾 Avg Memories: {avg_mem:.1f}")

    print("\n详细结果:")
    for r in results:
        icon = '✅' if r['correct'] else '❌'
        print(f"  {icon} {r['id']}: {r['time']:.1f}s, {r['memories']} mems")

    print("\n" + "=" * 80)

    await coordinator.stop_system()

    return accuracy


if __name__ == "__main__":
    accuracy = asyncio.run(main())
    print(f"\n🎯 Final Accuracy: {accuracy:.1f}%\n")
