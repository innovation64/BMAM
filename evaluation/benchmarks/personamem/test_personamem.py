#!/usr/bin/env python3
"""
PersonaMem Benchmark - 偏好记忆评测

测试系统对用户偏好和个人信息的记忆能力。

问题类型:
  - recall_user_shared_facts: 回忆用户分享的事实
  - provide_preference_aligned_recommendations: 提供符合偏好的推荐
  - suggest_new_ideas: 基于历史建议新想法
  - recalling_the_reasons_behind_previous_updates: 回忆偏好变化原因
  - track_full_preference_evolution: 追踪完整偏好演化
  - generalizing_to_new_scenarios: 泛化到新场景
  - recalling_facts_mentioned_by_the_user: 回忆用户提到的事实

使用:
  python3 test_personamem.py                    # 测试全部
  python3 test_personamem.py --questions 50     # 测试50题
  python3 test_personamem.py --type recall_user_shared_facts  # 测试特定类型
"""

import asyncio
import csv
import json
import os
import sys
import argparse
import time
import logging
import shutil
import re
from datetime import datetime
from pathlib import Path
from collections import Counter

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
    LLM_JUDGE = True
except ImportError:
    LLM_JUDGE = False

# Paths
PERSONAMEM_DIR = PROJECT_ROOT / 'data' / 'datasets' / 'personamem'
QUESTIONS_PATH = PERSONAMEM_DIR / 'questions_32k.csv'
CONTEXTS_PATH = PERSONAMEM_DIR / 'shared_contexts_32k.jsonl'
DATA_DIR = PROJECT_ROOT / 'data' / 'memory'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'personamem'
STATUS_FILE = RESULTS_DIR / 'live_status.json'


def clear_memory():
    """清空记忆文件"""
    # Memory databases
    db_files = ['brain_memory.db', 'temporal_lobe.db', 'working_memory.db', 'kv_value_store.db',
                'memory_vectors.index', 'memory_vectors_mappings.json']
    for f in db_files:
        p = DATA_DIR / f
        if p.exists(): p.unlink()

    # Memory checkpoints
    checkpoint_dir = DATA_DIR / 'checkpoints'
    if checkpoint_dir.exists():
        for f in checkpoint_dir.glob('*.json'):
            f.unlink()

    # State files
    state_dir = PROJECT_ROOT / 'data' / 'state'
    state_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                   'amygdala_state.json', 'story_arc_state.json', 'calibration_state.json']
    for f in state_files:
        p = state_dir / f
        if p.exists(): p.unlink()

    # User profile files
    for f in ['value_profiles.json', 'user_portraits.json']:
        p = PROJECT_ROOT / 'data' / f
        if p.exists(): p.unlink()

    # Cache directories (correct path: data/cache/)
    cache_dir = PROJECT_ROOT / 'data' / 'cache'
    for d in ['embedding', 'knowledge_graph', 'faiss_index']:
        p = cache_dir / d
        if p.exists(): shutil.rmtree(p)

    # Legacy paths (data/memory/)
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = DATA_DIR / d
        if p.exists(): shutil.rmtree(p)

    try:
        from src.memory.story_arc import reset_story_arc_manager
        reset_story_arc_manager()
    except ImportError:
        pass

    # 2025-12-24 FIX: Reset memory_system singleton to avoid stale DB connections
    # Without this reset, the old singleton holds a connection to the deleted database
    # which causes "attempt to write a readonly database" errors
    try:
        from src.memory.memory_system import advanced_memory_system
        advanced_memory_system._memory_system_instance = None
    except ImportError:
        pass


def save_status(status):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def load_data():
    """加载PersonaMem数据"""
    # 加载问题
    with open(QUESTIONS_PATH, 'r') as f:
        reader = csv.DictReader(f)
        questions = list(reader)

    # 加载上下文
    contexts = {}
    with open(CONTEXTS_PATH, 'r') as f:
        for line in f:
            ctx_data = json.loads(line)
            # 上下文ID是唯一的key
            for ctx_id, messages in ctx_data.items():
                contexts[ctx_id] = messages

    return questions, contexts


