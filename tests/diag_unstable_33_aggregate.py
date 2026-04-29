#!/usr/bin/env python3
"""Aggregate metrics across N unstable_33 runs (--tag diag_run{1..N}).

Reports:
  per-run accuracy
  mean / std
  majority-vote accuracy        (per-question majority of `now_correct`)
  oracle accuracy               (any-of-N correct)
  per-question path distribution + entropy
  per-question answer distribution
  route-conditioned accuracy    (orchestrator / reasoning_chain / conversation / temporal)

Diagnostic tool only — does not change the system, does not gate any
decision. Use the metrics to choose between B (deterministic routing
+ cache + arbitration) vs C (switch workload to AURA) vs continued
layer-specific surgery.
"""
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev


REPO = Path(__file__).parent.parent
RESULTS_DIR = REPO / 'metrics' / 'unstable_33'
AUDIT_DIR = REPO / 'metrics' / 'audit'


def find_files(tag_prefix: str):
    """Return [(result_json, audit_jsonl)] sorted by timestamp for tags
    matching `<tag_prefix>{1..}`. Each result is paired with the audit file
    written closest in time (the runner writes them with a few seconds of
    skew but same minute).
    """
    pairs = []
    for results_path in sorted(RESULTS_DIR.glob(f'unstable_33_*_{tag_prefix}*.json')):
        ts = results_path.stem.split('_')[2]  # YYYYMMDD_HHMMSS prefix piece
        # Match on the trailing tag suffix (like diag_run1, diag_run2…) by
        # parsing the canonical name "unstable_33_<ts>_<tag>".
        tag = '_'.join(results_path.stem.split('_')[4:])
        # Find audit file with same tag
        candidates = list(AUDIT_DIR.glob(f'audit_*_{tag}.jsonl'))
        audit_path = candidates[0] if candidates else None
        pairs.append((results_path, audit_path, tag))
    pairs.sort(key=lambda x: x[0].stat().st_mtime)
    return pairs


def load_run(result_path: Path, audit_path: Path):
    """Return (per_qid_correct: dict[qid -> bool], per_qid_path: dict[qid -> str],
                per_qid_pred: dict[qid -> str])."""
    res = json.loads(result_path.read_text())
    correct = {}
    pred = {}
    for i, r in enumerate(res['results'], 1):
        qid = f'unstable_33_{i:02d}'
        correct[qid] = bool(r.get('now_correct'))
        pred[qid] = r.get('generated', '')

    paths = {}
    if audit_path and audit_path.exists():
        for line in audit_path.read_text().splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            if ev.get('probe') != 'answer_path_decision':
                continue
            qid = ev.get('qid')
            if qid:
                paths[qid] = ev.get('answer_path')
    return correct, paths, pred


