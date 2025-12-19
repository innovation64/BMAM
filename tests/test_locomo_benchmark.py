#!/usr/bin/env python3
"""
LoCoMo Benchmark - 完整测试套件

测试配置:
- 1组5问:   python3 tests/test_locomo_benchmark.py --samples 1 --questions 5
- 1组20问:  python3 tests/test_locomo_benchmark.py --samples 1 --questions 20
- 1组199问: python3 tests/test_locomo_benchmark.py --samples 1 --questions 199
- 10组全部: python3 tests/test_locomo_benchmark.py --samples 10 --questions 199

Author: Claude Code
Date: 2025-11-11
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.paths import BMAMPaths


# Use centralized path management instead of hardcoded path
LOCOMO_DATA_PATH = BMAMPaths.LOCOMO_DATASET


def load_locomo_data():
    """加载所有 LoCoMo 数据"""
    with open(LOCOMO_DATA_PATH, 'r') as f:
        data = json.load(f)
    print(f"✓ Loaded {len(data)} LoCoMo samples")
    return data


async def ingest_conversation(coordinator, sample, verbose=False):
    """喂入单个样本的完整对话"""
    conversation = sample['conversation']
    total_turns = 0
    session_num = 1

    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_dialogues = conversation.get(session_key, [])

        if not session_dialogues:
            session_num += 1
            continue

        if verbose:
            session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
            print(f"  Session {session_num} ({session_date}): {len(session_dialogues)} turns")

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                await coordinator.process_input(f"{speaker}: {text}")
                total_turns += 1

        session_num += 1

    return total_turns


async def test_qa(coordinator, qa_pairs, verbose=False):
    """测试 QA 对"""
    results = []
    correct_count = 0

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        expected_answer = qa['answer']

        if verbose:
            print(f"  [{i}/{len(qa_pairs)}] Q: {question[:60]}...")

        # 生成回答
        result = await coordinator.process_user_input(question)
        actual_answer = result.response if hasattr(result, 'response') else str(result)

        # 判断正确性(简单包含检查)
        is_correct = expected_answer.lower() in actual_answer.lower()

        if is_correct:
            correct_count += 1

        if verbose:
            status = "✅" if is_correct else "❌"
            print(f"      {status} Expected: {expected_answer}, Got: {actual_answer[:50]}...")

        results.append({
            'question': question,
            'expected': expected_answer,
            'actual': actual_answer,
            'correct': is_correct
        })

    accuracy = (correct_count / len(qa_pairs)) * 100 if qa_pairs else 0
    return accuracy, correct_count, results


async def test_single_sample(sample_idx, sample, num_questions, verbose=True):
    """测试单个样本"""
    sample_id = sample['sample_id']

    if verbose:
        print(f"\n{'='*80}")
        print(f"Testing Sample {sample_idx+1}: {sample_id}")
        print(f"{'='*80}")

    # Phase 1: 喂入对话
    if verbose:
        print(f"\n[Phase 1] Ingesting conversation...")

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    total_turns = await ingest_conversation(coordinator, sample, verbose=verbose)

    if verbose:
        print(f"✓ Ingested {total_turns} turns")

    # 等待巩固
    await asyncio.sleep(3)

    # Phase 2: QA 测试
    if verbose:
        print(f"\n[Phase 2] Testing {num_questions} QA pairs...")

    # 新建 coordinator (Fresh)
    coordinator2 = BrainInspiredCoordinator()
    await coordinator2.initialize()

    qa_pairs = sample['qa'][:num_questions]
    accuracy, correct_count, results = await test_qa(coordinator2, qa_pairs, verbose=verbose)

    if verbose:
        print(f"\n✓ Results: {correct_count}/{num_questions} correct ({accuracy:.1f}%)")

    return {
        'sample_id': sample_id,
        'total_turns': total_turns,
        'num_questions': num_questions,
        'correct_count': correct_count,
        'accuracy': accuracy,
        'results': results
    }


async def main():
    parser = argparse.ArgumentParser(description='LoCoMo Benchmark Testing')
    parser.add_argument('--samples', type=int, default=1, help='Number of samples to test (1-10)')
    parser.add_argument('--questions', type=int, default=20, help='Number of questions per sample (1-199)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    num_samples = min(max(1, args.samples), 10)
    num_questions = min(max(1, args.questions), 199)

    print("\n" + "="*80)
    print("LoCoMo Benchmark Test")
    print("="*80)
    print(f"Configuration:")
    print(f"  - Samples: {num_samples}")
    print(f"  - Questions per sample: {num_questions}")
    print(f"  - Total QA tests: {num_samples * num_questions}")
    print("="*80)

    # 加载数据
    all_data = load_locomo_data()

    # 测试每个样本
    all_results = []
    total_correct = 0
    total_questions = 0

    start_time = datetime.now()

    for i in range(num_samples):
        sample = all_data[i]

        result = await test_single_sample(i, sample, num_questions, verbose=args.verbose)

        all_results.append(result)
        total_correct += result['correct_count']
        total_questions += result['num_questions']

        print(f"\nSample {i+1}/{num_samples} - {result['sample_id']}: {result['accuracy']:.1f}% ({result['correct_count']}/{result['num_questions']})")

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # 计算总体准确率
    overall_accuracy = (total_correct / total_questions) * 100 if total_questions > 0 else 0

    # 最终报告
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Samples tested: {num_samples}")
    print(f"Total questions: {total_questions}")
    print(f"Total correct: {total_correct}")
    print(f"Overall accuracy: {overall_accuracy:.1f}%")
    print(f"Time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("="*80)

    # 保存结果
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_benchmark'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    result_file = metrics_dir / f'results_{num_samples}samples_{num_questions}q_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    final_results = {
        'config': {
            'num_samples': num_samples,
            'num_questions': num_questions,
            'total_qa': total_questions
        },
        'summary': {
            'total_correct': total_correct,
            'total_questions': total_questions,
            'overall_accuracy': overall_accuracy,
            'elapsed_seconds': elapsed
        },
        'per_sample_results': all_results,
        'timestamp': datetime.now().isoformat()
    }

    with open(result_file, 'w') as f:
        json.dump(final_results, f, indent=2)

    print(f"\n✓ Results saved to: {result_file}")

    # 返回状态码
    threshold = 50.0
    if overall_accuracy >= threshold:
        print(f"\n✅ BENCHMARK PASSED (accuracy ≥ {threshold}%)")
        sys.exit(0)
    else:
        print(f"\n⚠️  Accuracy below threshold ({overall_accuracy:.1f}% < {threshold}%)")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
