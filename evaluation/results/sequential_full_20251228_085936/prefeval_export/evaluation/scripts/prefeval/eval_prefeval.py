#!/usr/bin/env python3
"""
PrefEval 评估脚本 - BMAM vs MemOS 对比

PrefEval: 偏好记忆评测数据集
- 测试系统记住用户偏好的能力
- 基于多轮对话，测试偏好的记忆和应用

数据文件:
- pref_processed.jsonl: 处理后的偏好对话数据 (1000样本)

使用:
  python eval_prefeval.py                      # 默认评估全部1000样本
  python eval_prefeval.py --samples 50         # 只测试50个对话
  python eval_prefeval.py --resume             # 从上次检查点继续
  python eval_prefeval.py --checkpoint-every 10  # 每10个样本保存检查点
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
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# Paths
DATA_DIR = PROJECT_ROOT / 'data'
DATASET_DIR = DATA_DIR / 'prefeval'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'prefeval'
EXPORT_DIR = DATA_DIR / 'export'  # 统一导出目录


def clear_memory():
    """清空记忆文件 - 修复: 使用正确的子目录路径"""
    # State files in /data/state/
    state_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                   'amygdala_state.json', 'story_arc_state.json', 'tom_state.json', 'calibration_state.json']
    state_dir = DATA_DIR / 'state'
    for f in state_files:
        p = state_dir / f
        if p.exists():
            p.unlink()

    # Memory DB files in /data/memory/
    memory_files = ['brain_memory.db', 'temporal_lobe.db', 'working_memory.db',
                    'kv_value_store.db', 'memory_vectors.index', 'memory_vectors_mappings.json']
    memory_dir = DATA_DIR / 'memory'
    for f in memory_files:
        p = memory_dir / f
        if p.exists():
            p.unlink()

    # Cache directories in /data/cache/
    cache_dir = DATA_DIR / 'cache'
    for d in ['embedding', 'knowledge_graph', 'faiss_index']:
        p = cache_dir / d
        if p.exists():
            shutil.rmtree(p)

    # Also clean legacy paths (for backwards compatibility)
    legacy_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                    'amygdala_state.json', 'brain_memory.db', 'temporal_lobe.db', 'working_memory.db',
                    'story_arc_state.json', 'tom_state.json', 'kv_value_store.db']
    for f in legacy_files:
        p = DATA_DIR / f
        if p.exists():
            p.unlink()


def export_memory(label: str, accuracy: float = 0.0):
    """导出记忆状态到 export 目录，带标签"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_subdir = EXPORT_DIR / f"{label}_{timestamp}_acc{accuracy*100:.0f}pct"
    export_subdir.mkdir(parents=True, exist_ok=True)

    # 复制 state 文件
    state_dir = DATA_DIR / 'state'
    state_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                   'amygdala_state.json', 'story_arc_state.json', 'tom_state.json']
    for f in state_files:
        src = state_dir / f
        if src.exists():
            shutil.copy2(src, export_subdir / f)

    # 复制 memory DB 文件
    memory_dir = DATA_DIR / 'memory'
    memory_files = ['brain_memory.db', 'temporal_lobe.db', 'kv_value_store.db',
                    'memory_vectors.index', 'memory_vectors_mappings.json']
    for f in memory_files:
        src = memory_dir / f
        if src.exists():
            shutil.copy2(src, export_subdir / f)

    # 写入元数据
    meta = {
        'label': label,
        'accuracy': accuracy,
        'timestamp': timestamp,
        'exported_files': [f for f in os.listdir(export_subdir) if not f.endswith('.json') or f != 'metadata.json']
    }
    with open(export_subdir / 'metadata.json', 'w', encoding='utf-8') as mf:
        json.dump(meta, mf, indent=2, ensure_ascii=False)

    return export_subdir


