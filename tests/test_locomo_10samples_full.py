#!/usr/bin/env python3
"""
LoCoMo 10 Samples Full Benchmark
每组测试前清空数据库，塑造完成后备份记忆文件

Usage:
  python3 tests/test_locomo_10samples_full.py
"""

import asyncio
import json
import os
import sys
import shutil
import time
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 关闭冗余日志
import warnings
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss', 'sentence_transformers', 'transformers', 'huggingface_hub', 'filelock']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.paths import BMAMPaths

# OpenAI client for LLM Judge
try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE_AVAILABLE = True
except ImportError:
    LLM_JUDGE_AVAILABLE = False

# 🔥 统一使用 BMAMPaths 管理路径，消除硬编码
LOCOMO_DATA_PATH = BMAMPaths.LOCOMO_DATASET
DATA_DIR = BMAMPaths.DATA_DIR
# 🔥 关键修复: 不再使用 data/memory/ 子目录，直接用 DATA_DIR
MEMORY_DIR = BMAMPaths.DATA_DIR  # 与 test_sequential.py 保持一致
BACKUP_DIR = BMAMPaths.BMAM_ROOT / 'locomo_archives'
CHECKPOINT_DIR = BMAMPaths.BMAM_ROOT / 'locomo_checkpoints'


def load_locomo_data():
    with open(LOCOMO_DATA_PATH, 'r') as f:
        return json.load(f)


def parse_locomo_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now()
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(date_str, fuzzy=True)
    except Exception:
        return datetime.now()


def clear_all_memory_files():
    """清空所有记忆相关文件 - 🔥 使用 BMAMPaths 统一管理"""
    result = BMAMPaths.clean_all_runtime_data()
    # 额外清理 faiss_index 目录（如果存在）
    faiss_dir = BMAMPaths.DATA_DIR / 'faiss_index'
    if faiss_dir.exists():
        shutil.rmtree(faiss_dir)
    print("  [清空] 所有记忆文件已删除")


def backup_memory_files(sample_id: str, timestamp: str):
    """备份当前记忆文件 - 🔥 从 MEMORY_DIR 备份"""
    backup_path = BACKUP_DIR / f"{sample_id}_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        'brain_memory.db',
        'hippocampus_state.json',
        'temporal_lobe.db',
        'amygdala_state.json',
        'prefrontal_state.json',
        'basal_ganglia_state.json',
        'working_memory.db',
        # 🔥 添加关键文件
        'kv_value_store.db',
        'memory_vectors.index',
        'memory_vectors_mappings.json',
        'story_arc_state.json',
    ]

    backed_up = 0
    for f in files_to_backup:
        src = MEMORY_DIR / f
        if src.exists():
            shutil.copy2(src, backup_path / f)
            backed_up += 1

    # 备份faiss_index目录
    faiss_src = MEMORY_DIR / 'faiss_index'
    if faiss_src.exists():
        shutil.copytree(faiss_src, backup_path / 'faiss_index')
        backed_up += 1

    # 备份 embedding_cache 目录
    embedding_cache_src = MEMORY_DIR / 'embedding_cache'
    if embedding_cache_src.exists():
        shutil.copytree(embedding_cache_src, backup_path / 'embedding_cache')
        backed_up += 1

    # 备份 checkpoints 目录
    checkpoints_src = MEMORY_DIR / 'checkpoints'
    if checkpoints_src.exists():
        shutil.copytree(checkpoints_src, backup_path / 'checkpoints')
        backed_up += 1

    print(f"  [备份] {backed_up} 个文件 -> {backup_path.name}")
    return str(backup_path)


def find_backup_for_sample(sample_id: str) -> Path:
    """查找样本的最新备份"""
    if not BACKUP_DIR.exists():
        return None
    # 查找以sample_id开头的备份目录
    backups = list(BACKUP_DIR.glob(f"{sample_id}_*"))
    if not backups:
        return None
    # 返回最新的备份
    return max(backups, key=lambda x: x.stat().st_mtime)


