#!/usr/bin/env python3
"""
BMAM Theory of Mind (ToM) 模块评估

ToM 是 BMAM V2.0 的核心创新之一，用于意图推理和欺骗检测

评估维度:
1. 意图推理 - 理解用户真实意图
2. 欺骗检测 - 识别矛盾或误导性信息
3. 情感理解 - 理解用户情绪状态
4. 信念跟踪 - 跟踪用户信念变化
5. 隐含意图识别 - 理解未明确表达的需求

使用:
  python eval_theory_of_mind.py --test intent       # 意图推理
  python eval_theory_of_mind.py --test deception    # 欺骗检测
  python eval_theory_of_mind.py --test emotion      # 情感理解
  python eval_theory_of_mind.py --test all          # 全部测试
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


# 意图推理测试用例
INTENT_INFERENCE_CASES = [
    {
        'context': [
            "User: I've been looking at laptops online all day.",
            "User: My current laptop is 5 years old and very slow.",
            "User: I saw some good deals but I'm not sure about the specs."
        ],
        'query': "Can you help me?",
        'expected_intent': "help_choose_laptop",
        'explicit_ask': False,
        'notes': "User implicitly asking for laptop recommendation"
    },
    {
        'context': [
            "User: I have a meeting at 2pm tomorrow.",
            "User: The meeting is in the downtown office.",
            "User: I heard traffic is bad around noon."
        ],
        'query': "What time should I leave?",
        'expected_intent': "travel_planning",
        'explicit_ask': True,
        'notes': "User needs travel time recommendation"
    },
    {
        'context': [
            "User: My friend recommended this Italian restaurant.",
            "User: I'm vegetarian though.",
            "User: I wonder if they have good options for me."
        ],
        'query': "What do you think?",
        'expected_intent': "restaurant_compatibility_check",
        'explicit_ask': False,
        'notes': "User wants to know if restaurant suits dietary needs"
    },
    {
        'context': [
            "User: I've been learning Python for 3 months.",
            "User: I can write basic scripts now.",
            "User: My friend is a data scientist and makes good money."
        ],
        'query': "What should I do next?",
        'expected_intent': "career_learning_advice",
        'explicit_ask': False,
        'notes': "User implicitly interested in data science career path"
    },
]


# 欺骗检测测试用例
DECEPTION_DETECTION_CASES = [
    {
        'memories': [
            "User said they love spicy food.",
            "User mentioned they eat Thai food every week.",
            "User said they can handle the spiciest dishes."
        ],
        'new_statement': "User: Actually, I've never liked spicy food.",
        'is_deceptive': True,
        'deception_type': "contradiction",
        'notes': "Direct contradiction with previous statements"
    },
    {
        'memories': [
            "User mentioned they work from home.",
            "User said they prefer remote work.",
        ],
        'new_statement': "User: I was at the office yesterday for a team meeting.",
        'is_deceptive': False,
        'deception_type': None,
        'notes': "Not deceptive - occasional office visits are normal for remote workers"
    },
    {
        'memories': [
            "User said they never drink alcohol.",
            "User mentioned they don't go to bars.",
        ],
        'new_statement': "User: I had a few beers with friends last night.",
        'is_deceptive': True,
        'deception_type': "contradiction",
        'notes': "Contradicts previous statement about not drinking"
    },
    {
        'memories': [
            "User said they are saving money for a house.",
            "User mentioned they cook at home to save money.",
        ],
        'new_statement': "User: I just bought a new gaming PC for $3000.",
        'is_deceptive': False,
        'deception_type': None,
        'notes': "Not necessarily deceptive - might have separate budgets"
    },
]


# 情感理解测试用例
EMOTION_UNDERSTANDING_CASES = [
    {
        'context': [
            "User: I worked so hard on that project for months.",
            "User: I stayed late every night to finish it.",
            "User: My boss just gave all the credit to my colleague."
        ],
        'expected_emotions': ['frustrated', 'disappointed', 'angry', 'upset'],
        'intensity': 'high',
        'notes': "User should be feeling very frustrated/upset"
    },
    {
        'context': [
            "User: I just found out I got the job!",
            "User: This is the company I've always wanted to work for.",
            "User: I can't believe it actually happened."
        ],
        'expected_emotions': ['excited', 'happy', 'thrilled', 'joyful'],
        'intensity': 'high',
        'notes': "User is clearly very happy"
    },
    {
        'context': [
            "User: My dog isn't eating much lately.",
            "User: The vet said the tests came back abnormal.",
            "User: They want to run more tests next week."
        ],
        'expected_emotions': ['worried', 'anxious', 'concerned', 'scared'],
        'intensity': 'medium',
        'notes': "User is worried about their pet"
    },
    {
        'context': [
            "User: I don't know what to do anymore.",
            "User: Everything I try seems to fail.",
            "User: Maybe I'm just not good enough."
        ],
        'expected_emotions': ['hopeless', 'sad', 'discouraged', 'depressed'],
        'intensity': 'high',
        'notes': "User may need emotional support"
    },
]


# 信念跟踪测试用例
BELIEF_TRACKING_CASES = [
    {
        'belief_changes': [
            ("User: I think Python is the best programming language.", "pro_python"),
            ("User: I tried Rust and it's actually quite good.", "neutral"),
            ("User: After using Rust for my project, I prefer it now.", "pro_rust"),
        ],
        'final_belief_query': "What programming language does the user prefer?",
        'expected_answer': "Rust",
        'notes': "Belief changed from Python to Rust over time"
    },
    {
        'belief_changes': [
            ("User: I love living in the city.", "pro_city"),
            ("User: The noise and pollution are getting to me.", "wavering"),
            ("User: I've started looking at houses in the suburbs.", "pro_suburbs"),
        ],
        'final_belief_query': "Does the user want to continue living in the city?",
        'expected_answer': "no",
        'notes': "User's preference changed from city to suburbs"
    },
]


# 隐含意图识别测试用例
IMPLICIT_INTENT_CASES = [
    {
        'statement': "User: It's getting late and I haven't eaten anything all day.",
        'implicit_intents': ['want_food', 'might_be_hungry', 'need_break'],
        'explicit_ask': False,
        'notes': "User might want food recommendation or break suggestion"
    },
    {
        'statement': "User: This report is due tomorrow and I still have 10 pages to write.",
        'implicit_intents': ['stressed', 'need_help', 'time_pressure'],
        'explicit_ask': False,
        'notes': "User might need help or efficiency tips"
    },
    {
        'statement': "User: My birthday is next week and I'll be turning 30.",
        'implicit_intents': ['milestone', 'might_want_celebration', 'reflection'],
        'explicit_ask': False,
        'notes': "User might be hinting about birthday plans"
    },
]


async def test_intent_inference(coord: HRMCoordinatorWrapper,
                                 llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """测试意图推理能力"""
    print("\n" + "=" * 50)
    print("意图推理测试")
    print("=" * 50)

    results = []

    for case_idx, case in enumerate(INTENT_INFERENCE_CASES):
        print(f"\n测试案例 {case_idx + 1}/{len(INTENT_INFERENCE_CASES)}")
        print(f"  预期意图: {case['expected_intent']}")

        clear_memory()
        await coord.start_system()

        try:
            # 塑造上下文记忆
            ts = datetime.now()
            for i, ctx in enumerate(case['context']):
                await coord.store_memory_with_timestamp(
                    ctx, ts + timedelta(minutes=i), "User", 0.7
                )

            await asyncio.sleep(0.5)

            # 发送查询
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            result = await coord.process_user_input(case['query'], context=context)

            if hasattr(result, 'response'):
                answer = result.response
            elif isinstance(result, dict):
                answer = result.get('response', str(result))
            else:
                answer = str(result)

            # 评估是否理解了意图
            intent_keywords = case['expected_intent'].replace('_', ' ').split()
            understood_intent = any(kw.lower() in answer.lower() for kw in intent_keywords)

            # LLM 评估
            if llm_client:
                try:
                    prompt = f"""Evaluate if the response correctly understands the user's implicit intent.