def entropy(counter: Counter) -> float:
    """Shannon entropy of a path distribution (in bits)."""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    h = 0.0
    for v in counter.values():
        p = v / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag-prefix', default='diag_run',
                        help='matches tags like <prefix>1, <prefix>2, ...')
    args = parser.parse_args()

    pairs = find_files(args.tag_prefix)
    if not pairs:
        print(f'No runs found for tag prefix {args.tag_prefix!r}')
        return
    print(f'Found {len(pairs)} runs:')
    for r, a, t in pairs:
        print(f'  {t}: {r.name}  audit={a.name if a else "MISSING"}')

    runs = [load_run(r, a) for r, a, _ in pairs]
    n = len(runs)
    qids = sorted({q for c, _, _ in runs for q in c})

    # ---- per-run accuracy ----
    print()
    print('=' * 70)
    print('Per-run accuracy')
    print('=' * 70)
    per_run = []
    for i, (correct, _, _) in enumerate(runs, 1):
        c = sum(1 for q in qids if correct.get(q))
        per_run.append(c)
        print(f'  run{i}: {c}/{len(qids)} ({c/len(qids)*100:.1f}%)')
    if n >= 2:
        print(f'  mean: {mean(per_run):.2f}  std: {stdev(per_run):.2f}  '
              f'min: {min(per_run)}  max: {max(per_run)}')

    # ---- majority + oracle ----
    print()
    print('=' * 70)
    print('Majority vote / oracle')
    print('=' * 70)
    majority_correct = 0
    oracle_correct = 0
    unanimous_correct = 0
    unanimous_wrong = 0
    for q in qids:
        votes = [c.get(q, False) for c, _, _ in runs]
        if sum(votes) > n / 2:
            majority_correct += 1
        if any(votes):
            oracle_correct += 1
        if all(votes):
            unanimous_correct += 1
        if not any(votes):
            unanimous_wrong += 1
    print(f'  majority-vote correct: {majority_correct}/{len(qids)} '
          f'({majority_correct/len(qids)*100:.1f}%)')
    print(f'  oracle (any-correct):  {oracle_correct}/{len(qids)} '
          f'({oracle_correct/len(qids)*100:.1f}%)')
    print(f'  unanimous correct:     {unanimous_correct}/{len(qids)} '
          f'(stable answers)')
    print(f'  unanimous wrong:       {unanimous_wrong}/{len(qids)} '
          f'(consistently failing)')
    print(f'  unstable (mix):        {len(qids)-unanimous_correct-unanimous_wrong}/{len(qids)}')

    # ---- per-question path distribution + entropy ----
    print()
    print('=' * 70)
    print('Per-question path distribution + entropy + correctness')
    print('=' * 70)
    print(f'{"qid":<22} {"unanim":<7} {"oracle":<7} {"paths_seen":<32} {"entropy":<8}')
    high_entropy_count = 0
    for q in qids:
        paths = [r[1].get(q, '?') for r in runs]
        ctr = Counter(paths)
        h = entropy(ctr)
        votes = [r[0].get(q, False) for r in runs]
        oracle = any(votes)
        unanim = all(votes) or not any(votes)
        if h > 1.0:
            high_entropy_count += 1
        path_str = ','.join(f'{p}:{c}' for p, c in ctr.most_common())
        print(f'{q:<22} {"yes" if unanim else "no":<7} '
              f'{"yes" if oracle else "no":<7} '
              f'{path_str[:30]:<32} {h:<8.2f}')
    print(f'\n  high-entropy (>1.0 bit) questions: {high_entropy_count}/{len(qids)}')

    # ---- route-conditioned accuracy ----
    print()
    print('=' * 70)
    print('Route-conditioned accuracy (across all runs × questions)')
    print('=' * 70)
    route_stats = defaultdict(lambda: [0, 0])  # [correct, total]
    for run_correct, run_paths, _ in runs:
        for q in qids:
            p = run_paths.get(q)
            if p is None:
                continue
            route_stats[p][1] += 1
            if run_correct.get(q):
                route_stats[p][0] += 1
    print(f'{"path":<24} {"correct":<14} {"rate":<8}')
    for p, (c, t) in sorted(route_stats.items(), key=lambda x: -x[1][1]):
        rate = c / t * 100 if t else 0
        print(f'{p:<24} {c}/{t:<13} {rate:>5.1f}%')

    # ---- per-question best path (oracle by route) ----
    print()
    print('=' * 70)
    print('Per-question best path (was the right answer reachable on any route?)')
    print('=' * 70)
    correct_by_path = defaultdict(int)  # path → questions where this path produced a correct
    for run_correct, run_paths, _ in runs:
        for q in qids:
            if run_correct.get(q):
                p = run_paths.get(q, '?')
                correct_by_path[p] += 1
    print('  total CORRECT outcomes per path (cumulative across runs):')
    for p, c in sorted(correct_by_path.items(), key=lambda x: -x[1]):
        print(f'    {p:<22} {c}')

    print()
    print('=' * 70)
    print('Decision-tree mapping')
    print('=' * 70)
    maj = majority_correct
    orc = oracle_correct
    if maj >= 27 or orc >= 29:
        verdict = 'B: deterministic routing + cache + arbitration'
    elif 24 <= maj <= 26 and orc - maj >= 3:
        verdict = 'stabilize routing first, then revisit fact_recall'
    elif maj <= 23 and orc - maj < 3:
        verdict = 'C: stop chasing LoCoMo, transition to AURA / different workload'
    else:
        verdict = 'mixed signal — see route-conditioned table'
    print(f'  majority={maj}/{len(qids)}  oracle={orc}/{len(qids)}  '
          f'gap={orc-maj}')
    print(f'  → recommended next step: {verdict}')


if __name__ == '__main__':
    main()
