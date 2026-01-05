#!/usr/bin/env python3
"""
LongMemEval Benchmark - 长期记忆评测

测试系统对长期对话记忆的推理能力,特别是时间推理。

问题类型:
  - temporal-reasoning: 时间推理 (133题) - 需要理解事件时间顺序
  - multi-session: 多会话推理 (133题) - 跨多个会话的信息整合
  - knowledge-update: 知识更新 (78题) - 信息随时间变化
  - single-session-user: 单会话用户信息 (70题)
  - single-session-assistant: 单会话助手信息 (56题)
  - single-session-preference: 单会话偏好 (30题)

使用:
  python3 test_longmemeval.py                    # 测试全部500题
  python3 test_longmemeval.py --questions 50     # 测试50题
  python3 test_longmemeval.py --type temporal-reasoning  # 只测时间推理
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
LONGMEMEVAL_DIR = PROJECT_ROOT / 'data' / 'datasets' / 'longmemeval'
ORACLE_PATH = LONGMEMEVAL_DIR / 'longmemeval_oracle.json'
DATA_DIR = PROJECT_ROOT / 'data' / 'memory'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'longmemeval'
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


def save_status(status):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def parse_date(date_str):
    """解析日期字符串 (e.g., '2023/04/10 (Mon) 23:07')"""
    if not date_str:
        return datetime.now()
    try:
        # 尝试解析 '2023/04/10 (Mon) 23:07' 格式
        import re
        match = re.match(r'(\d{4})/(\d{2})/(\d{2})\s*\([^)]*\)\s*(\d{2}):(\d{2})', date_str)
        if match:
            y, m, d, h, mi = map(int, match.groups())
            return datetime(y, m, d, h, mi)
        # 尝试其他格式
        from dateutil import parser
        return parser.parse(date_str, fuzzy=True)
    except:
        return datetime.now()


async def ingest_sample(coord, sample):
    """塑造单个样本的会话历史"""
    sessions = sample.get('haystack_sessions', [])
    dates = sample.get('haystack_dates', [])

    total_msgs = sum(len(s) for s in sessions)
    print(f"  塑造 {len(sessions)} 会话, {total_msgs} 消息...", end='', flush=True)
    start = time.time()

    for sess_idx, session in enumerate(sessions):
        # 获取会话日期
        sess_date = parse_date(dates[sess_idx] if sess_idx < len(dates) else None)

        for msg in session:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            has_answer = msg.get('has_answer', False)

            # 带答案的消息给予更高重要性
            importance = 0.8 if has_answer else 0.6

            await coord.store_memory_with_timestamp(
                f"{role.capitalize()}: {content[:1000]}",
                sess_date,
                role,
                importance
            )

    print(f" ✓ ({time.time()-start:.1f}s)")
    return total_msgs


async def llm_judge(client, q, gold, gen):
    """LLM评判开放式问答"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {q}
Gold answer: {gold}
Generated answer: {gen}

Be generous: same meaning = CORRECT. Same date different format = CORRECT.
Partial match with key info = CORRECT.
Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an expert grader"},
                      {"role": "user", "content": prompt}],
            temperature=0)
        return json.loads(r.choices[0].message.content).get("label", "").upper() == "CORRECT"
    except:
        return str(gold).lower() in str(gen).lower()


