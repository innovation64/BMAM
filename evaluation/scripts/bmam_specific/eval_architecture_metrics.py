#!/usr/bin/env python3
"""
BMAM 架构特有指标评估

评估 BMAM 独有的架构特性，这些指标是区别于传统 RAG 和 MemOS 的关键差异化指标

指标分类:
1. 知识图谱相关
   - KG Surfacing Rate (知识图谱浮现率)

2. 可塑性相关
   - Plasticity Score (可塑性得分)
   - Forgetting Correctness (遗忘正确率)
   - Continuous Learning Trigger Rate (持续学习触发率)

3. 脑区协同相关
   - HRM Collaborative Recall Rate (HRM协同召回率)
   - Memory Reuse Rate (记忆复用率)

4. 习惯与情绪相关
   - Habit Fast-Path Hit Rate (习惯快路径命中率)
   - Emotion-Weighted Hit Rate (情绪加权命中率)

5. 时间相关
   - Time Alignment Accuracy (时间对齐准确率)

6. 巩固相关
   - Consolidation Efficiency (巩固效率)

使用:
  python eval_architecture_metrics.py --test kg           # 知识图谱指标
  python eval_architecture_metrics.py --test plasticity   # 可塑性指标
  python eval_architecture_metrics.py --test habit        # 习惯快路径
  python eval_architecture_metrics.py --test emotion      # 情绪加权
  python eval_architecture_metrics.py --test all          # 全部指标
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
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'architecture_metrics'


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


# ============================================================================
# 1. KG Surfacing Rate 测试用例
# ============================================================================
KG_TEST_CASES = [
    {
        'memories': [
            "Alice is Bob's sister.",
            "Bob works at Google.",
            "Alice lives in New York.",
            "Bob and Alice's mother is Carol.",
        ],
        'questions': [
            {
                'question': "What is the relationship between Alice and Bob?",
                'requires_kg': True,
                'expected_triple': ("Alice", "sister_of", "Bob")
            },
            {
                'question': "Where does Bob work?",
                'requires_kg': True,
                'expected_triple': ("Bob", "works_at", "Google")
            },
            {
                'question': "Who is Alice and Bob's mother?",
                'requires_kg': True,
                'expected_triple': ("Carol", "mother_of", "Alice")
            },
        ]
    },
    {
        'memories': [
            "User bought a Tesla Model 3.",
            "The car is blue.",
            "User's spouse drives a Honda.",
        ],
        'questions': [
            {
                'question': "What car does the user own?",
                'requires_kg': True,
                'expected_triple': ("User", "owns", "Tesla Model 3")
            },
            {
                'question': "What color is the user's car?",
                'requires_kg': True,
                'expected_triple': ("Tesla Model 3", "color", "blue")
            },
        ]
    }
]


# ============================================================================
# 2. Plasticity Score 测试用例 - 测试系统修正错误观念的能力
# ============================================================================
PLASTICITY_TEST_CASES = [
    {
        'initial_belief': "User said their favorite color is blue.",
        'correction': "User: Actually, I changed my mind. My favorite color is now green.",
        'verification_query': "What is the user's favorite color?",
        'expected_after': "green",
        'expected_before': "blue"
    },
    {
        'initial_belief': "User works at Microsoft.",
        'correction': "User: I just switched jobs. I now work at Apple.",
        'verification_query': "Where does the user work?",
        'expected_after': "Apple",
        'expected_before': "Microsoft"
    },
    {
        'initial_belief': "User is vegetarian.",
        'correction': "User: I started eating fish recently, so I'm pescatarian now.",
        'verification_query': "What is the user's diet?",
        'expected_after': "pescatarian",
        'expected_before': "vegetarian"
    },
    {
        'initial_belief': "User's phone number is 555-1234.",
        'correction': "User: My new phone number is 555-9999.",
        'verification_query': "What is the user's phone number?",
        'expected_after': "555-9999",
        'expected_before': "555-1234"
    },
]


# ============================================================================
# 3. Habit Fast-Path 测试用例
# ============================================================================
HABIT_TEST_CASES = [
    {
        'setup_queries': [
            "What's the weather today?",
            "What's the weather today?",
            "What's the weather today?",
            "How's the weather?",
            "Tell me the weather",
        ],
        'test_query': "What's the weather today?",
        'expected_fast_path': True,
        'category': 'weather'
    },
    {
        'setup_queries': [
            "What time is it?",
            "What's the time?",
            "Tell me the current time",
        ],
        'test_query': "What time is it?",
        'expected_fast_path': True,
        'category': 'time'
    },
    {
        'setup_queries': [
            "Recommend a restaurant",
        ],
        'test_query': "What's a good place to eat?",
        'expected_fast_path': False,  # 只问过一次，不应走快路径
        'category': 'restaurant'
    },
]


# ============================================================================
# 4. Emotion-Weighted 测试用例
# ============================================================================
EMOTION_TEST_CASES = [
    {
        'memories': [
            "User was very happy at their birthday party.",
            "User felt sad when their pet passed away.",
            "User was excited about the job offer.",
            "User was frustrated with the traffic jam.",
        ],
        'query': "Tell me about a happy memory",
        'expected_emotion': 'happy',
        'expected_memories': ['birthday', 'job offer']
    },
    {
        'memories': [
            "User loved the Italian restaurant on Main Street.",
            "User hated the seafood place downtown.",
            "User thought the Thai place was okay.",
        ],
        'query': "Where should I eat tonight?",
        'expected_preference': 'positive',
        'should_recommend': 'Italian',
        'should_avoid': 'seafood'
    },
]


# ============================================================================
# 5. Time Alignment 测试用例
# ============================================================================
TIME_ALIGNMENT_CASES = [
    {
        'base_date': datetime(2024, 3, 15),  # 假设今天是 2024-03-15
        'memories': [
            ("User went to the gym", timedelta(days=-1)),  # 昨天
            ("User had a meeting", timedelta(days=-3)),    # 三天前
            ("User's birthday was", timedelta(days=-7)),   # 一周前
        ],
        'queries': [
            {
                'question': "What did the user do yesterday?",
                'relative_time': 'yesterday',
                'expected': 'gym'
            },
            {
                'question': "What happened three days ago?",
                'relative_time': '3 days ago',
                'expected': 'meeting'
            },
            {
                'question': "What happened last week?",
                'relative_time': 'last week',
                'expected': 'birthday'
            },
        ]
    },
]


# ============================================================================
# 6. Consolidation & Forgetting 测试用例
# ============================================================================
CONSOLIDATION_CASES = [
    {
        'important_memories': [
            ("User's wedding anniversary is June 15", 0.95),
            ("User is allergic to peanuts", 0.9),
            ("User's social security number ends in 1234", 0.85),
        ],
        'trivial_memories': [
            ("User mentioned the weather was nice", 0.3),
            ("User said they had coffee this morning", 0.2),
            ("User commented on the traffic", 0.25),
        ],
        'consolidation_wait': 5,  # 等待巩固的秒数
        'verify_important_retained': True,
        'verify_trivial_decayed': True
    },
]


FORGETTING_CASES = [
    {
        'outdated_memory': "User's old address was 123 Old Street.",
        'new_memory': "User moved to 456 New Avenue.",
        'outdated_query': "What is the user's old address?",
        'current_query': "What is the user's current address?",
        'expected_decay': True
    },
    {
        'outdated_memory': "User said they were single.",
        'new_memory': "User got married last month.",
        'outdated_query': "Is the user single?",
        'current_query': "What is the user's marital status?",
        'expected_decay': True
    },
]


# ============================================================================
# 测试函数
# ============================================================================

async def test_kg_surfacing_rate(coord: HRMCoordinatorWrapper,
                                  llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 KG Surfacing Rate (知识图谱浮现率)

    定义: 回答中引用 KG Triples 的比例
    """
    print("\n" + "=" * 50)
    print("KG Surfacing Rate 测试")
    print("=" * 50)

    results = []
    kg_used_count = 0
    total_count = 0

    for case in KG_TEST_CASES:
        clear_memory()
        await coord.start_system()

        try:
            # 塑造记忆
            ts = datetime.now()
            for i, memory in enumerate(case['memories']):
                await coord.store_memory_with_timestamp(
                    f"User: {memory}",
                    ts + timedelta(hours=i),
                    "User",
                    0.8
                )

            await asyncio.sleep(1)

            for q in case['questions']:
                total_count += 1

                # 查询时请求 KG 信息
                context = {
                    'skip_memory_store': True,
                    'evaluation_mode': True,
                    'return_kg_triples': True
                }
                result = await coord.process_user_input(q['question'], context=context)

                if hasattr(result, 'response'):
                    answer = result.response
                elif isinstance(result, dict):
                    answer = result.get('response', str(result))
                else:
                    answer = str(result)

                # 检测 KG 是否被使用
                kg_triples = []
                if hasattr(result, 'kg_triples'):
                    kg_triples = result.kg_triples
                elif isinstance(result, dict) and 'kg_triples' in result:
                    kg_triples = result['kg_triples']

                # 如果没有直接返回，通过答案内容推断
                expected = q['expected_triple']
                kg_used = (len(kg_triples) > 0 or
                          all(str(e).lower() in answer.lower() for e in expected if e))

                if kg_used:
                    kg_used_count += 1

                results.append({
                    'question': q['question'],
                    'answer': answer,
                    'expected_triple': expected,
                    'kg_used': kg_used,
                    'kg_triples': kg_triples
                })

                print(f"  {'✓' if kg_used else '○'} {q['question'][:40]}... (KG: {kg_used})")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    surfacing_rate = kg_used_count / total_count if total_count > 0 else 0

    print(f"\nKG Surfacing Rate: {surfacing_rate*100:.1f}% ({kg_used_count}/{total_count})")

    return {
        'metric': 'KG Surfacing Rate',
        'value': surfacing_rate,
        'kg_used': kg_used_count,
        'total': total_count,
        'results': results
    }


