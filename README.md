# BMAM: Brain-inspired Multi-Agent Memory System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **A biologically-inspired memory architecture for long-term conversational AI**

BMAM implements a multi-agent memory system inspired by human brain memory mechanisms, achieving state-of-the-art performance on the LoCoMo long-context memory benchmark.

## 📊 Performance

| System | LoCoMo Accuracy | Improvement |
|--------|-----------------|-------------|
| MemOS (Baseline) | 73.31% | - |
| BMAM V1 | 71.86% | -1.45% |
| **BMAM V2** | **75.38%** | **+2.07%** |

## 🧠 Architecture Overview

BMAM models five brain regions as specialized agents:

```
┌────────────────────────────────────────────────────────────────┐
│                   BrainInspiredCoordinator                     │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Hippocampus  │  │Temporal Lobe │  │   Amygdala   │         │
│  │  (Episodic)  │  │  (Semantic)  │  │  (Emotional) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                │
│  ┌────────────────────────────┐  ┌──────────────────┐         │
│  │   Prefrontal Cortex (PFC)  │  │  Basal Ganglia   │         │
│  │  ┌──────────┬───────────┐  │  │   (Procedural)   │         │
│  │  │ Working  │   ToM     │  │  └──────────────────┘         │
│  │  │  Memory  │  (mPFC)   │  │                               │
│  │  └──────────┴───────────┘  │                               │
│  └────────────────────────────┘                               │
├────────────────────────────────────────────────────────────────┤
│  StoryArc (Timeline) │ ReasoningValidator │ LearningManager   │
└────────────────────────────────────────────────────────────────┘
```

### Key Components

| Brain Region | Function | Neuroscience Basis |
|--------------|----------|-------------------|
| **Hippocampus** | Episodic memory storage & retrieval | CA1/CA3 pattern completion |
| **Temporal Lobe** | Semantic memory & knowledge graph | Anterior temporal lobe |
| **Amygdala** | Emotional tagging & salience | Emotional memory modulation |
| **Prefrontal Cortex** | Working memory & ToM | dlPFC + mPFC |
| **Basal Ganglia** | Procedural memory & habits | Striatum |

### V2.0 Features

- **StoryArc**: Timeline-based temporal reasoning with event indexing
- **Theory of Mind (ToM)**: Intent inference and adversarial query detection
- **Continuous Learning**: Online adaptation with memory consolidation

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/brain-inspired-ai/bmam.git
cd bmam

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

### Basic Usage

```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# Initialize
coordinator = BrainInspiredCoordinator()
await coordinator.initialize()

# Process input (automatically stores, indexes, consolidates)
result = await coordinator.process_user_input(
    "Remember that I met Sarah at the coffee shop on May 5th"
)

# Query memories
memories = await coordinator.query_memories("When did I meet Sarah?")
```

## 📂 Project Structure

```
BMAM/
├── src/
│   ├── agents/
│   │   ├── brain_regions/          # Brain region agents
│   │   │   ├── hippocampus_agent/  # Episodic memory
│   │   │   ├── temporal_lobe_agent/# Semantic + KG
│   │   │   ├── prefrontal_agent/   # Working memory + ToM
│   │   │   ├── amygdala_agent.py   # Emotional tagging
│   │   │   ├── basal_ganglia_agent.py  # Procedural memory
│   │   │   └── theory_of_mind_agent.py # ToM (mPFC)
│   │   └── core/                   # Core agents
│   ├── memory/
│   │   ├── story_arc.py            # Timeline management
│   │   └── memory_system/          # Storage backend
│   ├── coordination/               # Orchestration layer
│   └── utils/                      # Utilities
├── tests/                          # Test suite
├── evaluation/                     # Benchmark scripts
├── docs/                           # Documentation
└── config/                         # Configuration files
```

## 📖 Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [API Reference](docs/API.md)
- [Architecture Details](docs/ARCHITECTURE.md)
- [Benchmark Results](docs/BENCHMARKS.md)
- [Testing Guide](docs/TESTING.md)

## 🔬 Running Benchmarks

### LoCoMo Evaluation

```bash
# Set dataset path
export LOCOMO_DATASET_PATH=/path/to/locomo10.json

# Run evaluation
python evaluation/benchmarks/locomo/test_sequential.py --groups 1
```

### Unit Tests

```bash
pytest tests/unit/ -v
```

## 📊 Ablation Studies

| Configuration | Accuracy | Δ |
|--------------|----------|---|
| Full System | 75.38% | - |
| w/o StoryArc | 72.36% | -3.02% |
| w/o ToM | 74.87% | -0.51% |
| w/o Emotional Tagging | 74.36% | -1.02% |
| w/o Multi-hop KG | 73.87% | -1.51% |

## 🔗 Citation

If you use BMAM in your research, please cite:

```bibtex
@inproceedings{bmam2026,
  title={BMAM: Brain-inspired Multi-Agent Memory for Long-term Conversational AI},
  author={...},
  booktitle={Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (ACL)},
  year={2026}
}
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- LoCoMo benchmark team for the evaluation dataset
- OpenAI for embedding and language model APIs
- Neuroscience research that inspired this architecture

---

**Version**: 2.0
**Last Updated**: December 2024
**Status**: Research Release
