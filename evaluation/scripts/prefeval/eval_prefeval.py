#!/usr/bin/env python3
"""
PrefEval 评估脚本 - BMAM vs MemOS 对比

PrefEval: 偏好记忆评测数据集
- 测试系统记住用户偏好的能力
- 基于多轮对话，测试偏好的记忆和应用

数据文件:
- filtered_inter_turns.json: 对话数据

使用:
  python eval_prefeval.py                      # 默认评估
  python eval_prefeval.py --samples 50         # 只测试50个对话
  python eval_prefeval.py --add-turn 10        # 塑造前10轮对话
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


async def evaluate_with_llm_judge(query: str, response: str, conversation_context: str,
                                   llm_client: AsyncOpenAI) -> Dict[str, Any]:
    """使用 LLM 评判响应是否正确反映了用户偏好"""

    prompt = f"""You are evaluating whether an AI assistant's response correctly reflects the user's preferences based on their conversation history.

Conversation History (showing user's preferences):
{conversation_context}

User's Latest Query: {query}

Assistant's Response: {response}

Evaluate whether the response correctly reflects the user's stated preferences from the conversation history.

Score the response:
- 1.0: Perfectly reflects user preferences
- 0.75: Mostly reflects preferences with minor issues
- 0.5: Partially reflects preferences
- 0.25: Barely reflects preferences
- 0.0: Does not reflect preferences or contradicts them

Return JSON: {{"score": <float>, "reasoning": "<brief explanation>"}}"""

    try:
        r = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert evaluator for preference-aware AI systems."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        result = json.loads(r.choices[0].message.content)
        return {
            'score': float(result.get('score', 0.5)),
            'reasoning': result.get('reasoning', '')
        }
    except Exception as e:
        logging.warning(f"LLM judge failed: {e}")
        return {'score': 0.5, 'reasoning': 'evaluation failed'}


async def evaluate_conversation(conv_data: Dict, add_turns: int,
                                 llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """评估单个对话"""

    conv_id = conv_data.get('conversation_id', 'unknown')
    conversation = conv_data.get('conversation', [])

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
        # 塑造对话历史 (除了最后一轮)
        history = conversation[:-2] if len(conversation) > 2 else conversation[:-1]
        ingest_start = time.time()
        stored_count = await ingest_conversation(coord, history, add_turns)
        ingest_duration = (time.time() - ingest_start) * 1000

        # 等待巩固
        await asyncio.sleep(1)

        # 获取最后的用户消息
        last_user_msg = None
        for msg in reversed(conversation):
            if msg.get('role') == 'user':
                last_user_msg = msg.get('content', '')
                break

        if not last_user_msg:
            return {
                'conversation_id': conv_id,
                'error': 'no user message found',
                'score': 0
            }

        # 评估
        eval_result = await evaluate_preference(coord, last_user_msg, llm_client)

        # LLM 评判
        score = 0.5
        reasoning = ''
        if llm_client:
            # 构建上下文摘要
            context_summary = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}..."
                for msg in history[:10]
            ])
            judge_result = await evaluate_with_llm_judge(
                last_user_msg, eval_result['response'], context_summary, llm_client
            )
            score = judge_result['score']
            reasoning = judge_result['reasoning']

        return {
            'conversation_id': conv_id,
            'stored_memories': stored_count,
            'ingest_duration_ms': ingest_duration,
            'query': last_user_msg,
            'response': eval_result['response'],
            'response_duration_ms': eval_result['response_duration_ms'],
            'score': score,
            'reasoning': reasoning
        }
    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


def calculate_metrics(results: List[Dict]) -> Dict[str, Any]:
    """计算评估指标"""
    import numpy as np

    valid_results = [r for r in results if 'error' not in r]
    total = len(valid_results)

    if total == 0:
        return {'error': 'no valid results'}

    scores = [r['score'] for r in valid_results]
    response_times = [r['response_duration_ms'] for r in valid_results]

    # 计算不同阈值下的准确率
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
        'latency': {
            'mean': np.mean(response_times),
            'p50': np.percentile(response_times, 50),
            'p95': np.percentile(response_times, 95)
        }
    }


async def main():
    parser = argparse.ArgumentParser(description='PrefEval 评估脚本')
    parser.add_argument('--samples', type=int, default=None,
                       help='评估样本数量 (默认全部)')
    parser.add_argument('--add-turn', type=int, default=10,
                       help='塑造的对话轮数 (默认10)')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    dataset_path = DATASET_DIR / 'filtered_inter_turns.json'

    if not dataset_path.exists():
        print(f"错误: 数据集文件不存在: {dataset_path}")
        sys.exit(1)

    print("=" * 70)
    print("PrefEval 评估 - BMAM")
    print("=" * 70)
    print(f"数据集: {dataset_path.name}")
    print(f"塑造轮数: {args.add_turn}")

    # 加载数据
    print("加载数据...")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if args.samples:
        data = data[:args.samples]

    print(f"对话数: {len(data)}")

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
    results = []
    total_score = 0
    start_time = datetime.now()

    for idx, conv_data in enumerate(tqdm(data, desc="评估进度")):
        result = await evaluate_conversation(conv_data, args.add_turn, llm_client)
        results.append(result)

        if 'error' not in result:
            total_score += result['score']
            running_score = total_score / (idx + 1)
            tqdm.write(f"  [{idx+1}/{len(data)}] score={result['score']:.2f} | 累计: {running_score:.2f}")

    elapsed = (datetime.now() - start_time).total_seconds()

    # 计算指标
    metrics = calculate_metrics(results)

    # 打印结果
    print("\n" + "=" * 70)
    print("评估结果")
    print("=" * 70)

    if 'error' not in metrics:
        print(f"平均分数: {metrics['overall']['mean_score']:.4f} ± {metrics['overall']['std_score']:.4f}")
        print(f"有效样本: {metrics['overall']['total']}")
        print(f"错误样本: {metrics['overall']['errors']}")
        print(f"\n阈值准确率:")
        print(f"  acc@0.25: {metrics['overall']['acc@0.25']*100:.1f}%")
        print(f"  acc@0.5:  {metrics['overall']['acc@0.5']*100:.1f}%")
        print(f"  acc@0.75: {metrics['overall']['acc@0.75']*100:.1f}%")
        print(f"\n延迟 (ms): mean={metrics['latency']['mean']:.0f}, "
              f"p50={metrics['latency']['p50']:.0f}, p95={metrics['latency']['p95']:.0f}")
    else:
        print(f"评估失败: {metrics['error']}")

    print(f"\n耗时: {elapsed/60:.1f} 分钟")

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
