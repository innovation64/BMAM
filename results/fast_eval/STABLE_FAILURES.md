# Stable Failure Targets (Baseline)

Based on 3 fast_eval runs on identical code/state, these 14 questions
consistently fail — they are the TRUE optimization targets (not noise).

**Runs analyzed**: baseline_run1, baseline_run2, baseline_run3 (2026-04-08)
**Stable pass**: 11/29
**Stable fail**: 14/29 ← targets below
**Flaky (LLM judge noise)**: 4/29

## Targets by Category

### multi_hop (3)
- What did Melanie paint recently?
- What subject have Caroline and Melanie both painted?
- What symbols are important to Caroline?

**Pattern**: Need to aggregate multiple memories about the same entity+topic
across sessions. Retrieval finds individual mentions but can't summarize.

### temporal (3)
- When did Caroline meet up with her friends, family, and mentors?
- When did Melanie sign up for a pottery class?
- When did Melanie go to the pottery workshop?

**Pattern**: Wrong session matched. Multiple sessions mention same entity+
topic, picks the wrong date. Root cause: flat memory list ranking.

### open_domain (2)
- Would Caroline still want to pursue counseling as a career if she
  hadn't received support?
- Would Caroline be considered religious?

**Pattern**: Counterfactual / evaluative reasoning. Needs to infer from
facts, not retrieve.

### single_hop (3)
- What are Caroline's plans for the summer?
- What motivated Caroline to pursue counseling?
- What was Melanie's favorite book from her childhood?

**Pattern**: Retrieval miss. The right memory exists but isn't retrieved.

### adversarial (3)
- What is Melanie excited about in her adoption process?  (Melanie doesn't)
- What kind of counseling workshop did Melanie attend recently?  (she didn't)
- What does Caroline say running has been great for?  (she doesn't)

**Pattern**: False attribution. System fabricates answers instead of saying
"unable to determine". Fix: detect when premise is unsupported.

## Decision Rules

When evaluating a code change against these targets:
- **Hit ≥ 3 new passes** → real improvement, commit
- **Hit 1-2 new passes** → possible noise, verify with 2nd run
- **Hit 0 new passes** → no impact or regression
- **Regressed any stable-pass question** → investigate immediately

## Flaky Questions (LLM judge noise)

Not optimization targets — they flip between runs:
- How long ago was Caroline's 18th birthday? (temporal, 2/3)
- Would Melanie be considered a member of the LGBTQ community? (open, 2/3)
- Where did Oscar hide his bone once? (adv, 2/3)
- What kind of art does Caroline make? (multi, 1/3)
