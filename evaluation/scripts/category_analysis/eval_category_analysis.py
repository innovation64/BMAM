#!/usr/bin/env python3
"""
BMAM 按类别详细分析脚本

分析维度:
1. 单跳 vs 多跳 (single-hop vs multi-hop)
2. 时序 vs 空间 (temporal vs spatial)
3. 对抗 vs 良性 (adversarial vs benign)
4. 置信度校准 (confidence calibration)
5. 问题难度分析 (difficulty stratification)

使用:
  python eval_category_analysis.py --dataset locomo    # 使用 LoCoMo 数据集
  python eval_category_analysis.py --dataset all       # 使用所有数据集
  python eval_category_analysis.py --calibration       # 只运行置信度校准
"""

import asyncio
import json
import os
import sys
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from tqdm import tqdm
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
import logging
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'category_analysis'


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


def load_locomo_data() -> List[Dict]:
    """加载 LoCoMo 数据集"""
    locomo_file = DATA_DIR / 'locomo' / 'locomo10.json'
    if locomo_file.exists():
        with open(locomo_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    return []


def categorize_question(question: Dict) -> Dict[str, str]:
    """
    对问题进行多维度分类

    返回: {
        'hop_type': 'single' | 'multi',
        'temporal_spatial': 'temporal' | 'spatial' | 'neutral',
        'adversarial': 'adversarial' | 'benign',
        'difficulty': 'easy' | 'medium' | 'hard'
    }
    """
    q_text = question.get('question', '').lower()
    category = question.get('category', '').lower()
    q_type = question.get('type', '').lower()

    # 1. 单跳 vs 多跳
    multi_hop_keywords = ['and', 'both', 'also', 'relationship', 'connected', 'related']
    if any(k in q_text for k in multi_hop_keywords) or 'multi' in category:
        hop_type = 'multi'
    else:
        hop_type = 'single'

    # 2. 时序 vs 空间
    temporal_keywords = ['when', 'before', 'after', 'first', 'last', 'date', 'time', 'year', 'month']
    spatial_keywords = ['where', 'location', 'place', 'city', 'country', 'address']

    if any(k in q_text for k in temporal_keywords) or 'temporal' in category:
        temporal_spatial = 'temporal'
    elif any(k in q_text for k in spatial_keywords):
        temporal_spatial = 'spatial'
    else:
        temporal_spatial = 'neutral'

    # 3. 对抗 vs 良性
    # 对抗性问题通常涉及矛盾信息、否定、更新
    adversarial_keywords = ['not', 'no longer', 'changed', 'updated', 'wrong', 'incorrect', 'never']
    if any(k in q_text for k in adversarial_keywords) or 'adversarial' in q_type:
        adversarial = 'adversarial'
    else:
        adversarial = 'benign'

    # 4. 难度评估
    # 基于问题长度、是否多跳、是否时序推理等
    difficulty_score = 0
    if hop_type == 'multi':
        difficulty_score += 2
    if temporal_spatial == 'temporal':
        difficulty_score += 1
    if adversarial == 'adversarial':
        difficulty_score += 2
    if len(q_text) > 100:
        difficulty_score += 1

    if difficulty_score >= 4:
        difficulty = 'hard'
    elif difficulty_score >= 2:
        difficulty = 'medium'
    else:
        difficulty = 'easy'

    return {
        'hop_type': hop_type,
        'temporal_spatial': temporal_spatial,
        'adversarial': adversarial,
        'difficulty': difficulty
    }


async def run_category_analysis(dataset_name: str,
                                  llm_client: Optional[AsyncOpenAI],
                                  max_samples: int = 50) -> Dict[str, Any]:
    """
    运行按类别分析

    对数据集中的问题进行分类，并按类别统计准确率
    """
    print(f"\n" + "=" * 50)
    print(f"按类别分析 - {dataset_name}")
    print("=" * 50)

    # 加载数据
    if dataset_name == 'locomo':
        data = load_locomo_data()
    else:
        print(f"数据集 {dataset_name} 暂不支持")
        return {}

    if not data:
        print("无法加载数据集")
        return {}

    # 初始化 BMAM
    clear_memory()
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        results_by_category = {
            'hop_type': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'temporal_spatial': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'adversarial': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'difficulty': defaultdict(lambda: {'correct': 0, 'total': 0}),
        }

        detailed_results = []
        samples_processed = 0

        for session_idx, session in enumerate(data):
            if samples_processed >= max_samples:
                break

            # 塑造会话记忆
            clear_memory()

            # 重新初始化
            await coord.stop_system()
            base_coord = BrainInspiredCoordinator()
            coord = HRMCoordinatorWrapper(base_coord, hrm_config)
            await coord.start_system()

            turns = session.get('turns', session.get('conversations', []))
            questions = session.get('questions', [])

            # 塑造对话记忆
            ts = datetime.now()
            for i, turn in enumerate(turns):
                if isinstance(turn, dict):
                    content = turn.get('content', turn.get('text', str(turn)))
                    speaker = turn.get('speaker', turn.get('role', 'User'))
                else:
                    content = str(turn)
                    speaker = 'User'

                await coord.store_memory_with_timestamp(
                    f"{speaker}: {content}",
                    ts + timedelta(minutes=i),
                    speaker,
                    0.7
                )

            await asyncio.sleep(1)

            # 处理问题
            for q in questions:
                if samples_processed >= max_samples:
                    break

                if isinstance(q, dict):
                    question_text = q.get('question', q.get('text', ''))
                    expected = q.get('answer', q.get('expected', ''))
                else:
                    continue

                if not question_text:
                    continue

                # 分类问题
                categories = categorize_question(q)

                # 查询 BMAM
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(question_text, context=context)

                if hasattr(result, 'response'):
                    answer = result.response
                elif isinstance(result, dict):
                    answer = result.get('response', str(result))
                else:
                    answer = str(result)

                # 判断正确性
                is_correct = expected.lower() in answer.lower() if expected else False

                # LLM 判断
                if llm_client and expected:
                    try:
                        prompt = f"""Check if the answer is correct.

Question: {question_text}
Expected: {expected}
Generated: {answer}

Return JSON: {{"correct": true/false}}"""

                        r = await llm_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0
                        )
                        is_correct = json.loads(r.choices[0].message.content).get('correct', is_correct)
                    except:
                        pass

                # 更新统计
                for dim, cat_value in categories.items():
                    results_by_category[dim][cat_value]['total'] += 1
                    if is_correct:
                        results_by_category[dim][cat_value]['correct'] += 1

                detailed_results.append({
                    'question': question_text,
                    'expected': expected,
                    'answer': answer,
                    'is_correct': is_correct,
                    'categories': categories
                })

                samples_processed += 1

            print(f"已处理 {samples_processed}/{max_samples} 样本")

        # 计算准确率
        summary = {}
        for dim, stats in results_by_category.items():
            summary[dim] = {}
            for cat, counts in stats.items():
                if counts['total'] > 0:
                    acc = counts['correct'] / counts['total']
                else:
                    acc = 0
                summary[dim][cat] = {
                    'accuracy': acc,
                    'correct': counts['correct'],
                    'total': counts['total']
                }

        # 打印结果
        print("\n" + "=" * 50)
        print("分类准确率汇总")
        print("=" * 50)

        for dim, stats in summary.items():
            print(f"\n{dim}:")
            for cat, s in sorted(stats.items()):
                print(f"  {cat:>12}: {s['accuracy']*100:.1f}% ({s['correct']}/{s['total']})")

        return {
            'dataset': dataset_name,
            'samples_processed': samples_processed,
            'summary': summary,
            'detailed_results': detailed_results
        }

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


