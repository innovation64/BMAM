#!/usr/bin/env python3
"""
Per-question diff between two evaluation results.

Shows exactly which questions flipped from correct↔incorrect, grouped by
category. Use after every change to understand actual impact (not just
aggregate score).

Usage:
    python tests/diff_results.py BASELINE.json CURRENT.json

    # Diff two fast_eval files:
    python tests/diff_results.py results/fast_eval/baseline_*.json \\
                                  results/fast_eval/fix_X_*.json

    # Diff two full benchmark results:
    python tests/diff_results.py results/locomo_fresh_*.json \\
                                  results/locomo_test_*.json
"""
import json
import sys
from pathlib import Path

CATEGORY_NAMES = {
    1: 'multi_hop', 2: 'temporal', 3: 'open_domain',
    4: 'single_hop', 5: 'adversarial'
}

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
GRAY = '\033[90m'
BOLD = '\033[1m'
RESET = '\033[0m'


def load_results(path: Path) -> dict:
    """Load result file. Handles both fast_eval and full benchmark formats."""
    data = json.loads(path.read_text())

    # Fast eval format: {results: [...]} at top level
    if 'results' in data and isinstance(data['results'], list):
        if data['results'] and 'qa' in data['results'][0]:
            # Full benchmark format: {results: [{qa: {results: [...]}}]}
            qa_list = []
            for sample in data['results']:
                qa_list.extend(sample['qa']['results'])
            return {'qa': qa_list, 'label': path.stem}
        else:
            # Fast eval format
            return {'qa': data['results'], 'label': data.get('label', path.stem)}

    return {'qa': [], 'label': path.stem}


def diff(baseline: dict, current: dict) -> dict:
    """Build a diff between two result sets."""
    base_by_q = {q['question']: q for q in baseline['qa']}
    curr_by_q = {q['question']: q for q in current['qa']}

    # Match questions present in both
    common = set(base_by_q.keys()) & set(curr_by_q.keys())

    flips = {'improved': [], 'regressed': [], 'unchanged_pass': [], 'unchanged_fail': []}

    for q in common:
        b = base_by_q[q]
        c = curr_by_q[q]
        b_correct = b.get('correct', False)
        c_correct = c.get('correct', False)
        cat = c.get('category', 0)

        entry = {
            'question': q,
            'category': cat,
            'gold': c.get('gold', ''),
            'baseline_gen': str(b.get('generated', ''))[:100],
            'current_gen': str(c.get('generated', ''))[:100],
        }

        if c_correct and not b_correct:
            flips['improved'].append(entry)
        elif not c_correct and b_correct:
            flips['regressed'].append(entry)
        elif c_correct and b_correct:
            flips['unchanged_pass'].append(entry)
        else:
            flips['unchanged_fail'].append(entry)

    return {
        'common': len(common),
        'baseline_total': len(base_by_q),
        'current_total': len(curr_by_q),
        'flips': flips,
    }


def print_diff(d: dict, baseline_label: str, current_label: str):
    print(f"\n{BOLD}=== DIFF: {baseline_label} → {current_label} ==={RESET}")
    print(f"Questions: {d['common']} common ({d['baseline_total']} baseline / {d['current_total']} current)")

    flips = d['flips']
    base_correct = len(flips['improved']) + len(flips['unchanged_fail']) - len(flips['improved']) + len(flips['unchanged_pass']) + len(flips['regressed'])
    curr_correct = len(flips['unchanged_pass']) + len(flips['improved'])
    base_correct = len(flips['unchanged_pass']) + len(flips['regressed'])

    base_acc = base_correct / d['common'] * 100 if d['common'] else 0
    curr_acc = curr_correct / d['common'] * 100 if d['common'] else 0
    delta = curr_acc - base_acc

    delta_color = GREEN if delta > 0 else (RED if delta < 0 else GRAY)
    print(f"\nAccuracy: {base_acc:.1f}% → {curr_acc:.1f}% "
          f"{delta_color}({delta:+.1f}%){RESET}")
    print(f"  Improved: {GREEN}{len(flips['improved'])}{RESET}, "
          f"Regressed: {RED}{len(flips['regressed'])}{RESET}, "
          f"Unchanged: {len(flips['unchanged_pass']) + len(flips['unchanged_fail'])}")

    # Per-category breakdown
    print(f"\n{BOLD}Per-category flips:{RESET}")
    for cat in sorted(CATEGORY_NAMES.keys()):
        cat_imp = [f for f in flips['improved'] if f['category'] == cat]
        cat_reg = [f for f in flips['regressed'] if f['category'] == cat]
        cat_pass = [f for f in flips['unchanged_pass'] if f['category'] == cat]
        cat_fail = [f for f in flips['unchanged_fail'] if f['category'] == cat]
        cat_total = len(cat_imp) + len(cat_reg) + len(cat_pass) + len(cat_fail)

        if cat_total == 0:
            continue

        b_correct = len(cat_pass) + len(cat_reg)
        c_correct = len(cat_pass) + len(cat_imp)
        delta_cat = c_correct - b_correct
        delta_color_cat = GREEN if delta_cat > 0 else (RED if delta_cat < 0 else GRAY)
        name = CATEGORY_NAMES[cat]
        print(f"  {name:14s} {b_correct}/{cat_total} → {c_correct}/{cat_total} "
              f"{delta_color_cat}({delta_cat:+d}){RESET} "
              f"[+{len(cat_imp)} -{len(cat_reg)}]")

    # Show details
    if flips['regressed']:
        print(f"\n{RED}{BOLD}REGRESSED ({len(flips['regressed'])}):{RESET}")
        for f in flips['regressed']:
            cat = CATEGORY_NAMES.get(f['category'], '?')
            print(f"  {RED}-{RESET} [{cat}] {f['question'][:75]}")
            print(f"    {GRAY}gold:{RESET} {f['gold'][:60]}")
            print(f"    {GREEN}was:{RESET}  {f['baseline_gen'][:80]}")
            print(f"    {RED}now:{RESET}  {f['current_gen'][:80]}")
            print()

    if flips['improved']:
        print(f"\n{GREEN}{BOLD}IMPROVED ({len(flips['improved'])}):{RESET}")
        for f in flips['improved']:
            cat = CATEGORY_NAMES.get(f['category'], '?')
            print(f"  {GREEN}+{RESET} [{cat}] {f['question'][:75]}")
            print(f"    {GRAY}gold:{RESET} {f['gold'][:60]}")
            print(f"    {RED}was:{RESET}  {f['baseline_gen'][:80]}")
            print(f"    {GREEN}now:{RESET}  {f['current_gen'][:80]}")
            print()


def main():
    if len(sys.argv) != 3:
        print("Usage: python tests/diff_results.py BASELINE.json CURRENT.json")
        sys.exit(1)

    base_path = Path(sys.argv[1])
    curr_path = Path(sys.argv[2])

    if not base_path.exists():
        print(f"ERROR: Baseline file not found: {base_path}")
        sys.exit(1)
    if not curr_path.exists():
        print(f"ERROR: Current file not found: {curr_path}")
        sys.exit(1)

    baseline = load_results(base_path)
    current = load_results(curr_path)

    d = diff(baseline, current)
    print_diff(d, baseline['label'], current['label'])


if __name__ == '__main__':
    main()
