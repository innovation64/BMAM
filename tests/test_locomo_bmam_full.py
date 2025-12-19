#!/usr/bin/env python3
"""
LoCoMo BMAM Full Benchmark - 简洁输出版本

使用:
  python3 tests/test_locomo_bmam_full.py --samples 1 --questions all
  python3 tests/test_locomo_bmam_full.py --samples 10 --questions all
  python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all

Author: Claude Code
Date: 2025-11-28
"""

import asyncio
import json
import os
import sys
import argparse
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

# 关闭所有冗余日志
import warnings
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss', 'sentence_transformers', 'transformers', 'huggingface_hub', 'filelock']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.paths import BMAMPaths

# OpenAI client for LLM Judge
try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE_AVAILABLE = True
except ImportError:
    LLM_JUDGE_AVAILABLE = False

# Use centralized path management
LOCOMO_DATA_PATH = BMAMPaths.LOCOMO_DATASET


def load_locomo_data():
    """加载 LoCoMo 数据"""
    with open(LOCOMO_DATA_PATH, 'r') as f:
        return json.load(f)


def parse_locomo_date(date_str: str) -> datetime:
    """
    动态解析各种日期格式 - 使用dateutil自动识别

    支持格式:
    - "8:56 pm on 20 July, 2023" (LoCoMo格式)
    - "2023-07-20 20:56:00" (ISO格式)
    - "July 20, 2023" (美式)
    - "20/07/2023" (欧式)
    - 等等...dateutil支持的所有格式
    """
    if not date_str:
        return datetime.now()

    try:
        from dateutil import parser as date_parser
        # fuzzy=True 允许忽略无法解析的部分(如 "on")
        return date_parser.parse(date_str, fuzzy=True)
    except Exception:
        pass

    # Fallback: 如果dateutil失败，返回当前时间
    return datetime.now()


def print_progress_bar(current, total, prefix='', suffix='', length=40, fill='█'):
    """打印进度条"""
    percent = f"{100 * current / total:.1f}" if total > 0 else "0"
    filled = int(length * current // total) if total > 0 else 0
    bar = fill * filled + '░' * (length - filled)
    print(f'\r{prefix} |{bar}| {current}/{total} ({percent}%) {suffix}', end='', flush=True)


async def llm_judge_grader(client, question: str, gold_answer: str, generated_answer: str) -> bool:
    """LLM Judge 评分器 - 返回是否正确"""
    system_prompt = "You are an expert grader that determines if answers match a gold standard answer"

    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}

Be generous: if the generated answer covers the same topic/meaning as gold answer, it's CORRECT.
For time questions: same date in different formats = CORRECT.

Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("label", "WRONG").strip().upper() == "CORRECT"
    except:
        # Fallback
        return str(gold_answer).lower() in str(generated_answer).lower()