async def ingest_context(coord, messages, max_messages=None, user_id: str = "default"):
    """将对话历史塑造到记忆中

    Args:
        coord: 协调器
        messages: 消息列表
        max_messages: 最大消息数
        user_id: 用户标识 (用于区分不同用户)
    """
    if max_messages:
        messages = messages[:max_messages]

    print(f"塑造 {len(messages)} 条消息...")
    start = time.time()

    for idx, msg in enumerate(messages, 1):
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        if role == 'system':
            # 系统消息作为persona信息
            await coord.store_memory_with_timestamp(
                f"[Persona] {content}",
                datetime.now(),
                'system',
                0.9,
                user_id=user_id  # 🔥 传入 user_id
            )
        elif role == 'user':
            # 提取User:后的内容
            if content.startswith('User:'):
                content = content[5:].strip()
            await coord.store_memory_with_timestamp(
                f"User: {content}",
                datetime.now(),
                'user',
                0.7,
                user_id=user_id  # 🔥 传入 user_id
            )
        else:
            # assistant回复
            await coord.store_memory_with_timestamp(
                f"Assistant: {content[:500]}",
                datetime.now(),
                'assistant',
                0.5,
                user_id=user_id  # 🔥 传入 user_id
            )

        if idx % 20 == 0:
            print(f"\r  消息 {idx}/{len(messages)}", end='', flush=True)

    print(f"\r  消息 {len(messages)}/{len(messages)} ✓ ({time.time()-start:.1f}s)")
    return len(messages)


async def consolidate_and_synthesize_portrait(coord, user_id: str = "default"):
    """
    🔥 2025-12-24: 巩固阶段 - 合成用户肖像

    将碎片化的 persona 记忆整合成统一的用户描述，
    并更新到 SoulState.user_profile
    """
    # 1. 调用 persona_memory 合成肖像
    if hasattr(coord, 'persona_memory') and coord.persona_memory:
        portrait_data = await coord.persona_memory.synthesize_user_portrait(user_id)

        # 2. 更新 SoulState
        if portrait_data.get('portrait') or portrait_data.get('likes'):
            from src.coordination.soul_state import get_soul_state
            soul = get_soul_state()

            # 更新用户身份
            if portrait_data.get('portrait'):
                soul.update_user_identity(
                    name=user_id if user_id != 'default' else None,
                    description=portrait_data['portrait']
                )

            # 更新偏好
            for item in portrait_data.get('likes', [])[:10]:
                soul.add_user_preference(item, 'like', 0.7)
            for item in portrait_data.get('interests', [])[:10]:
                soul.add_user_preference(item, 'like', 0.7)
            for item in portrait_data.get('dislikes', [])[:5]:
                soul.add_user_preference(item, 'dislike', 0.7)

            # 缓存到 coord 供后续问答使用
            coord._cached_user_portrait = portrait_data

            return portrait_data

    return None


def extract_answer_choice(response: str) -> str:
    """从响应中提取答案选项 (a/b/c/d)"""
    response_lower = response.lower().strip()

    # 直接匹配 (a), (b), (c), (d)
    match = re.search(r'\(([abcd])\)', response_lower)
    if match:
        return f"({match.group(1)})"

    # 匹配 "answer is a" 或 "选择 a"
    match = re.search(r'(?:answer|choice|select|选择|答案)[:\s]*([abcd])', response_lower)
    if match:
        return f"({match.group(1)})"

    # 匹配开头的 a, b, c, d
    if response_lower.startswith(('a ', 'b ', 'c ', 'd ', 'a.', 'b.', 'c.', 'd.')):
        return f"({response_lower[0]})"

    return ""


