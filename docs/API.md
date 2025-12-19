# BMAM API Reference

> Brain-inspired Multi-Agent Memory Framework API Documentation

## Table of Contents

- [Core Components](#core-components)
- [BrainInspiredCoordinator](#braininspiredcoordinator)
- [Brain Region Agents](#brain-region-agents)
- [Memory Systems](#memory-systems)
- [Temporal Reasoning](#temporal-reasoning)
- [Theory of Mind](#theory-of-mind)

---

## Core Components

### Quick Start

```python
import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def main():
    # Initialize the coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Process user input
    result = await coordinator.process_user_input(
        "Remember that I met Sarah at the coffee shop yesterday"
    )

    # Query memories
    memories = await coordinator.query_memories("When did I meet Sarah?")

    # Cleanup
    await coordinator.shutdown()

asyncio.run(main())
```

---

## BrainInspiredCoordinator

The central orchestrator that coordinates all brain region agents.

### Initialization

```python
coordinator = BrainInspiredCoordinator(
    enable_persistence=True,      # Auto-save state to disk
    enable_background_processes=True,  # Enable consolidation/forgetting
    test_mode=False               # Production mode
)
await coordinator.initialize()
```

### Key Methods

#### `process_user_input(user_input: str, context: dict = None) -> dict`

Process user input through the complete cognitive pipeline.

**Parameters:**
- `user_input`: The user's message text
- `context`: Optional context dictionary with metadata

**Returns:**
```python
{
    'response': str,              # Generated response
    'memories_used': List[dict],  # Retrieved relevant memories
    'new_memories_stored': int,   # Number of new memories created
    'reasoning_chain': List[str], # Reasoning steps taken
    'confidence': float           # Response confidence score
}
```

**Example:**
```python
result = await coordinator.process_user_input(
    "I had lunch with Tom at the Italian restaurant last Tuesday",
    context={'speaker': 'user', 'session_id': 'abc123'}
)
```

#### `query_memories(query: str, top_k: int = 5) -> List[dict]`

Query the memory system for relevant memories.

**Parameters:**
- `query`: Natural language query
- `top_k`: Maximum number of results

**Returns:**
```python
[
    {
        'content': str,           # Memory content
        'relevance_score': float, # Similarity score
        'timestamp': datetime,    # When the memory was formed
        'source': str,            # Brain region source
        'metadata': dict          # Additional metadata
    }
]
```

#### `get_feature_health() -> dict`

Check the health status of all cognitive modules.

**Returns:**
```python
{
    'features': {
        'hippocampus': True,
        'temporal_lobe': True,
        'amygdala': True,
        'theory_of_mind': True,
        'story_arc': True,
        ...
    },
    'healthy_count': int,
    'total_count': int,
    'degraded_features': List[str]
}
```

---

## Brain Region Agents

### HippocampusAgent (Episodic Memory)

Stores and retrieves episodic memories - personal experiences and events.

```python
from src.agents.brain_regions.hippocampus_agent import HippocampusAgent

hippocampus = coordinator.hippocampus

# Store a memory
result = await hippocampus.store_memory(
    content="Met Sarah at Central Park on a sunny afternoon",
    entities=["Sarah", "Central Park"],
    importance=0.8,
    emotion_tags=["happy", "social"],
    metadata={
        'conversation_date': '2024-03-15',
        'speaker': 'user'
    }
)

# Retrieve memories
memories = await hippocampus.retrieve_memories(
    query="meetings with Sarah",
    top_k=5
)
```

### TemporalLobeAgent (Semantic Memory)

Stores consolidated semantic knowledge and facts.

```python
from src.agents.brain_regions.temporal_lobe_agent import TemporalLobeAgent

temporal_lobe = coordinator.temporal_lobe

# Query semantic knowledge
facts = await temporal_lobe.query_semantic_memory(
    query="What do I know about Sarah?",
    include_kg=True  # Include knowledge graph relations
)
```

### AmygdalaAgent (Emotional Processing)

Tags memories with emotional significance.

```python
from src.agents.brain_regions.amygdala_agent import AmygdalaAgent

amygdala = coordinator.amygdala

# Analyze emotional content
emotion_result = await amygdala.analyze_emotion(
    content="I was so excited when I got the job offer!"
)
# Returns: {'primary_emotion': 'joy', 'intensity': 0.9, 'valence': 'positive'}
```

### PrefrontalAgent (Working Memory & Theory of Mind)

Manages working memory and includes Theory of Mind capabilities.

```python
from src.agents.brain_regions.prefrontal_agent import PrefrontalAgent

prefrontal = coordinator.prefrontal

# Access working memory
working_memory = await prefrontal.get_working_memory()

# Theory of Mind: Infer user intent
intent = await prefrontal.infer_user_intent(
    query="What did I tell you about my sister?",
    context=recent_memories
)
# Returns: {'intent_type': 'recall_request', 'target_entity': 'sister', ...}
```

### BasalGangliaAgent (Procedural Memory)

Stores habitual patterns and procedural knowledge.

```python
from src.agents.brain_regions.basal_ganglia_agent import BasalGangliaAgent

basal_ganglia = coordinator.basal_ganglia

# Query habits
habits = await basal_ganglia.get_user_habits(entity="user")
```

---

## Memory Systems

### StoryArc (Temporal Indexing)

Manages timeline-based memory indexing for temporal reasoning.

```python
from src.memory.story_arc import get_story_arc_manager

story_arc = get_story_arc_manager()

# Query event time
result = await story_arc.query_event_time(
    entity="Caroline",
    event_keywords=["museum", "visit"]
)
# Returns: {'formatted_date': '5 July 2023', 'confidence': 0.95}

# Calculate time span
span = await story_arc.calculate_time_span(
    entity="Tom",
    start_event="first met",
    end_event="last seen"
)
# Returns: {'days': 45, 'formatted': '1 month and 15 days'}

# Get entity timeline
timeline = await story_arc.get_entity_timeline(entity="Sarah")
# Returns chronologically ordered events involving Sarah
```

### Memory Consolidation

Automatic consolidation from episodic to semantic memory.

```python
# Trigger manual consolidation
await coordinator.trigger_consolidation()

# Check consolidation status
status = await coordinator.get_consolidation_status()
```

---

## Temporal Reasoning

### FlexibleDateParser

Parses natural language dates and relative time expressions.

```python
from src.utils.flexible_date_parser import FlexibleDateParser

parser = FlexibleDateParser()

# Parse absolute dates
date = parser.parse("May 7, 2023")

# Parse relative dates (requires reference)
date = parser.parse_relative("yesterday", reference=datetime.now())
date = parser.parse_relative("last Tuesday", reference=datetime.now())
```

---

## Theory of Mind

### Intent Detection

Detect user intent and potential adversarial queries.

```python
from src.agents.brain_regions.theory_of_mind_agent import TheoryOfMindAgent

tom = coordinator.theory_of_mind

# Analyze query intent
analysis = await tom.analyze_query(
    query="You said my birthday is in March, right?",
    memories=relevant_memories
)
# Returns:
# {
#     'intent_type': 'confirmation_seeking',
#     'is_adversarial': True,
#     'adversarial_type': 'false_presupposition',
#     'confidence': 0.85,
#     'suggested_response_strategy': 'verify_and_correct'
# }
```

### Belief State Tracking

Track and update user mental state model.

```python
belief_state = await tom.get_user_belief_state(user_id="default")
# Returns user's known beliefs, preferences, and mental model
```

---

## Data Persistence

### State Management

```python
# Save all state
await coordinator.save_state()

# Load from saved state
await coordinator.load_state()

# Export to archive
from src.memory.memory_archive import MemoryArchive
archive = MemoryArchive(Path("backup.bma"))
await archive.save(coordinator)

# Import from archive
await archive.load(target_dir=BMAMPaths.DATA_DIR)
```

### Clean Room Reset

```python
from src.utils.paths import BMAMPaths

# Clear all runtime data (for testing)
result = BMAMPaths.clean_all_runtime_data()
print(f"Cleaned: {result['cleaned']}")
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `DEFAULT_MODEL` | `gpt-4o-mini` | LLM model for reasoning |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `TEMPERATURE` | `0.7` | LLM temperature |
| `MAX_TOKENS` | `1500` | Max response tokens |
| `BMAM_DATA_DIR` | `./data` | Data directory path |
| `BMAM_TEST_MODE` | `false` | Enable test mode |

### Programmatic Configuration

```python
from src.core.config import MemorySystemConfig

config = MemorySystemConfig(
    embedding_dimension=1536,
    cache_max_size=10000,
    max_vectors=5000
)
```

---

## Error Handling

All async methods may raise:

- `ConnectionError`: API connection issues
- `ValueError`: Invalid input parameters
- `MemoryError`: Storage capacity exceeded
- `TimeoutError`: Operation timeout

**Example:**
```python
try:
    result = await coordinator.process_user_input(user_input)
except ConnectionError:
    # Handle API failure - system will degrade gracefully
    result = await coordinator.process_user_input(user_input, offline_mode=True)
except Exception as e:
    logger.error(f"Processing failed: {e}")
```

---

## Performance Considerations

1. **Batch Operations**: Use batch methods for multiple memories
2. **Caching**: Embedding cache reduces API calls
3. **Background Processes**: Consolidation runs asynchronously
4. **Lazy Loading**: Modules load on-demand

```python
# Batch store memories
memories = [
    {"content": "Memory 1", "entities": ["A"]},
    {"content": "Memory 2", "entities": ["B"]},
]
await hippocampus.batch_store_memories(memories)
```

---

## Benchmarking

### LoCoMo Evaluation

```bash
# Run LoCoMo benchmark
python experiments/benchmarks/locomo/test_sequential.py --groups 10

# Expected output:
# Overall Accuracy: 75.38%
# - Single-hop: 82.1%
# - Multi-hop: 71.3%
# - Temporal: 69.2%
# - Adversarial: 78.5%
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2024-12 | StoryArc, Theory of Mind, LoCoMo 75.38% |
| 1.0.0 | 2024-11 | Initial release, LoCoMo 71.86% |
