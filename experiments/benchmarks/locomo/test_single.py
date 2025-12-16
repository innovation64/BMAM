#!/usr/bin/env python3
"""
LoCoMo 单组测试 - 测试指定的某一组

使用:
  python3 test_single.py --group conv-26        # 按名称指定
  python3 test_single.py --index 0              # 按索引指定 (0-9)
  python3 test_single.py --index 5 --questions 20   # 只测20题
  python3 test_single.py --group conv-30 --resume   # 从断点续传
  python3 test_single.py --group conv-30 --fresh    # 强制重新开始

断点续传:
  测试崩溃后，重新运行相同组会提示使用 --resume 续传或 --fresh 重来

可用组:
  [0] conv-26: 199题  [1] conv-30: 105题  [2] conv-41: 193题
  [3] conv-42: 260题  [4] conv-43: 242题  [5] conv-44: 158题
  [6] conv-47: 190题  [7] conv-48: 239题  [8] conv-49: 196题
  [9] conv-50: 204题
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

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# Optional HRM wrapper (may not exist in all versions)
try:
    from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper
    HRM_AVAILABLE = True
except ImportError:
    HRM_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE = True
except ImportError:
    LLM_JUDGE = False

# Dataset path - set via environment variable or default relative path
LOCOMO_PATH = Path(os.getenv('LOCOMO_DATASET_PATH', PROJECT_ROOT / 'datasets' / 'locomo' / 'locomo10.json'))
DATA_DIR = PROJECT_ROOT / 'data'
RESULTS_DIR = PROJECT_ROOT / 'experiments' / 'results' / 'single'
STATUS_FILE = RESULTS_DIR / 'live_status.json'
CHECKPOINT_FILE = RESULTS_DIR / 'checkpoint.json'


def save_checkpoint(group_id, phase, session_idx=0, qa_idx=0, correct=0, results=None):
    """保存断点信息"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            'group': group_id,
            'phase': phase,
            'session_idx': session_idx,
            'qa_idx': qa_idx,
            'correct': correct,
            'results': results or [],
            'updated': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)


