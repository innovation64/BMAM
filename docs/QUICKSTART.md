# BMAM Quick Start Guide

Get BMAM running in 5 minutes.

## Prerequisites

- Python 3.10+
- OpenAI API key

## Installation

```bash
# Clone
git clone https://github.com/brain-inspired-ai/bmam.git
cd bmam

# Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Basic Usage

### Interactive Session

```python
import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def chat():
    # Initialize
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Conversation loop
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit']:
            break

        result = await coordinator.process_user_input(user_input)
        print(f"BMAM: {result['response']}")

    await coordinator.shutdown()

asyncio.run(chat())
```

### Store and Query Memories

```python
async def demo():
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Store memories
    await coordinator.process_user_input(
        "I met Sarah at the coffee shop on May 5th, 2024"
    )
    await coordinator.process_user_input(
        "Sarah mentioned she loves hiking in the mountains"
    )

    # Query
    result = await coordinator.process_user_input(
        "When did I meet Sarah?"
    )
    print(result['response'])
    # Expected: "You met Sarah at the coffee shop on May 5th, 2024"

    result = await coordinator.process_user_input(
        "What does Sarah like?"
    )
    print(result['response'])
    # Expected: "Sarah loves hiking in the mountains"

asyncio.run(demo())
```

## Run Benchmark

```bash
# Set dataset path
export LOCOMO_DATASET_PATH=/path/to/locomo10.json

# Run evaluation
python experiments/benchmarks/locomo/test_sequential.py --groups 1
```

## Key Features

| Feature | Description | Module |
|---------|-------------|--------|
| Episodic Memory | Store personal experiences | `HippocampusAgent` |
| Semantic Memory | Extract and store facts | `TemporalLobeAgent` |
| Temporal Reasoning | "When did X happen?" | `StoryArc` |
| Intent Detection | Understand user goals | `TheoryOfMindAgent` |
| Auto Consolidation | Memory optimization | `BackgroundProcesses` |

## Project Structure

```
bmam/
├── src/
│   ├── agents/brain_regions/   # Brain region agents
│   ├── coordination/           # Coordinator & orchestration
│   ├── memory/                 # Memory systems
│   └── utils/                  # Utilities
├── experiments/                # Benchmarks
├── tests/                      # Unit tests
└── data/                       # Runtime data (generated)
```

## Common Operations

### Check System Health

```python
health = coordinator.get_feature_health()
print(f"Healthy modules: {health['healthy_count']}/{health['total_count']}")
```

### Manual Memory Query

```python
memories = await coordinator.query_memories("coffee shop", top_k=5)
for mem in memories:
    print(f"- {mem['content']} (score: {mem['relevance_score']:.2f})")
```

### Export/Import Memories

```python
from src.memory.memory_archive import MemoryArchive

# Export
archive = MemoryArchive(Path("backup.bma"))
await archive.save(coordinator)

# Import
await archive.load(target_dir=BMAMPaths.DATA_DIR)
```

### Reset All Data

```python
from src.utils.paths import BMAMPaths
BMAMPaths.clean_all_runtime_data()
```

## Troubleshooting

### "OpenAI API key not found"

```bash
# Check .env file exists and contains:
OPENAI_API_KEY=sk-your-key-here
```

### "FAISS not installed"

```bash
pip install faiss-cpu
```

### "Slow response times"

```python
# Enable caching
coordinator = BrainInspiredCoordinator(
    enable_embedding_cache=True
)
```

## Next Steps

- Read [API Reference](API.md) for detailed documentation
- Read [Architecture](ARCHITECTURE.md) for system design
- Run `pytest` to verify installation
- Explore `experiments/` for benchmarking

## Support

- Issues: https://github.com/brain-inspired-ai/bmam/issues
- Documentation: https://github.com/brain-inspired-ai/bmam/docs
