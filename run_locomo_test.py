"""
LoCoMo测试运行脚本
支持选择测试5题或20题，使用LLM Judge评估
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from evaluation.llm_judge_locomo import LoCoMoLLMJudge


async def run_locomo_test(num_questions=5):
    """
    运行LoCoMo测试

    Args:
        num_questions: 测试问题数量 (5 或 20)
    """
    print("=" * 80)
    print(f"🧪 LoCoMo Test - {num_questions} Questions with LLM Judge")
    print("=" * 80)
    print()

    # 加载官方数据集
    dataset_path = Path('data/benchmarks/locomo/locomo10.json')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 使用第一个样本（conv-26: Caroline的故事）
    sample = data[0]
    sample_id = sample['sample_id']
    conversation = sample['conversation']
    all_qa = sample['qa']

    # 选择前N个问题
    qa_pairs = all_qa[:num_questions]

    print(f"📁 Dataset: {dataset_path.name}")
    print(f"📋 Sample: {sample_id}")
    print(f"👤 Speakers: {conversation['speaker_a']} <-> {conversation['speaker_b']}")
    print(f"❓ Testing: {len(qa_pairs)} questions")
    print()

    # 初始化
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    judge = LoCoMoLLMJudge()

    # Phase 1: 学习所有sessions
    print("📚 Phase 1: Learning Conversation Sessions")
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

        print(f"  📅 Session {session_num} ({session_date}): {len(session_dialogues)} turns", end='')

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')

            if not text:
                continue

            # 将对话送入记忆系统
            context_text = f"On {session_date}, {speaker} said: '{text}'"
            await coordinator.process_user_input(context_text)
            total_turns += 1

        print(" ✓")
        session_num += 1

    print(f"\n✅ Stored {total_turns} conversation turns from {session_num-1} sessions\n")

    # Phase 2: 测试问题
    print(f"❓ Phase 2: Testing {len(qa_pairs)} Questions")
    print("-" * 80)

    results = []

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        gold_answer = qa['answer']
        evidence = qa.get('evidence', [])

        print(f"\nQ{i}: {question}")
        print(f"  📌 Gold: {gold_answer}")

        # 从记忆系统检索并回答
        start_time = datetime.now()
        result = await coordinator.process_user_input(question)
        elapsed = (datetime.now() - start_time).total_seconds()

        answer = result.response
        memories = len(result.memories_retrieved) if result.memories_retrieved else 0

        # LLM Judge评估
        judgment = await judge.judge_answer(question, str(gold_answer), answer)
        is_correct = judgment['correct']

        # 字符串匹配对比
        string_match = str(gold_answer).lower() in answer.lower()

        print(f"  🤖 Answer: {answer[:80]}..." if len(answer) > 80 else f"  🤖 Answer: {answer}")
        print(f"  ⏱️  {elapsed:.2f}s | 💾 {memories} memories")
        print(f"  🤖 LLM Judge: {judgment['label']}")

        if is_correct != string_match:
            print(f"  ⚠️  LLM disagrees with string match (String: {'✅' if string_match else '❌'})")

        results.append({
            'question': question,
            'gold_answer': str(gold_answer),
            'generated_answer': answer,
            'llm_correct': is_correct,
            'string_match': string_match,
            'llm_reasoning': judgment['reasoning'],
            'evidence': evidence,
            'time': elapsed,
            'memories': memories
        })

    # 统计结果
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)

    total = len(results)
    llm_correct = sum(1 for r in results if r['llm_correct'])
    string_correct = sum(1 for r in results if r['string_match'])

    llm_accuracy = (llm_correct / total * 100) if total > 0 else 0
    string_accuracy = (string_correct / total * 100) if total > 0 else 0

    print(f"\n✅ LLM Judge Accuracy: {llm_correct}/{total} = {llm_accuracy:.1f}%")
    print(f"📊 String Match Accuracy: {string_correct}/{total} = {string_accuracy:.1f}%")
    print(f"📈 Difference: {llm_accuracy - string_accuracy:+.1f}%")

    avg_time = sum(r['time'] for r in results) / total
    avg_memories = sum(r['memories'] for r in results) / total

    print(f"\n⏱️  Avg Response Time: {avg_time:.2f}s")
    print(f"💾 Avg Retrieved Memories: {avg_memories:.1f}")

    # 详细结果
    print(f"\n{'='*80}")
    print("Detailed Results:")
    print(f"{'='*80}")

    for i, r in enumerate(results, 1):
        llm_icon = '✅' if r['llm_correct'] else '❌'
        string_icon = '✅' if r['string_match'] else '❌'
        disagree = '⚠️ ' if r['llm_correct'] != r['string_match'] else ''

        print(f"{llm_icon} Q{i}: {r['question'][:50]}...")
        print(f"   LLM: {llm_icon} | String: {string_icon} {disagree}| {r['time']:.1f}s | {r['memories']} mems")

        if r['llm_correct'] != r['string_match']:
            print(f"   💭 {r['llm_reasoning'][:100]}...")

    print("\n" + "=" * 80)

    # 保存结果
    output_file = f"results/locomo_{num_questions}q_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("results", exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'num_questions': num_questions,
            'sample_id': sample_id,
            'llm_accuracy': llm_accuracy,
            'string_accuracy': string_accuracy,
            'avg_time': avg_time,
            'avg_memories': avg_memories,
            'results': results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Results saved to: {output_file}\n")

    await coordinator.stop_system()

    return {
        'llm_accuracy': llm_accuracy,
        'string_accuracy': string_accuracy,
        'llm_correct': llm_correct,
        'total': total
    }


async def main():
    """运行5题和20题测试"""

    print("\n" + "🔬" * 40)
    print("LoCoMo Benchmark Test Suite")
    print("🔬" * 40 + "\n")

    # 测试5题
    print("\n📝 Test 1: 5 Questions")
    result_5 = await run_locomo_test(num_questions=5)

    print("\n" + "⏸️ " * 40)
    print("Waiting 5 seconds before next test...")
    print("⏸️ " * 40 + "\n")
    await asyncio.sleep(5)

    # 测试20题
    print("\n📝 Test 2: 20 Questions")
    result_20 = await run_locomo_test(num_questions=20)

    # 对比结果
    print("\n" + "=" * 80)
    print("📊 Comparison: 5 Questions vs 20 Questions")
    print("=" * 80)

    print(f"\n5 Questions:")
    print(f"  LLM Judge: {result_5['llm_correct']}/5 = {result_5['llm_accuracy']:.1f}%")
    print(f"  String Match: {result_5['string_accuracy']:.1f}%")

    print(f"\n20 Questions:")
    print(f"  LLM Judge: {result_20['llm_correct']}/20 = {result_20['llm_accuracy']:.1f}%")
    print(f"  String Match: {result_20['string_accuracy']:.1f}%")

    accuracy_drop = result_5['llm_accuracy'] - result_20['llm_accuracy']
    print(f"\nAccuracy Change: {accuracy_drop:+.1f}% (from 5q to 20q)")

    if accuracy_drop > 5:
        print("⚠️  Significant accuracy drop detected!")
    elif accuracy_drop < -5:
        print("✨ Accuracy improved with more questions!")
    else:
        print("✅ Accuracy remains stable")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 单独测试指定数量
        num = int(sys.argv[1])
        asyncio.run(run_locomo_test(num_questions=num))
    else:
        # 运行完整测试套件
        asyncio.run(main())
