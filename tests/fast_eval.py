#!/usr/bin/env python3
"""
Fast Evaluation Runner — 30 questions, ~3 min runtime

Uses pre-shaped conv-26 memory backup to skip the 15-min shaping phase.
For rapid iteration during optimization. Reports per-category accuracy
and saves results compatible with diff_results.py.

Usage:
    python tests/fast_eval.py [--label NAME]
"""
import asyncio
import json
import os
import sys
import logging
import warnings
import argparse
from datetime import datetime
from pathlib import Path

warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.WARNING)
for ln in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss',
           'sentence_transformers', 'transformers', 'huggingface_hub', 'filelock']:
    logging.getLogger(ln).setLevel(logging.WARNING)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# BMAM root
BMAM_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BMAM_ROOT))
sys.path.insert(0, str(BMAM_ROOT / 'tests'))

CATEGORY_NAMES = {
    1: 'multi_hop', 2: 'temporal', 3: 'open_domain',
    4: 'single_hop', 5: 'adversarial'
}


async def shape_conv26_if_needed():
    """Run full shaping for conv-26 once to generate baseline memory state."""
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()

    from test_locomo_10samples_full import (
        load_locomo_data, test_single_sample
    )

    llm_client = AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL')
    )
    data = load_locomo_data()
    print("=== Initial shaping for conv-26 (one-time, ~15 min) ===")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    await test_single_sample(0, data[0], llm_client, timestamp)
    print("=== Shaping complete, memory backup created ===\n")


async def run_fast_eval(label: str = None):
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
    from src.utils.paths import BMAMPaths

    load_dotenv()

    # Load eval questions
    eval_file = BMAM_ROOT / 'tests' / 'fast_eval_questions.json'
    eval_data = json.loads(eval_file.read_text())
    questions = eval_data['questions']
    print(f"Loaded {len(questions)} eval questions")

    # Find conv-26 backup (must exist from a prior full run)
    archives = BMAM_ROOT / 'locomo_archives'

    def find_valid_backup():
        backups = sorted(archives.glob('conv-26_*'))
        for b in reversed(backups):
            # Valid backup must have core memory files
            has_memory_db = (b / 'memory' / 'brain_memory.db').exists()
            has_state = (b / 'state' / 'hippocampus_state.json').exists()
            if has_memory_db and has_state:
                return b
        return None

    backup = find_valid_backup()
    if not backup:
        print("No valid conv-26 backup found. Running full shaping...")
        await shape_conv26_if_needed()
        backup = find_valid_backup()
        if not backup:
            print("ERROR: Shaping completed but no valid backup created.")
            return

    print(f"Using memory backup: {backup.name}")

    # Restore memory from backup (state/ → data/state/, memory/ → data/memory/)
    BMAMPaths.clean_all_runtime_data()
    import shutil, stat
    data_dir = BMAMPaths.DATA_DIR
    (data_dir / 'state').mkdir(parents=True, exist_ok=True)
    (data_dir / 'memory').mkdir(parents=True, exist_ok=True)

    for item in backup.iterdir():
        if item.is_dir() and item.name in ('state', 'memory'):
            target = data_dir / item.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        elif item.is_dir() and item.name == 'embedding_cache':
            target = data_dir / 'cache' / 'embedding'
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)

    # Ensure restored files are writable (sqlite needs write access for journal)
    for p in data_dir.rglob('*'):
        if p.is_file():
            p.chmod(p.stat().st_mode | stat.S_IWUSR | stat.S_IWGRP)

    print(f"Memory restored from {backup.name}")

    # Init coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Init LLM judge
    llm_client = AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL')
    )

    from test_locomo_10samples_full import llm_judge_grader

    # Run questions
    results = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    label = label or 'fast_eval'
    correct = 0

    print(f"\nRunning {len(questions)} questions...")
    for i, q in enumerate(questions, 1):
        question = q['question']
        gold = q['gold']
        category = q['category']
        # Cat 5 = adversarial: gold is the TRAP answer system should avoid
        is_adversarial = (category == 5)

        try:
            result = await coordinator.process_user_input(
                question,
                context={'skip_memory_store': True}
            )
            generated = result.response if hasattr(result, 'response') else str(result)

            matches = await llm_judge_grader(llm_client, question, gold, generated)
            # For adversarial: correct = system did NOT fall into the trap
            is_correct = (not matches) if is_adversarial else matches
        except Exception as e:
            print(f"  ERROR on Q{i}: {e}")
            generated = f'ERROR: {e}'
            is_correct = False

        results.append({
            'question': question,
            'gold': gold,
            'generated': generated,
            'correct': is_correct,
            'category': category,
        })

        if is_correct:
            correct += 1

        status = '✓' if is_correct else '✗'
        print(f"  [{i:2d}/{len(questions)}] {status} cat={category} {question[:60]}")

    # Stats
    acc = correct / len(questions) * 100
    cat_stats = {}
    for r in results:
        cat = r['category']
        if cat not in cat_stats:
            cat_stats[cat] = {'c': 0, 't': 0}
        cat_stats[cat]['t'] += 1
        if r['correct']:
            cat_stats[cat]['c'] += 1

    print(f"\n{'='*60}")
    print(f"FAST EVAL RESULT: {acc:.1f}% ({correct}/{len(questions)})")
    print(f"\nCategory:")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        name = CATEGORY_NAMES.get(cat, f'cat_{cat}')
        print(f"  {name}: {s['c']}/{s['t']}")

    # Save
    out_dir = BMAM_ROOT / 'results' / 'fast_eval'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{label}_{timestamp}.json'
    with open(out_file, 'w') as f:
        json.dump({
            'label': label,
            'timestamp': timestamp,
            'accuracy': acc / 100,
            'correct': correct,
            'total': len(questions),
            'cat_stats': cat_stats,
            'results': results,
        }, f, indent=2, default=str)
    print(f"\nSaved: {out_file}")
    return out_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', type=str, default=None,
                        help='Label for this run (e.g. "baseline", "fix_X")')
    args = parser.parse_args()
    asyncio.run(run_fast_eval(args.label))
