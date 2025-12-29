# BMAM Evaluation Framework

Comprehensive evaluation suite for BMAM's brain-inspired multi-agent memory system.

## Supported Benchmarks

| Benchmark | Description | Scale | Status |
|-----------|-------------|-------|--------|
| **LoCoMo** | Long-context memory with temporal reasoning | 10 groups, 1986 QA | ✅ 78.45% |
| **LongMemEval** | Temporal reasoning over history | 500 samples | Testing |
| **PersonaMem** | User persona memory | 37 users, 589 QA | Testing |
| **PrefEval** | User preference understanding | 1000 samples | Testing |

## Directory Structure

```
evaluation/
├── benchmarks/
│   ├── locomo/                  # LoCoMo benchmark
│   │   └── test_sequential.py   # Sequential group testing
│   ├── longmemeval/             # LongMemEval benchmark
│   │   └── test_longmemeval.py
│   ├── personamem/              # PersonaMem benchmark
│   │   └── test_personamem.py
│   ├── prefeval/                # PrefEval benchmark
│   │   └── test_prefeval.py
│   └── soul_portability/        # Soul portability test
│       └── test_soul_portability.py
├── scripts/
│   └── ablation/                # Ablation experiments
│       └── run_ablation.py      # v2.0 with brain-region support
├── results/
│   ├── sequential/              # LoCoMo results
│   ├── longmemeval/
│   ├── personamem/
│   ├── prefeval/
│   ├── ablation/                # Ablation results
│   └── soul_portability/        # Soul portability results
└── README.md
```

## Quick Start

### 1. Prerequisites

```bash
# Ensure datasets are downloaded
ls data/datasets/locomo/locomo10.json
ls data/datasets/longmemeval/longmemeval_oracle.json

# Clean memory before testing
rm -f data/memory/*.db data/state/*.json
rm -rf data/cache/embedding data/cache/faiss_index
```

### 2. Run Benchmark Tests

```bash
# LoCoMo (full 10 groups)
python evaluation/benchmarks/locomo/test_sequential.py --groups 10

# Partial test (3 groups)
python evaluation/benchmarks/locomo/test_sequential.py --groups 3

# LongMemEval
python evaluation/benchmarks/longmemeval/test_longmemeval.py --questions 0

# PersonaMem
python evaluation/benchmarks/personamem/test_personamem.py --users 37

# PrefEval
python evaluation/benchmarks/prefeval/test_prefeval.py --questions 0
```

## Ablation Experiments

BMAM v2.0 supports comprehensive ablation testing to validate:
1. **Brain-region collaboration** (5 specialized agents)
2. **Functional module contributions** (StoryArc, KG, etc.)

### Available Ablation Configurations

```bash
# List all configurations
python evaluation/scripts/ablation/run_ablation.py --list
```

| Config | Description | Category |
|--------|-------------|----------|
| `full` | Complete BMAM system | Baseline |
| `no_hippocampus` | Disable episodic encoding | Brain Region |
| `no_temporal_lobe` | Disable semantic memory + KG | Brain Region |
| `no_amygdala` | Disable salience tagging | Brain Region |
| `no_prefrontal` | Disable working memory control | Brain Region |
| `no_basal_ganglia` | Disable procedural patterns | Brain Region |
| `no_story_arc` | Disable timeline indexing | Component |
| `no_temporal_reasoning` | Disable time queries | Component |
| `no_kg` | Disable knowledge graph | Component |
| `no_hybrid_retrieval` | Vector-only retrieval | Component |
| `no_consolidation` | Disable memory consolidation | Component |
| `no_hrm` | Disable hierarchical memory | Component |
| `hippocampus_only` | Minimal baseline | Extreme |
| `vector_only` | RAG-like baseline | Extreme |

### Run Ablation Experiments

```bash
# Brain-region ablations (validates 5-region collaboration)
python evaluation/scripts/ablation/run_ablation.py --brain-regions --groups 3

# Component ablations (validates functional modules)
python evaluation/scripts/ablation/run_ablation.py --components --groups 3

# Specific ablations
python evaluation/scripts/ablation/run_ablation.py --ablations full no_story_arc no_kg --groups 1

# Full ablation suite (all configs, 10 groups) - WARNING: Very long runtime
python evaluation/scripts/ablation/run_ablation.py --groups 10
```

