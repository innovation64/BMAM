#!/usr/bin/env python3
"""
BMAM 计算效率分析脚本

测试指标:
1. Latency (p50/p95/p99)
2. Memory usage vs 记忆数量
3. API cost 估算
4. 扩展性测试 (1K/10K/100K 记忆)
5. 吞吐量测试

使用:
  python eval_efficiency.py --test latency      # 延迟测试
  python eval_efficiency.py --test scalability  # 扩展性测试
  python eval_efficiency.py --test all          # 全部测试
"""

import asyncio
import json
import os
import sys
import argparse
import time
import psutil
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
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
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'efficiency'


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


def get_memory_usage() -> Dict[str, float]:
    """获取当前内存使用情况"""
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size
        'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
    }


def get_disk_usage() -> Dict[str, float]:
    """获取 data 目录磁盘使用"""
    total_size = 0
    for path in DATA_DIR.rglob('*'):
        if path.is_file():
            total_size += path.stat().st_size
    return {
        'disk_mb': total_size / 1024 / 1024
    }


async def test_latency(num_queries: int = 100) -> Dict[str, Any]:
    """
    延迟测试

    测试查询延迟的分布 (p50/p95/p99)
    """
    print("\n" + "=" * 50)
    print("延迟测试")
    print("=" * 50)

    clear_memory()

    # 初始化
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        # 先塑造一些记忆
        print("塑造测试记忆...")
        ts = datetime.now()
        for i in range(500):
            await coord.store_memory_with_timestamp(
                f"User mentioned fact number {i}: this is test content for memory {i}",
                ts + timedelta(minutes=i), "User", 0.5
            )

        # 等待巩固
        await asyncio.sleep(2)

        # 测试查询延迟
        print(f"运行 {num_queries} 次查询...")
        latencies = []
        queries = [
            "What did the user mention about fact 50?",
            "Tell me about the user's preferences",
            "What events happened recently?",
            "Summarize the user's activities",
            "What is fact number 100?",
        ]

        for i in tqdm(range(num_queries), desc="查询测试"):
            query = queries[i % len(queries)]
            start = time.time()

            context = {'skip_memory_store': True, 'evaluation_mode': True}
            await coord.process_user_input(query, context=context)

            latency = (time.time() - start) * 1000
            latencies.append(latency)

        # 计算统计
        results = {
            'num_queries': num_queries,
            'num_memories': 500,
            'latency_ms': {
                'mean': np.mean(latencies),
                'std': np.std(latencies),
                'min': np.min(latencies),
                'max': np.max(latencies),
                'p50': np.percentile(latencies, 50),
                'p75': np.percentile(latencies, 75),
                'p90': np.percentile(latencies, 90),
                'p95': np.percentile(latencies, 95),
                'p99': np.percentile(latencies, 99),
            },
            'raw_latencies': latencies
        }

        print(f"\n延迟统计 (ms):")
        print(f"  Mean: {results['latency_ms']['mean']:.0f}")
        print(f"  P50:  {results['latency_ms']['p50']:.0f}")
        print(f"  P95:  {results['latency_ms']['p95']:.0f}")
        print(f"  P99:  {results['latency_ms']['p99']:.0f}")

        return results

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


async def test_scalability(memory_sizes: List[int] = [100, 500, 1000, 5000, 10000]) -> Dict[str, Any]:
    """
    扩展性测试

    测试不同记忆数量下的性能变化
    """
    print("\n" + "=" * 50)
    print("扩展性测试")
    print("=" * 50)

    results = []

    for size in memory_sizes:
        print(f"\n测试记忆数量: {size}")
        clear_memory()

        # 初始化
        base_coord = BrainInspiredCoordinator()
        hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
        coord = HRMCoordinatorWrapper(base_coord, hrm_config)
        await coord.start_system()

        try:
            # 记录初始内存
            mem_before = get_memory_usage()

            # 塑造记忆
            ingest_start = time.time()
            ts = datetime.now()

            for i in tqdm(range(size), desc="塑造记忆", leave=False):
                await coord.store_memory_with_timestamp(
                    f"User mentioned fact {i}: content for memory number {i} with some additional text",
                    ts + timedelta(minutes=i), "User", 0.5
                )

            ingest_duration = (time.time() - ingest_start) * 1000

            # 等待巩固
            await asyncio.sleep(1)

            # 记录内存
            mem_after = get_memory_usage()
            disk_usage = get_disk_usage()

            # 测试查询延迟
            query_latencies = []
            for _ in range(20):
                start = time.time()
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                await coord.process_user_input(
                    f"What is fact number {size // 2}?",
                    context=context
                )
                query_latencies.append((time.time() - start) * 1000)

            result = {
                'memory_count': size,
                'ingest_duration_ms': ingest_duration,
                'ingest_rate_per_sec': size / (ingest_duration / 1000),
                'memory_usage_mb': {
                    'before': mem_before['rss_mb'],
                    'after': mem_after['rss_mb'],
                    'delta': mem_after['rss_mb'] - mem_before['rss_mb']
                },
                'disk_usage_mb': disk_usage['disk_mb'],
                'query_latency_ms': {
                    'mean': np.mean(query_latencies),
                    'p50': np.percentile(query_latencies, 50),
                    'p95': np.percentile(query_latencies, 95),
                }
            }

            results.append(result)

            print(f"  塑造耗时: {ingest_duration/1000:.1f}s ({result['ingest_rate_per_sec']:.0f}/s)")
            print(f"  内存增量: {result['memory_usage_mb']['delta']:.1f} MB")
            print(f"  磁盘使用: {result['disk_usage_mb']:.1f} MB")
            print(f"  查询延迟: p50={result['query_latency_ms']['p50']:.0f}ms, "
                  f"p95={result['query_latency_ms']['p95']:.0f}ms")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    return {'scalability_results': results}