def restore_memory_from_backup(backup_path: Path) -> bool:
    """从备份恢复记忆文件 - 🔥 恢复到 MEMORY_DIR"""
    if not backup_path or not backup_path.exists():
        return False

    # 先清空
    clear_all_memory_files()

    files_to_restore = [
        'brain_memory.db',
        'hippocampus_state.json',
        'temporal_lobe.db',
        'amygdala_state.json',
        'prefrontal_state.json',
        'basal_ganglia_state.json',
        'working_memory.db',
        # 🔥 添加关键文件
        'kv_value_store.db',
        'memory_vectors.index',
        'memory_vectors_mappings.json',
        'story_arc_state.json',
    ]

    restored = 0
    for f in files_to_restore:
        src = backup_path / f
        if src.exists():
            shutil.copy2(src, MEMORY_DIR / f)
            restored += 1

    # 恢复faiss_index目录
    faiss_src = backup_path / 'faiss_index'
    if faiss_src.exists():
        shutil.copytree(faiss_src, MEMORY_DIR / 'faiss_index')
        restored += 1

    # 恢复 embedding_cache 目录
    embedding_cache_src = backup_path / 'embedding_cache'
    if embedding_cache_src.exists():
        dst = MEMORY_DIR / 'embedding_cache'
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(embedding_cache_src, dst)
        restored += 1

    # 恢复 checkpoints 目录
    checkpoints_src = backup_path / 'checkpoints'
    if checkpoints_src.exists():
        dst = MEMORY_DIR / 'checkpoints'
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(checkpoints_src, dst)
        restored += 1

    print(f"  [恢复] {restored} 个文件/目录 <- {backup_path.name}")
    return restored > 0


# ============ 断点续传功能 ============

def save_checkpoint(sample_id: str, session_idx: int):
    """保存塑造断点 - 🔥 从 MEMORY_DIR 保存"""
    checkpoint_path = CHECKPOINT_DIR / sample_id
    checkpoint_path.mkdir(parents=True, exist_ok=True)

    files_to_save = [
        'brain_memory.db',
        'hippocampus_state.json',
        'temporal_lobe.db',
        'amygdala_state.json',
        'prefrontal_state.json',
        'basal_ganglia_state.json',
        'working_memory.db',
    ]

    saved = 0
    for f in files_to_save:
        src = MEMORY_DIR / f
        if src.exists():
            shutil.copy2(src, checkpoint_path / f)
            saved += 1

    # 保存faiss_index
    faiss_src = MEMORY_DIR / 'faiss_index'
    if faiss_src.exists():
        faiss_dst = checkpoint_path / 'faiss_index'
        if faiss_dst.exists():
            shutil.rmtree(faiss_dst)
        shutil.copytree(faiss_src, faiss_dst)
        saved += 1

    # 保存进度信息
    progress_info = {
        'sample_id': sample_id,
        'session_idx': session_idx,
        'timestamp': datetime.now().isoformat()
    }
    with open(checkpoint_path / 'checkpoint.json', 'w') as f:
        json.dump(progress_info, f, indent=2)

    return saved


def load_checkpoint(sample_id: str) -> int:
    """加载断点，返回已完成的session索引，-1表示无断点"""
    checkpoint_path = CHECKPOINT_DIR / sample_id
    progress_file = checkpoint_path / 'checkpoint.json'

    if not progress_file.exists():
        return -1

    try:
        with open(progress_file) as f:
            info = json.load(f)
        return info.get('session_idx', -1)
    except:
        return -1


