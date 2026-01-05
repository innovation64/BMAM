#!/usr/bin/env python3
"""
PersonaMem 评估脚本 - BMAM vs MemOS 对比

PersonaMem: 个性化记忆评测数据集
- 测试系统记住用户偏好的能力
- 多选题格式，需要选择正确答案

数据文件:
- questions_32k.csv: 问题和选项
- shared_contexts_32k.jsonl: 共享的对话上下文

使用:
  python eval_personamem.py                    # 默认评估
  python eval_personamem.py --samples 100      # 只测试100个样本
  python eval_personamem.py --categories 5     # 只测试前5个类别
"""

import asyncio
import json
import csv
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
import ast

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
DATASET_DIR = DATA_DIR / 'personamem'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'personamem'
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


def load_contexts(contexts_path: Path) -> Dict[str, List[Dict]]:
    """加载共享上下文

    支持两种数据格式:
    1. {context_id: [messages]} - 实际的 PersonaMem 格式
    2. {"shared_context_id": "xxx", "messages": [...]} - 旧格式
    """
    contexts = {}
    with open(contexts_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)

            # 格式1: {context_id_hash: [messages]} - PersonaMem 实际格式
            # 检测: 如果所有 key 都不是 'shared_context_id'/'id'/'messages'/'context'
            standard_keys = {'shared_context_id', 'id', 'messages', 'context'}
            item_keys = set(item.keys())

            if not item_keys.intersection(standard_keys):
                # 这是格式1: {hash: messages}
                for context_id, messages in item.items():
                    if isinstance(messages, list):
                        contexts[context_id] = messages
            else:
                # 格式2: 标准格式
                context_id = item.get('shared_context_id', item.get('id', ''))
                messages = item.get('messages', item.get('context', []))
                if context_id:
                    contexts[context_id] = messages

    return contexts


