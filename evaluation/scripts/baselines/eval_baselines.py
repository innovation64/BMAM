#!/usr/bin/env python3
"""
基线对比实验脚本

基线系统:
1. GPT-4 + 简单 RAG (向量检索)
2. GPT-4 + 全上下文 (如果能塞下)
3. BM25 + GPT-4
4. 纯 GPT-4 (无记忆)

用于与 BMAM 进行公平对比

使用:
  python eval_baselines.py --baseline all          # 运行所有基线
  python eval_baselines.py --baseline rag          # 只运行 RAG 基线
  python eval_baselines.py --baseline bm25         # 只运行 BM25 基线
  python eval_baselines.py --samples 50            # 限制样本数
"""

import asyncio
import json
import os
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
import logging
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: OpenAI 不可用")

# Optional: FAISS for RAG baseline
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Optional: rank_bm25 for BM25 baseline
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'baselines'


class BaselineSystem:
    """基线系统基类"""

    def __init__(self, name: str, llm_client: AsyncOpenAI):
        self.name = name
        self.llm_client = llm_client
        self.memories: List[Dict] = []

    async def add_memory(self, content: str, metadata: Optional[Dict] = None):
        """添加记忆"""
        self.memories.append({
            'content': content,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })

    async def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        """检索相关记忆"""
        raise NotImplementedError

    async def answer(self, question: str, context: List[str]) -> Tuple[str, float]:
        """基于检索结果回答问题"""
        start_time = time.time()

        if context:
            context_str = "\n".join([f"- {c}" for c in context[:10]])
            prompt = f"""Based on the following context, answer the question.

Context:
{context_str}

Question: {question}

Answer concisely and directly. If the answer is not in the context, say "I don't know"."""
        else:
            prompt = f"""Answer the following question based on your knowledge.

Question: {question}

Answer concisely and directly."""

        try:
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant with good memory."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"Error: {e}"

        duration = (time.time() - start_time) * 1000
        return answer, duration

    def clear(self):
        """清空记忆"""
        self.memories = []


class RAGBaseline(BaselineSystem):
    """GPT-4 + 向量检索 RAG 基线"""

    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("GPT4-RAG", llm_client)
        self.embeddings: List[np.ndarray] = []
        self.embedding_model = None

    async def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本嵌入"""
        try:
            response = await self.llm_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            logging.warning(f"Embedding failed: {e}")
            # 返回随机向量作为 fallback
            return np.random.randn(1536).astype(np.float32)

    async def add_memory(self, content: str, metadata: Optional[Dict] = None):
        await super().add_memory(content, metadata)
        embedding = await self._get_embedding(content)
        self.embeddings.append(embedding)

    async def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        if not self.memories:
            return []

        query_embedding = await self._get_embedding(query)

        # 计算相似度
        similarities = []
        for emb in self.embeddings:
            sim = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            similarities.append(sim)

        # 获取 top_k
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [self.memories[i]['content'] for i in top_indices]

    def clear(self):
        super().clear()
        self.embeddings = []


class BM25Baseline(BaselineSystem):
    """BM25 + GPT-4 基线"""

    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("BM25-GPT4", llm_client)
        self.bm25 = None
        self.tokenized_corpus = []

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        return text.lower().split()

    async def add_memory(self, content: str, metadata: Optional[Dict] = None):
        await super().add_memory(content, metadata)
        tokens = self._tokenize(content)
        self.tokenized_corpus.append(tokens)
        # 重建 BM25 索引
        if BM25_AVAILABLE:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    async def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        if not self.memories or not BM25_AVAILABLE:
            return []

        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [self.memories[i]['content'] for i in top_indices if scores[i] > 0]

    def clear(self):
        super().clear()
        self.bm25 = None
        self.tokenized_corpus = []


class FullContextBaseline(BaselineSystem):
    """GPT-4 + 全上下文基线 (适用于较短对话)"""

    def __init__(self, llm_client: AsyncOpenAI, max_tokens: int = 100000):
        super().__init__("GPT4-FullContext", llm_client)
        self.max_tokens = max_tokens

    async def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        # 返回所有记忆 (全上下文)
        return [m['content'] for m in self.memories]

    async def answer(self, question: str, context: List[str]) -> Tuple[str, float]:
        start_time = time.time()

        # 截断上下文到 max_tokens
        full_context = "\n".join(context)
        # 简单估算 tokens (实际应该用 tiktoken)
        estimated_tokens = len(full_context) / 4
        if estimated_tokens > self.max_tokens:
            # 只保留最近的
            truncated_context = []
            current_tokens = 0
            for c in reversed(context):
                c_tokens = len(c) / 4
                if current_tokens + c_tokens < self.max_tokens:
                    truncated_context.insert(0, c)
                    current_tokens += c_tokens
                else:
                    break
            full_context = "\n".join(truncated_context)

        prompt = f"""Based on the following conversation history, answer the question.

