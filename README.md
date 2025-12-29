# BMAM: Brain-inspired Multi-Agent Memory System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![arXiv](https://img.shields.io/badge/arXiv-2025.xxxxx-b31b1b.svg)](https://arxiv.org/)

> **The first brain-inspired multi-agent memory framework for long-term conversational AI**

BMAM implements a multi-agent memory system inspired by human brain memory mechanisms. It addresses the **Soul Erosion** problem—the gradual degradation of an AI agent's identity and behavioral consistency due to memory failures—through coordinated brain-region agents.

## Key Features

- **Brain-Region Specialization**: 5 specialized agents (Hippocampus, Temporal Lobe, Amygdala, Prefrontal Cortex, Basal Ganglia)
- **StoryArc Timeline**: Explicit temporal indexing for "when/how long/before-after" queries
- **Hybrid Retrieval**: BM25 + Dense Vectors + Knowledge Graph + Timeline fusion
- **Soul Portability**: Export/import memory archives (.bma format) for identity transfer
- **HRM Integration**: Hierarchical Recurrent Memory for multi-timescale organization

## Performance (SOTA on LoCoMo)

| Benchmark | Scale | Accuracy | vs MemOS |
|-----------|-------|----------|----------|
| **LoCoMo** | 10 groups, 1986 QA | **78.45%** | +5.14% |
| **LongMemEval** | 500 samples | Testing... | - |
| **PrefEval** | 1000 samples | Testing... | - |
| **PersonaMem** | 37 users, 589 QA | Testing... | - |

### LoCoMo Category Breakdown

| Category | Accuracy | Note |
|----------|----------|------|
| Single-hop | **82.00%** | SOTA |
| Multi-hop | **70.42%** | SOTA |
| Temporal | 62.31% | |
| Open-domain | **79.55%** | SOTA |

## Soul Erosion: Why Memory Matters

We introduce **Soul Erosion** as a framework for understanding AI memory failures:

| Erosion Type | Problem | BMAM Solution |
|--------------|---------|---------------|
| **Temporal** | Loses track of *when* events occurred | StoryArc timeline indexing |
| **Semantic** | Facts become inconsistent | Hippocampus→Temporal Lobe consolidation |
| **Identity** | User preferences forgotten | Amygdala salience tagging |

**Key insight**: No single memory mechanism can prevent all erosion types. BMAM's multi-agent design provides complementary protections.

## Architecture

```
                    BrainInspiredCoordinator
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │  │ Hippocampus │ │Temporal Lobe│ │   Amygdala  │   │
    │  │ (Episodic)  │ │(Semantic+KG)│ │ (Salience)  │   │
    │  └─────────────┘ └─────────────┘ └─────────────┘   │
    │                                                     │
    │  ┌─────────────────────────┐ ┌─────────────────┐   │
    │  │  Prefrontal Cortex      │ │  Basal Ganglia  │   │
    │  │  (Working Memory +      │ │  (Procedural +  │   │
    │  │   Routing Control)      │ │   Patterns)     │   │
    │  └─────────────────────────┘ └─────────────────┘   │
    │                                                     │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │  │  StoryArc   │ │  Temporal   │ │   Hybrid    │   │
    │  │ (Timeline)  │ │  Reasoning  │ │  Retrieval  │   │
    │  └─────────────┘ └─────────────┘ └─────────────┘   │
    └─────────────────────────────────────────────────────┘
```

| Brain Region | Function | Anti-Erosion Role |
|--------------|----------|-------------------|
| **Hippocampus** | Episodic memory encoding | Temporal anchoring with StoryArc |
| **Temporal Lobe** | Semantic memory + KG | Fact stability via consolidation |
| **Amygdala** | Salience tagging | Identity protection |
| **Prefrontal** | Working memory + routing | Context coherence |
| **Basal Ganglia** | Procedural patterns | Behavioral consistency |

## Installation

### Prerequisites

- Python 3.10+
- OpenAI API key (for embeddings and LLM judge)

### Setup

```bash
# Clone repository
git clone https://github.com/your-repo/bmam.git
cd bmam

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env:
# OPENAI_API_KEY=sk-xxx
# OPENAI_BASE_URL=https://api.openai.com/v1
```

### Dataset Preparation

Download datasets to `data/datasets/`:

```
data/datasets/
├── locomo/
│   └── locomo10.json           # LoCoMo (10 groups)
├── longmemeval/
│   └── longmemeval_oracle.json # LongMemEval (500 samples)
├── prefeval/
│   └── prefeval.json           # PrefEval (1000 samples)
└── personamem/
    └── personamem.json         # PersonaMem (37 users)
```

## Quick Start

```python
import asyncio
from datetime import datetime
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

async def main():
    # Initialize
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    # Store memory
    await coord.store_memory_with_timestamp(
        "User mentioned they love hiking in the mountains",
        datetime.now(),
        "user",
        importance=0.8
    )

    # Query
    result = await coord.process_user_input("What are my hobbies?")
    print(result.response)

asyncio.run(main())
```

## Evaluation

### Memory Cleanup (Required before each benchmark)

```bash
rm -f data/memory/*.db data/memory/*.index data/memory/*.json
rm -f data/memory/checkpoints/*.json data/state/*.json
rm -rf data/cache/embedding data/cache/faiss_index data/cache/knowledge_graph
```