def load_questions(questions_path: Path) -> List[Dict]:
    """加载问题"""
    questions = []
    with open(questions_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 解析选项
            try:
                options = ast.literal_eval(row['all_options'])
            except:
                options = row['all_options'].split('","')
                options = [o.strip('"[]') for o in options]

            questions.append({
                'persona_id': row['persona_id'],
                'question_id': row['question_id'],
                'question_type': row['question_type'],
                'topic': row['topic'],
                'question': row['user_question_or_message'],
                'correct_answer': row['correct_answer'],  # (a), (b), (c), (d)
                'options': options,
                'shared_context_id': row['shared_context_id'],
                'context_length': int(row.get('context_length_in_tokens', 0)),
            })
    return questions


async def ingest_context(coord, messages: List[Dict], persona_id: str) -> int:
    """塑造对话上下文"""
    count = 0
    ts = datetime.now()

    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        if content:
            speaker = 'User' if role == 'user' else 'Assistant'
            importance = 0.7

            await coord.store_memory_with_timestamp(
                f"{speaker}: {content}", ts, speaker, importance
            )
            count += 1

    return count


async def answer_multiple_choice(coord, question: str, options: List[str],
                                  llm_client: Optional[AsyncOpenAI]) -> str:
    """回答多选题，返回选择的答案 (a), (b), (c), (d)"""

    # 构造提示 - 强制格式约束
    options_text = "\n".join(options)
    full_question = f"""Based on our previous conversations, answer this multiple-choice question.

Question: {question}

Options:
{options_text}

IMPORTANT: You MUST select exactly ONE option from (a), (b), (c), or (d).
Your response format MUST be: "The answer is (X)" where X is a, b, c, or d.
Do NOT explain. Do NOT say "I don't know". Just pick the best option."""

    # 查询 BMAM
    context = {'skip_memory_store': True, 'evaluation_mode': True}
    result = await coord.process_user_input(full_question, context=context)

    if hasattr(result, 'response'):
        response = result.response
    elif isinstance(result, dict):
        response = result.get('response', str(result))
    else:
        response = str(result)

    # 提取选择的答案 - 增强提取逻辑
    response_lower = response.lower()

    # 方法1: 匹配 "the answer is (x)" 或 "answer: (x)"
    import re
    answer_match = re.search(r'(?:the\s+)?answer\s*(?:is|:)\s*\(?([abcd])\)?', response_lower)
    if answer_match:
        return f'({answer_match.group(1)})'

    # 方法2: 匹配 "**(x)**" 或 "**option (x)**" (markdown bold)
    bold_match = re.search(r'\*\*\(?([abcd])\)?\*\*', response_lower)
    if bold_match:
        return f'({bold_match.group(1)})'

    # 方法3: 尝试找到答案选项 (a), (b), (c), (d)
    for option in ['(a)', '(b)', '(c)', '(d)']:
        if option in response_lower:
            return option

    # 方法4: 尝试其他格式 a), a., option a
    for letter in ['a', 'b', 'c', 'd']:
        if letter + ')' in response_lower or letter + '.' in response_lower:
            return f'({letter})'
        if f'option {letter}' in response_lower:
            return f'({letter})'
        # 匹配开头的单独字母
        if response_lower.strip().startswith(letter) and len(response_lower.strip()) < 50:
            return f'({letter})'

    # 方法5: 如果响应很短且包含单个字母，提取它
    if len(response_lower.strip()) < 20:
        single_letter = re.search(r'\b([abcd])\b', response_lower)
        if single_letter:
            return f'({single_letter.group(1)})'

    # 默认返回第一个最可能的选项
    return '(a)'


async def evaluate_question(coord, question_data: Dict,
                            llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """评估单个问题"""
    start_time = time.time()

    predicted = await answer_multiple_choice(
        coord,
        question_data['question'],
        question_data['options'],
        llm_client
    )

    response_duration = (time.time() - start_time) * 1000

    correct_answer = question_data['correct_answer'].lower()
    is_correct = predicted.lower() == correct_answer

    return {
        'question_id': question_data['question_id'],
        'question_type': question_data['question_type'],
        'topic': question_data['topic'],
        'question': question_data['question'],
        'correct_answer': correct_answer,
        'predicted_answer': predicted,
        'is_correct': is_correct,
        'response_duration_ms': response_duration
    }


async def evaluate_persona(persona_id: str, persona_questions: List[Dict],
                           contexts: Dict[str, List[Dict]],
                           llm_client: Optional[AsyncOpenAI]) -> Dict[str, Any]:
    """评估单个 persona 的所有问题"""

    # 清空记忆
    clear_memory()

    # 初始化 coordinator
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    results = []
    try:
        # 获取这个 persona 的上下文
        context_id = persona_questions[0]['shared_context_id']
        context_messages = contexts.get(context_id, [])

        # 塑造上下文
        ingest_start = time.time()
        stored_count = await ingest_context(coord, context_messages, persona_id)
        ingest_duration = (time.time() - ingest_start) * 1000

        # 等待巩固
        await asyncio.sleep(1)

        # 评估每个问题
        for q in persona_questions:
            result = await evaluate_question(coord, q, llm_client)
            results.append(result)

        # 计算准确率并导出记忆
        correct = sum(1 for r in results if r['is_correct'])
        accuracy = correct / len(results) if results else 0
        export_path = export_memory(f"personamem_p{persona_id}", accuracy)
        print(f"    ✓ 记忆已导出: {export_path.name}")

        return {
            'persona_id': persona_id,
            'context_id': context_id,
            'stored_memories': stored_count,
            'ingest_duration_ms': ingest_duration,
            'results': results,
            'export_path': str(export_path)
        }
    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass


def calculate_metrics(all_results: List[Dict]) -> Dict[str, Any]:
    """计算评估指标"""
    import numpy as np

    all_questions = []
    for persona_result in all_results:
        all_questions.extend(persona_result['results'])

    total = len(all_questions)
    correct = sum(1 for r in all_questions if r['is_correct'])
    accuracy = correct / total if total > 0 else 0

    # 按问题类型统计
    type_stats = {}
    for q in all_questions:
        q_type = q['question_type']
        if q_type not in type_stats:
            type_stats[q_type] = {'total': 0, 'correct': 0}
        type_stats[q_type]['total'] += 1
        if q['is_correct']:
            type_stats[q_type]['correct'] += 1

    for t in type_stats:
        stats = type_stats[t]
        stats['accuracy'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0

    # 按 topic 统计
    topic_stats = {}
    for q in all_questions:
        topic = q['topic']
        if topic not in topic_stats:
            topic_stats[topic] = {'total': 0, 'correct': 0}
        topic_stats[topic]['total'] += 1
        if q['is_correct']:
            topic_stats[topic]['correct'] += 1

    for t in topic_stats:
        stats = topic_stats[t]
        stats['accuracy'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0

    # 延迟统计
    response_times = [q['response_duration_ms'] for q in all_questions]

    return {
        'overall': {
            'total': total,
            'correct': correct,
            'accuracy': accuracy,
            'num_personas': len(all_results)
        },
        'by_question_type': type_stats,
        'by_topic': topic_stats,
        'latency': {
            'mean': np.mean(response_times),
            'p50': np.percentile(response_times, 50),
            'p95': np.percentile(response_times, 95)
        }
    }


async def main():
    parser = argparse.ArgumentParser(description='PersonaMem 评估脚本')
    parser.add_argument('--samples', type=int, default=None,
                       help='评估样本数量 (默认全部)')
    parser.add_argument('--personas', type=int, default=None,
                       help='评估的 persona 数量')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    questions_path = DATASET_DIR / 'questions_32k.csv'
    contexts_path = DATASET_DIR / 'shared_contexts_32k.jsonl'

    if not questions_path.exists() or not contexts_path.exists():
        print(f"错误: 数据集文件不存在")
        print(f"  需要: {questions_path}")
        print(f"  需要: {contexts_path}")
        sys.exit(1)

    print("=" * 70)
    print("PersonaMem 评估 - BMAM")
    print("=" * 70)

    # 加载数据
    print("加载数据...")
    contexts = load_contexts(contexts_path)
    questions = load_questions(questions_path)

    print(f"上下文数: {len(contexts)}")
    print(f"问题数: {len(questions)}")

    # 按 persona 分组
    persona_questions = {}
    for q in questions:
        pid = q['persona_id']
        if pid not in persona_questions:
            persona_questions[pid] = []
        persona_questions[pid].append(q)

    print(f"Persona 数: {len(persona_questions)}")

    # 限制样本数
    personas_to_eval = list(persona_questions.keys())
    if args.personas:
        personas_to_eval = personas_to_eval[:args.personas]

    if args.samples:
        # 限制每个 persona 的问题数
        for pid in personas_to_eval:
            persona_questions[pid] = persona_questions[pid][:args.samples]

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM 已启用")

    # 评估
    all_results = []
    total_correct = 0
    total_questions = 0
    start_time = datetime.now()

    for idx, persona_id in enumerate(tqdm(personas_to_eval, desc="评估 Personas")):
        pq = persona_questions[persona_id]
        result = await evaluate_persona(persona_id, pq, contexts, llm_client)
        all_results.append(result)

        # 统计
        correct = sum(1 for r in result['results'] if r['is_correct'])
        total = len(result['results'])
        total_correct += correct
        total_questions += total

        running_acc = total_correct / total_questions if total_questions > 0 else 0
        tqdm.write(f"  Persona {persona_id}: {correct}/{total} | 累计: {running_acc*100:.1f}%")

    elapsed = (datetime.now() - start_time).total_seconds()

    # 计算指标
    metrics = calculate_metrics(all_results)

    # 打印结果
    print("\n" + "=" * 70)
    print("评估结果")
    print("=" * 70)
    print(f"总准确率: {metrics['overall']['accuracy']*100:.2f}% "
          f"({metrics['overall']['correct']}/{metrics['overall']['total']})")
    print(f"Personas: {metrics['overall']['num_personas']}")
    print(f"耗时: {elapsed/60:.1f} 分钟")

    print("\n按问题类型准确率:")
    for q_type, stats in sorted(metrics['by_question_type'].items()):
        print(f"  {q_type}: {stats['accuracy']*100:.1f}% ({stats['correct']}/{stats['total']})")

    print("\n延迟 (ms):")
    print(f"  mean={metrics['latency']['mean']:.0f}, "
          f"p50={metrics['latency']['p50']:.0f}, p95={metrics['latency']['p95']:.0f}")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"bmam_personamem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    output_data = {
        'config': {
            'personas': len(personas_to_eval),
            'total_questions': total_questions,
            'timestamp': datetime.now().isoformat()
        },
        'metrics': metrics,
        'results': all_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
