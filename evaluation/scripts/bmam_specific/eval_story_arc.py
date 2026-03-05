#!/usr/bin/env python3
"""
BMAM StoryArc 模块评估

StoryArc 是 BMAM V2.0 的核心创新之一，用于时间线管理和时序推理

评估维度:
1. 时间线构建质量 - 事件排序正确性
2. 时序推理能力 - before/after/during 关系
3. 时间跨度理解 - 短期/中期/长期事件
4. 时间冲突检测 - 矛盾时间信息处理
5. 事件因果链推理 - 基于时间的因果关系

使用:
  python eval_story_arc.py --test timeline       # 时间线构建
  python eval_story_arc.py --test temporal       # 时序推理
  python eval_story_arc.py --test conflict       # 冲突检测
  python eval_story_arc.py --test all            # 全部测试
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
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'bmam_specific'


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


# 时间线构建测试用例
TIMELINE_TEST_CASES = [
    {
        'events': [
            ("User graduated from college", "2018-05-15"),
            ("User started first job", "2018-07-01"),
            ("User got promoted", "2020-03-15"),
            ("User changed companies", "2022-01-10"),
        ],
        'questions': [
            ("What happened first: graduation or first job?", "graduation"),
            ("List the user's career events in order", ["graduated", "started", "promoted", "changed"]),
            ("What happened after the promotion?", "changed companies"),
        ]
    },
    {
        'events': [
            ("User met Sarah at a party", "2019-12-31"),
            ("User and Sarah started dating", "2020-02-14"),
            ("User proposed to Sarah", "2021-06-20"),
            ("User and Sarah got married", "2022-09-10"),
        ],
        'questions': [
            ("When did the user meet Sarah?", "2019"),
            ("What happened between meeting Sarah and getting married?", ["dating", "proposed"]),
            ("How long were they dating before the proposal?", "about a year"),
        ]
    },
]


# 时序推理测试用例
TEMPORAL_REASONING_CASES = [
    {
        'memories': [
            "User bought a car in January 2020.",
            "User sold the car in December 2022.",
            "User bought a new car in March 2023."
        ],
        'questions': [
            {
                'question': "Did the user have a car in June 2021?",
                'answer': "yes",
                'reasoning': "The user bought a car in Jan 2020 and sold it in Dec 2022"
            },
            {
                'question': "How long did the user own the first car?",
                'answer': "almost 3 years",
                'reasoning': "From Jan 2020 to Dec 2022"
            },
            {
                'question': "Was there any time when the user didn't have a car?",
                'answer': "yes, between December 2022 and March 2023",
                'reasoning': "Gap between selling and buying new car"
            }
        ]
    },
    {
        'memories': [
            "User started learning Python in 2018.",
            "User built their first web app in 2019.",
            "User learned machine learning in 2020.",
            "User got a job as ML engineer in 2021."
        ],
        'questions': [
            {
                'question': "Could the user have used ML skills in 2019?",
                'answer': "no",
                'reasoning': "User learned ML in 2020, after building the web app"
            },
            {
                'question': "What skills did the user have before getting the ML job?",
                'answer': "Python, web development, machine learning",
                'reasoning': "All learned before 2021"
            }
        ]
    }
]


# 时间冲突检测测试用例
TEMPORAL_CONFLICT_CASES = [
    {
        'memories': [
            "User said they were in Paris on July 4th, 2023.",
            "User mentioned attending a meeting in New York on July 4th, 2023.",
        ],
        'question': "Where was the user on July 4th, 2023?",
        'expected_behavior': "detect_conflict",
        'notes': "System should identify the location conflict"
    },
    {
        'memories': [
            "User bought the house in 2015.",
            "User said they moved into the house in 2014.",
        ],
        'question': "When did the user start living in the house?",
        'expected_behavior': "detect_conflict",
        'notes': "Can't move into a house before buying it"
    },
    {
        'memories': [
            "User's child was born in 2010.",
            "User said they got married in 2012.",
        ],
        'question': "When did the user get married relative to having their child?",
        'expected_behavior': "acknowledge_timeline",
        'notes': "This is unusual but not impossible"
    },
]


# 事件因果链测试用例
CAUSAL_CHAIN_CASES = [
    {
        'memories': [
            "User studied hard for the exam.",
            "User passed the exam with high scores.",
            "User got accepted into the university.",
            "User received a scholarship."
        ],
        'question': "Why did the user receive a scholarship?",
        'expected_chain': ["studied", "passed", "accepted", "scholarship"],
        'reasoning': "Temporal causal chain from studying to scholarship"
    },
    {
        'memories': [
            "User started exercising regularly in January.",
            "User lost 10 pounds by March.",
            "User's health improved.",
            "User's doctor reduced their medication."
        ],
        'question': "What led to the doctor reducing the user's medication?",
        'expected_chain': ["exercising", "lost weight", "health improved", "reduced medication"],
        'reasoning': "Exercise led to weight loss, health improvement, medication reduction"
    },
]


async def test_timeline_construction(coord: HRMCoordinatorWrapper,
                                      llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """测试时间线构建质量"""
    print("\n" + "=" * 50)
    print("时间线构建测试")
    print("=" * 50)

    results = []

    for case_idx, case in enumerate(TIMELINE_TEST_CASES):
        print(f"\n测试案例 {case_idx + 1}/{len(TIMELINE_TEST_CASES)}")

        clear_memory()
        await coord.start_system()

        try:
            # 塑造事件记忆 (打乱顺序)
            events = case['events'].copy()
            np.random.shuffle(events)  # 打乱顺序测试排序能力

            for event, date_str in events:
                ts = datetime.strptime(date_str, "%Y-%m-%d")
                await coord.store_memory_with_timestamp(
                    f"User: {event}",
                    ts,
                    "User",
                    0.8
                )

            await asyncio.sleep(1)

            # 测试问题
            case_results = []
            for q, expected in case['questions']:
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(q, context=context)

                if hasattr(result, 'response'):
                    answer = result.response
                elif isinstance(result, dict):
                    answer = result.get('response', str(result))
                else:
                    answer = str(result)

                # 评估
                if isinstance(expected, list):
                    # 检查顺序
                    all_present = all(e.lower() in answer.lower() for e in expected)
                    correct_order = check_order_in_text(answer, expected)
                    is_correct = all_present and correct_order
                else:
                    is_correct = expected.lower() in answer.lower()

                case_results.append({
                    'question': q,
                    'expected': expected,
                    'answer': answer,
                    'is_correct': is_correct
                })

                print(f"  {'✓' if is_correct else '✗'} {q[:40]}...")

            results.append({
                'case_idx': case_idx,
                'results': case_results,
                'accuracy': sum(1 for r in case_results if r['is_correct']) / len(case_results)
            })

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    overall_acc = np.mean([r['accuracy'] for r in results])
    print(f"\n时间线构建准确率: {overall_acc*100:.1f}%")

    return {
        'test': 'timeline_construction',
        'results': results,
        'overall_accuracy': overall_acc
    }


def check_order_in_text(text: str, expected_order: List[str]) -> bool:
    """检查文本中词语是否按预期顺序出现"""
    text_lower = text.lower()
    last_pos = -1

    for word in expected_order:
        pos = text_lower.find(word.lower())
        if pos == -1:
            return False
        if pos < last_pos:
            return False
        last_pos = pos

    return True


async def test_temporal_reasoning(coord: HRMCoordinatorWrapper,
                                   llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """测试时序推理能力"""
    print("\n" + "=" * 50)
    print("时序推理测试")
    print("=" * 50)

    results = []

    for case_idx, case in enumerate(TEMPORAL_REASONING_CASES):
        print(f"\n测试案例 {case_idx + 1}/{len(TEMPORAL_REASONING_CASES)}")

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

            case_results = []
            for q in case['questions']:
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(q['question'], context=context)

                if hasattr(result, 'response'):
                    answer = result.response
                elif isinstance(result, dict):
                    answer = result.get('response', str(result))
                else:
                    answer = str(result)

                # 评估
                is_correct = q['answer'].lower() in answer.lower()

                # LLM 评估
                if llm_client:
                    try:
                        prompt = f"""Evaluate if the answer demonstrates correct temporal reasoning.