async def ingest_conversation(coord, conversation: List[Dict], add_turns: int = 10) -> int:
    """
    塑造对话历史

    Args:
        coord: BMAM coordinator
        conversation: 对话列表
        add_turns: 塑造的对话轮数

    Returns:
        存储的消息数量
    """
    count = 0
    ts = datetime.now()

    # 只塑造前 add_turns 轮对话
    turns_to_add = conversation[:add_turns * 2] if add_turns > 0 else conversation

    for msg in turns_to_add:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        if content:
            speaker = 'User' if role == 'user' else 'Assistant'
            importance = 0.7 if role == 'user' else 0.5

            await coord.store_memory_with_timestamp(
                f"{speaker}: {content}", ts, speaker, importance
            )
            count += 1

    return count


async def evaluate_preference(coord, last_user_message: str,
                              llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """
    评估偏好记忆

    给定最后一个用户消息，让系统生成响应，
    然后评估响应是否体现了用户的偏好
    """
    start_time = time.time()

    # 查询 BMAM
    context = {'skip_memory_store': True, 'evaluation_mode': True}
    result = await coord.process_user_input(last_user_message, context=context)

    response_duration = (time.time() - start_time) * 1000

    if hasattr(result, 'response'):
        response = result.response
    elif isinstance(result, dict):
        response = result.get('response', str(result))
    else:
        response = str(result)

    return {
        'query': last_user_message,
        'response': response,
        'response_duration_ms': response_duration
    }


def parse_xml_response(response: str, tag: str) -> str:
    """从 XML 格式的响应中提取指定标签的内容"""
    import re
    match = re.search(f"<{tag}>(.*?)</{tag}>", response, re.DOTALL)
    return match.group(1).strip() if match else ""


async def evaluate_violate_preference(llm_client: AsyncOpenAI, preference: str, question: str, response: str) -> Dict[str, str]:
    """评估响应是否违反用户偏好"""
    prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant's response violates the user's stated preference.
Evaluate the response based on these criteria:

Answer "Yes" if:

1. The response contains any recommendations that directly contradict or violate the user's stated preference without any reasoning for why it recommends these contrasting items and no acknowledgment of the user's preference at all.

Answer "No" if:

1. The response respects the user's stated preference.
2. It's acceptable if it includes options that could potentially conflict with the preference, as long as it has acknowledged the user's preference and also specified the reason why or how to avoid the conflict.
3. If the response does not acknowledge the user's preference and if no recommendations violate the user's preference, there is no violation.

Here is the conversation:
User's preference: {preference}
User query: {question}
Assistant response: {response}

Examine the response meticulously and answer. Answer in this exact XML format:
<explanation>[1 very short sentence explanation]</explanation>
<answer>[Yes/No]</answer>"""

    try:
        r = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            timeout=30.0
        )
        api_response = r.choices[0].message.content
        return {
            "explanation": parse_xml_response(api_response, "explanation"),
            "answer": parse_xml_response(api_response, "answer")
        }
    except Exception as e:
        logging.warning(f"evaluate_violate_preference failed: {e}")
        return {"explanation": "evaluation failed", "answer": "No"}


async def evaluate_acknowledge_preference(llm_client: AsyncOpenAI, question: str, response: str) -> Dict[str, str]:
    """评估响应是否承认用户偏好"""
    prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant acknowledges any user preference in answering the user's query.

Evaluate the response based on these stringent criteria:

1. Check if the response explicitly or implicitly mentions or references a user preference. 2. The content of the preference is irrelevant for this check; only its presence matters.

Answer "Yes" if:

1. The response explicitly mentions or refers to a user preference in answering the user's question. Examples include: "Based on your previous preference for xxxx"; "Based on your previous preference, I would suggest you xxxx"; "Since you mentioned you prefer/dislike xxxx"; "Since you are a xxxx"; "I will recommend the following given your preference for xxx", etc. You should extract the "xxxx" in your answer. If it only says "Based on our previous conversation, I recommend..." and does not explicitly mention any preference, you should answer 'No'.
2. The response assumes the user preference in answering the user's question implicitly. For example, when the user asks 'Can you recommend me cars to drive?', if the response is 'Based on your preference, I will recommend non-EV cars, ...', then this indicates the assistant assumes that the user's preference is a dislike of EV cars, and you should answer 'Yes'.

Answer "No" if the response does not mention or refer to any user preference explicitly or implicitly. If you cannot extract the sentence stating what the preference is, answer 'No'.

Here is the assistant's response:
The user's question is: {question}
Assistant response: {response}

Examine the response meticulously and answer. Please answer in this exact XML format without any additional text:
<preference>[quote of the sentence that acknowledges/mentions what the preference is; leave it blank if there is none]</preference>
<answer>[Yes/No]</answer>"""

    try:
        r = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            timeout=30.0
        )
        api_response = r.choices[0].message.content
        return {
            "preference_mention": parse_xml_response(api_response, "preference"),
            "answer": parse_xml_response(api_response, "answer")
        }
    except Exception as e:
        logging.warning(f"evaluate_acknowledge_preference failed: {e}")
        return {"preference_mention": "", "answer": "No"}


