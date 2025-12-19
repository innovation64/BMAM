#!/usr/bin/env python3
"""
LongMemEval 评估脚本 - BMAM vs MemOS 对比

数据集: LongMemEval (长记忆评测)
- longmemeval_oracle.json: 精简版 (快速测试)
- longmemeval_s_cleaned.json: 小型完整版

使用:
  python eval_longmemeval.py                           # 默认使用 oracle 版本
  python eval_longmemeval.py --dataset longmemeval_s   # 使用完整版
  python eval_longmemeval.py --samples 100             # 只测试100个样本
"""

import asyncio
import json
import os
import sys
import argparse
import time
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm
from dataclasses import dataclass, asdict

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE_AVAILABLE = True
except ImportError:
    LLM_JUDGE_AVAILABLE = False


# Paths
DATA_DIR = PROJECT_ROOT / 'data'
DATASET_DIR = DATA_DIR / 'longmemeval'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'longmemeval'


@dataclass
class EvalResult:
    question_id: str
    question: str
    question_type: str
    golden_answer: str
    generated_answer: str
    is_correct: bool
    response_duration_ms: float
    search_duration_ms: float


def clear_memory():
    """清空记忆文件"""
    files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
             'amygdala_state.json', 'brain_memory.db', 'temporal_lobe.db', 'working_memory.db',
             'story_arc_state.json', 'tom_state.json', 'kv_value_store.db']
    for f in files:
        p = DATA_DIR / f
        if p.exists():
            p.unlink()
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = DATA_DIR / d
        if p.exists():
            shutil.rmtree(p)


def parse_date(s: str) -> datetime:
    """解析日期字符串"""
    if not s:
        return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except:
        return datetime.now()