### Benchmark Tests

```bash
# LoCoMo (10 groups, ~10 hours)
python evaluation/benchmarks/locomo/test_sequential.py --groups 10

# LongMemEval (500 samples)
python evaluation/benchmarks/longmemeval/test_longmemeval.py --questions 0

# PrefEval (1000 samples)
python evaluation/benchmarks/prefeval/test_prefeval.py --questions 0

# PersonaMem (37 users)
python evaluation/benchmarks/personamem/test_personamem.py --users 37
```

### Ablation Experiments

BMAM supports two levels of ablation to validate multi-agent collaboration:

#### Brain-Region Ablation (Validates 5-region collaboration)

```bash
# Run all brain-region ablations
python evaluation/scripts/ablation/run_ablation.py --brain-regions --groups 3

# Available ablations:
# - no_hippocampus: Disable episodic encoding
# - no_temporal_lobe: Disable semantic memory + KG
# - no_amygdala: Disable salience tagging
# - no_prefrontal: Disable working memory control
# - no_basal_ganglia: Disable procedural patterns
```

#### Component Ablation (Validates functional modules)

```bash
# Run component ablations
python evaluation/scripts/ablation/run_ablation.py --components --groups 3

# Available ablations:
# - no_story_arc: Disable timeline indexing
# - no_temporal_reasoning: Disable time queries
# - no_kg: Disable knowledge graph
# - no_hybrid_retrieval: Vector-only retrieval
# - no_consolidation: Disable memory consolidation
```

#### List All Ablation Configs

```bash
python evaluation/scripts/ablation/run_ablation.py --list
```

### Soul Portability Test

Validates memory archive export/import and identity consistency:

```bash
# Run soul portability test
python evaluation/benchmarks/soul_portability/test_soul_portability.py

# With more questions
python evaluation/benchmarks/soul_portability/test_soul_portability.py --questions 50
```

**Test Phases:**
1. **Shaping**: Store memories and answer test questions
2. **Export**: Save memory archive (.bma format)
3. **Restore**: Clear memory and reload from archive
4. **Consistency**: Compare answers before/after restore

**Soul Integrity Score**: Weighted composite of export success, restore success, and answer consistency.

## Project Structure

```
BMAM/
├── src/
│   ├── agents/
│   │   ├── brain_regions/           # 5 brain-region agents
│   │   │   ├── hippocampus_agent/   # Episodic memory
│   │   │   ├── temporal_lobe_agent/ # Semantic + KG
│   │   │   ├── prefrontal_agent/    # Working memory
│   │   │   ├── amygdala_agent.py    # Salience tagging
│   │   │   └── basal_ganglia_agent.py
│   │   └── core/                    # Functional agents
│   ├── memory/
│   │   ├── story_arc.py             # Timeline management
│   │   ├── memory_archive.py        # .bma format
│   │   └── memory_system/           # Storage backend
│   ├── coordination/
│   │   ├── brain_coordinator_refactored.py
│   │   ├── hrm_coordinator_wrapper.py
│   │   └── memory_archive_manager.py
│   ├── config/
│   │   └── ablation_config.py       # Ablation configurations
│   └── reasoning/
│       └── memory_reasoning_chain.py
├── evaluation/
│   ├── benchmarks/
│   │   ├── locomo/
│   │   ├── longmemeval/
│   │   ├── prefeval/
│   │   ├── personamem/
│   │   └── soul_portability/        # Soul portability test
│   ├── scripts/
│   │   └── ablation/                # Ablation experiments
│   └── results/
├── data/
│   ├── datasets/                    # Benchmark datasets
│   ├── memory/                      # Runtime storage
│   └── state/                       # Agent states
└── archives/                        # Memory archives (.bma)
```

## Memory Archive Format (.bma)

BMAM supports exporting/importing memory as `.bma` archives:

```python
from src.coordination.memory_archive_manager import MemoryArchiveManager

# Export
archive_manager = MemoryArchiveManager(coordinator)
result = archive_manager.export_archive(
    archive_name="my_memory",
    output_dir=Path("archives/"),
    tags=["user_profile", "v1"]
)

# Import
result = archive_manager.load_archive(Path("archives/my_memory.bma"))
```

**Archive Contents:**
- SQLite database (episodic + semantic memories)
- FAISS vector index
- Brain-region state files (JSON)
- Knowledge graph
- StoryArc timeline
- Manifest with checksums

## Troubleshooting

### Common Issues

**1. OpenAI API Errors (502/Cloudflare)**
- Check API key and base URL in `.env`
- Wait and retry for temporary issues

**2. Memory Pollution**
- Clean memory before each benchmark
- Never run multiple benchmarks in parallel

**3. Out of Memory**
- Ensure 8GB+ RAM
- Reduce batch size with `--groups 1`

### Verify Installation

```bash
python3 -c "from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator; print('OK')"
```

## Citation

```bibtex
@inproceedings{bmam2025,
  title={BMAM: Brain-inspired Multi-Agent Memory for Long-term Conversational AI},
  author={...},
  booktitle={ACL 2025},
  year={2025}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Version**: 2.1
**Last Updated**: December 2025
