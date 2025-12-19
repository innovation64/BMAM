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
from src.utils.paths import BMAMPaths

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE = True
except ImportError:
    LLM_JUDGE = False

# Dataset path - 使用 BMAMPaths 统一管理
LOCOMO_PATH = BMAMPaths.LOCOMO_DATASET
# 🔥 使用 BMAMPaths 统一路径管理，不再硬编码
DATA_DIR = BMAMPaths.DATA_DIR
RESULTS_DIR = PROJECT_ROOT / 'experiments' / 'results' / 'sequential'
STATUS_FILE = RESULTS_DIR / 'live_status.json'


def clear_memory():
    """清空记忆文件 - 使用 BMAMPaths.clean_all_runtime_data() 保证一致性"""
    result = BMAMPaths.clean_all_runtime_data()
    # 额外清理可能存在的目录
    for d in ['faiss_index']:
        p = BMAMPaths.DATA_DIR / d
        if p.exists(): shutil.rmtree(p)


def export_memory(sample_id: str, acc: float, group_idx: int, coord=None):
    """
    自动导出记忆到 .bma 归档，方便后续切换测试

    🔥 BMA v2.1 格式包含:
    - brain_regions/temporal_lobe.db  (长期记忆)
    - brain_regions/brain_memory.db   (主记忆)
    - brain_regions/working_memory.db (工作记忆)
    - brain_regions/kv_store.db       (KV存储)
    - brain_regions/*.json            (各脑区状态)
    - vectors/                        (FAISS索引)
    - cache/embeddings.json           (Embedding缓存)
    - calibration_state.json          (校准状态)
    """
    try:
        # 确保导出目录存在
        BMAMPaths.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 生成归档名称: locomo_conv-26_73.4pct_20251219_123456.bma
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"locomo_{sample_id}_{acc*100:.1f}pct_{ts}"
        archive_path = BMAMPaths.EXPORTS_DIR / f"{archive_name}.bma"
        archive_path.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (archive_path / "brain_regions").mkdir(exist_ok=True)
        (archive_path / "vectors").mkdir(exist_ok=True)
        (archive_path / "cache").mkdir(exist_ok=True)

        exported_files = []

        # 1. 导出数据库文件
        db_files = [
            (BMAMPaths.BRAIN_MEMORY_DB, "brain_regions/brain_memory.db"),
            (BMAMPaths.TEMPORAL_LOBE_DB, "brain_regions/temporal_lobe.db"),
            (BMAMPaths.WORKING_MEMORY_DB, "brain_regions/working_memory.db"),
            (BMAMPaths.KV_VALUE_STORE_DB, "brain_regions/kv_store.db"),
        ]
        for src, dst in db_files:
            if src.exists():
                shutil.copy2(src, archive_path / dst)
                exported_files.append(dst)

        # 2. 导出状态文件
        state_files = [
            (BMAMPaths.HIPPOCAMPUS_STATE, "brain_regions/hippocampus_state.json"),
            (BMAMPaths.PREFRONTAL_STATE, "brain_regions/prefrontal_state.json"),
            (BMAMPaths.AMYGDALA_STATE, "brain_regions/amygdala_state.json"),
            (BMAMPaths.BASAL_GANGLIA_STATE, "brain_regions/basal_ganglia_state.json"),
            (BMAMPaths.CALIBRATION_STATE, "calibration_state.json"),
        ]
        for src, dst in state_files:
            if src.exists():
                shutil.copy2(src, archive_path / dst)
                exported_files.append(dst)

        # 3. 导出 FAISS 向量索引
        if BMAMPaths.FAISS_INDEX_DIR.exists():
            for f in BMAMPaths.FAISS_INDEX_DIR.iterdir():
                shutil.copy2(f, archive_path / "vectors" / f.name)
                exported_files.append(f"vectors/{f.name}")

        # 4. 导出 Embedding 缓存
        embed_cache = BMAMPaths.EMBEDDING_CACHE_DIR / "embeddings.json"
        if embed_cache.exists():
            shutil.copy2(embed_cache, archive_path / "cache/embeddings.json")
            exported_files.append("cache/embeddings.json")

        # 5. 创建 manifest
        manifest = {
            "format_version": "2.1.0",
            "archive_type": "bmam_memory_archive",
            "created_at": datetime.now().isoformat(),
            "test_info": {
                "dataset": "locomo",
                "sample_id": sample_id,
                "accuracy": acc,
                "group_index": group_idx,
            },
            "files": exported_files,
            "statistics": {
                "db_count": len([f for f in exported_files if f.endswith('.db')]),
                "state_count": len([f for f in exported_files if f.endswith('.json')]),
            }
        }
        with open(archive_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        print(f"  💾 已导出: exports/{archive_name}.bma ({len(exported_files)} files)")
        return True
    except Exception as e:
        print(f"  ⚠️ 导出失败: {e}")
        return False


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
    p.add_argument('--start-from', type=int, default=0, help='从第N组开始（0-indexed），跳过之前的组')
    p.add_argument('--questions', default='all')
    p.add_argument('--skip-shaping', action='store_true', help='跳过记忆塑造，直接测试QA')
    p.add_argument('--export', action='store_true', help='每组测试后自动导出记忆到 data/exports/')
    p.add_argument('--no-export', action='store_true', help='禁用自动导出（默认启用）')
    args = p.parse_args()

    start_from = max(0, args.start_from)
    num_groups = min(max(1, args.groups), 10)
    num_q = 'all' if args.questions == 'all' else int(args.questions)
    skip_shaping = args.skip_shaping
    # 默认启用自动导出，除非明确禁用
    auto_export = not args.no_export

    print("=" * 60)
    start_info = f" (从第{start_from+1}组开始)" if start_from > 0 else ""
    print(f"LoCoMo 顺序测试: {num_groups} 组, 每组 {num_q} 题{start_info}" + (" (跳过塑造)" if skip_shaping else "") + (" [自动导出]" if auto_export else ""))
    print("=" * 60)

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")) if LLM_JUDGE else None
    data = json.load(open(LOCOMO_PATH))
    print(f"✓ 加载 {len(data)} 组")

    results = []
    total_c, total_t = 0, 0
    start = datetime.now()

    # 支持从指定位置开始
    actual_end = min(num_groups, len(data))
    for i in range(start_from, actual_end):
        r = await test_group(i, data[i], num_q, client, actual_end, skip_shaping=skip_shaping)
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

        # 🔥 自动导出记忆归档，方便后续切换测试
        if auto_export:
            export_memory(r['id'], r['acc'], i)

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