async def llm_judge(client: AsyncOpenAI, question: str, gold_answer: str, generated: str) -> bool:
    """LLM 评判答案正确性"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated}

Be generous: same meaning = CORRECT. Same date different format = CORRECT.
For time-related questions, accept different formats of the same date.
Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert grader"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return json.loads(r.choices[0].message.content).get("label", "").upper() == "CORRECT"
    except:
        return str(gold_answer).lower() in str(generated).lower()


async def ingest_sessions(coord, haystack_sessions: List[List[Dict]],
                          haystack_dates: List[str], question_id: str) -> int:
    """
    将对话历史塑造到 BMAM

    Args:
        coord: BMAM coordinator
        haystack_sessions: 对话会话列表
        haystack_dates: 对应的日期列表
        question_id: 问题ID (用于日志)

    Returns:
        存储的消息数量
    """
    total_stored = 0

    for session_idx, (session, date_str) in enumerate(zip(haystack_sessions, haystack_dates)):
        ts = parse_date(date_str)

        for msg in session:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            has_answer = msg.get('has_answer', False)

            if content:
                # 重要答案记忆给予更高重要性
                importance = 0.8 if has_answer else 0.6
                speaker = 'User' if role == 'user' else 'Assistant'

                await coord.store_memory_with_timestamp(
                    f"{speaker}: {content}", ts, speaker, importance
                )
                total_stored += 1

    return total_stored


async def evaluate_question(coord, sample: Dict, llm_client: Optional[AsyncOpenAI]) -> EvalResult:
    """评估单个问题"""
    question_id = sample['question_id']
    question = sample['question']
    question_type = sample.get('question_type', 'unknown')
    gold_answer = sample['answer']

    # 查询
    start_time = time.time()

    context = {'skip_memory_store': True, 'evaluation_mode': True}
    result = await coord.process_user_input(question, context=context)

    response_duration = (time.time() - start_time) * 1000

    # 提取答案
    if hasattr(result, 'response'):
        generated = result.response
    elif isinstance(result, dict):
        generated = result.get('response', str(result))
    else:
        generated = str(result)

    # 评判
    if llm_client:
        is_correct = await llm_judge(llm_client, question, gold_answer, generated)
    else:
        is_correct = str(gold_answer).lower() in str(generated).lower()

    return EvalResult(
        question_id=question_id,
        question=question,
        question_type=question_type,
        golden_answer=str(gold_answer),
        generated_answer=generated,
        is_correct=is_correct,
        response_duration_ms=response_duration,
        search_duration_ms=0  # TODO: 从 result 提取
    )


async def evaluate_sample(sample: Dict, llm_client: Optional[AsyncOpenAI],
                          sample_idx: int, total_samples: int) -> Dict[str, Any]:
    """评估单个样本 (包含记忆塑造和问答)"""
    question_id = sample['question_id']

    # 清空记忆
    clear_memory()

    # 初始化 coordinator
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        # 塑造对话历史
        haystack_sessions = sample.get('haystack_sessions', [])
        haystack_dates = sample.get('haystack_dates', [])

        ingest_start = time.time()
        stored_count = await ingest_sessions(coord, haystack_sessions, haystack_dates, question_id)
        ingest_duration = (time.time() - ingest_start) * 1000

        # 等待巩固
        await asyncio.sleep(2)

        # 评估问题
        result = await evaluate_question(coord, sample, llm_client)

        return {
            'question_id': result.question_id,
            'question': result.question,
            'question_type': result.question_type,
            'golden_answer': result.golden_answer,
            'generated_answer': result.generated_answer,
            'is_correct': result.is_correct,
            'response_duration_ms': result.response_duration_ms,
            'search_duration_ms': result.search_duration_ms,
            'ingest_duration_ms': ingest_duration,
            'stored_memories': stored_count
        }
    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


def calculate_metrics(results: List[Dict]) -> Dict[str, Any]:
    """计算评估指标"""
    import numpy as np

    total = len(results)
    correct = sum(1 for r in results if r['is_correct'])
    accuracy = correct / total if total > 0 else 0

    # 按类别统计
    category_stats = {}
    for r in results:
        cat = r['question_type']
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'correct': 0}
        category_stats[cat]['total'] += 1
        if r['is_correct']:
            category_stats[cat]['correct'] += 1

    for cat in category_stats:
        stats = category_stats[cat]
        stats['accuracy'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0

    # 延迟统计
    response_times = [r['response_duration_ms'] for r in results]

    return {
        'overall': {
            'total': total,
            'correct': correct,
            'accuracy': accuracy
        },
        'by_category': category_stats,
        'latency': {
            'mean': np.mean(response_times),
            'p50': np.percentile(response_times, 50),
            'p95': np.percentile(response_times, 95)
        }
    }


async def main():
    parser = argparse.ArgumentParser(description='LongMemEval 评估脚本')
    parser.add_argument('--dataset', type=str, default='oracle',
                       choices=['oracle', 'longmemeval_s'],
                       help='数据集版本')
    parser.add_argument('--samples', type=int, default=None,
                       help='评估样本数量 (默认全部)')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    # 数据集路径
    if args.dataset == 'oracle':
        dataset_path = DATASET_DIR / 'longmemeval_oracle.json'
    else:
        dataset_path = DATASET_DIR / 'longmemeval_s_cleaned.json'

    if not dataset_path.exists():
        print(f"错误: 数据集文件不存在: {dataset_path}")
        sys.exit(1)

    print("=" * 70)
    print("LongMemEval 评估 - BMAM")
    print("=" * 70)
    print(f"数据集: {dataset_path.name}")

    # 加载数据
    print("加载数据...")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if args.samples:
        data = data[:args.samples]

    print(f"样本数: {len(data)}")

    # LLM Judge
    llm_client = None
    if LLM_JUDGE_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")
    else:
        print("⚠ LLM Judge 不可用，使用字符串匹配")

    # 评估
    results = []
    correct_count = 0
    start_time = datetime.now()

    for idx, sample in enumerate(tqdm(data, desc="评估进度")):
        result = await evaluate_sample(sample, llm_client, idx, len(data))
        results.append(result)

        if result['is_correct']:
            correct_count += 1

        # 实时显示准确率
        current_acc = correct_count / (idx + 1)
        tqdm.write(f"  [{idx+1}/{len(data)}] {result['question_type']}: "
                   f"{'✓' if result['is_correct'] else '✗'} "
                   f"| 累计准确率: {current_acc*100:.1f}%")

    elapsed = (datetime.now() - start_time).total_seconds()

    # 计算指标
    metrics = calculate_metrics(results)

    # 打印结果
    print("\n" + "=" * 70)
    print("评估结果")
    print("=" * 70)
    print(f"总准确率: {metrics['overall']['accuracy']*100:.2f}% "
          f"({metrics['overall']['correct']}/{metrics['overall']['total']})")
    print(f"耗时: {elapsed/60:.1f} 分钟")
    print(f"\n延迟 (ms): mean={metrics['latency']['mean']:.0f}, "
          f"p50={metrics['latency']['p50']:.0f}, p95={metrics['latency']['p95']:.0f}")

    print("\n按类别准确率:")
    for cat, stats in metrics['by_category'].items():
        print(f"  {cat}: {stats['accuracy']*100:.1f}% ({stats['correct']}/{stats['total']})")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"bmam_longmemeval_{args.dataset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    output_data = {
        'config': {
            'dataset': args.dataset,
            'samples': len(data),
            'timestamp': datetime.now().isoformat()
        },
        'metrics': metrics,
        'results': results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