Question: {q['question']}
Expected reasoning: {q['reasoning']}
Expected answer should contain: {q['answer']}
Generated answer: {answer}

Return JSON: {{"correct": true/false, "reasoning_quality": 0.0-1.0}}"""

                        r = await llm_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0
                        )
                        judge_result = json.loads(r.choices[0].message.content)
                        is_correct = judge_result.get('correct', is_correct)
                        reasoning_quality = judge_result.get('reasoning_quality', 0.5)
                    except:
                        reasoning_quality = 0.5
                else:
                    reasoning_quality = 0.5

                case_results.append({
                    'question': q['question'],
                    'expected': q['answer'],
                    'answer': answer,
                    'is_correct': is_correct,
                    'reasoning_quality': reasoning_quality
                })

                print(f"  {'✓' if is_correct else '✗'} {q['question'][:40]}...")

            results.append({
                'case_idx': case_idx,
                'results': case_results,
                'accuracy': sum(1 for r in case_results if r['is_correct']) / len(case_results)
            })

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    overall_acc = np.mean([r['accuracy'] for r in results])
    print(f"\n时序推理准确率: {overall_acc*100:.1f}%")

    return {
        'test': 'temporal_reasoning',
        'results': results,
        'overall_accuracy': overall_acc
    }


async def test_temporal_conflict_detection(coord: HRMCoordinatorWrapper,
                                            llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """测试时间冲突检测能力"""
    print("\n" + "=" * 50)
    print("时间冲突检测测试")
    print("=" * 50)

    results = []

    for case_idx, case in enumerate(TEMPORAL_CONFLICT_CASES):
        print(f"\n测试案例 {case_idx + 1}/{len(TEMPORAL_CONFLICT_CASES)}")
        print(f"  预期行为: {case['expected_behavior']}")

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

            # 查询
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            result = await coord.process_user_input(case['question'], context=context)

            if hasattr(result, 'response'):
                answer = result.response
            elif isinstance(result, dict):
                answer = result.get('response', str(result))
            else:
                answer = str(result)

            # 检测是否识别了冲突
            conflict_keywords = ['conflict', 'inconsistent', 'contradiction', 'unclear',
                               'both', 'different', 'confusing', 'uncertain']
            detected_conflict = any(kw in answer.lower() for kw in conflict_keywords)

            expected_detection = case['expected_behavior'] == 'detect_conflict'
            is_correct = detected_conflict == expected_detection

            results.append({
                'case_idx': case_idx,
                'memories': case['memories'],
                'question': case['question'],
                'answer': answer,
                'expected_behavior': case['expected_behavior'],
                'detected_conflict': detected_conflict,
                'is_correct': is_correct,
                'notes': case['notes']
            })

            print(f"  检测冲突: {detected_conflict}")
            print(f"  {'✓' if is_correct else '✗'} 结果正确")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    overall_acc = sum(1 for r in results if r['is_correct']) / len(results)
    print(f"\n冲突检测准确率: {overall_acc*100:.1f}%")

    return {
        'test': 'temporal_conflict_detection',
        'results': results,
        'overall_accuracy': overall_acc
    }


async def main():
    parser = argparse.ArgumentParser(description='BMAM StoryArc 评估')
    parser.add_argument('--test', type=str, default='all',
                       choices=['all', 'timeline', 'temporal', 'conflict'],
                       help='测试类型')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM StoryArc 模块评估")
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
        'module': 'StoryArc',
        'tests': {}
    }

    start_time = datetime.now()

    if args.test in ['all', 'timeline']:
        results['tests']['timeline'] = await test_timeline_construction(coord, llm_client)

    if args.test in ['all', 'temporal']:
        results['tests']['temporal'] = await test_temporal_reasoning(coord, llm_client)

    if args.test in ['all', 'conflict']:
        results['tests']['conflict'] = await test_temporal_conflict_detection(coord, llm_client)

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    # 汇总
    print("\n" + "=" * 70)
    print("StoryArc 评估汇总")
    print("=" * 70)

    for test_name, test_result in results['tests'].items():
        print(f"  {test_name}: {test_result['overall_accuracy']*100:.1f}%")

    overall = np.mean([t['overall_accuracy'] for t in results['tests'].values()])
    print(f"\n  总体: {overall*100:.1f}%")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"story_arc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