async def llm_judge_choice(client, question, options, gold, gen):
    """LLM评判多选题"""
    prompt = f"""Question: {question}

Options:
{options}

Correct answer: {gold}
Generated response: {gen}

Does the generated response select the same option as the correct answer?
Return JSON: {{"match": true or false}}"""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an expert grader for multiple choice questions"},
                      {"role": "user", "content": prompt}],
            temperature=0)
        return json.loads(r.choices[0].message.content).get("match", False)
    except:
        # Fallback: 简单匹配
        return gold.lower() in gen.lower()


async def test_questions(coord, questions, client, question_type=None, user_ids: list = None):
    """测试问题集

    Args:
        coord: 协调器
        questions: 问题列表
        client: OpenAI 客户端
        question_type: 只测试特定类型
        user_ids: 用户ID列表 (用于过滤已塑造记忆的用户的问题)
    """
    # 🔥 2025-12-27: 支持多用户过滤
    if user_ids:
        original_count = len(questions)
        questions = [q for q in questions if q.get('shared_context_id') in user_ids]
        print(f"  ⚠️ 过滤到 {len(questions)}/{original_count} 题属于 {len(user_ids)} 个已塑造用户")

    if question_type:
        questions = [q for q in questions if q['question_type'] == question_type]

    correct = 0
    results = []
    type_stats = Counter()
    type_correct = Counter()

    print(f"测试 {len(questions)} 题...")

    for i, q in enumerate(questions, 1):
        qtext = q['user_question_or_message']
        gold = q['correct_answer']
        options = q['all_options']
        qtype = q['question_type']

        # 构建带选项的问题 - 系统应自动检索 persona 记忆
        full_question = f"{qtext}\n\nOptions:\n{options}\n\nPlease select the best answer (a, b, c, or d)."

        # 🔥 2025-12-27: 使用问题所属的用户ID进行记忆检索
        question_user_id = q.get('shared_context_id')
        r = await coord.process_user_input(full_question, context={
            'skip_memory_store': True,
            'evaluation_mode': True,
            'user_id': question_user_id
        })
        gen = r.response if hasattr(r, 'response') else str(r)

        # 提取答案
        extracted = extract_answer_choice(gen)

        # 判断正确性
        if client:
            ok = await llm_judge_choice(client, qtext, options, gold, gen)
        else:
            ok = gold.lower() in gen.lower() or (extracted and gold.lower() == extracted.lower())

        if ok:
            correct += 1
            type_correct[qtype] += 1

        # 🔥 FIX-001: 反馈循环 - 让系统从错误中学习
        # 映射 PersonaMem 问题类型到反馈 query_type
        qtype_map = {
            'preference': 'preference',
            'biographical': 'factual',
            'temporal': 'temporal',
            'relational': 'factual'
        }
        feedback_qtype = qtype_map.get(qtype, 'factual')
        await coord.apply_feedback(
            query_type=feedback_qtype,
            reward_signal=1.0 if ok else 0.0,
            query=qtext,
            response=gen
        )

        type_stats[qtype] += 1
        results.append({
            'question': qtext[:100],
            'type': qtype,
            'gold': gold,
            'gen': gen[:200],
            'extracted': extracted,
            'ok': ok
        })

        print(f"\r  {i}/{len(questions)} {'✓' if ok else '✗'} acc={correct/i*100:.1f}%", end='', flush=True)

        # 更新状态
        if i % 10 == 0:
            save_status({
                'mode': 'personamem',
                'progress': f"{i}/{len(questions)}",
                'running_acc': correct/i,
                'by_type': {t: type_correct[t]/type_stats[t] if type_stats[t] > 0 else 0
                           for t in type_stats},
                'updated': datetime.now().isoformat()
            })

    print(f" → {correct}/{len(questions)} = {correct/len(questions)*100:.1f}%")

    # 按类型统计
    print("\n按类型精度:")
    for t in sorted(type_stats.keys()):
        acc = type_correct[t] / type_stats[t] * 100 if type_stats[t] > 0 else 0
        print(f"  {t}: {type_correct[t]}/{type_stats[t]} = {acc:.1f}%")

    # 🔥 2025-12-27: 返回实际测试的问题数量
    return correct, results, dict(type_stats), dict(type_correct), len(questions)


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--questions', type=int, default=0, help='测试问题数 (0=全部)')
    p.add_argument('--type', type=str, default=None, help='只测试特定类型')
    p.add_argument('--max-context', type=int, default=100, help='每个用户最大塑造消息数')
    p.add_argument('--users', type=int, default=1, help='塑造多少个用户的上下文 (默认1)')
    p.add_argument('--skip-shaping', action='store_true', help='跳过塑造阶段')
    args = p.parse_args()

    print("=" * 60)
    print(f"PersonaMem 评测")
    print("=" * 60)

    # 加载数据
    questions, contexts = load_data()
    print(f"✓ 加载 {len(questions)} 题, {len(contexts)} 上下文")

    if args.questions > 0:
        questions = questions[:args.questions]
        print(f"  限制测试 {len(questions)} 题")

    if args.type:
        orig_len = len(questions)
        questions = [q for q in questions if q['question_type'] == args.type]
        print(f"  过滤类型 '{args.type}': {orig_len} → {len(questions)} 题")

    # 初始化
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")) if LLM_JUDGE else None

    if not args.skip_shaping:
        clear_memory()

    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    # 🔥 2025-12-27: 多用户塑造支持
    shaped_user_ids = []

    # 塑造上下文
    if not args.skip_shaping:
        # 获取要塑造的用户列表
        all_ctx_ids = list(contexts.keys())
        num_users = min(args.users, len(all_ctx_ids))
        selected_ctx_ids = all_ctx_ids[:num_users]

        print(f"🔧 塑造 {num_users} 个用户的上下文...")

        for user_idx, ctx_id in enumerate(selected_ctx_ids, 1):
            messages = contexts[ctx_id]
            print(f"\n[用户 {user_idx}/{num_users}] {ctx_id[:16]}...")

            # 塑造记忆
            await ingest_context(coord, messages, max_messages=args.max_context, user_id=ctx_id)

            # 巩固阶段
            print("  ⏳ 巩固...", end='', flush=True)
            portrait_data = await consolidate_and_synthesize_portrait(coord, user_id=ctx_id)
            if portrait_data:
                print(f" done (portrait: {portrait_data.get('memory_count', 0)} memories)")
            else:
                print(" done")

            shaped_user_ids.append(ctx_id)

        print(f"\n✅ 完成 {len(shaped_user_ids)} 个用户的记忆塑造")
    else:
        print("跳过塑造阶段")
        shaped_user_ids = None  # 跳过塑造时测试所有问题

    # 测试
    start = datetime.now()
    # 🔥 2025-12-27: 传入已塑造的用户ID列表
    correct, results, type_stats, type_correct, tested_count = await test_questions(
        coord, questions, client, args.type, user_ids=shaped_user_ids
    )
    elapsed = (datetime.now() - start).total_seconds()

    acc = correct / tested_count if tested_count else 0

    print("\n" + "=" * 60)
    print(f"完成! 总精度: {acc*100:.2f}% ({correct}/{tested_count})")
    print(f"耗时: {elapsed/60:.1f} min")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(RESULTS_DIR / f'result_{ts}.json', 'w') as f:
        json.dump({
            'config': {'questions': tested_count, 'type': args.type, 'max_context': args.max_context},
            'summary': {'acc': acc, 'correct': correct, 'total': tested_count, 'elapsed': elapsed},
            'by_type': {t: {'correct': type_correct.get(t, 0), 'total': type_stats.get(t, 0),
                           'acc': type_correct.get(t, 0)/type_stats.get(t, 1)}
                       for t in type_stats},
            'results': results[:50]  # 只保存前50条详细结果
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {RESULTS_DIR / f'result_{ts}.json'}")


if __name__ == '__main__':
    asyncio.run(main())