async def ingest_conversation(coordinator, sample, sample_idx, num_samples) -> Dict:
    """喂入对话和观察 - 使用store_memory_with_timestamp存储记忆

    🔥 修复: 同时存储conversation和observation数据
    - conversation: 原始对话
    - observation: 结构化事件摘要 (关键事实)
    """
    from datetime import datetime

    conversation = sample['conversation']
    observation = sample.get('observation', {})  # 🔥 获取observation数据
    session_num = 1
    start_time = time.time()

    # 统计总sessions和turns，并获取日期信息
    sessions_data = []
    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_date_key = f'{session_key}_date_time'
        obs_key = f'{session_key}_observation'

        dialogues = conversation.get(session_key, [])
        session_date = conversation.get(session_date_key, '2024-01-01')  # fallback date
        session_obs = observation.get(obs_key, {})  # 🔥 获取session的observation

        sessions_data.append((dialogues, session_date, session_obs))
        session_num += 1

    total_sessions = len(sessions_data)
    total_turns_estimate = sum(len(s[0]) for s in sessions_data)
    total_obs_estimate = sum(sum(len(obs_list) for obs_list in s[2].values()) for s in sessions_data)

    print(f"\n[Sample {sample_idx+1}/{num_samples}] 记忆塑造: {total_sessions} sessions, ~{total_turns_estimate} turns, ~{total_obs_estimate} observations")

    processed_turns = 0
    processed_obs = 0
    for i, (session_dialogues, session_date, session_obs) in enumerate(sessions_data, 1):
        # 解析日期 - 支持LoCoMo格式 "8:56 pm on 20 July, 2023"
        timestamp = parse_locomo_date(session_date)

        # 并发存储记忆
        tasks = []

        # 🔥 1. 存储对话记忆
        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                content = f"{speaker}: {text}"
                task = coordinator.store_memory_with_timestamp(
                    content=content,
                    timestamp=timestamp,
                    speaker=speaker,
                    importance=0.6
                )
                tasks.append(task)

        # 🔥 2. 存储observation记忆 (结构化事件摘要)
        # observation格式: {speaker: [[obs_text, ref], ...]}
        obs_tasks = []
        for speaker, obs_list in session_obs.items():
            for obs_item in obs_list:
                if isinstance(obs_item, list) and len(obs_item) >= 1:
                    obs_text = obs_item[0]
                    # 🔥 Observation是关键事实，给予更高重要性
                    obs_content = f"[Event] {speaker}: {obs_text}"
                    task = coordinator.store_memory_with_timestamp(
                        content=obs_content,
                        timestamp=timestamp,
                        speaker=speaker,
                        importance=0.8  # 🔥 更高重要性
                    )
                    obs_tasks.append(task)

        # 并发执行所有任务
        await asyncio.gather(*tasks)
        await asyncio.gather(*obs_tasks)
        processed_turns += len(tasks)
        processed_obs += len(obs_tasks)

        # 更新进度
        print_progress_bar(
            i, total_sessions,
            prefix='  塑造进度',
            suffix=f'Session {i} ({len(tasks)} turns, {len(obs_tasks)} obs)'
        )

    duration = time.time() - start_time
    print(f"\n  ✓ 完成: {processed_turns} turns + {processed_obs} observations in {duration:.1f}s")

    return {'total_turns': processed_turns, 'total_obs': processed_obs, 'sessions': total_sessions, 'duration': duration}


async def test_qa(coordinator, qa_pairs, llm_client, sample_idx, num_samples) -> Dict:
    """QA测试 - 简洁输出"""
    total = len(qa_pairs)
    correct = 0
    results = []

    print(f"\n[Sample {sample_idx+1}/{num_samples}] QA测试: {total} questions")

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        gold = qa.get('answer', qa.get('expected_answer', ''))
        category = qa.get('category', 0)

        # 生成回答
        # 🔥 FIX: 禁止在QA阶段保存记忆，避免QA对话污染检索结果
        result = await coordinator.process_user_input(
            question,
            context={'skip_memory_store': True}  # 🔥 不保存QA对话到记忆
        )
        generated = result.response if hasattr(result, 'response') else str(result)

        # 评判
        if LLM_JUDGE_AVAILABLE and llm_client:
            is_correct = await llm_judge_grader(llm_client, question, gold, generated)
        else:
            is_correct = str(gold).lower() in str(generated).lower()

        if is_correct:
            correct += 1

        results.append({
            'question': question,
            'gold': gold,
            'generated': generated,
            'correct': is_correct,
            'category': category
        })

        # 实时显示
        acc = correct / i * 100
        mark = '✓' if is_correct else '✗'
        print_progress_bar(
            i, total,
            prefix='  QA进度',
            suffix=f'{mark} 累计精度: {acc:.1f}%'
        )

    accuracy = correct / total if total > 0 else 0
    print(f"\n  ✓ 结果: {correct}/{total} = {accuracy*100:.1f}%")

    return {'correct': correct, 'total': total, 'accuracy': accuracy, 'results': results}


