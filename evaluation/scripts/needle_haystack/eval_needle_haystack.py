#!/usr/bin/env python3
"""
Needle-in-Haystack 测试脚本

测试 BMAM 在大规模记忆中检索特定信息的能力

实验设计:
1. 生成大量"干草堆"记忆 (无关信息)
2. 在不同深度插入"针" (关键信息)
3. 测试系统是否能准确检索"针"

可调参数:
- haystack_size: 干草堆大小 (1K, 10K, 100K)
- needle_depth: 针的深度位置 (0%, 25%, 50%, 75%, 100%)
- needle_type: 针的类型 (fact, event, preference)

使用:
  python eval_needle_haystack.py --size 1000 --depths 0 25 50 75 100
  python eval_needle_haystack.py --size 10000 --depths 50
"""

import asyncio
import json
import os
import sys
import argparse
import time
import random
import shutil
from datetime import datetime, timedelta
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
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'needle_haystack'


# 干草堆模板 (生成无关信息)
HAYSTACK_TEMPLATES = [
    "User discussed the weather forecast for {city}. It will be {weather} tomorrow.",
    "User mentioned they went to {place} and enjoyed {activity}.",
    "User talked about their {relation} who lives in {city}.",
    "User shared that they prefer {food} for {meal}.",
    "User mentioned they watched {movie} and thought it was {opinion}.",
    "User discussed their work project about {topic}.",
    "User talked about buying {item} from {store}.",
    "User mentioned they exercise by doing {exercise} {frequency}.",
    "User shared their favorite {category} is {item}.",
    "User discussed plans to visit {city} in {month}.",
]

HAYSTACK_FILLERS = {
    'city': ['New York', 'London', 'Tokyo', 'Paris', 'Sydney', 'Berlin', 'Rome', 'Madrid', 'Seoul', 'Dubai'],
    'weather': ['sunny', 'rainy', 'cloudy', 'snowy', 'windy', 'humid', 'cold', 'warm'],
    'place': ['museum', 'park', 'restaurant', 'beach', 'mountain', 'mall', 'theater', 'gym'],
    'activity': ['hiking', 'swimming', 'reading', 'painting', 'cooking', 'shopping', 'dining'],
    'relation': ['friend', 'cousin', 'colleague', 'neighbor', 'classmate', 'mentor'],
    'food': ['pizza', 'sushi', 'pasta', 'salad', 'soup', 'steak', 'tacos'],
    'meal': ['breakfast', 'lunch', 'dinner', 'snack'],
    'movie': ['action film', 'comedy', 'drama', 'documentary', 'thriller'],
    'opinion': ['amazing', 'okay', 'boring', 'interesting', 'thought-provoking'],
    'topic': ['AI', 'marketing', 'design', 'finance', 'engineering'],
    'item': ['laptop', 'phone', 'clothes', 'books', 'furniture'],
    'store': ['Amazon', 'local shop', 'online store', 'mall'],
    'exercise': ['running', 'yoga', 'swimming', 'cycling', 'weight training'],
    'frequency': ['daily', 'weekly', 'twice a week', 'monthly'],
    'category': ['color', 'season', 'music genre', 'cuisine', 'sport'],
    'month': ['January', 'March', 'June', 'September', 'December'],
}

# 针模板 (关键信息)
NEEDLE_TEMPLATES = {
    'fact': {
        'template': "User's {attribute} is {value}.",
        'question': "What is the user's {attribute}?",
        'attributes': [
            ('birthday', 'March 15, 1990'),
            ('phone number', '555-123-4567'),
            ('email', 'user@example.com'),
            ('address', '123 Main Street, Anytown'),
            ('social security last 4', '1234'),
        ]
    },
    'event': {
        'template': "User attended {event} on {date}.",
        'question': "When did the user attend {event}?",
        'events': [
            ('their wedding', 'June 20, 2020'),
            ('graduation ceremony', 'May 15, 2018'),
            ('job interview at Google', 'October 3, 2023'),
            ('medical checkup', 'January 8, 2024'),
            ('sister\'s birthday party', 'April 12, 2023'),
        ]
    },
    'preference': {
        'template': "User specifically mentioned they {preference}.",
        'question': "What did the user specifically mention about their preference?",
        'preferences': [
            ('are severely allergic to peanuts', 'are severely allergic to peanuts'),
            ('hate horror movies', 'hate horror movies'),
            ('love classical music', 'love classical music'),
            ('prefer window seats on flights', 'prefer window seats on flights'),
            ('are vegetarian', 'are vegetarian'),
        ]
    }
}


