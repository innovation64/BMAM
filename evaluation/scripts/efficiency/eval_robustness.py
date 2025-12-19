#!/usr/bin/env python3
"""
BMAM 检索鲁棒性测试

测试系统在不同负载下的稳定性和可靠性

测试维度:
1. 并发查询压力测试 (模拟 QPS)
2. 成功率统计
3. 延迟分布 (P50/P90/P99)
4. 错误类型分析

使用:
  python eval_robustness.py --qps 1 5 10 20    # 测试不同 QPS
  python eval_robustness.py --duration 60      # 运行 60 秒
"""

import asyncio
import json
import os
import sys
import argparse
import shutil
import time
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

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'robustness'


# 测试查询
TEST_QUERIES = [
    "What is the user's name?",
    "Where does the user work?",
    "What are the user's hobbies?",
    "When did the user last travel?",
    "What food does the user prefer?",
    "Who is the user's best friend?",
    "What is the user's favorite movie?",
    "Where did the user go to school?",
    "What is the user's phone number?",
    "Does the user have any pets?",
]


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


class QueryResult:
    """查询结果"""
    def __init__(self, query: str, start_time: float):
        self.query = query
        self.start_time = start_time
        self.end_time: Optional[float] = None
        self.success: bool = False
        self.error: Optional[str] = None
        self.response: Optional[str] = None

    @property
    def latency_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


async def single_query(coord: HRMCoordinatorWrapper,
                        query: str,
                        semaphore: asyncio.Semaphore) -> QueryResult:
    """执行单个查询"""
    result = QueryResult(query, time.time())

    async with semaphore:
        try:
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            response = await coord.process_user_input(query, context=context)

            if hasattr(response, 'response'):
                result.response = response.response
            elif isinstance(response, dict):
                result.response = response.get('response', str(response))
            else:
                result.response = str(response)

            result.success = True
        except Exception as e:
            result.error = str(e)
            result.success = False

        result.end_time = time.time()
        return result


async def run_qps_test(coord: HRMCoordinatorWrapper,
                        target_qps: int,
                        duration_seconds: int) -> Dict[str, Any]:
    """
    运行 QPS 测试

    使用令牌桶算法控制查询速率
    """
    print(f"\n测试 QPS={target_qps}, 持续 {duration_seconds}s")

    # 并发控制
    max_concurrent = min(target_qps * 2, 50)  # 最大并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    results: List[QueryResult] = []
    start_time = time.time()
    end_time = start_time + duration_seconds

    # 计算查询间隔
    interval = 1.0 / target_qps if target_qps > 0 else 1.0

    query_idx = 0
    tasks = []

    while time.time() < end_time:
        # 获取下一个查询
        query = TEST_QUERIES[query_idx % len(TEST_QUERIES)]
        query_idx += 1

        # 创建查询任务
        task = asyncio.create_task(single_query(coord, query, semaphore))
        tasks.append(task)

        # 控制速率
        await asyncio.sleep(interval)

    # 等待所有任务完成
    if tasks:
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in completed_results:
            if isinstance(r, QueryResult):
                results.append(r)

    # 统计
    total_queries = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total_queries - successful

    success_rate = successful / total_queries if total_queries > 0 else 0

    latencies = [r.latency_ms for r in results if r.success]

    if latencies:
        latency_stats = {
            'mean': np.mean(latencies),
            'std': np.std(latencies),
            'min': np.min(latencies),
            'max': np.max(latencies),
            'p50': np.percentile(latencies, 50),
            'p90': np.percentile(latencies, 90),
            'p99': np.percentile(latencies, 99),
        }
    else:
        latency_stats = {}

    # 错误分析
    error_types = defaultdict(int)
    for r in results:
        if r.error:
            # 简化错误类型
            error_key = r.error[:50] if len(r.error) > 50 else r.error
            error_types[error_key] += 1

    actual_qps = total_queries / duration_seconds

    print(f"  完成 {total_queries} 查询, 实际 QPS: {actual_qps:.1f}")
    print(f"  成功率: {success_rate*100:.1f}%")
    if latency_stats:
        print(f"  延迟: mean={latency_stats['mean']:.0f}ms, "
              f"p50={latency_stats['p50']:.0f}ms, p99={latency_stats['p99']:.0f}ms")

    return {
        'target_qps': target_qps,
        'actual_qps': actual_qps,
        'duration_seconds': duration_seconds,
        'total_queries': total_queries,
        'successful': successful,
        'failed': failed,
        'success_rate': success_rate,
        'latency_ms': latency_stats,
        'error_types': dict(error_types)
    }