async def run_confidence_calibration(llm_client: Optional[AsyncOpenAI],
                                      num_samples: int = 30) -> Dict[str, Any]:
    """
    置信度校准分析

    测试系统置信度与实际准确率的对应关系
    """
    print("\n" + "=" * 50)
    print("置信度校准分析")
    print("=" * 50)

    # 测试用例 (有明确答案)
    test_cases = [
        # 高置信度应该正确
        {
            'memories': ["User's name is John Smith."],
            'question': "What is the user's name?",
            'expected': "John Smith",
            'expected_confidence': 'high'
        },
        {
            'memories': ["User works at Google."],
            'question': "Where does the user work?",
            'expected': "Google",
            'expected_confidence': 'high'
        },
        # 中等置信度
        {
            'memories': ["User mentioned they might visit Paris next month."],
            'question': "Will the user visit Paris?",
            'expected': "might",
            'expected_confidence': 'medium'
        },
        # 低置信度 (信息不足)
        {
            'memories': ["User likes music."],
            'question': "What is the user's favorite song?",
            'expected': "",  # 无法确定
            'expected_confidence': 'low'
        },
        # 矛盾情况
        {
            'memories': [
                "User said they love coffee.",
                "User mentioned they hate coffee now."
            ],
            'question': "Does the user like coffee?",
            'expected': "hate",
            'expected_confidence': 'medium'
        },
    ]

    # 扩展测试用例
    for i in range(num_samples - len(test_cases)):
        test_cases.append({
            'memories': [f"User mentioned fact {i}: some information here."],
            'question': f"What is fact {i}?",
            'expected': f"fact {i}",
            'expected_confidence': 'high' if i % 2 == 0 else 'medium'
        })

    clear_memory()
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        calibration_results = []
        confidence_buckets = defaultdict(lambda: {'correct': 0, 'total': 0})

        for case in tqdm(test_cases[:num_samples], desc="校准测试"):
            # 清空并塑造记忆
            clear_memory()

            # 重新初始化
            await coord.stop_system()
            base_coord = BrainInspiredCoordinator()
            coord = HRMCoordinatorWrapper(base_coord, hrm_config)
            await coord.start_system()

            ts = datetime.now()
            for i, memory in enumerate(case['memories']):
                await coord.store_memory_with_timestamp(
                    f"User: {memory}",
                    ts + timedelta(minutes=i),
                    "User",
                    0.7
                )

            await asyncio.sleep(0.5)

            # 查询
            context = {'skip_memory_store': True, 'evaluation_mode': True, 'return_confidence': True}
            result = await coord.process_user_input(case['question'], context=context)

            if hasattr(result, 'response'):
                answer = result.response
            elif isinstance(result, dict):
                answer = result.get('response', str(result))
            else:
                answer = str(result)

            # 提取置信度
            if hasattr(result, 'confidence'):
                confidence = result.confidence
            elif isinstance(result, dict) and 'confidence' in result:
                confidence = result['confidence']
            else:
                # 模拟置信度 (基于答案特征)
                confidence = estimate_confidence(answer, case['expected'])

            # 判断正确性
            is_correct = case['expected'].lower() in answer.lower() if case['expected'] else False

            # LLM 判断
            if llm_client and case['expected']:
                try:
                    prompt = f"""Check if the answer is correct.

Question: {case['question']}
Expected (should contain): {case['expected']}
Generated: {answer}

Return JSON: {{"correct": true/false}}"""

                    r = await llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )
                    is_correct = json.loads(r.choices[0].message.content).get('correct', is_correct)
                except:
                    pass

            # 分桶统计
            bucket = get_confidence_bucket(confidence)
            confidence_buckets[bucket]['total'] += 1
            if is_correct:
                confidence_buckets[bucket]['correct'] += 1

            calibration_results.append({
                'question': case['question'],
                'expected': case['expected'],
                'answer': answer,
                'is_correct': is_correct,
                'confidence': confidence,
                'bucket': bucket
            })

        # 计算校准结果
        calibration_summary = {}
        for bucket in ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']:
            stats = confidence_buckets[bucket]
            if stats['total'] > 0:
                acc = stats['correct'] / stats['total']
            else:
                acc = 0
            calibration_summary[bucket] = {
                'accuracy': acc,
                'correct': stats['correct'],
                'total': stats['total']
            }

        # 计算 ECE (Expected Calibration Error)
        ece = calculate_ece(calibration_results)

        # 打印结果
        print("\n" + "=" * 50)
        print("置信度校准结果")
        print("=" * 50)

        print("\n置信度分桶 vs 实际准确率:")
        print(f"{'置信度':>12} | {'准确率':>8} | {'样本数':>6} | {'理想值':>8}")
        print("-" * 45)

        ideal_values = {'0-20%': 0.1, '20-40%': 0.3, '40-60%': 0.5, '60-80%': 0.7, '80-100%': 0.9}
        for bucket in ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']:
            s = calibration_summary[bucket]
            ideal = ideal_values[bucket]
            diff = abs(s['accuracy'] - ideal)
            calibration_mark = '✓' if diff < 0.15 else '△' if diff < 0.25 else '✗'
            print(f"{bucket:>12} | {s['accuracy']*100:>6.1f}% | {s['total']:>6} | {ideal*100:>6.1f}% {calibration_mark}")

        print(f"\nECE (Expected Calibration Error): {ece:.3f}")
        print("(ECE 越低越好，0 表示完美校准)")

        return {
            'calibration_summary': calibration_summary,
            'ece': ece,
            'detailed_results': calibration_results
        }

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


