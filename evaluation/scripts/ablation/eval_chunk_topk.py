#!/usr/bin/env python3
"""
BMAM Chunk Size & Top-K 消融实验

对标 MemOS Paper Section 6.3
测试不同 chunk size 和 Top-K 参数对性能的影响

测试维度:
1. Chunk Size: 256, 512, 1024, 2048 tokens
2. Top-K: 3, 5, 10, 20, 50
3. 在 LoCoMo 各子任务上的表现

输出指标:
- LLM-Judge 准确率
- F1 Score
- ROUGE-L
- 语义相似度 (Cosine Similarity)

使用:
  python eval_chunk_topk.py --chunk-sizes 256 512 1024
  python eval_chunk_topk.py --top-k 3 5 10 20
  python eval_chunk_topk.py --full  # 完整测试
"""

import asyncio
import json
import os
import sys
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
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

try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    ROUGE_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'chunk_topk'


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


def compute_f1(prediction: str, reference: str) -> float:
    """计算 F1 Score"""
    pred_tokens = set(prediction.lower().split())
    ref_tokens = set(reference.lower().split())

    if not pred_tokens or not ref_tokens:
        return 0.0

    common = pred_tokens & ref_tokens
    if not common:
        return 0.0

    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1


def compute_rouge_l(prediction: str, reference: str, scorer=None) -> float:
    """计算 ROUGE-L Score"""
    if ROUGE_AVAILABLE and scorer:
        scores = scorer.score(reference, prediction)
        return scores['rougeL'].fmeasure
    else:
        # Fallback: 使用 LCS 近似
        return compute_lcs_similarity(prediction, reference)


def compute_lcs_similarity(s1: str, s2: str) -> float:
    """计算 LCS 相似度"""
    words1 = s1.lower().split()
    words2 = s2.lower().split()

    if not words1 or not words2:
        return 0.0

    m, n = len(words1), len(words2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if words1[i-1] == words2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    lcs_len = dp[m][n]
    return 2 * lcs_len / (m + n) if (m + n) > 0 else 0.0


class MetricsCalculator:
    """指标计算器"""

    def __init__(self):
        self.rouge_scorer = None
        self.sbert_model = None

        if ROUGE_AVAILABLE:
            self.rouge_scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

        if SBERT_AVAILABLE:
            try:
                self.sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                pass

    def compute_cosine_similarity(self, text1: str, text2: str) -> float:
        """计算余弦相似度"""
        if self.sbert_model:
            embeddings = self.sbert_model.encode([text1, text2])
            cos_sim = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(cos_sim)
        else:
            # Fallback: Jaccard 相似度
            set1 = set(text1.lower().split())
            set2 = set(text2.lower().split())
            if not set1 or not set2:
                return 0.0
            return len(set1 & set2) / len(set1 | set2)

    def compute_all_metrics(self, prediction: str, reference: str) -> Dict[str, float]:
        """计算所有指标"""
        return {
            'f1': compute_f1(prediction, reference),
            'rouge_l': compute_rouge_l(prediction, reference, self.rouge_scorer),
            'cosine_sim': self.compute_cosine_similarity(prediction, reference)
        }


async def run_chunk_topk_test(chunk_size: int, top_k: int,
                                data: List[Dict],
                                llm_client: Optional[AsyncOpenAI],
                                metrics_calc: MetricsCalculator,
                                max_samples: int = 20) -> Dict[str, Any]:
    """
    运行单次 chunk_size + top_k 配置测试
    """
    print(f"\n测试配置: chunk_size={chunk_size}, top_k={top_k}")

    clear_memory()

    # 配置 BMAM
    # 注意: 这里需要根据实际 BMAM 接口调整 chunk_size 和 top_k 参数
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(
        enable_multi_timescale=True,
        enable_act=True,
        # 如果 HRMConfig 支持这些参数:
        # chunk_size=chunk_size,
        # retrieval_top_k=top_k,
    )
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)

    # 设置检索参数 (如果接口支持)
    if hasattr(coord, 'set_retrieval_params'):
        coord.set_retrieval_params(chunk_size=chunk_size, top_k=top_k)

    await coord.start_system()

    try:
        results_by_category = defaultdict(list)
        all_results = []
        samples_processed = 0

        for session in data:
            if samples_processed >= max_samples:
                break

            turns = session.get('turns', session.get('conversations', []))
            questions = session.get('questions', [])

            # 塑造记忆
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

            await asyncio.sleep(0.5)

            # 测试问题
            for q in questions:
                if samples_processed >= max_samples:
                    break

                if isinstance(q, dict):
                    question = q.get('question', q.get('text', ''))
                    expected = q.get('answer', q.get('expected', ''))
                    category = q.get('category', q.get('type', 'other'))
                else:
                    continue

                if not question:
                    continue

                # 查询
                context = {
                    'skip_memory_store': True,
                    'evaluation_mode': True,
                    'top_k': top_k  # 传递 top_k 参数
                }
                result = await coord.process_user_input(question, context=context)

                if hasattr(result, 'response'):
                    answer = result.response
                elif isinstance(result, dict):
                    answer = result.get('response', str(result))
                else:
                    answer = str(result)

                # 计算指标
                metrics = metrics_calc.compute_all_metrics(answer, expected)

                # LLM 判断
                is_correct = expected.lower() in answer.lower() if expected else False
                if llm_client and expected:
                    try:
                        prompt = f"""Check if the answer is correct.

Question: {question}
Expected: {expected}
Generated: {answer}

Return JSON: {{"correct": true/false, "score": 0.0-1.0}}"""

                        r = await llm_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0
                        )
                        judge_result = json.loads(r.choices[0].message.content)
                        is_correct = judge_result.get('correct', is_correct)
                        metrics['llm_judge_score'] = judge_result.get('score', 1.0 if is_correct else 0.0)
                    except:
                        metrics['llm_judge_score'] = 1.0 if is_correct else 0.0
                else:
                    metrics['llm_judge_score'] = 1.0 if is_correct else 0.0

                result_entry = {
                    'question': question,
                    'expected': expected,
                    'answer': answer,
                    'is_correct': is_correct,
                    'category': category,
                    'metrics': metrics
                }

                all_results.append(result_entry)
                results_by_category[category].append(result_entry)
                samples_processed += 1

            # 清理记忆为下一个 session
            clear_memory()
            await coord.stop_system()
            base_coord = BrainInspiredCoordinator()
            coord = HRMCoordinatorWrapper(base_coord, hrm_config)
            await coord.start_system()

        # 汇总结果
        overall_metrics = {
            'accuracy': np.mean([1 if r['is_correct'] else 0 for r in all_results]),
            'llm_judge': np.mean([r['metrics']['llm_judge_score'] for r in all_results]),
            'f1': np.mean([r['metrics']['f1'] for r in all_results]),
            'rouge_l': np.mean([r['metrics']['rouge_l'] for r in all_results]),
            'cosine_sim': np.mean([r['metrics']['cosine_sim'] for r in all_results]),
        }

        # 按类别汇总
        category_metrics = {}
        for cat, results in results_by_category.items():
            category_metrics[cat] = {
                'accuracy': np.mean([1 if r['is_correct'] else 0 for r in results]),
                'llm_judge': np.mean([r['metrics']['llm_judge_score'] for r in results]),
                'f1': np.mean([r['metrics']['f1'] for r in results]),
                'count': len(results)
            }

        print(f"  准确率: {overall_metrics['accuracy']*100:.1f}%")
        print(f"  F1: {overall_metrics['f1']:.3f}")
        print(f"  ROUGE-L: {overall_metrics['rouge_l']:.3f}")
        print(f"  Cosine Sim: {overall_metrics['cosine_sim']:.3f}")

        return {
            'chunk_size': chunk_size,
            'top_k': top_k,
            'samples': samples_processed,
            'overall': overall_metrics,
            'by_category': category_metrics,
            'detailed': all_results
        }

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


