"""
LoCoMo Official Dataset Test - 使用LLM Judge评估
使用官方locomo10.json数据集，包含完整对话历史
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Use relative path instead of hardcoded absolute path
_BMAM_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(_BMAM_ROOT))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.paths import BMAMPaths
from evaluation.llm_judge_locomo import LoCoMoLLMJudge


def load_locomo_dataset(num_samples=None):
    """
    加载LoCoMo官方数据集

    Args:
        num_samples: 加载前N个样本（None表示全部）

    Returns:
        List of samples with conversation and QA pairs
    """
    # Use centralized path management instead of hardcoded path
    dataset_path = BMAMPaths.LOCOMO_DATASET

    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if num_samples:
        data = data[:num_samples]

    print(f"📁 Loaded {len(data)} LoCoMo samples from official dataset")
    return data


async def test_single_conversation(sample_id: str, conversation_dict: dict, qa_pairs: list, coordinator, judge):
    """
    测试单个对话样本

    Args:
        sample_id: 样本ID (e.g., "conv-26")
        conversation_dict: 对话字典,包含session_1, session_2等
        qa_pairs: QA问题列表 [{'question': ..., 'answer': ..., 'evidence': ...}, ...]
        coordinator: BrainCoordinator实例
        judge: LLM Judge实例

    Returns:
        测试结果统计
    """
    print(f"\n{'='*80}")
    print(f"📋 Testing Sample: {sample_id}")
    print(f"{'='*80}")

    speaker_a = conversation_dict.get('speaker_a', 'User')
    speaker_b = conversation_dict.get('speaker_b', 'Agent')

    print(f"👤 Speakers: {speaker_a} <-> {speaker_b}")

    # Phase 1: 学习所有session的对话历史
    print(f"\n📚 Phase 1: Learning All Sessions")
    print("-" * 80)

    total_turns = 0
    session_num = 1

    # 遍历所有session
    while f'session_{session_num}' in conversation_dict:
        session_key = f'session_{session_num}'
        session_date = conversation_dict.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation_dict[session_key]

        if not session_dialogues:
            session_num += 1
            continue

        print(f"\n  📅 Session {session_num} ({session_date}): {len(session_dialogues)} turns")

        # 处理每个对话turn
        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            dia_id = turn.get('dia_id', '')

            if not text:
                continue

            # 将对话送入记忆系统（模拟真实对话）
            # 为了更好地模拟真实对话，可以包含时间信息
            context_text = f"On {session_date}, {speaker} said: '{text}'"
            await coordinator.process_user_input(context_text)

            total_turns += 1

        session_num += 1

    print(f"\n✅ Learning complete: {total_turns} conversation turns from {session_num-1} sessions stored in memory")

    # Phase 2: 测试QA问题
    print(f"\n❓ Phase 2: Testing {len(qa_pairs)} Questions")
    print("-" * 80)

    results = []

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        gold_answer = qa['answer']
        evidence = qa.get('evidence', [])
        category = qa.get('category', 'unknown')

        print(f"\n  Q{i}: {question}")
        print(f"  📌 Gold Answer: {gold_answer}")
        print(f"  📚 Evidence: {evidence}")

        # 从记忆系统检索并回答
        start_time = datetime.now()
        result = await coordinator.process_user_input(question)
        elapsed = (datetime.now() - start_time).total_seconds()

        generated_answer = result.response
        memories_count = len(result.memories_retrieved) if result.memories_retrieved else 0

        print(f"  🤖 Generated: {generated_answer[:100]}...")
        print(f"  ⏱️  Time: {elapsed:.2f}s")
        print(f"  💾 Retrieved Memories: {memories_count}")

        # LLM Judge评估
        judgment = await judge.judge_answer(question, str(gold_answer), generated_answer)
        is_correct = judgment['correct']

        # 字符串匹配作为对比
        string_match = str(gold_answer).lower() in generated_answer.lower()

        print(f"  🤖 LLM Judge: {judgment['label']}")
        print(f"  💭 Reasoning: {judgment['reasoning'][:100]}...")
        print(f"  {'✅' if is_correct else '❌'} LLM Judge Result")

        if is_correct != string_match:
            print(f"  ⚠️  LLM Judge disagrees with string matching!")

        results.append({
            'question': question,
            'gold_answer': str(gold_answer),
            'generated_answer': generated_answer,
            'llm_correct': is_correct,
            'llm_reasoning': judgment['reasoning'],
            'string_match': string_match,
            'evidence': evidence,
            'category': category,
            'time': elapsed,
            'memories': memories_count
        })

    return results


async def main():
    """主测试流程"""

    print("=" * 80)
    print("🧪 LoCoMo Official Dataset Test with LLM Judge")
    print("=" * 80)
    print()

    # 配置
    NUM_SAMPLES = None  # None=全部10个, 或设置为1, 5, 10等

    # 加载数据集
    dataset = load_locomo_dataset(num_samples=NUM_SAMPLES)

    # 初始化
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    judge = LoCoMoLLMJudge()

    # 测试每个样本
    all_results = []

    for sample in dataset:
        sample_id = sample['sample_id']
        conversation = sample['conversation']
        qa_pairs = sample['qa']

        sample_results = await test_single_conversation(
            sample_id=sample_id,
            conversation=conversation,
            qa_pairs=qa_pairs,
            coordinator=coordinator,
            judge=judge
        )

        all_results.extend(sample_results)

        # 每个样本后停止coordinator并重新初始化（清空记忆）
        await coordinator.stop_system()
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()

    # 最终统计
    print("\n" + "=" * 80)
    print("📊 Final Summary - All Samples")
    print("=" * 80)

    total = len(all_results)
    llm_correct = sum(1 for r in all_results if r['llm_correct'])
    string_correct = sum(1 for r in all_results if r['string_match'])

    llm_accuracy = (llm_correct / total * 100) if total > 0 else 0
    string_accuracy = (string_correct / total * 100) if total > 0 else 0

    print(f"\n✅ LLM Judge Accuracy: {llm_correct}/{total} ({llm_accuracy:.1f}%)")
    print(f"📊 String Match Accuracy: {string_correct}/{total} ({string_accuracy:.1f}%)")
    print(f"📈 Accuracy Difference: {llm_accuracy - string_accuracy:+.1f}%")

    avg_time = sum(r['time'] for r in all_results) / total if total > 0 else 0
    avg_memories = sum(r['memories'] for r in all_results) / total if total > 0 else 0

    print(f"\n⏱️  Avg Response Time: {avg_time:.2f}s")
    print(f"💾 Avg Retrieved Memories: {avg_memories:.1f}")

    # 按category统计
    category_stats = {}
    for r in all_results:
        cat = r['category']
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'correct': 0}
        category_stats[cat]['total'] += 1
        if r['llm_correct']:
            category_stats[cat]['correct'] += 1

    print(f"\n📊 By Category:")
    for cat, stats in sorted(category_stats.items()):
        acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  Category {cat}: {stats['correct']}/{stats['total']} ({acc:.1f}%)")

    # 分歧案例分析
    disagreements = [r for r in all_results if r['llm_correct'] != r['string_match']]
    if disagreements:
        print(f"\n⚠️  LLM vs String Disagreements: {len(disagreements)} cases")
        for i, r in enumerate(disagreements[:3], 1):  # 只显示前3个
            print(f"\n  Case {i}:")
            print(f"    Q: {r['question']}")
            print(f"    Gold: {r['gold_answer']}")
            print(f"    Generated: {r['generated_answer'][:80]}...")
            print(f"    LLM: {'✅' if r['llm_correct'] else '❌'}, String: {'✅' if r['string_match'] else '❌'}")

    print("\n" + "=" * 80)

    # 保存详细结果
    output_file = f"results/locomo_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("results", exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'total_samples': len(dataset),
            'total_questions': total,
            'llm_accuracy': llm_accuracy,
            'string_accuracy': string_accuracy,
            'results': all_results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")

    await coordinator.stop_system()


if __name__ == "__main__":
    asyncio.run(main())