def restore_from_checkpoint(sample_id: str) -> bool:
    """从断点恢复记忆文件

    🔧 修复: 先验证断点文件完整性，再清空并恢复
    防止断点文件丢失/损坏时导致记忆全部丢失
    """
    checkpoint_path = CHECKPOINT_DIR / sample_id
    if not checkpoint_path.exists():
        return False

    # 🔧 关键修复: 先验证断点文件是否存在且有效
    critical_file = checkpoint_path / 'hippocampus_state.json'
    if not critical_file.exists():
        print(f"  [警告] 断点文件不完整 (缺少 hippocampus_state.json)")
        return False

    # 验证hippocampus_state.json不是空的
    try:
        import json
        with open(critical_file) as f:
            state = json.load(f)
        memories = state.get('memories', [])
        if len(memories) == 0:
            print(f"  [警告] 断点记忆为空，从头开始")
            return False
        print(f"  [断点验证] 找到 {len(memories)} 条记忆")
    except Exception as e:
        print(f"  [警告] 断点文件损坏: {e}")
        return False

    # 验证通过，现在可以安全清空并恢复
    clear_all_memory_files()

    files_to_restore = [
        'brain_memory.db',
        'hippocampus_state.json',
        'temporal_lobe.db',
        'amygdala_state.json',
        'prefrontal_state.json',
        'basal_ganglia_state.json',
        'working_memory.db',
    ]

    restored = 0
    for f in files_to_restore:
        src = checkpoint_path / f
        if src.exists():
            shutil.copy2(src, MEMORY_DIR / f)
            restored += 1

    # 恢复faiss_index
    faiss_src = checkpoint_path / 'faiss_index'
    if faiss_src.exists():
        faiss_dst = MEMORY_DIR / 'faiss_index'
        if faiss_dst.exists():
            shutil.rmtree(faiss_dst)
        shutil.copytree(faiss_src, faiss_dst)
        restored += 1

    return restored > 0


def clear_checkpoint(sample_id: str):
    """清除断点（塑造完成后调用）"""
    checkpoint_path = CHECKPOINT_DIR / sample_id
    if checkpoint_path.exists():
        shutil.rmtree(checkpoint_path)


LIVE_STATUS_FILE = Path(__file__).parent.parent / 'metrics' / 'locomo_bmam_full' / 'live_status.json'


def update_live_status(sample_idx: int, sample_id: str, phase: str, progress: dict):
    """写入实时状态文件供监控脚本读取"""
    LIVE_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    status = {
        'sample_idx': sample_idx,
        'sample_id': sample_id,
        'phase': phase,  # 'shaping' or 'qa'
        'progress': progress,
        'timestamp': datetime.now().isoformat()
    }
    with open(LIVE_STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)


def print_progress_bar(current, total, prefix='', suffix='', length=40, fill='█'):
    percent = f"{100 * current / total:.1f}" if total > 0 else "0"
    filled = int(length * current // total) if total > 0 else 0
    bar = fill * filled + '░' * (length - filled)
    print(f'\r{prefix} |{bar}| {current}/{total} ({percent}%) {suffix}', end='', flush=True)


async def llm_judge_grader(client, question: str, gold_answer: str, generated_answer: str) -> bool:
    system_prompt = "You are an expert grader that determines if answers match a gold standard answer"

    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}

Be generous: if the generated answer covers the same topic/meaning as gold answer, it's CORRECT.
For time questions: same date in different formats = CORRECT.

Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("label", "WRONG").strip().upper() == "CORRECT"
    except:
        return str(gold_answer).lower() in str(generated_answer).lower()


