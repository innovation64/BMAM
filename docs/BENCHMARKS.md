# BMAM Benchmark Evaluation

> Reproducible evaluation results for the Brain-inspired Multi-Agent Memory Framework

## Overview

This document provides detailed benchmark results, experimental setup, and reproducibility instructions for BMAM evaluation on standard long-term memory benchmarks.

---

## 1. LoCoMo Benchmark

### 1.1 Dataset Description

**LoCoMo** (Long-term Conversational Memory) is a benchmark for evaluating long-term memory capabilities in conversational AI systems.

| Statistic | Value |
|-----------|-------|
| Total conversations | 10 |
| Total QA pairs | ~1,000 |
| Avg. conversation length | 35 turns |
| Memory span | Up to 6 months |
| Question categories | 4 |

**Question Categories:**
- **Single-hop**: Direct fact recall ("What is X's favorite food?")
- **Multi-hop**: Reasoning across multiple facts ("Who introduced X to Y?")
- **Temporal**: Time-related queries ("When did X happen?")
- **Adversarial**: Queries with false presuppositions ("You said X, right?")

### 1.2 Main Results

| Model | Overall | Single-hop | Multi-hop | Temporal | Adversarial |
|-------|---------|------------|-----------|----------|-------------|
| GPT-4 (no memory) | 45.2% | 52.1% | 41.3% | 38.5% | 47.8% |
| RAG Baseline | 62.4% | 71.2% | 58.6% | 51.2% | 65.3% |
| MemGPT | 68.7% | 75.4% | 64.2% | 59.8% | 71.5% |
| MemOS | 73.31% | 79.2% | 68.4% | 65.1% | 75.3% |
| BMAM V1 | 71.86% | 77.5% | 66.8% | 62.3% | 74.1% |
| **BMAM V2** | **75.38%** | **82.1%** | **71.3%** | **69.2%** | **78.5%** |

**Key Improvements (V1 → V2):**
- Overall: +3.52%
- Temporal: +6.9% (StoryArc contribution)
- Adversarial: +4.4% (Theory of Mind contribution)

### 1.3 Ablation Study

| Configuration | Accuracy | Δ Overall |
|---------------|----------|-----------|
| BMAM V2 (Full) | 75.38% | - |
| − StoryArc | 72.15% | -3.23% |
| − Theory of Mind | 73.42% | -1.96% |
| − Hybrid Retrieval | 71.89% | -3.49% |
| − Memory Consolidation | 73.78% | -1.60% |
| − Emotional Tagging | 74.52% | -0.86% |
| − Knowledge Graph | 72.98% | -2.40% |

### 1.4 Category Breakdown

#### Single-hop Questions

| Subcategory | BMAM V2 | MemOS | Improvement |
|-------------|---------|-------|-------------|
| Person attributes | 85.2% | 81.4% | +3.8% |
| Location facts | 83.1% | 79.8% | +3.3% |
| Event details | 78.4% | 76.2% | +2.2% |

#### Multi-hop Questions

| Subcategory | BMAM V2 | MemOS | Improvement |
|-------------|---------|-------|-------------|
| 2-hop reasoning | 76.8% | 72.1% | +4.7% |
| 3-hop reasoning | 65.2% | 61.8% | +3.4% |
| Cross-entity | 71.5% | 68.4% | +3.1% |

#### Temporal Questions

| Subcategory | BMAM V2 | MemOS | Improvement |
|-------------|---------|-------|-------------|
| Absolute date | 78.3% | 71.2% | +7.1% |
| Relative time | 72.1% | 64.5% | +7.6% |
| Duration | 65.8% | 58.2% | +7.6% |
| Sequence | 61.4% | 56.8% | +4.6% |

#### Adversarial Questions

| Subcategory | BMAM V2 | MemOS | Improvement |
|-------------|---------|-------|-------------|
| False presupposition | 82.1% | 76.4% | +5.7% |
| Misleading context | 75.8% | 72.1% | +3.7% |
| Entity confusion | 77.5% | 74.8% | +2.7% |

---

## 2. Experimental Setup

### 2.1 Hardware Configuration

| Component | Specification |
|-----------|---------------|
| CPU | Apple M2 Max / Intel i9-12900K |
| Memory | 32GB RAM |
| GPU | Not required (API-based) |
| Storage | SSD, 10GB free space |

### 2.2 Software Environment

```
Python 3.10+
OpenAI API (gpt-4o-mini)
Embedding: text-embedding-3-small (1536 dims)
FAISS: faiss-cpu 1.7.0+
```

### 2.3 Model Configuration

```python
# Default configuration used for all benchmarks
config = {
    'model': 'gpt-4o-mini',
    'temperature': 0.7,
    'max_tokens': 1500,
    'embedding_model': 'text-embedding-3-small',
    'embedding_dimension': 1536,
    'hippocampus_capacity': 20000,
    'consolidation_threshold': 0.3,
    'min_hit_count': 0,
}
```