async def evaluate_hallucinate_preference(llm_client: AsyncOpenAI, preference: str, restatement: str) -> Dict[str, str]:
    """评估响应是否幻觉用户偏好"""
    if not restatement.strip():
        return {"explanation": "No restatement provided by assistant", "answer": "No"}

    prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant's restatement of the user's stated preference is the same preference. Evaluate the response based on these stringent criteria to answer if the assistant has hallucinated the preference or not:

Answer "Yes" if:

1. The assistant's restatement differs from the original preference in meaning or intent.
2. The assistant's restatement contradicts the original preference.
3. The assistant's restatement is not related or irrelevant to the original preference.

Answer "No" if has not hallucinated:

1. The assistant's restatement matches the original preference.
2. The assistant's restatement is a minor paraphrase that fully preserves the meaning and intent of the original preference.
3. The restatement is just empty, no hallucination.

Here is the information:
Original user preference: "{preference}"
Assistant's restatement: "{restatement}"
Examine the original preference and the assistant's restatement meticulously and answer. Please answer in this exact XML format without any other additional text:
<explanation>[1 short sentence explanation]</explanation>
<answer>[Yes/No]</answer>"""

    try:
        r = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            timeout=30.0
        )
        api_response = r.choices[0].message.content
        return {
            "explanation": parse_xml_response(api_response, "explanation"),
            "answer": parse_xml_response(api_response, "answer")
        }
    except Exception as e:
        logging.warning(f"evaluate_hallucinate_preference failed: {e}")
        return {"explanation": "evaluation failed", "answer": "No"}


async def evaluate_helpful_response(llm_client: AsyncOpenAI, question: str, response: str) -> Dict[str, str]:
    """评估响应是否有帮助"""
    prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant provides any substantive response to the user's query.
Evaluate the response based on these stringent criteria:

Answer "Yes" if any of the following:

1. The response provides specific, relevant recommendations or advice related to the user's query without any apologetic statements or claims of inability to respond.
2. It remembers the user's preference and provides recommendations or suggestions to the user's query without any apologetic statements or claims of inability to respond.

Answer "No" if any of the following:

1. The response contains apologetic statements or claims of inability to respond due to lack of memory of the user's preference.
2. The assistant asks for more information without providing any substantive suggestions, advices directly related to the query.
3. The response doesn't address the user's query.
4. Even if the agent provides some relevant recommendations, if the agent first expresses an inability to follow the user's preference, answer 'No'.

Examples of unhelpful responses: (Answer: No):

"Unfortunately, I don't actually have enough context about your specific preferences for xxx"
"Unfortunately, we haven't had a previous discussion about your preferences for xxx. Could you let me know your preference for xxx?"
"I apologize, but I don't have access to your personal information or previous conversations."
"I'm sorry, but I can't provide a specific answer without more details."

Here is the conversation:
User query: {question}
Assistant response: {response}

Examine the response meticulously and answer. Answer in this exact XML format:
<explanation>[1 very short sentence explanation]</explanation>
<answer>[Yes/No]</answer>"""

    try:
        r = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            timeout=30.0
        )
        api_response = r.choices[0].message.content
        return {
            "explanation": parse_xml_response(api_response, "explanation"),
            "answer": parse_xml_response(api_response, "answer")
        }
    except Exception as e:
        logging.warning(f"evaluate_helpful_response failed: {e}")
        return {"explanation": "evaluation failed", "answer": "No"}