async def test_single_sample(sample_idx, sample, num_questions, llm_client, num_samples, skip_ingestion=False) -> Dict:
    """测试单个样本 - 使用同一个coordinator保持记忆连续性"""
    sample_id = sample['sample_id']
    total_qa = len(sample['qa'])
    actual_questions = total_qa if num_questions == 'all' else min(num_questions, total_qa)

    # 创建单一coordinator实例
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Phase 1: 记忆塑造
    if skip_ingestion:
        print(f"\n[Sample {sample_idx+1}/{num_samples}] 跳过记忆塑造 (使用已有记忆)")
        ingest_metrics = {'total_turns': 0, 'sessions': 0, 'duration': 0, 'skipped': True}
    else:
        ingest_metrics = await ingest_conversation(coordinator, sample, sample_idx, num_samples)

        # 等待巩固
        print("  ⏳ 等待记忆巩固 (3s)...", end='', flush=True)
        await asyncio.sleep(3)
        print(" done")

    # Phase 2: QA测试 (使用同一个coordinator)
    qa_pairs = sample['qa'][:actual_questions]
    qa_metrics = await test_qa(coordinator, qa_pairs, llm_client, sample_idx, num_samples)

    return {
        'sample_id': sample_id,
        'ingest': ingest_metrics,
        'qa': qa_metrics,
        'questions_tested': actual_questions
    }


async def main():
    parser = argparse.ArgumentParser(description='LoCoMo BMAM Benchmark')
    parser.add_argument('--samples', type=int, default=1)
    parser.add_argument('--questions', default='all')
    parser.add_argument('--skip-ingestion', action='store_true')
    args = parser.parse_args()

    num_samples = min(max(1, args.samples), 10)
    num_questions = 'all' if str(args.questions).lower() == 'all' else int(args.questions)

    print("=" * 60)
    print(f"LoCoMo BMAM Benchmark")
    print(f"  Samples: {num_samples}, Questions: {num_questions}")
    print(f"  LLM Judge: {'✓' if LLM_JUDGE_AVAILABLE else '✗ (fallback)'}")
    print("=" * 60)

    # LLM Judge
    llm_client = None
    if LLM_JUDGE_AVAILABLE:
        try:
            llm_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL")
            )
        except:
            pass

    # 加载数据
    data = load_locomo_data()
    print(f"✓ Loaded {len(data)} samples")

    # 测试
    all_results = []
    total_correct = 0
    total_questions = 0
    start_time = datetime.now()

    for i in range(num_samples):
        result = await test_single_sample(
            i, data[i], num_questions, llm_client, num_samples, args.skip_ingestion
        )
        all_results.append(result)
        total_correct += result['qa']['correct']
        total_questions += result['qa']['total']

    elapsed = (datetime.now() - start_time).total_seconds()
    overall_acc = total_correct / total_questions if total_questions > 0 else 0

    # 最终结果
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"总精度: {overall_acc*100:.2f}% ({total_correct}/{total_questions})")
    print(f"耗时: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Category breakdown
    category_names = {1: 'multi_hop', 2: 'temporal', 3: 'open_domain', 4: 'single_hop'}
    cat_stats = {}
    for r in all_results:
        for qa in r['qa']['results']:
            cat = qa['category']
            if cat not in cat_stats:
                cat_stats[cat] = {'c': 0, 't': 0}
            cat_stats[cat]['t'] += 1
            if qa['correct']:
                cat_stats[cat]['c'] += 1

    print("\nCategory:")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        acc = s['c'] / s['t'] * 100 if s['t'] > 0 else 0
        name = category_names.get(cat, f'cat_{cat}')
        print(f"  {name}: {acc:.1f}% ({s['c']}/{s['t']})")

    # 保存结果
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_bmam_full'
    metrics_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = metrics_dir / f'results_{num_samples}s_{num_questions}q_{timestamp}.json'

    with open(result_file, 'w') as f:
        json.dump({
            'config': {'samples': num_samples, 'questions': str(num_questions)},
            'summary': {'accuracy': overall_acc, 'correct': total_correct, 'total': total_questions, 'elapsed': elapsed},
            'category_stats': cat_stats,
            'results': all_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n✓ 结果保存: {result_file}")

    if overall_acc >= 0.50:
        print(f"\n✅ PASSED (≥50%)")
    else:
        print(f"\n⚠️  BELOW THRESHOLD (<50%)")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