async def test_throughput(duration_seconds: int = 30) -> Dict[str, Any]:
    """
    吞吐量测试

    测试系统在持续负载下的吞吐量
    """
    print("\n" + "=" * 50)
    print(f"吞吐量测试 ({duration_seconds}秒)")
    print("=" * 50)

    clear_memory()

    # 初始化
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        # 先塑造一些记忆
        ts = datetime.now()
        for i in range(200):
            await coord.store_memory_with_timestamp(
                f"Test memory {i}", ts, "User", 0.5
            )
        await asyncio.sleep(1)

        # 吞吐量测试
        queries_completed = 0
        latencies = []
        start_time = time.time()

        print("运行吞吐量测试...")
        while time.time() - start_time < duration_seconds:
            query_start = time.time()
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            await coord.process_user_input("What is test memory 100?", context=context)
            latency = (time.time() - query_start) * 1000
            latencies.append(latency)
            queries_completed += 1

        elapsed = time.time() - start_time
        qps = queries_completed / elapsed

        results = {
            'duration_seconds': duration_seconds,
            'queries_completed': queries_completed,
            'qps': qps,
            'latency_ms': {
                'mean': np.mean(latencies),
                'p50': np.percentile(latencies, 50),
                'p95': np.percentile(latencies, 95),
                'p99': np.percentile(latencies, 99),
            }
        }

        print(f"\n吞吐量: {qps:.2f} QPS")
        print(f"完成查询: {queries_completed}")
        print(f"延迟 p50: {results['latency_ms']['p50']:.0f}ms")
        print(f"延迟 p95: {results['latency_ms']['p95']:.0f}ms")

        return results

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


def estimate_api_cost(num_memories: int, num_queries: int) -> Dict[str, float]:
    """
    估算 API 成本

    基于 OpenAI 定价估算
    """
    # 定价 (USD, 2024)
    EMBEDDING_COST_PER_1K = 0.00002  # text-embedding-3-small
    GPT4O_MINI_INPUT_COST_PER_1K = 0.00015
    GPT4O_MINI_OUTPUT_COST_PER_1K = 0.0006

    # 估算 token 数量
    avg_memory_tokens = 50
    avg_query_tokens = 30
    avg_context_tokens = 500
    avg_response_tokens = 100

    # Embedding 成本 (每条记忆)
    embedding_cost = (num_memories * avg_memory_tokens / 1000) * EMBEDDING_COST_PER_1K

    # 查询成本
    query_input_cost = (num_queries * (avg_query_tokens + avg_context_tokens) / 1000) * GPT4O_MINI_INPUT_COST_PER_1K
    query_output_cost = (num_queries * avg_response_tokens / 1000) * GPT4O_MINI_OUTPUT_COST_PER_1K

    total_cost = embedding_cost + query_input_cost + query_output_cost

    return {
        'num_memories': num_memories,
        'num_queries': num_queries,
        'embedding_cost_usd': embedding_cost,
        'query_input_cost_usd': query_input_cost,
        'query_output_cost_usd': query_output_cost,
        'total_cost_usd': total_cost,
        'cost_per_1k_memories_usd': (embedding_cost / num_memories) * 1000 if num_memories > 0 else 0,
        'cost_per_query_usd': (query_input_cost + query_output_cost) / num_queries if num_queries > 0 else 0,
    }


async def main():
    parser = argparse.ArgumentParser(description='BMAM 效率分析')
    parser.add_argument('--test', type=str, default='all',
                       choices=['all', 'latency', 'scalability', 'throughput', 'cost'],
                       help='测试类型')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM 计算效率分析")
    print("=" * 70)

    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }

    start_time = datetime.now()

    # 延迟测试
    if args.test in ['all', 'latency']:
        results['tests']['latency'] = await test_latency(num_queries=50)

    # 扩展性测试
    if args.test in ['all', 'scalability']:
        results['tests']['scalability'] = await test_scalability(
            memory_sizes=[100, 500, 1000, 2000]
        )

    # 吞吐量测试
    if args.test in ['all', 'throughput']:
        results['tests']['throughput'] = await test_throughput(duration_seconds=20)

    # 成本估算
    if args.test in ['all', 'cost']:
        print("\n" + "=" * 50)
        print("API 成本估算")
        print("=" * 50)
        for memories, queries in [(1000, 100), (10000, 1000), (100000, 10000)]:
            cost = estimate_api_cost(memories, queries)
            print(f"\n{memories:,} 记忆 + {queries:,} 查询:")
            print(f"  Embedding: ${cost['embedding_cost_usd']:.4f}")
            print(f"  Query: ${cost['query_input_cost_usd'] + cost['query_output_cost_usd']:.4f}")
            print(f"  Total: ${cost['total_cost_usd']:.4f}")

        results['tests']['cost_estimates'] = {
            '1k_memories_100_queries': estimate_api_cost(1000, 100),
            '10k_memories_1k_queries': estimate_api_cost(10000, 1000),
            '100k_memories_10k_queries': estimate_api_cost(100000, 10000),
        }

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"efficiency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
