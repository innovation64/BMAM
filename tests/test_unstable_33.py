#!/usr/bin/env python3
"""
LoCoMo unstable_33 churn-set runner.

Restores the conv-26 OLDBACKUP (locked memory state from 2026-04-13) and
replays only the 33 questions that flipped right↔wrong between two
back-to-back full runs (see tests/data/locomo_unstable_33.json). Used as a
fast feedback loop for answer-selection / answer-shaping changes — runs in
~10 minutes instead of the 55-minute full benchmark.

What "good" looks like:
  - right_to_wrong  (21 questions, were correct in run1): want as many as
    possible to come back correct, i.e. they were unstable losses
  - wrong_to_right  (12 questions, were correct in run2):  want them to
    stay correct, i.e. they were unstable wins we should keep

Usage:
  python tests/test_unstable_33.py
  python tests/test_unstable_33.py --tag c1-evidence-selector

The --tag suffix is appended to the result filename so multiple variants
can be compared.
"""

import asyncio
import json
import os
import sys
import logging
import warnings
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Quiet the world the same way the full benchmark does, so progress is
# readable. (Production logging is fine; we just don't want it interleaved.)
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for _name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss',
              'sentence_transformers', 'transformers', 'huggingface_hub',
              'filelock']:
    logging.getLogger(_name).setLevel(logging.CRITICAL)
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.paths import BMAMPaths

# Reuse the runner's restore + judge helpers verbatim so this stays
# behaviourally identical to the full benchmark; if the full runner's
# semantics change, this picks them up automatically.
from tests.test_locomo_10samples_full import (
    find_backup_for_sample,
    restore_memory_from_backup,
    llm_judge_grader,
    LLM_JUDGE_AVAILABLE,
)

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    _llm_judge_ready = LLM_JUDGE_AVAILABLE
except ImportError:
    _llm_judge_ready = False

FIXTURE_PATH = Path(__file__).parent / 'data' / 'locomo_unstable_33.json'
RESULTS_DIR = Path(__file__).parent.parent / 'metrics' / 'unstable_33'


def _print_row(idx: int, total: int, q: dict, generated: str, is_correct: bool):
    direction = q['churn_direction']
    cat = q['category_name']
    mark = '✓' if is_correct else '✗'
    flip = ''
    if direction == 'right_to_wrong':
        flip = ' RECOVERED' if is_correct else ' STILL_LOST'
    else:  # wrong_to_right
        flip = ' KEPT' if is_correct else ' LOST_AGAIN'
    print(f'[{idx:>2}/{total}] {mark} [{cat}/{direction[:8]}]{flip} '
          f'Q: {q["question"][:80]}')
    print(f'         gold: {str(q["gold"])[:90]}')
    print(f'         pred: {str(generated)[:120]}')


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', type=str, default='', help='suffix for result filename')
    parser.add_argument('--limit', type=int, default=0, help='cap to first N questions (debug)')
    args = parser.parse_args()

    if not FIXTURE_PATH.exists():
        print(f'fixture missing: {FIXTURE_PATH}')
        sys.exit(2)
    fixture = json.loads(FIXTURE_PATH.read_text())
    questions = fixture['questions']
    if args.limit > 0:
        questions = questions[:args.limit]
    print('=' * 60)
    print(f'unstable_33 churn-set runner ({len(questions)} questions)')
    print('=' * 60)

    # 1. Restore the locked memory state.
    sample_id = fixture['sample_id']
    backup = find_backup_for_sample(sample_id)
    if not backup:
        print(f'no backup found for {sample_id}; cannot run')
        sys.exit(2)
    print(f'  [restore] {backup.name}')
    if not restore_memory_from_backup(backup):
        print('  [restore] failed')
        sys.exit(2)

    # 2. Coordinator + judge.
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    llm_client = None
    if _llm_judge_ready:
        try:
            llm_client = AsyncOpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
                base_url=os.getenv('OPENAI_BASE_URL'),
            )
        except Exception as e:
            print(f'  [judge] LLM client failed: {e}; falling back to substring')

    # 3. Replay.
    start = datetime.now()
    results = []
    recovered = 0   # right_to_wrong → correct
    still_lost = 0  # right_to_wrong → wrong
    kept = 0        # wrong_to_right → correct
    lost_again = 0  # wrong_to_right → wrong

    for i, q in enumerate(questions, 1):
        question = q['question']
        gold = q['gold']
        out = await coordinator.process_user_input(
            question,
            context={'skip_memory_store': True}
        )
        generated = out.response if hasattr(out, 'response') else str(out)

        if llm_client:
            is_correct = await llm_judge_grader(llm_client, question, gold, generated)
        else:
            is_correct = str(gold).lower() in str(generated).lower()

        results.append({
            'question': question,
            'gold': gold,
            'generated': generated,
            'category': q['category'],
            'category_name': q['category_name'],
            'churn_direction': q['churn_direction'],
            'run1_correct': q['run1_correct'],
            'run2_correct': q['run2_correct'],
            'now_correct': bool(is_correct),
        })

        if q['churn_direction'] == 'right_to_wrong':
            if is_correct:
                recovered += 1
            else:
                still_lost += 1
        else:
            if is_correct:
                kept += 1
            else:
                lost_again += 1

        _print_row(i, len(questions), q, generated, is_correct)

    elapsed = (datetime.now() - start).total_seconds()

    # 4. Report.
    total_correct = recovered + kept
    print()
    print('=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'  total: {total_correct}/{len(questions)} '
          f'({total_correct / len(questions) * 100:.1f}%)')
    print(f'  right_to_wrong (n=21):  recovered={recovered}  still_lost={still_lost}')
    print(f'  wrong_to_right (n=12):  kept={kept}        lost_again={lost_again}')
    print(f'  elapsed: {elapsed:.1f}s')
    print()
    # Category breakdown
    from collections import defaultdict
    by_cat = defaultdict(lambda: [0, 0])
    for r in results:
        by_cat[r['category_name']][1] += 1
        if r['now_correct']:
            by_cat[r['category_name']][0] += 1
    print('  by category:')
    for cat, (c, t) in sorted(by_cat.items()):
        print(f'    {cat:<12} {c}/{t} ({c / t * 100:.1f}%)')

    # 5. Persist for diffing.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = f'_{args.tag}' if args.tag else ''
    out_path = RESULTS_DIR / f'unstable_33_{ts}{suffix}.json'
    out_path.write_text(json.dumps({
        'timestamp': ts,
        'tag': args.tag,
        'fixture': str(FIXTURE_PATH),
        'fixture_total': fixture['total'],
        'tested': len(results),
        'summary': {
            'total_correct': total_correct,
            'recovered': recovered,
            'still_lost': still_lost,
            'kept': kept,
            'lost_again': lost_again,
            'elapsed_s': elapsed,
        },
        'results': results,
    }, indent=2, ensure_ascii=False))
    print(f'  saved: {out_path}')


if __name__ == '__main__':
    asyncio.run(main())