async def ingest_conversation(coordinator, sample, sample_idx, sample_id: str = '') -> dict:
    """喂入对话和观察 - 支持断点续传"""
    conversation = sample['conversation']
    observation = sample.get('observation', {})
    session_num = 1
    start_time = time.time()

    sessions_data = []
    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_date_key = f'{session_key}_date_time'
        obs_key = f'{session_key}_observation'

        dialogues = conversation.get(session_key, [])
        session_date = conversation.get(session_date_key, '2024-01-01')
        session_obs = observation.get(obs_key, {})

        sessions_data.append((dialogues, session_date, session_obs))
        session_num += 1

    total_sessions = len(sessions_data)
    total_turns_estimate = sum(len(s[0]) for s in sessions_data)
    total_obs_estimate = sum(sum(len(obs_list) for obs_list in s[2].values()) for s in sessions_data)

    # 检查断点
    start_session = 0
    checkpoint_session = load_checkpoint(sample_id)
    if checkpoint_session >= 0:
        # 有断点，恢复记忆
        if restore_from_checkpoint(sample_id):
            start_session = checkpoint_session + 1  # 从下一个session开始
            print(f"  [续传] 从Session {start_session + 1}/{total_sessions} 继续 (断点: S{checkpoint_session + 1})")
        else:
            print(f"  [警告] 断点恢复失败，从头开始")

    if start_session == 0:
        print(f"  [塑造] {total_sessions} sessions, ~{total_turns_estimate} turns, ~{total_obs_estimate} obs")
    else:
        remaining = total_sessions - start_session
        print(f"  [塑造] 剩余 {remaining}/{total_sessions} sessions")

    processed_turns = 0
    processed_obs = 0
    for i, (session_dialogues, session_date, session_obs) in enumerate(sessions_data):
        # 跳过已完成的sessions
        if i < start_session:
            continue

        timestamp = parse_locomo_date(session_date)
        tasks = []

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                content = f"{speaker}: {text}"
                task = coordinator.store_memory_with_timestamp(
                    content=content,
                    timestamp=timestamp,
                    speaker=speaker,
                    importance=0.6
                )
                tasks.append(task)

        obs_tasks = []
        for speaker, obs_list in session_obs.items():
            for obs_item in obs_list:
                if isinstance(obs_item, list) and len(obs_item) >= 1:
                    obs_text = obs_item[0]
                    obs_content = f"[Event] {speaker}: {obs_text}"
                    task = coordinator.store_memory_with_timestamp(
                        content=obs_content,
                        timestamp=timestamp,
                        speaker=speaker,
                        importance=0.8
                    )
                    obs_tasks.append(task)

        await asyncio.gather(*tasks)
        await asyncio.gather(*obs_tasks)
        processed_turns += len(tasks)
        processed_obs += len(obs_tasks)

        # 保存断点
        save_checkpoint(sample_id, i)

        print_progress_bar(i + 1, total_sessions, prefix='  塑造', suffix=f'S{i + 1}')

    # 塑造完成，清除断点
    clear_checkpoint(sample_id)

    duration = time.time() - start_time
    print(f"\n  [完成] {processed_turns} turns + {processed_obs} obs in {duration:.1f}s")

    return {'total_turns': processed_turns, 'total_obs': processed_obs, 'sessions': total_sessions, 'duration': duration}


async def test_qa(coordinator, qa_pairs, llm_client, sample_idx: int = 0, sample_id: str = '') -> dict:
    """QA测试"""
    total = len(qa_pairs)
    correct = 0
    results = []

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        gold = qa.get('answer', qa.get('expected_answer', ''))
        category = qa.get('category', 0)

        result = await coordinator.process_user_input(
            question,
            context={'skip_memory_store': True}
        )
        generated = result.response if hasattr(result, 'response') else str(result)

        if LLM_JUDGE_AVAILABLE and llm_client:
            is_correct = await llm_judge_grader(llm_client, question, gold, generated)
        else:
            is_correct = str(gold).lower() in str(generated).lower()

        if is_correct:
            correct += 1

        results.append({
            'question': question,
            'gold': gold,
            'generated': generated,
            'correct': is_correct,
            'category': category
        })

        acc = correct / i * 100
        mark = '✓' if is_correct else '✗'
        print_progress_bar(i, total, prefix='  QA', suffix=f'{mark} {acc:.1f}%')

        # 每5个问题更新一次实时状态
        if i % 5 == 0 or i == total:
            update_live_status(sample_idx, sample_id, 'qa', {
                'current': i, 'total': total, 'correct': correct, 'accuracy': acc
            })

    accuracy = correct / total if total > 0 else 0
    print(f"\n  [结果] {correct}/{total} = {accuracy*100:.1f}%")

    return {'correct': correct, 'total': total, 'accuracy': accuracy, 'results': results}