Context: {case['context']}
User's query: {case['query']}
Expected intent: {case['expected_intent']}
System response: {answer}

Did the response address the user's underlying intent (not just the literal question)?
Return JSON: {{"understood_intent": true/false, "intent_score": 0.0-1.0, "explanation": "..."}}"""

                    r = await llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )
                    judge_result = json.loads(r.choices[0].message.content)
                    understood_intent = judge_result.get('understood_intent', understood_intent)
                    intent_score = judge_result.get('intent_score', 0.5)
                except:
                    intent_score = 0.5
            else:
                intent_score = 0.5 if understood_intent else 0.0

            results.append({
                'case_idx': case_idx,
                'expected_intent': case['expected_intent'],
                'explicit_ask': case['explicit_ask'],
                'answer': answer,
                'understood_intent': understood_intent,
                'intent_score': intent_score
            })

            print(f"  理解意图: {'✓' if understood_intent else '✗'}")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    overall_acc = sum(1 for r in results if r['understood_intent']) / len(results)
    avg_score = np.mean([r['intent_score'] for r in results])

    print(f"\n意图推理准确率: {overall_acc*100:.1f}%")
    print(f"平均意图分数: {avg_score:.2f}")

    return {
        'test': 'intent_inference',
        'results': results,
        'overall_accuracy': overall_acc,
        'average_intent_score': avg_score
    }


async def test_deception_detection(coord: HRMCoordinatorWrapper,
                                    llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """测试欺骗/矛盾检测能力"""
    print("\n" + "=" * 50)
    print("欺骗检测测试")
    print("=" * 50)

    results = []

    for case_idx, case in enumerate(DECEPTION_DETECTION_CASES):
        print(f"\n测试案例 {case_idx + 1}/{len(DECEPTION_DETECTION_CASES)}")
        print(f"  实际是否矛盾: {case['is_deceptive']}")

        clear_memory()
        await coord.start_system()

        try:
            # 塑造历史记忆
            ts = datetime.now()
            for i, memory in enumerate(case['memories']):
                await coord.store_memory_with_timestamp(
                    memory, ts + timedelta(hours=i), "User", 0.8
                )

            await asyncio.sleep(0.5)

            # 发送新陈述并询问是否矛盾
            query = f"{case['new_statement']}\n\nDoes this contradict what the user said before?"
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            result = await coord.process_user_input(query, context=context)

            if hasattr(result, 'response'):
                answer = result.response
            elif isinstance(result, dict):
                answer = result.get('response', str(result))
            else:
                answer = str(result)

            # 检测系统是否识别了矛盾
            contradiction_keywords = ['contradict', 'inconsistent', 'different', 'conflict',
                                     'doesn\'t match', 'opposite', 'not consistent', 'changed']
            detected_contradiction = any(kw in answer.lower() for kw in contradiction_keywords)

            # 评估正确性
            is_correct = detected_contradiction == case['is_deceptive']

            results.append({
                'case_idx': case_idx,
                'memories': case['memories'],
                'new_statement': case['new_statement'],
                'is_actually_deceptive': case['is_deceptive'],
                'detected_contradiction': detected_contradiction,
                'is_correct': is_correct,
                'answer': answer
            })

            print(f"  检测矛盾: {detected_contradiction}")
            print(f"  {'✓' if is_correct else '✗'} 判断正确")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    overall_acc = sum(1 for r in results if r['is_correct']) / len(results)
    print(f"\n欺骗检测准确率: {overall_acc*100:.1f}%")

    # 细分统计
    true_positives = sum(1 for r in results if r['is_actually_deceptive'] and r['detected_contradiction'])
    false_positives = sum(1 for r in results if not r['is_actually_deceptive'] and r['detected_contradiction'])
    true_negatives = sum(1 for r in results if not r['is_actually_deceptive'] and not r['detected_contradiction'])
    false_negatives = sum(1 for r in results if r['is_actually_deceptive'] and not r['detected_contradiction'])

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0

    print(f"Precision: {precision:.2f}, Recall: {recall:.2f}")

    return {
        'test': 'deception_detection',
        'results': results,
        'overall_accuracy': overall_acc,
        'precision': precision,
        'recall': recall
    }


async def test_emotion_understanding(coord: HRMCoordinatorWrapper,
                                      llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """测试情感理解能力"""
    print("\n" + "=" * 50)
    print("情感理解测试")
    print("=" * 50)

    results = []

    for case_idx, case in enumerate(EMOTION_UNDERSTANDING_CASES):
        print(f"\n测试案例 {case_idx + 1}/{len(EMOTION_UNDERSTANDING_CASES)}")
        print(f"  预期情绪: {case['expected_emotions']}")

        clear_memory()
        await coord.start_system()

        try:
            # 塑造上下文
            ts = datetime.now()
            for i, ctx in enumerate(case['context']):
                await coord.store_memory_with_timestamp(
                    ctx, ts + timedelta(minutes=i), "User", 0.8
                )

            await asyncio.sleep(0.5)

            # 询问用户情绪
            query = "How is the user feeling based on the conversation?"
            context = {'skip_memory_store': True, 'evaluation_mode': True}
            result = await coord.process_user_input(query, context=context)

            if hasattr(result, 'response'):
                answer = result.response
            elif isinstance(result, dict):
                answer = result.get('response', str(result))
            else:
                answer = str(result)

            # 检测识别的情绪
            recognized_emotions = [e for e in case['expected_emotions'] if e.lower() in answer.lower()]
            emotion_recognition_rate = len(recognized_emotions) / len(case['expected_emotions'])

            results.append({
                'case_idx': case_idx,
                'context': case['context'],
                'expected_emotions': case['expected_emotions'],
                'recognized_emotions': recognized_emotions,
                'answer': answer,
                'recognition_rate': emotion_recognition_rate,
                'intensity': case['intensity']
            })

            print(f"  识别情绪: {recognized_emotions}")
            print(f"  识别率: {emotion_recognition_rate*100:.0f}%")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    avg_recognition = np.mean([r['recognition_rate'] for r in results])
    print(f"\n情感识别平均准确率: {avg_recognition*100:.1f}%")

    return {
        'test': 'emotion_understanding',
        'results': results,
        'average_recognition_rate': avg_recognition
    }


async def main():
    parser = argparse.ArgumentParser(description='BMAM Theory of Mind 评估')
    parser.add_argument('--test', type=str, default='all',
                       choices=['all', 'intent', 'deception', 'emotion'],
                       help='测试类型')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM Theory of Mind 模块评估")
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
        'module': 'Theory of Mind',
        'tests': {}
    }

    start_time = datetime.now()

    if args.test in ['all', 'intent']:
        results['tests']['intent_inference'] = await test_intent_inference(coord, llm_client)

    if args.test in ['all', 'deception']:
        results['tests']['deception_detection'] = await test_deception_detection(coord, llm_client)

    if args.test in ['all', 'emotion']:
        results['tests']['emotion_understanding'] = await test_emotion_understanding(coord, llm_client)

    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = elapsed

    # 汇总
    print("\n" + "=" * 70)
    print("Theory of Mind 评估汇总")
    print("=" * 70)

    for test_name, test_result in results['tests'].items():
        if 'overall_accuracy' in test_result:
            print(f"  {test_name}: {test_result['overall_accuracy']*100:.1f}%")
        elif 'average_recognition_rate' in test_result:
            print(f"  {test_name}: {test_result['average_recognition_rate']*100:.1f}%")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"tom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
