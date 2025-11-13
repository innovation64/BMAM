#!/usr/bin/env python3
"""
LoCoMo BMAM Full Benchmark - 完整记忆框架测试
使用LLM Judge评分,适配BMAM记忆框架特性

测试配置:
- 1组前5问:   python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
- 1组前20问:  python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20 --verbose
- 1组全部:    python3 tests/test_locomo_bmam_full.py --samples 1 --questions all --verbose
- 10组全部:   python3 tests/test_locomo_bmam_full.py --samples 10 --questions all

快速测试 (跳过录入,复用已有记忆):
- 跳过录入:   python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 5 --verbose
- 测试更多:   python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --verbose
- 测试全部:   python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all --verbose

特性:
- 每组问题数量不固定(自动检测)
- LLM Judge 评分 (参考MemOS标准)
- 记录完整metrics (包括时间/tokens/记忆检索等)
- 适配BMAM记忆框架(非RAG)

Author: Claude Code
Date: 2025-11-11
"""

import asyncio
import json
import os
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# OpenAI client for LLM Judge
try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE_AVAILABLE = True
except ImportError:
    print("⚠️  OpenAI not available, will use simple string matching")
    LLM_JUDGE_AVAILABLE = False


LOCOMO_DATA_PATH = '/Users/liyang/Desktop/testversion/archived/MemOS/evaluation/data/locomo/locomo10.json'


def load_locomo_data():
    """加载所有 LoCoMo 数据"""
    with open(LOCOMO_DATA_PATH, 'r') as f:
        data = json.load(f)

    # 统计每组的问题数量
    qa_counts = [len(sample['qa']) for sample in data]
    print(f"✓ Loaded {len(data)} LoCoMo samples")
    print(f"  QA counts per sample: min={min(qa_counts)}, max={max(qa_counts)}, avg={sum(qa_counts)/len(qa_counts):.1f}")

    return data