def classify_error_type(evaluations: Dict[str, Dict[str, str]]) -> str:
    """
    根据 4 个 LLM 评估结果分类错误类型 - 与 MemOS 5 类别对齐

    5 Categories:
    1. Preference-Unaware Violation - 不知道偏好但违反了
    2. Preference Hallucination Violation - 编造了错误的偏好
    3. Inconsistency Violation - 知道偏好但给出矛盾回答
    4. Unhelpful Response - 无帮助的回答
    5. Personalized Response - 个性化回答 (最佳)
    """
    violate = evaluations.get("violate_preference", {}).get("answer", "No")
    acknowledge = evaluations.get("acknowledge_preference", {}).get("answer", "No")
    hallucinate = evaluations.get("hallucinate_preference", {}).get("answer", "No")
    helpful = evaluations.get("helpful_response", {}).get("answer", "No")

    if violate == "Yes" and acknowledge == "No" and helpful == "Yes":
        return "Preference-Unaware Violation"
    elif violate == "Yes" and acknowledge == "Yes" and hallucinate == "Yes" and helpful == "Yes":
        return "Preference Hallucination Violation"
    elif violate == "Yes" and acknowledge == "Yes" and hallucinate == "No" and helpful == "Yes":
        return "Inconsistency Violation"
    elif violate == "No" and helpful == "No":
        return "Unhelpful Response"
    else:
        return "Personalized Response"


async def evaluate_with_llm_judge(preference: str, question: str, response: str,
                                   llm_client: AsyncOpenAI) -> Dict[str, Any]:
    """使用 4 个 LLM 评估来评判响应 - 与 MemOS 评估方法对齐"""

    # 首先评估 acknowledge_preference 因为后续需要用到其结果
    eval_acknowledge = await evaluate_acknowledge_preference(llm_client, question, response)

    # 并行执行其他 3 个评估
    eval_violate, eval_hallucinate, eval_helpful = await asyncio.gather(
        evaluate_violate_preference(llm_client, preference, question, response),
        evaluate_hallucinate_preference(llm_client, preference, eval_acknowledge.get("preference_mention", "")),
        evaluate_helpful_response(llm_client, question, response)
    )

    evaluations = {
        "violate_preference": eval_violate,
        "acknowledge_preference": eval_acknowledge,
        "hallucinate_preference": eval_hallucinate,
        "helpful_response": eval_helpful
    }

    error_type = classify_error_type(evaluations)

    # 为向后兼容,也计算一个数值 score
    score_map = {
        "Personalized Response": 1.0,
        "Inconsistency Violation": 0.5,
        "Preference Hallucination Violation": 0.25,
        "Preference-Unaware Violation": 0.25,
        "Unhelpful Response": 0.0
    }

    return {
        'evaluations': evaluations,
        'error_type': error_type,
        'score': score_map.get(error_type, 0.5),
        'reasoning': f"{error_type}: violate={eval_violate.get('answer')}, acknowledge={eval_acknowledge.get('answer')}, hallucinate={eval_hallucinate.get('answer')}, helpful={eval_helpful.get('answer')}"
    }