async def test_sample(coord, sample, client):
    """测试单个样本"""
    q = sample['question']
    gold = sample['answer']

    r = await coord.process_user_input(q, context={'skip_memory_store': True, 'evaluation_mode': True})
    gen = r.response if hasattr(r, 'response') else str(r)

    if client:
        ok = await llm_judge(client, q, gold, gen)
    else:
        ok = str(gold).lower() in str(gen).lower()

    return ok, gen


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--questions', type=int, default=50, help='测试问题数')
    p.add_argument('--type', type=str, default=None, help='只测试特定类型 (temporal-reasoning, multi-session, etc.)')
    p.add_argument('--skip-shaping', action='store_true', help='跳过塑造阶段 (用于调试)')
    args = p.parse_args()

    print("=" * 60)
    print(f"LongMemEval 评测")
    print("=" * 60)

    # 🔥 启动时先清理内存，防止上次中断的残留污染
    clear_memory()
    print("✓ 内存已清理")

    # 加载数据
    with open(ORACLE_PATH, 'r') as f:
        data = json.load(f)

    print(f"✓ 加载 {len(data)} 样本")

    # 过滤类型
    if args.type:
        orig_len = len(data)
        data = [d for d in data if d['question_type'] == args.type]
        print(f"  过滤类型 '{args.type}': {orig_len} → {len(data)} 样本")

    # 限制数量
    if args.questions > 0:
        data = data[:args.questions]
        print(f"  限制测试 {len(data)} 样本")

    # 🔥 2025-12-29: 添加Checkpoint支持断点续跑
    from evaluation.checkpoint_manager import CheckpointManager
    # 使用固定名称以支持跨运行恢复
    checkpoint = CheckpointManager("longmemeval")
    completed_ids = set()
    restored_correct = 0
    restored_tested = 0
    restored_type_stats = {}
    restored_type_correct = {}
    if checkpoint.has_checkpoint():
        # 加载checkpoint并恢复统计数据
        with open(checkpoint.checkpoint_file, 'r') as f:
            ckpt_data = json.load(f)
        completed_ids = set(ckpt_data.get('completed_ids', []))
        metadata = ckpt_data.get('metadata', {})
        restored_correct = metadata.get('correct', 0)
        restored_tested = metadata.get('tested', len(completed_ids))
        restored_type_stats = metadata.get('type_stats', {})
        restored_type_correct = metadata.get('type_correct', {})
        print(f"📌 发现检查点: 已完成 {len(completed_ids)} 样本, 正确 {restored_correct}/{restored_tested} = {restored_correct/restored_tested*100:.1f}%")
        if restored_type_stats:
            print(f"   类型统计: {dict(restored_type_stats)}")

    # 初始化
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")) if LLM_JUDGE else None

    # 统计 - 从checkpoint恢复
    correct = restored_correct
    results = []
    type_stats = Counter(restored_type_stats)
    type_correct = Counter(restored_type_correct)
    start = datetime.now()
    skipped = 0

    for i, sample in enumerate(data, 1):
        qtype = sample['question_type']
        sample_id = sample['question_id']

        # 🔥 跳过已完成的样本
        if sample_id in completed_ids:
            skipped += 1
            continue

        type_stats[qtype] += 1

        print(f"\n[{i}/{len(data)}] {sample_id} ({qtype})")

        # 清空并塑造
        if not args.skip_shaping:
            clear_memory()

            base_coord = BrainInspiredCoordinator()
            hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
            coord = HRMCoordinatorWrapper(base_coord, hrm_config)
            await coord.start_system()

            await ingest_sample(coord, sample)
            await asyncio.sleep(1)  # 短暂巩固
        else:
            if i == 1:
                base_coord = BrainInspiredCoordinator()
                hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
                coord = HRMCoordinatorWrapper(base_coord, hrm_config)
                await coord.start_system()

        # 测试
        ok, gen = await test_sample(coord, sample, client)
        if ok:
            correct += 1
            type_correct[qtype] += 1

        results.append({
            'id': sample['question_id'],
            'type': qtype,
            'question': sample['question'],
            'gold': sample['answer'],
            'gen': str(gen)[:300],
            'ok': ok
        })

        # tested = 已完成的样本数 + 当前这个 (因为还没add到completed_ids)
        tested = len(completed_ids) + 1
        acc = correct / tested if tested > 0 else 0
        print(f"  Q: {sample['question'][:60]}...")
        print(f"  A: {str(sample['answer'])[:60]}...")
        print(f"  → {'✓' if ok else '✗'} (累计: {correct}/{tested} = {acc*100:.1f}%)")

        # 🔥 保存checkpoint (包含每种类型的统计)
        completed_ids.add(sample_id)
        checkpoint.save(completed_ids, metadata={
            'correct': correct,
            'tested': len(completed_ids),  # 用completed_ids长度作为tested
            'accuracy': acc,
            'elapsed_seconds': (datetime.now() - start).total_seconds(),
            'type_stats': dict(type_stats),
            'type_correct': dict(type_correct)
        })

        # 保存状态
        save_status({
            'mode': 'longmemeval',
            'progress': f"{i}/{len(data)}",
            'running_acc': acc,
            'by_type': {t: type_correct[t]/type_stats[t] if type_stats[t] > 0 else 0
                       for t in type_stats},
            'updated': datetime.now().isoformat()
        })

    elapsed = (datetime.now() - start).total_seconds()
    acc = correct / len(data) if data else 0

    print("\n" + "=" * 60)
    print(f"完成! 总精度: {acc*100:.2f}% ({correct}/{len(data)})")
    print(f"耗时: {elapsed/60:.1f} min")

    print("\n按类型精度:")
    for t in sorted(type_stats.keys()):
        t_acc = type_correct[t] / type_stats[t] * 100 if type_stats[t] > 0 else 0
        print(f"  {t}: {type_correct[t]}/{type_stats[t]} = {t_acc:.1f}%")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(RESULTS_DIR / f'result_{ts}.json', 'w') as f:
        json.dump({
            'config': {'questions': len(data), 'type': args.type},
            'summary': {'acc': acc, 'correct': correct, 'total': len(data), 'elapsed': elapsed},
            'by_type': {t: {'correct': type_correct.get(t, 0), 'total': type_stats.get(t, 0),
                           'acc': type_correct.get(t, 0)/type_stats.get(t, 1)}
                       for t in type_stats},
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {RESULTS_DIR / f'result_{ts}.json'}")

    # 🔥 清理checkpoint
    checkpoint.clear()
    print(f"🗑️  清理checkpoint: {checkpoint.test_name}")


if __name__ == '__main__':
    asyncio.run(main())
