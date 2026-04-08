# Stable Failure Targets (Baseline, judge-fixed)

Based on 3 fast_eval runs with the **corrected judge** (adversarial
questions now use `adversarial_answer` with inverted match).

**Runs analyzed**: baseline_judgefix, baseline_jf2, baseline_jf3 (2026-04-08)
**Score range**: 13-16/29 across 3 runs
**Stable pass**: 13/29
**Stable fail**: 12/29 ← real optimization targets
**Flaky (noise)**: 4/29

## Evolution from pre-judgefix baseline

Pre-judgefix (broken): 14 stable fail, including 3 adversarial
Post-judgefix (correct): 12 stable fail, only 1 adversarial

The "reduction" of 2 stable fails = benchmark correctness fix, not
system improvement. 2 adversarial failures were measurement artifacts.

## Targets by Category

### multi_hop (3)
- What did Melanie paint recently?
- What subject have Caroline and Melanie both painted?
- What symbols are important to Caroline?

**Pattern**: Cross-session aggregation. Retrieval finds individual
mentions but can't summarize across multiple memories.

### temporal (3)
- When did Caroline meet up with her friends, family, and mentors?
- When did Melanie sign up for a pottery class?
- When did Melanie go to the pottery workshop?

**Pattern**: Wrong session matched. Multiple sessions mention same
entity+topic, picks wrong date. Root cause: flat memory list ranking
can't disambiguate "signed up" vs "made a plate".

### open_domain (2)
- Would Caroline still want to pursue counseling as a career if she
  hadn't received support?
- Would Caroline be considered religious?

**Pattern**: Counterfactual / evaluative reasoning. Needs inference,
not retrieval.

### single_hop (3)
- What are Caroline's plans for the summer?
- What motivated Caroline to pursue counseling?
- What was Melanie's favorite book from her childhood?

**Pattern**: Retrieval miss. Right memory exists but isn't retrieved.

### adversarial (1)
- What does Caroline say running has been great for?

**Pattern**: False attribution. System retrieves Melanie's running
benefits and attributes to Caroline. Fix: entity-constraint check at
retrieval or generation time.

Note: Q27 "Where did Oscar hide his bone once?" is FLAKY (1/3) — it
passed in jf2 once. System is edge-case handling it poorly.

## Decision Rules

When evaluating a code change vs baseline:
- **Hit ≥ 3 new passes** → real improvement, commit
- **Hit 1-2 new passes** → possible noise (run again to verify)
- **Hit 0 new passes** → no impact
- **Regressed any stable-pass question** → investigate immediately

Variance is ~3 questions (10%). Signal requires > noise floor.

## Flaky Questions (LLM judge or retrieval noise)

Not optimization targets — they flip between runs:
- What kind of art does Caroline make? (multi_hop, 1/3)
- What did Caroline research? (multi_hop, 2/3)
- How long ago was Caroline's 18th birthday? (temporal, 1/3)
- Where did Oscar hide his bone once? (adversarial, 1/3)