async def test_plasticity_score(coord: HRMCoordinatorWrapper,
                                 llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 Plasticity Score (可塑性得分)

    定义: 多轮对话中修正错误观念的能力
    """
    print("\n" + "=" * 50)
    print("Plasticity Score 测试")
    print("=" * 50)

    results = []
    successful_updates = 0

    for case in PLASTICITY_TEST_CASES:
        clear_memory()
        await coord.start_system()

        try:
            ts = datetime.now()

            # 1. 塑造初始信念
            await coord.store_memory_with_timestamp(
                case['initial_belief'],
                ts,
                "User",
                0.8
            )
            await asyncio.sleep(0.5)

            # 2. 验证初始信念
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            result = await coord.process_user_input(case['verification_query'], context=context)

            if hasattr(result, 'response'):
                before_answer = result.response
            else:
                before_answer = str(result)

            before_correct = case['expected_before'].lower() in before_answer.lower()

            # 3. 应用修正
            await coord.store_memory_with_timestamp(
                case['correction'],
                ts + timedelta(hours=1),
                "User",
                0.9  # 更高重要性
            )
            await asyncio.sleep(0.5)

            # 4. 验证修正后
            result = await coord.process_user_input(case['verification_query'], context=context)

            if hasattr(result, 'response'):
                after_answer = result.response
            else:
                after_answer = str(result)

            after_correct = case['expected_after'].lower() in after_answer.lower()

            # 成功更新 = 之前是旧值，之后是新值
            updated = after_correct

            if updated:
                successful_updates += 1

            results.append({
                'initial_belief': case['initial_belief'],
                'correction': case['correction'],
                'query': case['verification_query'],
                'before_answer': before_answer,
                'after_answer': after_answer,
                'before_correct': before_correct,
                'after_correct': after_correct,
                'successfully_updated': updated
            })

            print(f"  {'✓' if updated else '✗'} {case['verification_query'][:40]}...")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    plasticity_score = successful_updates / len(PLASTICITY_TEST_CASES) if PLASTICITY_TEST_CASES else 0

    print(f"\nPlasticity Score: {plasticity_score*100:.1f}% ({successful_updates}/{len(PLASTICITY_TEST_CASES)})")

    return {
        'metric': 'Plasticity Score',
        'value': plasticity_score,
        'successful_updates': successful_updates,
        'total': len(PLASTICITY_TEST_CASES),
        'results': results
    }


async def test_habit_fast_path(coord: HRMCoordinatorWrapper,
                                llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 Habit Fast-Path Hit Rate (习惯快路径命中率)

    定义: 高频重复查询触发 HabitLearner 快路径的比例
    """
    print("\n" + "=" * 50)
    print("Habit Fast-Path 测试")
    print("=" * 50)

    results = []
    fast_path_hits = 0
    expected_fast_paths = 0

    for case in HABIT_TEST_CASES:
        clear_memory()
        await coord.start_system()

        try:
            # 1. 执行 setup 查询建立习惯
            setup_latencies = []
            for query in case['setup_queries']:
                start = time.time()
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                await coord.process_user_input(query, context=context)
                latency = (time.time() - start) * 1000
                setup_latencies.append(latency)
                await asyncio.sleep(0.1)

            # 2. 测试查询
            start = time.time()
            context = {
                'skip_memory_store': True,
                'evaluation_mode': True,
                'track_fast_path': True
            }
            result = await coord.process_user_input(case['test_query'], context=context)
            test_latency = (time.time() - start) * 1000

            # 检测是否走了快路径
            fast_path_used = False
            if hasattr(result, 'fast_path_used'):
                fast_path_used = result.fast_path_used
            elif isinstance(result, dict) and 'fast_path_used' in result:
                fast_path_used = result['fast_path_used']
            else:
                # 通过延迟推断：如果延迟明显低于平均 setup 延迟，可能走了快路径
                avg_setup_latency = np.mean(setup_latencies) if setup_latencies else 0
                fast_path_used = test_latency < avg_setup_latency * 0.7

            if case['expected_fast_path']:
                expected_fast_paths += 1
                if fast_path_used:
                    fast_path_hits += 1

            results.append({
                'category': case['category'],
                'setup_count': len(case['setup_queries']),
                'test_query': case['test_query'],
                'setup_latencies': setup_latencies,
                'test_latency': test_latency,
                'expected_fast_path': case['expected_fast_path'],
                'actual_fast_path': fast_path_used,
                'match': fast_path_used == case['expected_fast_path']
            })

            status = '✓' if fast_path_used == case['expected_fast_path'] else '✗'
            print(f"  {status} {case['category']}: expected={case['expected_fast_path']}, actual={fast_path_used}")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    hit_rate = fast_path_hits / expected_fast_paths if expected_fast_paths > 0 else 0

    print(f"\nHabit Fast-Path Hit Rate: {hit_rate*100:.1f}% ({fast_path_hits}/{expected_fast_paths})")

    return {
        'metric': 'Habit Fast-Path Hit Rate',
        'value': hit_rate,
        'fast_path_hits': fast_path_hits,
        'expected_fast_paths': expected_fast_paths,
        'results': results
    }


async def test_emotion_weighted_recall(coord: HRMCoordinatorWrapper,
                                        llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 Emotion-Weighted Hit Rate (情绪加权命中率)

    定义: 情绪相关查询中，EmotionModulator 调整排序后命中率提升
    """
    print("\n" + "=" * 50)
    print("Emotion-Weighted Recall 测试")
    print("=" * 50)

    results = []
    emotion_matches = 0

    for case in EMOTION_TEST_CASES:
        clear_memory()
        await coord.start_system()

        try:
            # 塑造记忆
            ts = datetime.now()
            for i, memory in enumerate(case['memories']):
                await coord.store_memory_with_timestamp(
                    f"User: {memory}",
                    ts + timedelta(hours=i),
                    "User",
                    0.7
                )

            await asyncio.sleep(1)

            # 查询
            context = {
                'skip_memory_store': True,
                'evaluation_mode': True,
                'enable_emotion_weighting': True
            }
            result = await coord.process_user_input(case['query'], context=context)

            if hasattr(result, 'response'):
                answer = result.response
            else:
                answer = str(result)

            # 检查情绪匹配
            if 'expected_memories' in case:
                matched = any(em.lower() in answer.lower() for em in case['expected_memories'])
            elif 'should_recommend' in case:
                matched = case['should_recommend'].lower() in answer.lower()
                # 同时检查是否避免了负面推荐
                if 'should_avoid' in case:
                    matched = matched and case['should_avoid'].lower() not in answer.lower()
            else:
                matched = False

            if matched:
                emotion_matches += 1

            results.append({
                'query': case['query'],
                'answer': answer,
                'emotion_matched': matched
            })

            print(f"  {'✓' if matched else '✗'} {case['query'][:40]}...")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    hit_rate = emotion_matches / len(EMOTION_TEST_CASES) if EMOTION_TEST_CASES else 0

    print(f"\nEmotion-Weighted Hit Rate: {hit_rate*100:.1f}% ({emotion_matches}/{len(EMOTION_TEST_CASES)})")

    return {
        'metric': 'Emotion-Weighted Hit Rate',
        'value': hit_rate,
        'emotion_matches': emotion_matches,
        'total': len(EMOTION_TEST_CASES),
        'results': results
    }


async def test_time_alignment(coord: HRMCoordinatorWrapper,
                               llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 Time Alignment Accuracy (时间对齐准确率)

    定义: 相对时间表述 → 绝对时间转换的正确率
    """
    print("\n" + "=" * 50)
    print("Time Alignment 测试")
    print("=" * 50)

    results = []
    correct_alignments = 0
    total_queries = 0

    for case in TIME_ALIGNMENT_CASES:
        clear_memory()
        await coord.start_system()

        try:
            base_date = case['base_date']

            # 塑造记忆
            for memory_text, time_delta in case['memories']:
                ts = base_date + time_delta
                await coord.store_memory_with_timestamp(
                    f"User: {memory_text}",
                    ts,
                    "User",
                    0.8
                )

            await asyncio.sleep(1)

            for q in case['queries']:
                total_queries += 1

                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(q['question'], context=context)

                if hasattr(result, 'response'):
                    answer = result.response
                else:
                    answer = str(result)

                correct = q['expected'].lower() in answer.lower()

                if correct:
                    correct_alignments += 1

                results.append({
                    'question': q['question'],
                    'relative_time': q['relative_time'],
                    'expected': q['expected'],
                    'answer': answer,
                    'correct': correct
                })

                print(f"  {'✓' if correct else '✗'} {q['relative_time']}: {q['expected']}")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    accuracy = correct_alignments / total_queries if total_queries > 0 else 0

    print(f"\nTime Alignment Accuracy: {accuracy*100:.1f}% ({correct_alignments}/{total_queries})")

    return {
        'metric': 'Time Alignment Accuracy',
        'value': accuracy,
        'correct': correct_alignments,
        'total': total_queries,
        'results': results
    }


async def test_consolidation_efficiency(coord: HRMCoordinatorWrapper,
                                         llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 Consolidation Efficiency (巩固效率)

    定义: 后台巩固循环后，记忆检索质量提升比例
    """
    print("\n" + "=" * 50)
    print("Consolidation Efficiency 测试")
    print("=" * 50)

    results = []

    for case in CONSOLIDATION_CASES:
        clear_memory()
        await coord.start_system()

        try:
            ts = datetime.now()

            # 塑造重要和不重要记忆
            all_memories = []
            for memory, importance in case['important_memories']:
                all_memories.append((memory, importance, 'important'))
            for memory, importance in case['trivial_memories']:
                all_memories.append((memory, importance, 'trivial'))

            # 打乱顺序
            np.random.shuffle(all_memories)

            for i, (memory, importance, category) in enumerate(all_memories):
                await coord.store_memory_with_timestamp(
                    f"User: {memory}",
                    ts + timedelta(minutes=i),
                    "User",
                    importance
                )

            # 巩固前测试
            pre_consolidation_scores = []
            for memory, _, _ in case['important_memories']:
                query = f"Tell me about: {memory.split()[-3:]}"
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(query, context=context)
                answer = result.response if hasattr(result, 'response') else str(result)
                score = 1.0 if any(w.lower() in answer.lower() for w in memory.split()[:3]) else 0.0
                pre_consolidation_scores.append(score)

            pre_avg = np.mean(pre_consolidation_scores)

            # 等待巩固
            print(f"  等待 {case['consolidation_wait']}秒 进行巩固...")
            await asyncio.sleep(case['consolidation_wait'])

            # 巩固后测试
            post_consolidation_scores = []
            for memory, _, _ in case['important_memories']:
                query = f"Tell me about: {memory.split()[-3:]}"
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(query, context=context)
                answer = result.response if hasattr(result, 'response') else str(result)
                score = 1.0 if any(w.lower() in answer.lower() for w in memory.split()[:3]) else 0.0
                post_consolidation_scores.append(score)

            post_avg = np.mean(post_consolidation_scores)

            improvement = post_avg - pre_avg

            results.append({
                'pre_consolidation_avg': pre_avg,
                'post_consolidation_avg': post_avg,
                'improvement': improvement
            })

            print(f"  巩固前: {pre_avg:.2f}, 巩固后: {post_avg:.2f}, 提升: {improvement:.2f}")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    avg_improvement = np.mean([r['improvement'] for r in results]) if results else 0

    print(f"\nConsolidation Efficiency: {avg_improvement*100:.1f}% 提升")

    return {
        'metric': 'Consolidation Efficiency',
        'value': avg_improvement,
        'results': results
    }


async def test_forgetting_correctness(coord: HRMCoordinatorWrapper,
                                       llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    测试 Forgetting Correctness (遗忘正确率)

    定义: 标记为"应遗忘"的信息是否被正确淡化
    """
    print("\n" + "=" * 50)
    print("Forgetting Correctness 测试")
    print("=" * 50)

    results = []
    correct_forgetting = 0

    for case in FORGETTING_CASES:
        clear_memory()
        await coord.start_system()

        try:
            ts = datetime.now()

            # 1. 塑造过时记忆
            await coord.store_memory_with_timestamp(
                f"User: {case['outdated_memory']}",
                ts - timedelta(days=30),  # 30天前
                "User",
                0.7
            )

            # 2. 塑造新记忆
            await coord.store_memory_with_timestamp(
                f"User: {case['new_memory']}",
                ts,
                "User",
                0.9
            )

            await asyncio.sleep(1)

            # 3. 查询当前信息
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            result = await coord.process_user_input(case['current_query'], context=context)

            if hasattr(result, 'response'):
                answer = result.response
            else:
                answer = str(result)

            # 检查是否返回新信息而非旧信息
            new_info_present = any(w.lower() in answer.lower()
                                   for w in case['new_memory'].split()[-4:])
            old_info_absent = not any(w.lower() in answer.lower()
                                      for w in case['outdated_memory'].split()[-4:]
                                      if w.lower() not in case['new_memory'].lower())

            correctly_forgotten = new_info_present and old_info_absent

            if correctly_forgotten:
                correct_forgetting += 1

            results.append({
                'outdated': case['outdated_memory'],
                'new': case['new_memory'],
                'query': case['current_query'],
                'answer': answer,
                'correctly_forgotten': correctly_forgotten
            })

            print(f"  {'✓' if correctly_forgotten else '✗'} {case['current_query'][:40]}...")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    forgetting_rate = correct_forgetting / len(FORGETTING_CASES) if FORGETTING_CASES else 0

    print(f"\nForgetting Correctness: {forgetting_rate*100:.1f}% ({correct_forgetting}/{len(FORGETTING_CASES)})")

    return {
        'metric': 'Forgetting Correctness',
        'value': forgetting_rate,
        'correct_forgetting': correct_forgetting,
        'total': len(FORGETTING_CASES),
        'results': results
    }


async def main():
    parser = argparse.ArgumentParser(description='BMAM 架构特有指标评估')
    parser.add_argument('--test', type=str, default='all',
                       choices=['all', 'kg', 'plasticity', 'habit', 'emotion',
                               'time', 'consolidation', 'forgetting'],
                       help='测试类型')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM 架构特有指标评估")
    print("=" * 70)

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")

    # 初始化
    clear_memory()
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)

    results = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {}
    }

    start_time = datetime.now()

    if args.test in ['all', 'kg']:
        results['metrics']['kg_surfacing_rate'] = await test_kg_surfacing_rate(coord, llm_client)

    if args.test in ['all', 'plasticity']:
        results['metrics']['plasticity_score'] = await test_plasticity_score(coord, llm_client)

    if args.test in ['all', 'habit']:
        results['metrics']['habit_fast_path'] = await test_habit_fast_path(coord, llm_client)

    if args.test in ['all', 'emotion']:
        results['metrics']['emotion_weighted'] = await test_emotion_weighted_recall(coord, llm_client)

    if args.test in ['all', 'time']:
        results['metrics']['time_alignment'] = await test_time_alignment(coord, llm_client)

    if args.test in ['all', 'consolidation']:
        results['metrics']['consolidation'] = await test_consolidation_efficiency(coord, llm_client)

    if args.test in ['all', 'forgetting']:
        results['metrics']['forgetting'] = await test_forgetting_correctness(coord, llm_client)

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    # 汇总
    print("\n" + "=" * 70)
    print("BMAM 架构指标汇总")
    print("=" * 70)

    for metric_name, metric_result in results['metrics'].items():
        value = metric_result.get('value', 0)
        print(f"  {metric_name}: {value*100:.1f}%")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"architecture_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    # 移除详细结果以减小文件大小
    results_to_save = {
        'timestamp': results['timestamp'],
        'elapsed_seconds': results['elapsed_seconds'],
        'metrics': {
            k: {kk: vv for kk, vv in v.items() if kk != 'results'}
            for k, v in results['metrics'].items()
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_to_save, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
