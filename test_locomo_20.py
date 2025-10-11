"""
LoCoMo 20题测试 - 使用官方数据集的前20个问题
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
    print("🧪 LoCoMo 20-Question Test")
    print("=" * 80)

    # 加载官方数据集
    dataset_path = Path('/Users/liyang/Desktop/testversion/BMAM/data/benchmarks/locomo/locomo10.json')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample = data[0]
    conversation = sample['conversation']
    qa_list = sample['qa'][:20]  # 取前20个问题

    print(f"\n📁 Dataset: {dataset_path.name}")
    print(f"📋 Sample: {sample['sample_id']}")
    print(f"👤 Speakers: {conversation['speaker_a']} <-> {conversation['speaker_b']}")
    print(f"❓ Questions: {len(qa_list)}")

    coordinator = BrainInspiredCoordinator()
    judge = LoCoMoLLMJudge()

    # Phase 1: 学习所有sessions
    print("\n📚 Phase 1: Learning All Sessions")
    print("-" * 80)

    total_turns = 0
    session_num = 1

    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation.get(session_key, [])

        if not session_dialogues:
            session_num += 1
            continue

        print(f"  📅 Session {session_num} ({session_date}): {len(session_dialogues)} turns", end='', flush=True)

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')

            if not text:
                continue

            context_text = f"On {session_date}, {speaker} said: '{text}'"
            await coordinator.process_user_input(context_text)
            total_turns += 1

        print(" ✓")
        session_num += 1

    print(f"\n✅ Stored {total_turns} conversation turns from {session_num-1} sessions\n")

    # Phase 2: 测试20个问题
    print("❓ Phase 2: Testing 20 Questions")
    print("-" * 80)

    results = []
    start_all = datetime.now()

    for i, qa in enumerate(qa_list, 1):
        question = qa['question']
        gold_answer = str(qa['answer'])

        print(f"\n{i:2d}. {question[:70]}")
        print(f"    📌 Gold: {gold_answer[:60]}")

        try:
            start = datetime.now()
            result = await coordinator.process_user_input(question)
            elapsed = (datetime.now() - start).total_seconds()

            answer = result.response
            memories = len(result.memories_retrieved) if result.memories_retrieved else 0

            # LLM Judge评估
            judgment = await judge.judge_answer(question, gold_answer, answer)
            is_correct = judgment['correct']

            # 字符串匹配对比
            string_match = gold_answer.lower() in answer.lower()

            print(f"    🤖 {answer[:70]}...")
            print(f"    {'✅' if is_correct else '❌'} LLM Judge: {judgment['label']} | ⏱️  {elapsed:.1f}s | 💾 {memories}")

            if is_correct != string_match:
                print(f"    ⚠️  LLM disagrees with string (String: {'✅' if string_match else '❌'})")

            results.append({
                'id': i,
                'question': question,
                'gold': gold_answer,
                'answer': answer,
                'llm_correct': is_correct,
                'string_correct': string_match,
                'time': elapsed,
                'memories': memories,
                'reasoning': judgment['reasoning']
            })

        except Exception as e:
            print(f"    ✗ Error: {e}")
            results.append({
                'id': i,
                'question': question,
                'gold': gold_answer,
                'llm_correct': False,
                'string_correct': False,
                'time': 0,
                'memories': 0,
                'error': str(e)
            })

    total_time = (datetime.now() - start_all).total_seconds()

    # 统计结果
    print("\n" + "=" * 80)
    print("📊 Results Summary")
    print("=" * 80)

    total = len(results)
    llm_correct = sum(1 for r in results if r['llm_correct'])
    string_correct = sum(1 for r in results if r['string_correct'])

    llm_accuracy = (llm_correct / total * 100) if total > 0 else 0
    string_accuracy = (string_correct / total * 100) if total > 0 else 0

    print(f"\n✅ LLM Judge Accuracy: {llm_correct}/{total} = {llm_accuracy:.1f}%")
    print(f"📊 String Match Accuracy: {string_correct}/{total} = {string_accuracy:.1f}%")
    print(f"📈 Difference: {llm_accuracy - string_accuracy:+.1f}%")

    avg_time = sum(r['time'] for r in results) / total if total > 0 else 0
    avg_mem = sum(r['memories'] for r in results) / total if total > 0 else 0

    print(f"\n⏱️  Total Time: {total_time/60:.1f} min")
    print(f"⏱️  Avg Time per Question: {avg_time:.1f}s")
    print(f"💾 Avg Memories Retrieved: {avg_mem:.1f}")

    # 分歧案例
    disagreements = [r for r in results if r['llm_correct'] != r['string_correct']]
    if disagreements:
        print(f"\n⚠️  LLM vs String Disagreements: {len(disagreements)} cases")
        for r in disagreements[:3]:
            print(f"\n  Q{r['id']}: {r['question'][:50]}...")
            print(f"    Gold: {r['gold'][:40]}")
            print(f"    Answer: {r['answer'][:60]}...")
            print(f"    LLM: {'✅' if r['llm_correct'] else '❌'} | String: {'✅' if r['string_correct'] else '❌'}")

    # 详细结果
    print(f"\n{'='*80}")
    print("Detailed Results:")
    print(f"{'='*80}")
    for r in results:
        icon = '✅' if r['llm_correct'] else '❌'
        disagree = '⚠️' if r['llm_correct'] != r['string_correct'] else '  '
        print(f"{icon} {disagree} Q{r['id']:2d}: {r['time']:.1f}s | {r['memories']:2d} mems")

    print("\n" + "=" * 80)

    # 保存结果
    output_file = f"results/locomo_20q_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'sample_id': sample['sample_id'],
            'num_questions': total,
            'llm_accuracy': llm_accuracy,
            'string_accuracy': string_accuracy,
            'total_time_seconds': total_time,
            'results': results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    await coordinator.stop_system()

    print(f"\n🎯 Final LLM Judge Accuracy: {llm_accuracy:.1f}%\n")

    return llm_accuracy


if __name__ == "__main__":
    accuracy = asyncio.run(main())