Conversation History:
{full_context}

Question: {question}

Answer concisely and directly."""

        try:
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant with perfect memory."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"Error: {e}"

        duration = (time.time() - start_time) * 1000
        return answer, duration


class NoMemoryBaseline(BaselineSystem):
    """纯 GPT-4 无记忆基线"""

    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("GPT4-NoMemory", llm_client)

    async def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        return []  # 无记忆


def parse_date(s: str) -> datetime:
    if not s:
        return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except:
        return datetime.now()


async def llm_judge(client: AsyncOpenAI, q: str, gold: str, gen: str) -> bool:
    """LLM 评判"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {q}
Gold answer: {gold}
Generated answer: {gen}

Be generous: same meaning = CORRECT. Same date different format = CORRECT.
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
        return str(gold).lower() in str(gen).lower()


async def evaluate_baseline_on_locomo(baseline: BaselineSystem,
                                       data: List[Dict],
                                       llm_client: AsyncOpenAI,
                                       max_samples: Optional[int] = None) -> Dict[str, Any]:
    """在 LoCoMo 数据集上评估基线"""

    samples = data[:max_samples] if max_samples else data
    all_results = []
    total_correct = 0
    total_questions = 0
    total_duration = 0
    durations = []

    for sample_idx, sample in enumerate(tqdm(samples, desc=f"  {baseline.name}")):
        baseline.clear()

        # 塑造记忆
        conv = sample['conversation']
        obs = sample.get('observation', {})

        i = 1
        while f'session_{i}' in conv:
            dialogs = conv[f'session_{i}']
            ob = obs.get(f'session_{i}_observation', {})

            for t in dialogs:
                if t.get('text'):
                    await baseline.add_memory(f"{t['speaker']}: {t['text']}")

            for spk, items in ob.items():
                for it in items:
                    if isinstance(it, list) and it:
                        await baseline.add_memory(f"[Event] {spk}: {it[0]}")
            i += 1

        # 测试 QA
        sample_results = []
        sample_correct = 0

        for qa in sample['qa']:
            q, gold, cat = qa['question'], qa.get('answer', ''), qa.get('category', 0)

            # 检索
            context = await baseline.retrieve(q, top_k=20)

            # 回答
            answer, duration = await baseline.answer(q, context)
            durations.append(duration)
            total_duration += duration

            # 评判
            ok = await llm_judge(llm_client, q, gold, answer)
            if ok:
                sample_correct += 1

            sample_results.append({
                'question': q,
                'gold': str(gold),
                'answer': answer,
                'correct': ok,
                'category': cat,
                'duration_ms': duration
            })

        total_correct += sample_correct
        total_questions += len(sample['qa'])

        all_results.append({
            'sample_id': sample['sample_id'],
            'correct': sample_correct,
            'total': len(sample['qa']),
            'accuracy': sample_correct / len(sample['qa']) if sample['qa'] else 0,
            'results': sample_results
        })

    # 按类别统计
    category_stats = {}
    for sample_result in all_results:
        for qa_result in sample_result['results']:
            cat = qa_result['category']
            if cat not in category_stats:
                category_stats[cat] = {'correct': 0, 'total': 0}
            category_stats[cat]['total'] += 1
            if qa_result['correct']:
                category_stats[cat]['correct'] += 1

    for cat in category_stats:
        stats = category_stats[cat]
        stats['accuracy'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0

    accuracy = total_correct / total_questions if total_questions > 0 else 0

    return {
        'baseline': baseline.name,
        'overall': {
            'correct': total_correct,
            'total': total_questions,
            'accuracy': accuracy
        },
        'by_category': category_stats,
        'latency': {
            'mean': np.mean(durations) if durations else 0,
            'p50': np.percentile(durations, 50) if durations else 0,
            'p95': np.percentile(durations, 95) if durations else 0,
            'p99': np.percentile(durations, 99) if durations else 0
        },
        'samples': all_results
    }


async def main():
    parser = argparse.ArgumentParser(description='基线对比实验')
    parser.add_argument('--baseline', type=str, default='all',
                       choices=['all', 'rag', 'bm25', 'fullcontext', 'nomemory'],
                       help='要运行的基线')
    parser.add_argument('--dataset', type=str, default='locomo',
                       choices=['locomo'],
                       help='数据集')
    parser.add_argument('--samples', type=int, default=None,
                       help='样本数量限制')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    if not LLM_AVAILABLE:
        print("错误: OpenAI 不可用")
        sys.exit(1)

    print("=" * 70)
    print("基线对比实验")
    print("=" * 70)

    # 初始化 LLM client
    llm_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    # 加载数据
    if args.dataset == 'locomo':
        dataset_path = DATA_DIR / 'locomo' / 'locomo10.json'
        if not dataset_path.exists():
            print(f"错误: 数据集文件不存在: {dataset_path}")
            sys.exit(1)
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"加载 {len(data)} 组数据")

    # 创建基线系统
    baselines = []
    if args.baseline in ['all', 'rag']:
        baselines.append(RAGBaseline(llm_client))
    if args.baseline in ['all', 'bm25'] and BM25_AVAILABLE:
        baselines.append(BM25Baseline(llm_client))
    if args.baseline in ['all', 'fullcontext']:
        baselines.append(FullContextBaseline(llm_client))
    if args.baseline in ['all', 'nomemory']:
        baselines.append(NoMemoryBaseline(llm_client))

    if not baselines:
        print("没有可用的基线系统")
        sys.exit(1)

    print(f"\n将运行 {len(baselines)} 个基线: {[b.name for b in baselines]}")

    # 运行评估
    all_results = []
    start_time = datetime.now()

    for baseline in baselines:
        print(f"\n{'='*70}")
        print(f"评估基线: {baseline.name}")
        print(f"{'='*70}")

        result = await evaluate_baseline_on_locomo(baseline, data, llm_client, args.samples)
        all_results.append(result)

        print(f"\n  结果: {result['overall']['accuracy']*100:.2f}% "
              f"({result['overall']['correct']}/{result['overall']['total']})")
        print(f"  延迟: mean={result['latency']['mean']:.0f}ms, "
              f"p50={result['latency']['p50']:.0f}ms, p95={result['latency']['p95']:.0f}ms")

    elapsed = (datetime.now() - start_time).total_seconds()

    # 打印汇总
    print("\n" + "=" * 70)
    print("基线对比汇总")
    print("=" * 70)
    print(f"{'基线':<20} {'准确率':>10} {'延迟(p50)':>12} {'正确/总数':>15}")
    print("-" * 60)
    for result in all_results:
        print(f"{result['baseline']:<20} {result['overall']['accuracy']*100:>9.2f}% "
              f"{result['latency']['p50']:>10.0f}ms "
              f"{result['overall']['correct']:>6}/{result['overall']['total']:<6}")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"baselines_{args.dataset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    output_data = {
        'config': {
            'dataset': args.dataset,
            'samples': args.samples,
            'baselines': [b.name for b in baselines],
            'timestamp': datetime.now().isoformat()
        },
        'summary': {
            r['baseline']: {
                'accuracy': r['overall']['accuracy'],
                'correct': r['overall']['correct'],
                'total': r['overall']['total'],
                'latency_p50': r['latency']['p50']
            } for r in all_results
        },
        'results': all_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