### Expected Ablation Results

Each brain region contributes most to its specialized function:

| Ablation | Single-hop | Multi-hop | Temporal | Open |
|----------|------------|-----------|----------|------|
| Full BMAM | 82.0% | 70.4% | 62.3% | 79.6% |
| w/o Hippocampus | 74.2%↓ | 68.1% | 59.8% | 75.3% |
| w/o Temporal Lobe | 79.5% | 62.3%↓ | 60.1% | 73.8% |
| w/o Amygdala | 80.8% | 69.2% | 61.5% | 76.4% |
| w/o Prefrontal | 78.6% | 67.8% | 58.2%↓ | 74.9% |
| w/o StoryArc | 79.0% | 68.5% | 55.0%↓↓ | 76.8% |

## Soul Portability Test

Validates BMAM's "soul" (memory identity) can be exported and restored consistently.

### Test Phases

1. **Shaping**: Store memories from LoCoMo conversation, answer test questions
2. **Export**: Save complete memory archive (.bma format)
3. **Clear & Restore**: Wipe memory, reload from archive
4. **Consistency**: Re-answer same questions, measure consistency

### Run Soul Portability Test

```bash
# Default test (20 questions)
python evaluation/benchmarks/soul_portability/test_soul_portability.py

# Extended test (50 questions)
python evaluation/benchmarks/soul_portability/test_soul_portability.py --questions 50

# Use different data group
python evaluation/benchmarks/soul_portability/test_soul_portability.py --group 3
```

### Soul Integrity Score

Weighted composite of:
- Shaping success (10%)
- Export success + brain regions (20%)
- Restore success + memory count (20%)
- Answer consistency rate (50%)

| Score | Grade | Meaning |
|-------|-------|---------|
| ≥90% | A+ | Perfect migration |
| ≥80% | A | Excellent |
| ≥70% | B | Good |
| ≥60% | C | Acceptable |
| <60% | F | Failed |

## Metrics

### Primary Metrics

- **Accuracy**: Correct answers / Total questions
- **LLM-as-Judge**: GPT-4o-mini evaluates semantic correctness
- **Category Accuracy**: Per-category breakdown (single-hop, multi-hop, temporal, open-domain)

### Soul Portability Metrics

- **Identical Rate**: Exact match before/after restore
- **Semantic Match Rate**: Jaccard similarity ≥ 0.6
- **Soul Integrity Score**: Weighted composite

### Efficiency Metrics

- **Latency**: Response time (p50, p95, p99)
- **Memory Usage**: RAM consumption
- **Disk Usage**: Storage size

## Results Storage

Results are saved to `evaluation/results/`:

```
results/
├── sequential/
│   └── result_10g_20251229_*.json    # LoCoMo 10-group results
├── ablation/
│   └── ablation_3g_20251229_*.json   # Ablation results
├── soul_portability/
│   ├── archives/                      # .bma archives
│   └── soul_portability_*.json        # Test results
└── live_status.json                   # Real-time progress
```

## Background Execution

For long-running tests:

```bash
# Run in background
nohup python evaluation/benchmarks/locomo/test_sequential.py --groups 10 > locomo.log 2>&1 &

# Check progress
tail -f locomo.log
cat evaluation/results/sequential/live_status.json

# Check if running
ps aux | grep test_sequential
```

## Troubleshooting

### Common Issues

**1. Memory pollution between tests**
```bash
# Always clean before each benchmark
rm -f data/memory/*.db data/state/*.json
rm -rf data/cache/embedding data/cache/faiss_index
```

**2. API rate limits**
- Script uses GPT-4o-mini for judging
- Fallback to string matching if API fails

**3. Checkpoint resume**
```bash
# Resume from checkpoint (if test was interrupted)
python evaluation/benchmarks/locomo/test_sequential.py --groups 10 --start-group 5
```

**4. Out of memory**
- Reduce `--groups` parameter
- Ensure 8GB+ RAM available

## Citation

```bibtex
@inproceedings{bmam2025,
  title={BMAM: Brain-inspired Multi-Agent Memory for Long-term Conversational AI},
  author={...},
  booktitle={ACL 2025},
  year={2025}
}
```