async def evaluate_conversation(conv_data: Dict, add_turns: int,
                                 llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """评估单个对话 - 支持新版 pref_processed.jsonl 格式"""

    conv_id = conv_data.get('conversation_id', 'unknown')
    conversation = conv_data.get('conversation', [])
    preference = conv_data.get('preference', '')
    question = conv_data.get('question', '')

    if len(conversation) < 2:
        return {
            'conversation_id': conv_id,
            'error': 'conversation too short',
            'score': 0
        }

    # 清空记忆
    clear_memory()

    # 初始化 coordinator
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    try:
        # 塑造完整对话历史
        ingest_start = time.time()
        stored_count = await ingest_conversation(coord, conversation, add_turns)
        ingest_duration = (time.time() - ingest_start) * 1000

        # 等待巩固
        await asyncio.sleep(1)

        # 使用数据集中的 question 字段进行评估
        test_question = question if question else conv_data.get('question', '')
        if not test_question:
            # 回退: 使用最后一个用户消息
            for msg in reversed(conversation):
                if msg.get('role') == 'user':
                    test_question = msg.get('content', '')
                    break

        if not test_question:
            return {
                'conversation_id': conv_id,
                'error': 'no question found',
                'score': 0
            }

        # 评估
        eval_result = await evaluate_preference(coord, test_question, llm_client)

        # LLM 评判 - 使用 4 个评估维度与 MemOS 对齐
        score = 0.5
        reasoning = ''
        error_type = 'Unknown'
        evaluations = {}

        if llm_client and preference:
            judge_result = await evaluate_with_llm_judge(
                preference, test_question, eval_result['response'], llm_client
            )
            score = judge_result['score']
            reasoning = judge_result['reasoning']
            error_type = judge_result['error_type']
            evaluations = judge_result['evaluations']

        # 跳过单个样本导出，将在评估结束时统一导出

        return {
            'conversation_id': conv_id,
            'stored_memories': stored_count,
            'ingest_duration_ms': ingest_duration,
            'query': test_question,
            'preference': preference,
            'response': eval_result['response'],
            'response_duration_ms': eval_result['response_duration_ms'],
            'score': score,
            'error_type': error_type,
            'evaluations': evaluations,
            'reasoning': reasoning
        }
    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


def calculate_metrics(results: List[Dict]) -> Dict[str, Any]:
    """计算评估指标 - 与 MemOS 5 类别对齐"""
    import numpy as np
    from collections import Counter

    valid_results = [r for r in results if 'error' not in r]
    total = len(valid_results)

    if total == 0:
        return {'error': 'no valid results'}

    scores = [r['score'] for r in valid_results]
    response_times = [r['response_duration_ms'] for r in valid_results]
    error_types = [r.get('error_type', 'Unknown') for r in valid_results]

    # 统计 5 类别分布
    error_counter = Counter(error_types)
    category_distribution = {}
    for error_type, count in error_counter.items():
        category_distribution[error_type] = {
            'count': count,
            'percentage': (count / total) * 100
        }

    # 确保所有 5 类别都有统计
    all_categories = [
        "Preference-Unaware Violation",
        "Preference Hallucination Violation",
        "Inconsistency Violation",
        "Unhelpful Response",
        "Personalized Response"
    ]
    for cat in all_categories:
        if cat not in category_distribution:
            category_distribution[cat] = {'count': 0, 'percentage': 0.0}

    # 计算不同阈值下的准确率 (向后兼容)
    thresholds = [0.25, 0.5, 0.75]
    threshold_accuracy = {}
    for t in thresholds:
        correct = sum(1 for s in scores if s >= t)
        threshold_accuracy[f'acc@{t}'] = correct / total

    return {
        'overall': {
            'total': total,
            'errors': len(results) - total,
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            **threshold_accuracy
        },
        'category_distribution': category_distribution,
        'latency': {
            'mean': np.mean(response_times),
            'p50': np.percentile(response_times, 50),
            'p95': np.percentile(response_times, 95)
        }
    }


def load_checkpoint(checkpoint_path: Path) -> tuple:
    """加载检查点"""
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            cp = json.load(f)
        return cp.get('completed_indices', []), cp.get('results', [])
    return [], []


def save_checkpoint(checkpoint_path: Path, completed_indices: list, results: list):
    """保存检查点"""
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump({
            'completed_indices': completed_indices,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }, f, ensure_ascii=False)


def get_score_label(error_type: str) -> str:
    """返回错误类型的简短标签 - 与 MemOS 5 类别对齐"""
    # 直接返回 error_type,因为现在使用 5 类别系统
    return error_type


async def main():
    parser = argparse.ArgumentParser(description='PrefEval 评估脚本')
    parser.add_argument('--samples', type=int, default=None,
                       help='评估样本数量 (默认全部1000)')
    parser.add_argument('--add-turn', type=int, default=10,
                       help='塑造的对话轮数 (默认10)')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    parser.add_argument('--log-dir', type=str, default=None,
                       help='日志输出目录')
    parser.add_argument('--resume', action='store_true',
                       help='从上次检查点继续')
    parser.add_argument('--checkpoint-every', type=int, default=20,
                       help='每N个样本保存检查点 (默认20)')
    args = parser.parse_args()

    dataset_path = DATASET_DIR / 'pref_processed.jsonl'
    checkpoint_path = RESULTS_DIR / 'prefeval_checkpoint.json'

    if not dataset_path.exists():
        print(f"错误: 数据集文件不存在: {dataset_path}")
        sys.exit(1)

    print("=" * 70)
    print("PrefEval 评估 - BMAM")
    print("=" * 70)
    print(f"数据集: {dataset_path.name}")
    print(f"塑造轮数: {args.add_turn}")
    print(f"检查点间隔: 每 {args.checkpoint_every} 个样本")

    # 加载数据 - JSONL 格式
    print("加载数据...")
    data = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            # 转换为统一格式
            data.append({
                'conversation_id': f"{item.get('persona', 'unknown')}_{item.get('topic', 'unknown')}_{len(data)}",
                'preference': item.get('preference', ''),
                'question': item.get('question', ''),
                'explanation': item.get('explanation', ''),
                'conversation': item.get('conversation', [])
            })

    if args.samples:
        data = data[:args.samples]

    print(f"对话数: {len(data)}")

    # 检查点恢复
    completed_indices = []
    results = []
    if args.resume:
        completed_indices, results = load_checkpoint(checkpoint_path)
        if completed_indices:
            print(f"✓ 从检查点恢复: 已完成 {len(completed_indices)}/{len(data)} 个样本")
        else:
            print("⚠ 未找到检查点,从头开始")

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")
    else:
        print("⚠ LLM Judge 不可用")

    # 评估
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    total_score = sum(r.get('score', 0) for r in results if 'error' not in r)
    start_time = datetime.now()

    pending_indices = [i for i in range(len(data)) if i not in completed_indices]
    print(f"待评估: {len(pending_indices)} 个样本")

    # 设置日志文件
    log_file = None
    if args.log_dir:
        log_dir = Path(args.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / 'prefeval.log', 'a', encoding='utf-8')
        if not completed_indices:
            log_file.write("=" * 60 + "\n")
            log_file.write("PrefEval 评测\n")
            log_file.write("=" * 60 + "\n")
            log_file.write(f"✓ 加载 {len(data)} 样本\n\n")
            log_file.flush()

    for idx in tqdm(pending_indices, desc="评估进度"):
        conv_data = data[idx]
        result = await evaluate_conversation(conv_data, args.add_turn, llm_client)
        results.append(result)
        completed_indices.append(idx)

        if 'error' not in result:
            total_score += result['score']
            valid_count = len([r for r in results if 'error' not in r])
            running_score = total_score / valid_count if valid_count > 0 else 0

            error_type = result.get('error_type', 'Unknown')
            turns = result.get('stored_memories', 0)

            # 写入日志文件
            if log_file:
                log_file.write(f"[{len(completed_indices)}/{len(data)}] 塑造 {turns} 轮对话... → {error_type}\n\n")
                log_file.flush()

            tqdm.write(f"  [{len(completed_indices)}/{len(data)}] {error_type} (score={result['score']:.2f})")

        # 保存检查点
        if len(completed_indices) % args.checkpoint_every == 0:
            save_checkpoint(checkpoint_path, completed_indices, results)
            tqdm.write(f"  💾 检查点已保存 ({len(completed_indices)} 个样本)")

    # 最终保存检查点
    save_checkpoint(checkpoint_path, completed_indices, results)

    if log_file:
        log_file.close()

    elapsed = (datetime.now() - start_time).total_seconds()

    # 计算指标
    metrics = calculate_metrics(results)

    # 打印结果
    print("\n" + "=" * 70)
    print("评估结果 (5 Categories - MemOS Aligned)")
    print("=" * 70)

    if 'error' not in metrics:
        print(f"有效样本: {metrics['overall']['total']}")
        print(f"错误样本: {metrics['overall']['errors']}")

        # 打印 5 类别分布
        print(f"\n类别分布:")
        cat_dist = metrics.get('category_distribution', {})
        print(f"  Preference-Unaware Violation:      {cat_dist.get('Preference-Unaware Violation', {}).get('percentage', 0):.1f}%")
        print(f"  Preference Hallucination Violation: {cat_dist.get('Preference Hallucination Violation', {}).get('percentage', 0):.1f}%")
        print(f"  Inconsistency Violation:           {cat_dist.get('Inconsistency Violation', {}).get('percentage', 0):.1f}%")
        print(f"  Unhelpful Response:                {cat_dist.get('Unhelpful Response', {}).get('percentage', 0):.1f}%")
        print(f"  Personalized Response:             {cat_dist.get('Personalized Response', {}).get('percentage', 0):.1f}%")

        print(f"\n平均分数: {metrics['overall']['mean_score']:.4f} ± {metrics['overall']['std_score']:.4f}")
        print(f"\n延迟 (ms): mean={metrics['latency']['mean']:.0f}, "
              f"p50={metrics['latency']['p50']:.0f}, p95={metrics['latency']['p95']:.0f}")
    else:
        print(f"评估失败: {metrics['error']}")

    print(f"\n耗时: {elapsed/60:.1f} 分钟")

    # 写入最终结果到日志
    if args.log_dir:
        log_dir = Path(args.log_dir)
        with open(log_dir / 'prefeval.log', 'a', encoding='utf-8') as lf:
            lf.write("\n" + "=" * 60 + "\n")
            lf.write("评估结果 (5 Categories - MemOS Aligned)\n")
            lf.write("=" * 60 + "\n")
            if 'error' not in metrics:
                lf.write(f"有效样本: {metrics['overall']['total']}\n")
                cat_dist = metrics.get('category_distribution', {})
                lf.write(f"\n类别分布:\n")
                lf.write(f"  Preference-Unaware Violation:      {cat_dist.get('Preference-Unaware Violation', {}).get('percentage', 0):.1f}%\n")
                lf.write(f"  Preference Hallucination Violation: {cat_dist.get('Preference Hallucination Violation', {}).get('percentage', 0):.1f}%\n")
                lf.write(f"  Inconsistency Violation:           {cat_dist.get('Inconsistency Violation', {}).get('percentage', 0):.1f}%\n")
                lf.write(f"  Unhelpful Response:                {cat_dist.get('Unhelpful Response', {}).get('percentage', 0):.1f}%\n")
                lf.write(f"  Personalized Response:             {cat_dist.get('Personalized Response', {}).get('percentage', 0):.1f}%\n")
                lf.write(f"\n平均分数: {metrics['overall']['mean_score']:.4f} ± {metrics['overall']['std_score']:.4f}\n")
            lf.write(f"耗时: {elapsed/60:.1f} 分钟\n")

        # 导出最终记忆状态
        if 'error' not in metrics:
            memory_backup = log_dir / 'memory_backup_prefeval'
            memory_backup.mkdir(parents=True, exist_ok=True)
            export_memory(f"prefeval_final", metrics['overall']['mean_score'])
            # 复制记忆文件到备份目录
            for f in ['brain_memory.db', 'temporal_lobe.db', 'hippocampus_state.json']:
                src = DATA_DIR / 'memory' / f if 'db' in f else DATA_DIR / 'state' / f
                if src.exists():
                    shutil.copy2(src, memory_backup / f)

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"bmam_prefeval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    output_data = {
        'config': {
            'samples': len(data),
            'add_turns': args.add_turn,
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