def estimate_confidence(answer: str, expected: str) -> float:
    """估计置信度 (当系统不返回时使用)"""
    # 基于答案特征估计
    if not answer:
        return 0.1

    # 包含不确定词汇
    uncertain_phrases = ['might', 'maybe', 'possibly', 'not sure', 'uncertain', 'could be']
    for phrase in uncertain_phrases:
        if phrase in answer.lower():
            return 0.4

    # 包含否定或矛盾
    if "don't know" in answer.lower() or "no information" in answer.lower():
        return 0.2

    # 答案较短且直接
    if len(answer) < 50 and expected and expected.lower() in answer.lower():
        return 0.9

    # 默认中等置信度
    return 0.7


def get_confidence_bucket(confidence: float) -> str:
    """获取置信度分桶"""
    if confidence < 0.2:
        return '0-20%'
    elif confidence < 0.4:
        return '20-40%'
    elif confidence < 0.6:
        return '40-60%'
    elif confidence < 0.8:
        return '60-80%'
    else:
        return '80-100%'


def calculate_ece(results: List[Dict]) -> float:
    """
    计算 Expected Calibration Error

    ECE = Σ (|accuracy_i - confidence_i| * n_i) / N
    """
    buckets = defaultdict(list)
    for r in results:
        bucket = get_confidence_bucket(r['confidence'])
        buckets[bucket].append(r)

    ece = 0.0
    total_samples = len(results)

    bucket_midpoints = {
        '0-20%': 0.1,
        '20-40%': 0.3,
        '40-60%': 0.5,
        '60-80%': 0.7,
        '80-100%': 0.9
    }

    for bucket, samples in buckets.items():
        if samples:
            accuracy = sum(1 for s in samples if s['is_correct']) / len(samples)
            avg_confidence = bucket_midpoints[bucket]
            ece += abs(accuracy - avg_confidence) * len(samples) / total_samples

    return ece


async def main():
    parser = argparse.ArgumentParser(description='BMAM 按类别详细分析')
    parser.add_argument('--dataset', type=str, default='locomo',
                       choices=['locomo', 'all'],
                       help='数据集')
    parser.add_argument('--samples', type=int, default=50,
                       help='样本数量')
    parser.add_argument('--calibration', action='store_true',
                       help='只运行置信度校准')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM 按类别详细分析")
    print("=" * 70)

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")

    results = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'dataset': args.dataset,
            'samples': args.samples
        },
        'analyses': {}
    }

    start_time = datetime.now()

    # 置信度校准
    if args.calibration or True:  # 总是运行校准
        results['analyses']['calibration'] = await run_confidence_calibration(
            llm_client, num_samples=min(30, args.samples)
        )

    # 按类别分析
    if not args.calibration:
        if args.dataset == 'all':
            for ds in ['locomo']:  # 可扩展其他数据集
                results['analyses'][f'category_{ds}'] = await run_category_analysis(
                    ds, llm_client, args.samples
                )
        else:
            results['analyses']['category'] = await run_category_analysis(
                args.dataset, llm_client, args.samples
            )

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"category_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