async def llm_judge_grader(client, question: str, gold_answer: str, generated_answer: str) -> Dict[str, Any]:
    """
    LLM Judge 评分器 (参考MemOS标准)
    返回: {judgment: bool, reasoning: str}
    """
    system_prompt = """You are an expert grader that determines if answers to questions match a gold standard answer"""

    accuracy_prompt = f"""
Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given:
    (1) a question (posed by one user to another user),
    (2) a 'gold' (ground truth) answer,
    (3) a generated answer from a memory system

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer. The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might use relative time references (like "last Tuesday" or "next month"), but you should be generous - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response.

Return a JSON with two keys: "label" (CORRECT or WRONG) and "reasoning" (one sentence).
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": accuracy_prompt},
            ],
            temperature=0,
        )

        message_content = response.choices[0].message.content
        result = json.loads(message_content)

        judgment = result.get("label", "WRONG").strip().upper() == "CORRECT"
        reasoning = result.get("reasoning", "No reasoning provided")

        return {"judgment": judgment, "reasoning": reasoning}

    except Exception as e:
        print(f"    ⚠️  LLM Judge error: {e}")
        # Fallback to simple matching
        judgment = str(gold_answer).lower() in str(generated_answer).lower()
        return {"judgment": judgment, "reasoning": f"Fallback matching (error: {str(e)})"}


async def simple_judge(question: str, gold_answer: str, generated_answer: str) -> Dict[str, Any]:
    """简单判断器 (当LLM Judge不可用时)"""
    judgment = str(gold_answer).lower() in str(generated_answer).lower()
    return {
        "judgment": judgment,
        "reasoning": "Simple substring matching (LLM Judge not available)"
    }


async def ingest_conversation(coordinator: BrainInspiredCoordinator, sample: Dict, verbose: bool = False) -> Dict[str, Any]:
    """
    喂入单个样本的完整对话 (Session边界并发优化)

    优化策略:
    - Session间串行 (保留时间顺序)
    - Session内并发 (加速处理)
    - 预期提升: 3-4倍速度

    返回: {total_turns, sessions, duration_sec, throughput}
    """
    conversation = sample['conversation']
    total_turns = 0
    session_num = 1

    start_time = time.time()

    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_dialogues = conversation.get(session_key, [])

        if not session_dialogues:
            session_num += 1
            continue

        if verbose:
            session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
            print(f"  Session {session_num} ({session_date}): {len(session_dialogues)} turns", end='')

        # 🚀 Session内并发处理 (保留session边界)
        session_start = time.time()
        tasks = []
        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                task = coordinator.process_input(f"{speaker}: {text}")
                tasks.append(task)

        # 等待当前session完成
        await asyncio.gather(*tasks)
        session_duration = time.time() - session_start
        total_turns += len(tasks)

        if verbose:
            print(f" → {session_duration:.1f}s ({len(tasks)/session_duration:.1f} turns/sec)")

        session_num += 1

    duration_sec = time.time() - start_time
    throughput = total_turns / duration_sec if duration_sec > 0 else 0

    return {
        'total_turns': total_turns,
        'sessions': session_num - 1,
        'duration_sec': duration_sec,
        'throughput': throughput
    }


async def test_qa_with_llm_judge(
    coordinator: BrainInspiredCoordinator,
    qa_pairs: List[Dict],
    llm_client,
    verbose: bool = False,
    num_judge_runs: int = 1
) -> Dict[str, Any]:
    """
    测试 QA 对,使用 LLM Judge 评分

    Args:
        num_judge_runs: LLM Judge运行次数 (MemOS默认3次)

    Returns:
        {
            'results': [...],
            'correct_count': int,
            'total_questions': int,
            'accuracy': float,
            'llm_judge_scores': [float, ...],  # 每次运行的准确率
            'total_duration_sec': float
        }
    """
    results = []
    start_time = time.time()

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        gold_answer = qa['answer']
        category = qa.get('category', 0)

        if verbose:
            print(f"  [{i}/{len(qa_pairs)}] Q: {question[:60]}...")

        # 生成回答
        qa_start = time.time()
        result = await coordinator.process_user_input(question)
        qa_duration = time.time() - qa_start

        generated_answer = result.response if hasattr(result, 'response') else str(result)

        # 记录检索到的记忆数量
        memories_retrieved = 0
        if hasattr(coordinator, 'memory_coordinator'):
            try:
                memories = await coordinator.memory_coordinator.smart_retrieve(
                    query=question,
                    top_k=5
                )
                memories_retrieved = len(memories)
            except Exception as e:
                if verbose:
                    print(f"    ⚠️  Memory retrieval failed: {e}")

        # LLM Judge 评分 (多次运行)
        judgments = []
        reasonings = []

        for run_idx in range(num_judge_runs):
            if LLM_JUDGE_AVAILABLE and llm_client:
                judge_result = await llm_judge_grader(llm_client, question, gold_answer, generated_answer)
            else:
                judge_result = await simple_judge(question, gold_answer, generated_answer)

            judgments.append(judge_result['judgment'])
            reasonings.append(judge_result['reasoning'])

        # 记录结果
        qa_result = {
            'question': question,
            'gold_answer': gold_answer,
            'generated_answer': generated_answer,
            'category': category,
            'judgments': judgments,  # List of bools
            'reasonings': reasonings,  # List of strings
            'memories_retrieved': memories_retrieved,
            'response_duration_ms': qa_duration * 1000,
            'answer_length': len(generated_answer)
        }

        results.append(qa_result)

        if verbose:
            majority_correct = sum(judgments) > len(judgments) / 2
            status = "✅" if majority_correct else "❌"
            print(f"    {status} Judgments: {sum(judgments)}/{len(judgments)} CORRECT")
            print(f"    Expected: {gold_answer}")
            print(f"    Got: {generated_answer[:100]}...")

    total_duration = time.time() - start_time

    # 计算每次运行的准确率
    llm_judge_scores = []
    for run_idx in range(num_judge_runs):
        correct = sum(1 for r in results if r['judgments'][run_idx])
        accuracy = correct / len(results) if results else 0.0
        llm_judge_scores.append(accuracy)

    # 整体统计 (使用多数投票)
    correct_count = sum(1 for r in results if sum(r['judgments']) > len(r['judgments']) / 2)
    accuracy = correct_count / len(results) if results else 0.0

    return {
        'results': results,
        'correct_count': correct_count,
        'total_questions': len(results),
        'accuracy': accuracy,
        'llm_judge_scores': llm_judge_scores,
        'total_duration_sec': total_duration
    }


async def test_single_sample(
    sample_idx: int,
    sample: Dict,
    num_questions: int,  # 'all' or int
    llm_client,
    verbose: bool = True,
    num_judge_runs: int = 1,
    skip_ingestion: bool = False
) -> Dict[str, Any]:
    """测试单个样本"""
    sample_id = sample['sample_id']

    # 确定要测试的问题数量
    total_qa_available = len(sample['qa'])
    if num_questions == 'all':
        actual_num_questions = total_qa_available
    else:
        actual_num_questions = min(num_questions, total_qa_available)

    if verbose:
        print(f"\n{'='*80}")
        print(f"Testing Sample {sample_idx+1}: {sample_id}")
        print(f"  QA pairs: {actual_num_questions}/{total_qa_available}")
        print(f"{'='*80}")

    # Phase 1: 喂入对话 (可跳过)
    if skip_ingestion:
        if verbose:
            print(f"\n⏭️  [Phase 1] Skipped ingestion, using existing memory")
        ingest_metrics = {
            'total_turns': 0,
            'sessions': 0,
            'duration_sec': 0.0,
            'throughput': 0.0,
            'skipped': True
        }
    else:
        if verbose:
            print(f"\n[Phase 1] Ingesting conversation...")

        coordinator1 = BrainInspiredCoordinator()
        await coordinator1.initialize()

        ingest_metrics = await ingest_conversation(coordinator1, sample, verbose=verbose)

        if verbose:
            print(f"✓ Ingested {ingest_metrics['total_turns']} turns in {ingest_metrics['duration_sec']:.1f}s "
                  f"({ingest_metrics['throughput']:.1f} turns/sec)")

        # 等待巩固
        consolidation_wait = 3
        if verbose:
            print(f"\n⏳ Waiting {consolidation_wait}s for consolidation...")
        await asyncio.sleep(consolidation_wait)

    # Phase 2: QA 测试 (新coordinator模拟fresh start)
    if verbose:
        print(f"\n[Phase 2] Testing {actual_num_questions} QA pairs with LLM Judge...")

    coordinator2 = BrainInspiredCoordinator()
    await coordinator2.initialize()

    qa_pairs = sample['qa'][:actual_num_questions]
    qa_metrics = await test_qa_with_llm_judge(
        coordinator2,
        qa_pairs,
        llm_client,
        verbose=verbose,
        num_judge_runs=num_judge_runs
    )

    if verbose:
        print(f"\n✓ Results: {qa_metrics['correct_count']}/{qa_metrics['total_questions']} correct ({qa_metrics['accuracy']*100:.1f}%)")
        if len(qa_metrics['llm_judge_scores']) > 1:
            import statistics
            mean_score = statistics.mean(qa_metrics['llm_judge_scores'])
            std_score = statistics.stdev(qa_metrics['llm_judge_scores']) if len(qa_metrics['llm_judge_scores']) > 1 else 0.0
            print(f"  LLM Judge: {mean_score:.4f} ± {std_score:.4f}")

    return {
        'sample_id': sample_id,
        'sample_idx': sample_idx,
        'ingest_metrics': ingest_metrics,
        'qa_metrics': qa_metrics,
        'num_questions_tested': actual_num_questions,
        'total_qa_available': total_qa_available
    }


async def main():
    parser = argparse.ArgumentParser(description='LoCoMo BMAM Full Benchmark')
    parser.add_argument('--samples', type=int, default=1, help='Number of samples to test (1-10)')
    parser.add_argument('--questions', default=20, help='Number of questions per sample ("all" or int)')
    parser.add_argument('--judge-runs', type=int, default=3, help='Number of LLM Judge runs per question (default: 3)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--skip-ingestion', action='store_true', help='Skip conversation ingestion, use existing memory (saves ~120s)')

    args = parser.parse_args()

    num_samples = min(max(1, args.samples), 10)

    # 解析 questions 参数
    if str(args.questions).lower() == 'all':
        num_questions = 'all'
        questions_str = 'all'
    else:
        num_questions = int(args.questions)
        questions_str = str(num_questions)

    print("\n" + "="*80)
    print("LoCoMo BMAM Full Benchmark")
    print("="*80)
    print(f"Configuration:")
    print(f"  - Samples: {num_samples}")
    print(f"  - Questions per sample: {questions_str}")
    print(f"  - LLM Judge runs: {args.judge_runs}")
    print(f"  - Skip ingestion: {args.skip_ingestion}")
    print(f"  - LLM Judge available: {LLM_JUDGE_AVAILABLE}")
    print("="*80)

    # 初始化 LLM Judge client
    llm_client = None
    if LLM_JUDGE_AVAILABLE:
        try:
            llm_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL")
            )
            print("✓ LLM Judge initialized (gpt-4o-mini)")
        except Exception as e:
            print(f"⚠️  LLM Judge initialization failed: {e}")
            print("  Falling back to simple string matching")

    # 加载数据
    all_data = load_locomo_data()

    # 测试每个样本
    all_results = []
    total_correct = 0
    total_questions = 0
    all_llm_judge_scores = []

    start_time = datetime.now()

    for i in range(num_samples):
        sample = all_data[i]

        result = await test_single_sample(
            i,
            sample,
            num_questions,
            llm_client,
            verbose=args.verbose,
            num_judge_runs=args.judge_runs,
            skip_ingestion=args.skip_ingestion
        )

        all_results.append(result)
        total_correct += result['qa_metrics']['correct_count']
        total_questions += result['qa_metrics']['total_questions']
        all_llm_judge_scores.extend(result['qa_metrics']['llm_judge_scores'])

        print(f"\nSample {i+1}/{num_samples} - {result['sample_id']}: "
              f"{result['qa_metrics']['accuracy']*100:.1f}% "
              f"({result['qa_metrics']['correct_count']}/{result['qa_metrics']['total_questions']})")

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # 计算总体准确率和LLM Judge统计
    overall_accuracy = (total_correct / total_questions) if total_questions > 0 else 0.0

    if all_llm_judge_scores:
        import statistics
        llm_judge_mean = statistics.mean(all_llm_judge_scores)
        llm_judge_std = statistics.stdev(all_llm_judge_scores) if len(all_llm_judge_scores) > 1 else 0.0
    else:
        llm_judge_mean = 0.0
        llm_judge_std = 0.0

    # 最终报告
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Samples tested: {num_samples}")
    print(f"Total questions: {total_questions}")
    print(f"Total correct: {total_correct}")
    print(f"Overall accuracy: {overall_accuracy*100:.2f}%")
    print(f"LLM Judge score: {llm_judge_mean:.4f} ± {llm_judge_std:.4f}")
    print(f"Time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("="*80)

    # 按category统计
    category_stats = {}
    for result in all_results:
        for qa_result in result['qa_metrics']['results']:
            cat = qa_result['category']
            if cat not in category_stats:
                category_stats[cat] = {'correct': 0, 'total': 0}

            # 多数投票
            is_correct = sum(qa_result['judgments']) > len(qa_result['judgments']) / 2
            if is_correct:
                category_stats[cat]['correct'] += 1
            category_stats[cat]['total'] += 1

    print("\nCategory Breakdown:")
    category_names = {1: 'multi hop', 2: 'temporal reasoning', 3: 'open domain', 4: 'single hop'}
    for cat in sorted(category_stats.keys()):
        stats = category_stats[cat]
        acc = (stats['correct'] / stats['total']) if stats['total'] > 0 else 0.0
        cat_name = category_names.get(cat, f'category_{cat}')
        print(f"  {cat_name}: {acc*100:.1f}% ({stats['correct']}/{stats['total']})")

    # 保存结果
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_bmam_full'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = metrics_dir / f'results_{num_samples}samples_{questions_str}q_{timestamp}.json'

    final_results = {
        'config': {
            'num_samples': num_samples,
            'questions_per_sample': questions_str,
            'num_judge_runs': args.judge_runs,
            'llm_judge_available': LLM_JUDGE_AVAILABLE,
            'total_qa_tested': total_questions
        },
        'summary': {
            'total_correct': total_correct,
            'total_questions': total_questions,
            'overall_accuracy': overall_accuracy,
            'llm_judge_mean': llm_judge_mean,
            'llm_judge_std': llm_judge_std,
            'elapsed_seconds': elapsed,
            'category_stats': category_stats
        },
        'per_sample_results': all_results,
        'timestamp': datetime.now().isoformat(),
        'framework': 'BMAM'
    }

    with open(result_file, 'w') as f:
        json.dump(final_results, f, indent=2)

    print(f"\n✓ Results saved to: {result_file}")

    # 返回状态码
    threshold = 0.50  # 50%
    if overall_accuracy >= threshold:
        print(f"\n✅ BENCHMARK PASSED (accuracy ≥ {threshold*100:.0f}%)")
        sys.exit(0)
    else:
        print(f"\n⚠️  Accuracy below threshold ({overall_accuracy*100:.1f}% < {threshold*100:.0f}%)")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