def generate_haystack(size: int) -> List[str]:
    """生成干草堆记忆"""
    memories = []
    for _ in range(size):
        template = random.choice(HAYSTACK_TEMPLATES)
        # 填充模板
        filled = template
        for key, values in HAYSTACK_FILLERS.items():
            if '{' + key + '}' in filled:
                filled = filled.replace('{' + key + '}', random.choice(values))
        memories.append(filled)
    return memories


def generate_needle(needle_type: str, index: int = 0) -> Tuple[str, str, str]:
    """生成针 (关键信息)

    Returns:
        (needle_content, question, expected_answer)
    """
    config = NEEDLE_TEMPLATES[needle_type]

    if needle_type == 'fact':
        attr, value = config['attributes'][index % len(config['attributes'])]
        content = config['template'].format(attribute=attr, value=value)
        question = config['question'].format(attribute=attr)
        answer = value
    elif needle_type == 'event':
        event, date = config['events'][index % len(config['events'])]
        content = config['template'].format(event=event, date=date)
        question = config['question'].format(event=event)
        answer = date
    else:  # preference
        pref, ans = config['preferences'][index % len(config['preferences'])]
        content = config['template'].format(preference=pref)
        question = config['question']
        answer = ans

    return content, question, answer


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


async def run_needle_test(haystack_size: int, needle_depth: int, needle_type: str,
                           llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    运行单次针测试

    Args:
        haystack_size: 干草堆大小
        needle_depth: 针的位置 (0-100%)
        needle_type: 针的类型
        llm_client: LLM 客户端
    """
    print(f"\n  测试: size={haystack_size}, depth={needle_depth}%, type={needle_type}")

    # 清空记忆
    clear_memory()

    # 初始化 coordinator
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        # 生成干草堆
        haystack = generate_haystack(haystack_size)

        # 生成针
        needle_content, question, expected_answer = generate_needle(needle_type)

        # 计算针的插入位置
        needle_pos = int(haystack_size * needle_depth / 100)

        # 插入针
        haystack.insert(needle_pos, needle_content)

        # 塑造记忆
        print(f"    塑造 {len(haystack)} 条记忆...")
        ingest_start = time.time()
        ts = datetime.now()

        for i, memory in enumerate(tqdm(haystack, desc="    塑造", leave=False)):
            # 模拟时间流逝
            memory_ts = ts + timedelta(minutes=i)
            await coord.store_memory_with_timestamp(f"User: {memory}", memory_ts, "User", 0.5)

        ingest_duration = (time.time() - ingest_start) * 1000

        # 等待巩固
        await asyncio.sleep(2)

        # 查询
        print(f"    查询: {question}")
        query_start = time.time()

        context = {'skip_memory_store': True, 'evaluation_mode': True}
        result = await coord.process_user_input(question, context=context)

        query_duration = (time.time() - query_start) * 1000

        if hasattr(result, 'response'):
            answer = result.response
        elif isinstance(result, dict):
            answer = result.get('response', str(result))
        else:
            answer = str(result)

        # 评判
        is_correct = expected_answer.lower() in answer.lower()

        # LLM 评判 (更准确)
        if llm_client:
            try:
                prompt = f"""Check if the generated answer contains the correct information.

Question: {question}
Expected answer: {expected_answer}
Generated answer: {answer}

Return JSON: {{"correct": true/false}}"""
                r = await llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                is_correct = json.loads(r.choices[0].message.content).get('correct', is_correct)
            except:
                pass

        print(f"    结果: {'✓' if is_correct else '✗'} ({query_duration:.0f}ms)")

        return {
            'haystack_size': haystack_size,
            'needle_depth': needle_depth,
            'needle_type': needle_type,
            'needle_position': needle_pos,
            'question': question,
            'expected_answer': expected_answer,
            'generated_answer': answer,
            'is_correct': is_correct,
            'ingest_duration_ms': ingest_duration,
            'query_duration_ms': query_duration
        }

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


async def main():
    parser = argparse.ArgumentParser(description='Needle-in-Haystack 测试')
    parser.add_argument('--size', type=int, default=1000,
                       help='干草堆大小 (默认1000)')
    parser.add_argument('--depths', type=int, nargs='+', default=[0, 25, 50, 75, 100],
                       help='针的深度位置 (默认 0 25 50 75 100)')
    parser.add_argument('--types', type=str, nargs='+', default=['fact', 'event', 'preference'],
                       choices=['fact', 'event', 'preference'],
                       help='针的类型')
    parser.add_argument('--repeats', type=int, default=3,
                       help='每个配置重复次数')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("Needle-in-Haystack 测试 - BMAM")
    print("=" * 70)
    print(f"干草堆大小: {args.size}")
    print(f"测试深度: {args.depths}%")
    print(f"针类型: {args.types}")
    print(f"重复次数: {args.repeats}")

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")

    # 运行测试
    all_results = []
    start_time = datetime.now()

    total_tests = len(args.depths) * len(args.types) * args.repeats
    test_idx = 0

    for depth in args.depths:
        for needle_type in args.types:
            for repeat in range(args.repeats):
                test_idx += 1
                print(f"\n[{test_idx}/{total_tests}]", end='')

                result = await run_needle_test(
                    args.size, depth, needle_type, llm_client
                )
                result['repeat'] = repeat
                all_results.append(result)

    elapsed = (datetime.now() - start_time).total_seconds()

    # 汇总结果
    print("\n" + "=" * 70)
    print("Needle-in-Haystack 测试结果")
    print("=" * 70)

    # 按深度汇总
    print("\n按深度准确率:")
    for depth in args.depths:
        depth_results = [r for r in all_results if r['needle_depth'] == depth]
        correct = sum(1 for r in depth_results if r['is_correct'])
        total = len(depth_results)
        acc = correct / total if total > 0 else 0
        print(f"  深度 {depth:>3}%: {acc*100:.1f}% ({correct}/{total})")

    # 按类型汇总
    print("\n按类型准确率:")
    for needle_type in args.types:
        type_results = [r for r in all_results if r['needle_type'] == needle_type]
        correct = sum(1 for r in type_results if r['is_correct'])
        total = len(type_results)
        acc = correct / total if total > 0 else 0
        print(f"  {needle_type:>12}: {acc*100:.1f}% ({correct}/{total})")

    # 总体准确率
    total_correct = sum(1 for r in all_results if r['is_correct'])
    total_tests = len(all_results)
    overall_acc = total_correct / total_tests if total_tests > 0 else 0
    print(f"\n总体准确率: {overall_acc*100:.1f}% ({total_correct}/{total_tests})")

    # 延迟统计
    query_times = [r['query_duration_ms'] for r in all_results]
    print(f"\n查询延迟 (ms): mean={np.mean(query_times):.0f}, "
          f"p50={np.percentile(query_times, 50):.0f}, p95={np.percentile(query_times, 95):.0f}")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"needle_haystack_{args.size}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    output_data = {
        'config': {
            'haystack_size': args.size,
            'depths': args.depths,
            'types': args.types,
            'repeats': args.repeats,
            'timestamp': datetime.now().isoformat()
        },
        'summary': {
            'overall_accuracy': overall_acc,
            'by_depth': {
                depth: {
                    'accuracy': sum(1 for r in all_results if r['needle_depth'] == depth and r['is_correct']) /
                               len([r for r in all_results if r['needle_depth'] == depth])
                               if [r for r in all_results if r['needle_depth'] == depth] else 0
                }
                for depth in args.depths
            },
            'by_type': {
                t: {
                    'accuracy': sum(1 for r in all_results if r['needle_type'] == t and r['is_correct']) /
                               len([r for r in all_results if r['needle_type'] == t])
                               if [r for r in all_results if r['needle_type'] == t] else 0
                }
                for t in args.types
            }
        },
        'results': all_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
