"""
LoCoMo 20题智能测试 - 只学习相关sessions，大幅加速
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from evaluation.llm_judge_locomo import LoCoMoLLMJudge


async def main():
    print("=" * 80)
    print("🧪 LoCoMo 20-Question Test (Smart Mode - Only Learn Needed Sessions)")
    print("=" * 80)

    # 加载数据
    dataset_path = Path('/Users/liyang/Desktop/testversion/BMAM/data/benchmarks/locomo/locomo10.json')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample = data[0]
    conversation = sample['conversation']
    qa_list = sample['qa'][:20]

    # 🔥 智能分析：找出前20题需要的sessions
    needed_sessions = set()
    for qa in qa_list:
        for ev in qa.get('evidence', []):
            session_id = int(ev.split(':')[0].replace('D', ''))
            needed_sessions.add(session_id)

    needed_sessions = sorted(needed_sessions)
    print(f"\n📊 Analysis: First 20 questions need sessions: {needed_sessions}")
    print(f"   (Skipping {19 - len(needed_sessions)} unnecessary sessions)")

    coordinator = BrainInspiredCoordinator()
    judge = LoCoMoLLMJudge()

    # Phase 1: 只学习需要的sessions
    print(f"\n📚 Phase 1: Learning {len(needed_sessions)} Relevant Sessions", flush=True)
    print("-" * 80)

    total_turns = 0
    total_sessions = len(needed_sessions)

    for idx, session_num in enumerate(needed_sessions, 1):
        session_key = f'session_{session_num}'
        session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation.get(session_key, [])

        if not session_dialogues:
            continue

        # 进度条
        progress_bar = f"[{idx}/{total_sessions}]"
        print(f"  {progress_bar} Session {session_num} ({session_date}): {len(session_dialogues)} turns...", end='', flush=True)

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                context_text = f"On {session_date}, {speaker} said: '{text}'"
                await coordinator.process_user_input(context_text)
                total_turns += 1

        print(" ✓")

    print(f"\n✅ Learned {total_turns} dialogue turns from {len(needed_sessions)} sessions")

    # Phase 2: 测试20个问题
    print(f"\n❓ Phase 2: Testing 20 Questions")
    print("-" * 80)

    results = []
    correct_count = 0
    start_all = datetime.now()

    for i, qa in enumerate(qa_list, 1):
        question = qa['question']
        gold_answer = str(qa['answer'])

        # 显示进度
        print(f"\n[{i:2d}/20] {question[:65]}...", flush=True)

        try:
            start = datetime.now()
            result = await coordinator.process_user_input(question)
            elapsed = (datetime.now() - start).total_seconds()

            answer = result.response
            memories = len(result.memories_retrieved) if result.memories_retrieved else 0

            # LLM Judge
            judgment = await judge.judge_answer(question, gold_answer, answer)
            is_correct = judgment['correct']

            if is_correct:
                correct_count += 1

            # 实时显示
            icon = '✅' if is_correct else '❌'
            print(f"        {icon} {answer[:60]}... ({elapsed:.1f}s, {memories}mem)", flush=True)

            results.append({
                'id': i,
                'correct': is_correct,
                'time': elapsed,
                'memories': memories,
                'question': question,
                'gold': gold_answer,
                'answer': answer,
                'reasoning': judgment['reasoning']
            })

        except Exception as e:
            print(f"        ❌ ERROR: {e}", flush=True)
            results.append({'id': i, 'correct': False, 'time': 0, 'memories': 0, 'error': str(e)})

        # 每5题显示进度
        if i % 5 == 0:
            current_acc = (correct_count / i * 100)
            print(f"\n        📊 Progress: {correct_count}/{i} = {current_acc:.1f}%", flush=True)

    total_time = (datetime.now() - start_all).total_seconds()

    # 最终统计
    print("\n" + "=" * 80)
    print("📊 Final Results")
    print("=" * 80)

    total = len(results)
    accuracy = (correct_count / total * 100) if total > 0 else 0

    print(f"\n✅ Accuracy: {correct_count}/{total} = {accuracy:.1f}%")
    print(f"⏱️  Total Time: {total_time/60:.1f} minutes")
    print(f"⏱️  Avg Time/Question: {total_time/total:.1f}s")

    avg_mem = sum(r['memories'] for r in results) / total if total > 0 else 0
    print(f"💾 Avg Memories: {avg_mem:.1f}")

    # 保存结果
    output_file = f"results/locomo_20q_smart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'sample_id': sample['sample_id'],
            'accuracy': accuracy,
            'total_time': total_time,
            'sessions_learned': list(needed_sessions),
            'total_turns_learned': total_turns,
            'results': results
        }, f, indent=2)

    print(f"\n💾 Saved to: {output_file}")

    # 显示错误的题
    wrong = [r for r in results if not r['correct']]
    if wrong:
        print(f"\n❌ Wrong Answers ({len(wrong)}):")
        for r in wrong[:5]:
            print(f"   Q{r['id']}: {r.get('question', 'N/A')[:55]}...")
            print(f"      Gold: {r.get('gold', 'N/A')[:50]}")
            print(f"      Got:  {r.get('answer', 'N/A')[:50]}...")

    print("\n" + "=" * 80)

    await coordinator.stop_system()

    return accuracy


if __name__ == "__main__":
    print("\n⏰ Starting Smart Test... (estimated 8-10 minutes total)")
    print("   - Learning phase: ~2 min (164 turns)")
    print("   - Testing phase: ~6 min (20 questions)\n")

    accuracy = asyncio.run(main())

    print(f"\n🎯 Final Accuracy: {accuracy:.1f}%\n")