async def main():
    parser = argparse.ArgumentParser(description='BMAM Chunk Size & Top-K 消融实验')
    parser.add_argument('--chunk-sizes', type=int, nargs='+', default=[512, 1024],
                       help='Chunk sizes to test')
    parser.add_argument('--top-k', type=int, nargs='+', default=[5, 10, 20],
                       help='Top-K values to test')
    parser.add_argument('--samples', type=int, default=30,
                       help='样本数量')
    parser.add_argument('--full', action='store_true',
                       help='运行完整测试 (256-2048 chunks, 3-50 top-k)')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    if args.full:
        args.chunk_sizes = [256, 512, 1024, 2048]
        args.top_k = [3, 5, 10, 20, 50]

    print("=" * 70)
    print("BMAM Chunk Size & Top-K 消融实验")
    print("=" * 70)
    print(f"Chunk Sizes: {args.chunk_sizes}")
    print(f"Top-K: {args.top_k}")

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")

    # 加载数据
    data = load_locomo_data()
    if not data:
        print("❌ 无法加载 LoCoMo 数据集")
        return

    print(f"✓ 加载 {len(data)} 个 sessions")

    # 初始化指标计算器
    metrics_calc = MetricsCalculator()

    results = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'chunk_sizes': args.chunk_sizes,
            'top_k': args.top_k,
            'samples_per_config': args.samples
        },
        'experiments': []
    }

    start_time = datetime.now()

    # 运行所有配置组合
    total_configs = len(args.chunk_sizes) * len(args.top_k)
    config_idx = 0

    for chunk_size in args.chunk_sizes:
        for top_k in args.top_k:
            config_idx += 1
            print(f"\n[{config_idx}/{total_configs}]", end='')

            result = await run_chunk_topk_test(
                chunk_size, top_k, data, llm_client, metrics_calc, args.samples
            )
            results['experiments'].append(result)

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    # 生成汇总表格
    print("\n" + "=" * 70)
    print("结果汇总")
    print("=" * 70)

    # 构建表格 (chunk_size x top_k)
    print("\n准确率矩阵 (Chunk Size x Top-K):")
    header = "         " + " ".join([f"K={k:>4}" for k in args.top_k])
    print(header)
    print("-" * len(header))

    for chunk_size in args.chunk_sizes:
        row = f"C={chunk_size:>4} "
        for top_k in args.top_k:
            exp = next((e for e in results['experiments']
                       if e['chunk_size'] == chunk_size and e['top_k'] == top_k), None)
            if exp:
                acc = exp['overall']['accuracy'] * 100
                row += f" {acc:>5.1f}%"
            else:
                row += "   N/A"
        print(row)

    # 找到最佳配置
    best_exp = max(results['experiments'], key=lambda x: x['overall']['accuracy'])
    print(f"\n最佳配置: chunk_size={best_exp['chunk_size']}, top_k={best_exp['top_k']}")
    print(f"  准确率: {best_exp['overall']['accuracy']*100:.1f}%")
    print(f"  F1: {best_exp['overall']['f1']:.3f}")
    print(f"  ROUGE-L: {best_exp['overall']['rouge_l']:.3f}")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"chunk_topk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    # 移除 detailed results 以减小文件大小
    results_to_save = {
        **results,
        'experiments': [{k: v for k, v in exp.items() if k != 'detailed'}
                       for exp in results['experiments']]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_to_save, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