def load_checkpoint():
    """加载断点信息"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def clear_checkpoint():
    """清除断点"""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def clear_memory():
    """清空记忆文件"""
    files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
             'amygdala_state.json', 'brain_memory.db', 'temporal_lobe.db', 'working_memory.db']
    for f in files:
        p = DATA_DIR / f
        if p.exists(): p.unlink()
    # 清除目录
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = DATA_DIR / d
        if p.exists(): shutil.rmtree(p)


def parse_date(s):
    if not s: return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except: return datetime.now()


def save_status(status):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


async def llm_judge(client, q, gold, gen):
    """LLM评判 - 与MemOS标准对齐"""
    system_prompt = """You are an expert grader that determines if answers to questions match a gold standard answer"""

    accuracy_prompt = f"""Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given the following data:
    (1) a question (posed by one user to another user),
    (2) a 'gold' (ground truth) answer,
    (3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Do you remember what I got the last time I went to Hawaii?
Gold answer: A shell necklace
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {q}
Gold answer: {gold}
Generated answer: {gen}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label"."""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": accuracy_prompt}],
            temperature=0)
        return json.loads(r.choices[0].message.content).get("label", "").upper() == "CORRECT"
    except: return str(gold).lower() in str(gen).lower()


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--group', type=str, help='组名称 (如 conv-26)')
    p.add_argument('--index', type=int, help='组索引 (0-9)')
    p.add_argument('--questions', default='all')
    p.add_argument('--list', action='store_true', help='列出所有可用组')
    p.add_argument('--resume', action='store_true', help='从断点续传')
    p.add_argument('--fresh', action='store_true', help='强制重新开始')
    p.add_argument('--hrm', action='store_true', help='使用HRM迭代反馈模式')
    args = p.parse_args()

    data = json.load(open(LOCOMO_PATH))

    # 列出所有组
    if args.list:
        print("可用组:")
        for i, d in enumerate(data):
            print(f"  [{i}] {d['sample_id']}: {len(d['qa'])} 题")
        return

    # 确定要测试的组
    if args.group:
        sample = next((d for d in data if d['sample_id'] == args.group), None)
        if not sample:
            print(f"❌ 找不到组: {args.group}")
            print("可用组:", [d['sample_id'] for d in data])
            return
        group_idx = data.index(sample)
    elif args.index is not None:
        if args.index < 0 or args.index >= len(data):
            print(f"❌ 索引超出范围: {args.index} (有效: 0-{len(data)-1})")
            return
        sample = data[args.index]
        group_idx = args.index
    else:
        print("❌ 请指定 --group 或 --index")
        p.print_help()
        return

    num_q = 'all' if args.questions == 'all' else int(args.questions)
    group_id = sample['sample_id']

    # 检查断点
    checkpoint = load_checkpoint()
    resume_mode = False
    start_session = 0
    start_qa = 0
    prev_correct = 0
    prev_results = []

    if checkpoint and checkpoint.get('group') == group_id and not args.fresh:
        if args.resume:
            resume_mode = True
        else:
            print(f"⚠️  发现未完成的测试: {group_id}")
            print(f"   阶段: {checkpoint.get('phase')}, 进度: session={checkpoint.get('session_idx')}, qa={checkpoint.get('qa_idx')}")
            print(f"   使用 --resume 续传, --fresh 重新开始")
            return

    if resume_mode:
        start_session = checkpoint.get('session_idx', 0)
        start_qa = checkpoint.get('qa_idx', 0)
        prev_correct = checkpoint.get('correct', 0)
        prev_results = checkpoint.get('results', [])
        print(f"📍 断点续传: 从 session {start_session}, qa {start_qa} 继续")

    print("=" * 60)
    print(f"LoCoMo 单组测试: {group_id} (索引 {group_idx})")
    qa_count = len(sample['qa'])
    print(f"问题数: {num_q if num_q == 'all' else f'{num_q}/{qa_count}'}")
    if resume_mode:
        print(f"续传模式: session从{start_session}开始, qa从{start_qa}开始")
    print("=" * 60)

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")) if LLM_JUDGE else None

    # 清除记忆（仅在非续传模式）
    if not resume_mode:
        clear_memory()
        clear_checkpoint()

    # 选择 coordinator 模式
    base_coord = BrainInspiredCoordinator()
    await base_coord.initialize()

    if args.hrm:
        if not HRM_AVAILABLE:
            print("⚠️  HRM 模式不可用，使用标准模式")
            coord = base_coord
        else:
            print("🔄 使用 HRM 迭代反馈模式")
            coord = HRMCoordinatorWrapper(base_coord)
            await coord.initialize()
    else:
        coord = base_coord

    # 记忆塑造
    conv = sample['conversation']
    obs = sample.get('observation', {})
    sessions = []
    i = 1
    while f'session_{i}' in conv:
        sessions.append((conv[f'session_{i}'], conv.get(f'session_{i}_date_time', ''), obs.get(f'session_{i}_observation', {})))
        i += 1

    print(f"\n记忆塑造: {len(sessions)} sessions" + (f" (从{start_session+1}开始)" if start_session > 0 else ""))
    start = time.time()

    for idx, (dialogs, date, ob) in enumerate(sessions, 1):
        # 跳过已完成的session
        if idx <= start_session:
            print(f"\r  Session {idx}/{len(sessions)} [跳过]", end='', flush=True)
            continue

        ts = parse_date(date)
        # 格式化日期用于 [Context:] 前缀
        date_context = ts.strftime('%d %B %Y') if ts else ''  # e.g., "08 May 2023"

        # 🔥 2025-12-16 FIX: 先存储原始对话，收集精确的 event_time
        # 然后让 [Event] 记忆继承这些精确时间
        dialog_tasks = []
        for t in dialogs:
            if t.get('text'):
                content = f"{t['speaker']}: {t['text']}"
                dialog_tasks.append(coord.store_memory_with_timestamp(content, ts, t['speaker'], 0.6))

        # 执行对话存储并收集结果
        dialog_results = []
        for task in dialog_tasks:
            result = await task
            dialog_results.append(result)

        # 从对话结果中提取精确的 event_time (relative/absolute 方法提取的)
        # 用于传递给 [Event] 记忆
        session_event_times = []
        for result in dialog_results:
            if result and isinstance(result, dict):
                # 检查存储结果中是否有精确的 event_time
                # 实际上我们需要从 hippocampus 的返回中获取
                # 但当前返回格式可能没有 event_time，所以我们需要另一种方式
                pass

        # 🔥 简化方案：从对话文本中直接解析相对时间词
        # 如果对话包含 "yesterday", "last week" 等，计算对应的日期
        from src.agents.brain_regions.hippocampus_agent.storage import extract_event_time_from_content

        session_earliest_event_time = None
        for t in dialogs:
            text = t.get('text', '')
            if text:
                # 尝试从对话中解析相对时间
                parsed_time, method = extract_event_time_from_content(text, fallback_time=ts)
                # 只使用高置信度方法 (relative, absolute) 的结果
                if parsed_time and method in ('relative', 'absolute'):
                    if session_earliest_event_time is None or parsed_time < session_earliest_event_time:
                        session_earliest_event_time = parsed_time

        # 存储 [Event] 记忆，使用继承的 event_time
        event_tasks = []
        for spk, items in ob.items():
            for it in items:
                if isinstance(it, list) and it:
                    event_content = f"[Event] {spk}: {it[0]}"
                    # 🔥 传递继承的 event_time
                    event_tasks.append(coord.store_memory_with_timestamp(
                        event_content, ts, spk, 0.8,
                        inherited_event_time=session_earliest_event_time
                    ))

        # 执行 [Event] 存储
        for task in event_tasks:
            await task

        # 保存断点
        save_checkpoint(group_id, 'ingest', session_idx=idx)
        save_status({'group': group_id, 'phase': 'ingest', 'progress': f"{idx}/{len(sessions)}", 'updated': datetime.now().isoformat()})
        print(f"\r  Session {idx}/{len(sessions)}", end='', flush=True)

    print(f" ✓ ({time.time()-start:.1f}s)")

    # 真正的巩固处理
    print("⏳ 巩固中...", end='', flush=True)
    consolidation_start = time.time()
    try:
        # 调用显式巩固
        if hasattr(coord, 'consolidate_memories'):
            result = await coord.consolidate_memories()
            consolidated = result.get('consolidated', 0) if isinstance(result, dict) else 0
            print(f" ✓ ({consolidated} 条, {time.time()-consolidation_start:.1f}s)")
        else:
            await asyncio.sleep(3)
            print(" done (fallback)")
    except Exception as e:
        print(f" ⚠️ 失败: {e}")
        await asyncio.sleep(1)

    # QA测试
    qas = sample['qa'] if num_q == 'all' else sample['qa'][:num_q]
    print(f"\nQA测试: {len(qas)} 题" + (f" (从{start_qa+1}开始)" if start_qa > 0 else ""))

    correct = prev_correct
    results = prev_results.copy()
    cat_stats = {}

    # 从已有结果重建分类统计
    for r in results:
        cat = r.get('cat', 0)
        if cat not in cat_stats:
            cat_stats[cat] = {'c': 0, 't': 0}
        cat_stats[cat]['t'] += 1
        if r.get('ok'): cat_stats[cat]['c'] += 1

    for i, qa in enumerate(qas, 1):
        # 跳过已完成的题目
        if i <= start_qa:
            continue

        q, gold, cat = qa['question'], qa.get('answer', ''), qa.get('category', 0)
        # 🔥 2025-12-16 FIX: evaluation_mode=True 阻止响应污染
        r = await coord.process_user_input(q, context={'skip_memory_store': True, 'evaluation_mode': True})
        gen = r.response if hasattr(r, 'response') else str(r)
        ok = await llm_judge(client, q, gold, gen) if client else str(gold).lower() in str(gen).lower()
        if ok: correct += 1

        # 分类统计
        if cat not in cat_stats:
            cat_stats[cat] = {'c': 0, 't': 0}
        cat_stats[cat]['t'] += 1
        if ok: cat_stats[cat]['c'] += 1

        results.append({'q': q, 'gold': gold, 'gen': gen, 'ok': ok, 'cat': cat})

        # 获取检索统计
        retrieval_stats = getattr(coord, 'last_retrieval_stats', {})

        # 保存断点
        save_checkpoint(group_id, 'qa', session_idx=len(sessions), qa_idx=i, correct=correct, results=results)
        save_status({
            'group': group_id, 'phase': 'qa', 'progress': f"{i}/{len(qas)}",
            'acc': correct/i, 'updated': datetime.now().isoformat(),
            'retrieval': retrieval_stats  # 多轮检索统计
        })
        mr = '🔄' if retrieval_stats.get('multi_round') else '⚡'
        print(f"\r  {i}/{len(qas)} {'✓' if ok else '✗'} {mr} acc={correct/i*100:.1f}%", end='', flush=True)

    acc = correct / len(qas)
    print(f"\n\n{'='*60}")
    print(f"结果: {correct}/{len(qas)} = {acc*100:.2f}%")

    # 分类精度 (与LoCoMo数据集定义一致)
    cat_names = {1: 'multi_hop', 2: 'temporal', 3: 'open_domain', 4: 'single_hop', 5: 'adversarial'}
    print("\n分类精度:")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        cat_acc = s['c'] / s['t'] * 100 if s['t'] > 0 else 0
        print(f"  {cat_names.get(cat, f'cat_{cat}')}: {cat_acc:.1f}% ({s['c']}/{s['t']})")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f'{group_id}_{ts}.json'

    with open(result_file, 'w') as f:
        json.dump({
            'config': {'group': group_id, 'index': group_idx, 'questions': str(num_q)},
            'summary': {'acc': acc, 'correct': correct, 'total': len(qas)},
            'category_stats': cat_stats,
            'results': results
        }, f, indent=2, ensure_ascii=False)

    # 测试完成，清除断点
    clear_checkpoint()
    print(f"\n✓ 保存: {result_file}")


if __name__ == '__main__':
    asyncio.run(main())