async def test_single_sample(sample_idx: int, sample: dict, llm_client, timestamp: str, use_backup: bool = True) -> dict:
    """测试单个样本 - 支持从备份恢复或断点续传"""
    sample_id = sample['sample_id']

    print(f"\n{'='*60}")
    print(f"[Sample {sample_idx+1}/10] {sample_id}")
    print('='*60)

    ingest_metrics = None
    backup_path = None

    # 检查是否有备份可用
    existing_backup = find_backup_for_sample(sample_id) if use_backup else None

    if existing_backup:
        # 从备份恢复
        print(f"  [发现备份] {existing_backup.name}")
        restore_memory_from_backup(existing_backup)
        backup_path = str(existing_backup)
        ingest_metrics = {'from_backup': True, 'backup_path': str(existing_backup)}
    else:
        # 检查是否有断点
        checkpoint_session = load_checkpoint(sample_id)
        has_checkpoint = checkpoint_session >= 0

        if not has_checkpoint:
            # 没有断点，清空记忆从头开始
            clear_all_memory_files()
            print(f"  [清空] 所有记忆文件已删除")

        # 创建coordinator进行塑造
        coordinator_ingest = BrainInspiredCoordinator()
        await coordinator_ingest.initialize()

        # 记忆塑造 (支持断点续传)
        ingest_metrics = await ingest_conversation(coordinator_ingest, sample, sample_idx, sample_id)

        # 等待巩固
        print("  [巩固] 等待3s...", end='', flush=True)
        await asyncio.sleep(3)
        print(" done")

        # 备份记忆文件
        backup_path = backup_memory_files(sample_id, timestamp)

    # 6. 创建新coordinator进行QA测试
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 7. QA测试
    qa_pairs = sample['qa']  # 所有问题
    print(f"  [测试] {len(qa_pairs)} questions")
    qa_metrics = await test_qa(coordinator, qa_pairs, llm_client, sample_idx, sample_id)

    return {
        'sample_id': sample_id,
        'sample_idx': sample_idx,
        'ingest': ingest_metrics,
        'qa': qa_metrics,
        'backup_path': backup_path,
        'questions_tested': len(qa_pairs)
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-from', type=int, default=0, help='从第几个样本开始(0-9)')
    args = parser.parse_args()

    start_idx = args.start_from

    print("="*60)
    print("LoCoMo 10 Samples Full Benchmark")
    print(f"  LLM Judge: {'✓' if LLM_JUDGE_AVAILABLE else '✗ (fallback)'}")
    if start_idx > 0:
        print(f"  从Sample {start_idx + 1} (索引{start_idx}) 开始")
    print("="*60)

    # 创建备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # LLM Judge
    llm_client = None
    if LLM_JUDGE_AVAILABLE:
        try:
            llm_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL")
            )
        except:
            pass

    # 加载数据
    data = load_locomo_data()
    print(f"✓ Loaded {len(data)} samples")

    # 结果文件目录
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_bmam_full'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # 测试所有10个样本
    all_results = []
    total_correct = 0
    total_questions = 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 如果从中间开始，尝试加载之前的结果
    if start_idx > 0:
        prev_files = sorted(metrics_dir.glob('results_10samples_all_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
        for prev_file in prev_files:
            try:
                with open(prev_file) as f:
                    prev_data = json.load(f)
                prev_results = prev_data.get('results', [])
                # 检查是否有我们需要的之前样本
                if prev_results and any(r.get('sample_idx', -1) < start_idx for r in prev_results):
                    # 加载之前的结果
                    for r in prev_results:
                        if r.get('sample_idx', -1) < start_idx:
                            all_results.append(r)
                            total_correct += r['qa']['correct']
                            total_questions += r['qa']['total']
                    # 使用之前的时间戳保持一致
                    timestamp = prev_file.stem.replace('results_10samples_all_', '')
                    print(f"✓ 加载之前的结果: {len(all_results)} 个样本 ({total_correct}/{total_questions})")
                    break
            except Exception as e:
                continue

    start_time = datetime.now()
    result_file = metrics_dir / f'results_10samples_all_{timestamp}.json'

    for i in range(start_idx, 10):
        result = await test_single_sample(i, data[i], llm_client, timestamp)
        all_results.append(result)
        total_correct += result['qa']['correct']
        total_questions += result['qa']['total']

        # 实时显示累计结果
        running_acc = total_correct / total_questions * 100
        print(f"  [累计] {total_correct}/{total_questions} = {running_acc:.1f}%")

        # 每完成一组就实时写入结果文件 (供监控脚本读取)
        elapsed_so_far = (datetime.now() - start_time).total_seconds()
        cat_stats = {}
        for r in all_results:
            for qa in r['qa']['results']:
                cat = qa['category']
                if cat not in cat_stats:
                    cat_stats[cat] = {'c': 0, 't': 0}
                cat_stats[cat]['t'] += 1
                if qa['correct']:
                    cat_stats[cat]['c'] += 1

        with open(result_file, 'w') as f:
            json.dump({
                'config': {'samples': 10, 'questions': 'all', 'per_sample_reset': True},
                'summary': {'accuracy': total_correct / total_questions, 'correct': total_correct, 'total': total_questions, 'elapsed': elapsed_so_far},
                'category_stats': cat_stats,
                'results': all_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"  [保存] 实时结果 -> {result_file.name}")

    elapsed = (datetime.now() - start_time).total_seconds()
    overall_acc = total_correct / total_questions if total_questions > 0 else 0

    # 最终结果
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"总精度: {overall_acc*100:.2f}% ({total_correct}/{total_questions})")
    print(f"耗时: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Category breakdown
    category_names = {1: 'multi_hop', 2: 'temporal', 3: 'open_domain', 4: 'single_hop', 5: 'adversarial'}
    cat_stats = {}
    for r in all_results:
        for qa in r['qa']['results']:
            cat = qa['category']
            if cat not in cat_stats:
                cat_stats[cat] = {'c': 0, 't': 0}
            cat_stats[cat]['t'] += 1
            if qa['correct']:
                cat_stats[cat]['c'] += 1

    print("\nCategory:")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        acc = s['c'] / s['t'] * 100 if s['t'] > 0 else 0
        name = category_names.get(cat, f'cat_{cat}')
        print(f"  {name}: {acc:.1f}% ({s['c']}/{s['t']})")

    # Per-sample results
    print("\nPer-Sample:")
    for r in all_results:
        acc = r['qa']['accuracy'] * 100
        print(f"  {r['sample_id']}: {acc:.1f}% ({r['qa']['correct']}/{r['qa']['total']})")

    # 保存结果
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_bmam_full'
    metrics_dir.mkdir(parents=True, exist_ok=True)
    result_file = metrics_dir / f'results_10samples_all_{timestamp}.json'

    with open(result_file, 'w') as f:
        json.dump({
            'config': {'samples': 10, 'questions': 'all', 'per_sample_reset': True},
            'summary': {'accuracy': overall_acc, 'correct': total_correct, 'total': total_questions, 'elapsed': elapsed},
            'category_stats': cat_stats,
            'results': all_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n✓ 结果保存: {result_file}")

    if overall_acc >= 0.70:
        print(f"\n✅ EXCELLENT (≥70%)")
    elif overall_acc >= 0.50:
        print(f"\n✅ PASSED (≥50%)")
    else:
        print(f"\n⚠️  BELOW THRESHOLD (<50%)")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