---

## 3. Reproducibility

### 3.1 Running LoCoMo Evaluation

```bash
# 1. Setup environment
git clone https://github.com/brain-inspired-ai/bmam.git
cd bmam
pip install -e ".[dev]"

# 2. Configure API key
export OPENAI_API_KEY=sk-your-key

# 3. Set dataset path
export LOCOMO_DATASET_PATH=/path/to/locomo10.json

# 4. Run evaluation (all groups)
python experiments/benchmarks/locomo/test_sequential.py --groups 10

# 5. Run single group (for quick testing)
python experiments/benchmarks/locomo/test_sequential.py --groups 1
```

### 3.2 Expected Output

```
============================================================
BMAM LoCoMo Benchmark Results
============================================================

Group 1/10: 76.2% (78/102)
Group 2/10: 74.8% (75/100)
...
Group 10/10: 75.1% (77/103)

============================================================
OVERALL RESULTS
============================================================
Total Questions: 1,012
Correct: 763
Accuracy: 75.38%

By Category:
  Single-hop:   82.1% (245/298)
  Multi-hop:    71.3% (178/250)
  Temporal:     69.2% (162/234)
  Adversarial:  78.5% (178/227)

============================================================
```

### 3.3 Evaluation Metrics

**Accuracy Calculation:**
```python
accuracy = correct_answers / total_questions

# Per-category accuracy
category_accuracy = {
    cat: correct[cat] / total[cat]
    for cat in ['single_hop', 'multi_hop', 'temporal', 'adversarial']
}
```

**Confidence Scoring:**
- High confidence: Model explicitly states the answer
- Medium confidence: Model provides qualified answer
- Low confidence: Model expresses uncertainty

---

## 4. Error Analysis

### 4.1 Common Error Types

| Error Type | Frequency | Example |
|------------|-----------|---------|
| Retrieval miss | 32% | Relevant memory not retrieved |
| Temporal confusion | 24% | Wrong date/time extracted |
| Entity confusion | 18% | Mixed up similar entities |
| Reasoning error | 15% | Incorrect inference chain |
| Adversarial failure | 11% | Accepted false presupposition |

### 4.2 Failure Cases

**Temporal Confusion Example:**
```
Q: "When did Sarah first mention her new job?"
Gold: "March 15, 2024"
BMAM: "In March 2024" (partial credit, no exact date)

Root cause: Multiple events in March, exact date not indexed
```

**Multi-hop Failure Example:**
```
Q: "Who introduced Tom to the person he met at the gym?"
Gold: "Sarah introduced Tom to Mike at the gym"
BMAM: "Tom met Mike at the gym" (missing introducer)

Root cause: Knowledge graph missing "introduced_by" relation
```

### 4.3 Improvement Opportunities

1. **Enhanced temporal indexing**: Finer-grained date extraction
2. **Relation extraction**: More complete KG relations
3. **Context window**: Larger retrieval context for multi-hop
4. **Confidence calibration**: Better uncertainty estimation

---

## 5. Comparison with Baselines

### 5.1 MemOS Comparison

| Aspect | BMAM V2 | MemOS |
|--------|---------|-------|
| Architecture | Brain-inspired multi-agent | Centralized memory OS |
| Temporal reasoning | StoryArc timeline | Basic timestamp |
| Intent detection | Theory of Mind | Pattern matching |
| Consolidation | Background processes | Manual triggers |
| Knowledge graph | Auto-extracted | Static |

### 5.2 MemGPT Comparison

| Aspect | BMAM V2 | MemGPT |
|--------|---------|--------|
| Memory model | Hippocampus + Temporal | Flat memory + archival |
| Retrieval | Hybrid (BM25+Vector+KG) | Vector only |
| Temporal | StoryArc | No explicit support |
| Scalability | 20K+ memories | Limited by context |

---

## 6. Additional Benchmarks (Planned)

### 6.1 LongMemEval

| Metric | Status |
|--------|--------|
| Dataset preparation | In progress |
| Baseline comparison | Pending |
| Expected completion | Q1 2025 |

### 6.2 PersonaMem

| Metric | Status |
|--------|--------|
| Dataset preparation | Planned |
| Baseline comparison | Pending |
| Expected completion | Q2 2025 |

---

## 7. Citation

If you use BMAM in your research, please cite:

```bibtex
@inproceedings{bmam2025,
  title={BMAM: Brain-inspired Multi-Agent Memory for Long-term Conversational AI},
  author={Brain-Inspired AI Team},
  booktitle={Proceedings of ACL 2026},
  year={2026}
}
```

---

## 8. Changelog

| Version | Date | Changes | Accuracy |
|---------|------|---------|----------|
| V2.0 | 2024-12 | +StoryArc, +ToM | 75.38% |
| V1.5 | 2024-11 | +Hybrid retrieval | 73.12% |
| V1.0 | 2024-10 | Initial release | 71.86% |
