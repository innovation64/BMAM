#!/usr/bin/env python3
"""
LoCoMo 顺序测试 - 依次测试10组数据

使用:
  python3 test_sequential.py                    # 测试全部10组
  python3 test_sequential.py --groups 5         # 测试前5组
  python3 test_sequential.py --questions 20     # 每组只测20题

数据集: 10组 (conv-26, conv-30, conv-41, ..., conv-50)
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
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

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
RESULTS_DIR = PROJECT_ROOT / 'experiments' / 'results' / 'sequential'
STATUS_FILE = RESULTS_DIR / 'live_status.json'


def clear_memory():
    """清空记忆文件"""
    files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
             'amygdala_state.json', 'brain_memory.db', 'temporal_lobe.db', 'working_memory.db']
    for f in files:
        p = DATA_DIR / f
        if p.exists(): p.unlink()
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
    """LLM评判 - 使用宽松评判标准"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {q}
Gold answer: {gold}
Generated answer: {gen}

Be generous: same meaning = CORRECT. Same date different format = CORRECT.
Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an expert grader"},
                      {"role": "user", "content": prompt}],
            temperature=0)
        return json.loads(r.choices[0].message.content).get("label", "").upper() == "CORRECT"
    except: return str(gold).lower() in str(gen).lower()


async def ingest(coord, sample, group_idx, total):
    conv = sample['conversation']
    obs = sample.get('observation', {})
    sessions = []
    i = 1
    while f'session_{i}' in conv:
        sessions.append((conv[f'session_{i}'], conv.get(f'session_{i}_date_time', ''), obs.get(f'session_{i}_observation', {})))
        i += 1

    print(f"\n[{group_idx+1}/{total}] {sample['sample_id']}: 塑造 {len(sessions)} sessions")
    start = time.time()

    for idx, (dialogs, date, ob) in enumerate(sessions, 1):
        ts = parse_date(date)

        # 🔥 2025-12-16 FIX: 先存储对话，再解析时间用于 [Event]
        dialog_tasks = []
        for t in dialogs:
            if t.get('text'):
                dialog_tasks.append(coord.store_memory_with_timestamp(f"{t['speaker']}: {t['text']}", ts, t['speaker'], 0.6))

        for task in dialog_tasks:
            await task

        # 从对话中解析精确的事件时间
        from src.agents.brain_regions.hippocampus_agent.storage import extract_event_time_from_content
        session_earliest_event_time = None
        for t in dialogs:
            text = t.get('text', '')
            if text:
                parsed_time, method = extract_event_time_from_content(text, fallback_time=ts)
                if parsed_time and method in ('relative', 'absolute'):
                    if session_earliest_event_time is None or parsed_time < session_earliest_event_time:
                        session_earliest_event_time = parsed_time

        # 存储 [Event] 时传递继承的 event_time
        event_tasks = []
        for spk, items in ob.items():
            for it in items:
                if isinstance(it, list) and it:
                    event_tasks.append(coord.store_memory_with_timestamp(
                        f"[Event] {spk}: {it[0]}", ts, spk, 0.8,
                        inherited_event_time=session_earliest_event_time
                    ))

        for task in event_tasks:
            await task

        print(f"\r  Session {idx}/{len(sessions)}", end='', flush=True)

    print(f" ✓ ({time.time()-start:.1f}s)")
    return len(sessions)


async def test_qa(coord, qas, client, group_idx, total):
    correct = 0
    results = []
    print(f"[{group_idx+1}/{total}] QA: {len(qas)} 题")

    for i, qa in enumerate(qas, 1):
        q, gold, cat = qa['question'], qa.get('answer', ''), qa.get('category', 0)
        # 🔥 2025-12-16 FIX: evaluation_mode=True 阻止响应污染 (外部探索/主动询问提示)
        r = await coord.process_user_input(q, context={'skip_memory_store': True, 'evaluation_mode': True})
        gen = r.response if hasattr(r, 'response') else str(r)
        ok = await llm_judge(client, q, gold, gen) if client else str(gold).lower() in str(gen).lower()
        if ok: correct += 1
        results.append({'q': q, 'gold': gold, 'gen': gen, 'ok': ok, 'cat': cat})
        print(f"\r  {i}/{len(qas)} {'✓' if ok else '✗'} acc={correct/i*100:.1f}%", end='', flush=True)

    print(f" → {correct}/{len(qas)} = {correct/len(qas)*100:.1f}%")
    return correct, results


async def test_group(idx, sample, num_q, client, total, skip_shaping=False):
    if not skip_shaping:
        clear_memory()

    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    if not skip_shaping:
        await ingest(coord, sample, idx, total)
        print("  ⏳ 巩固...", end='', flush=True)
        await asyncio.sleep(3)
        print(" done")
    else:
        print(f"\n[{idx+1}/{total}] {sample['sample_id']}: 跳过塑造，直接测试")

    qas = sample['qa'] if num_q == 'all' else sample['qa'][:num_q]
    correct, results = await test_qa(coord, qas, client, idx, total)
    return {'id': sample['sample_id'], 'idx': idx, 'correct': correct, 'total': len(qas), 'acc': correct/len(qas), 'results': results}


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--groups', type=int, default=10)
    p.add_argument('--questions', default='all')
    p.add_argument('--skip-shaping', action='store_true', help='跳过记忆塑造，直接测试QA')
    args = p.parse_args()

    num_groups = min(max(1, args.groups), 10)
    num_q = 'all' if args.questions == 'all' else int(args.questions)
    skip_shaping = args.skip_shaping

    print("=" * 60)
    print(f"LoCoMo 顺序测试: {num_groups} 组, 每组 {num_q} 题" + (" (跳过塑造)" if skip_shaping else ""))
    print("=" * 60)

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")) if LLM_JUDGE else None
    data = json.load(open(LOCOMO_PATH))
    print(f"✓ 加载 {len(data)} 组")

    results = []
    total_c, total_t = 0, 0
    start = datetime.now()

    for i in range(num_groups):
        r = await test_group(i, data[i], num_q, client, num_groups, skip_shaping=skip_shaping)
        results.append(r)
        total_c += r['correct']
        total_t += r['total']

        # 实时状态
        save_status({
            'mode': 'sequential', 'current_group': i+1, 'total_groups': num_groups,
            'current_id': r['id'], 'running_acc': total_c/total_t,
            'completed': [{'id': x['id'], 'acc': x['acc']} for x in results],
            'updated': datetime.now().isoformat()
        })
        print(f"  📊 累计: {total_c}/{total_t} = {total_c/total_t*100:.1f}%\n")

    elapsed = (datetime.now() - start).total_seconds()
    acc = total_c / total_t

    print("\n" + "=" * 60)
    print(f"完成! 总精度: {acc*100:.2f}% ({total_c}/{total_t})")
    print(f"耗时: {elapsed/60:.1f} min")
    print("\n各组精度:")
    for r in results:
        print(f"  {r['id']}: {r['acc']*100:.1f}% ({r['correct']}/{r['total']})")

    # 保存
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(RESULTS_DIR / f'result_{num_groups}g_{ts}.json', 'w') as f:
        json.dump({'config': {'groups': num_groups, 'questions': str(num_q)},
                   'summary': {'acc': acc, 'correct': total_c, 'total': total_t, 'elapsed': elapsed},
                   'results': results}, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    asyncio.run(main())