async def run_memory_operations_test(coord: HRMCoordinatorWrapper,
                                      num_operations: int = 100) -> Dict[str, Any]:
    """
    测试记忆添加和搜索操作的鲁棒性
    """
    print(f"\n记忆操作测试 ({num_operations} 次)")

    add_results = []
    search_results = []

    # 测试 ADD 操作
    print("  测试 ADD 操作...")
    ts = datetime.now()

    for i in tqdm(range(num_operations), desc="  ADD", leave=False):
        start = time.time()
        success = True
        error = None

        try:
            await coord.store_memory_with_timestamp(
                f"User mentioned fact {i}: test content for memory operation {i}",
                ts + timedelta(seconds=i),
                "User",
                0.7
            )
        except Exception as e:
            success = False
            error = str(e)

        latency = (time.time() - start) * 1000
        add_results.append({
            'success': success,
            'latency_ms': latency,
            'error': error
        })

    # 测试 SEARCH 操作
    print("  测试 SEARCH 操作...")

    for i in tqdm(range(num_operations), desc="  SEARCH", leave=False):
        start = time.time()
        success = True
        error = None

        try:
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            await coord.process_user_input(f"What is fact {i}?", context=context)
        except Exception as e:
            success = False
            error = str(e)

        latency = (time.time() - start) * 1000
        search_results.append({
            'success': success,
            'latency_ms': latency,
            'error': error
        })

    # 统计
    def compute_stats(results: List[Dict]) -> Dict:
        successful = [r for r in results if r['success']]
        latencies = [r['latency_ms'] for r in successful]

        return {
            'total': len(results),
            'successful': len(successful),
            'failed': len(results) - len(successful),
            'success_rate': len(successful) / len(results) if results else 0,
            'latency_ms': {
                'mean': np.mean(latencies) if latencies else 0,
                'p50': np.percentile(latencies, 50) if latencies else 0,
                'p90': np.percentile(latencies, 90) if latencies else 0,
                'p99': np.percentile(latencies, 99) if latencies else 0,
            }
        }

    add_stats = compute_stats(add_results)
    search_stats = compute_stats(search_results)

    print(f"  ADD: 成功率={add_stats['success_rate']*100:.1f}%, "
          f"p50={add_stats['latency_ms']['p50']:.0f}ms")
    print(f"  SEARCH: 成功率={search_stats['success_rate']*100:.1f}%, "
          f"p50={search_stats['latency_ms']['p50']:.0f}ms")

    return {
        'add': add_stats,
        'search': search_stats
    }


async def main():
    parser = argparse.ArgumentParser(description='BMAM 检索鲁棒性测试')
    parser.add_argument('--qps', type=int, nargs='+', default=[1, 5, 10],
                       help='目标 QPS 值')
    parser.add_argument('--duration', type=int, default=30,
                       help='每个 QPS 测试持续时间 (秒)')
    parser.add_argument('--operations', type=int, default=100,
                       help='记忆操作测试数量')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM 检索鲁棒性测试")
    print("=" * 70)
    print(f"QPS 测试: {args.qps}")
    print(f"每次持续: {args.duration}s")

    results = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'qps_levels': args.qps,
            'duration_per_qps': args.duration,
            'operations_test_size': args.operations
        },
        'qps_tests': [],
        'memory_operations': None
    }

    start_time = datetime.now()

    # 初始化
    clear_memory()
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        # 预热：塑造一些基础记忆
        print("\n预热：塑造基础记忆...")
        ts = datetime.now()
        for i in range(50):
            await coord.store_memory_with_timestamp(
                f"User info {i}: name John, work at Tech Corp, hobby is reading",
                ts, "User", 0.7
            )
        await asyncio.sleep(1)

        # QPS 测试
        for qps in args.qps:
            result = await run_qps_test(coord, qps, args.duration)
            results['qps_tests'].append(result)

        # 记忆操作测试
        clear_memory()
        await coord.stop_system()
        base_coord = BrainInspiredCoordinator()
        coord = HRMCoordinatorWrapper(base_coord, hrm_config)
        await coord.start_system()

        results['memory_operations'] = await run_memory_operations_test(
            coord, args.operations
        )

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    # 汇总
    print("\n" + "=" * 70)
    print("鲁棒性测试汇总")
    print("=" * 70)

    print("\nQPS vs 成功率/延迟:")
    print(f"{'QPS':>6} | {'成功率':>8} | {'P50(ms)':>8} | {'P99(ms)':>8}")
    print("-" * 40)
    for test in results['qps_tests']:
        success = test['success_rate'] * 100
        p50 = test['latency_ms'].get('p50', 0)
        p99 = test['latency_ms'].get('p99', 0)
        print(f"{test['target_qps']:>6} | {success:>7.1f}% | {p50:>8.0f} | {p99:>8.0f}")

    print("\n记忆操作:")
    ops = results['memory_operations']
    print(f"  ADD:    成功率 {ops['add']['success_rate']*100:.1f}%, "
          f"P50 {ops['add']['latency_ms']['p50']:.0f}ms, "
          f"P99 {ops['add']['latency_ms']['p99']:.0f}ms")
    print(f"  SEARCH: 成功率 {ops['search']['success_rate']*100:.1f}%, "
          f"P50 {ops['search']['latency_ms']['p50']:.0f}ms, "
          f"P99 {ops['search']['latency_ms']['p99']:.0f}ms")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"robustness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
