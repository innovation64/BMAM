# BMAM System Architecture

> Brain-inspired Multi-Agent Memory Architecture for Long-term Conversational AI

## Abstract

BMAM implements a neuroscience-inspired memory architecture that models the human memory system through specialized agents corresponding to distinct brain regions. The system achieves state-of-the-art performance on the LoCoMo benchmark (75.38% accuracy), surpassing existing baselines through biologically-plausible memory consolidation, temporal reasoning, and Theory of Mind capabilities.

---

## 1. Design Philosophy

### 1.1 Neuroscience Foundations

BMAM's architecture is grounded in established neuroscience research on memory systems:

| Brain Region | Cognitive Function | BMAM Implementation |
|--------------|-------------------|---------------------|
| **Hippocampus** | Episodic memory encoding | `HippocampusAgent` - event storage & pattern separation |
| **Temporal Lobe** | Semantic memory storage | `TemporalLobeAgent` - knowledge consolidation & KG |
| **Amygdala** | Emotional tagging | `AmygdalaAgent` - affect-based memory enhancement |
| **Prefrontal Cortex** | Working memory & executive control | `PrefrontalAgent` - context management |
| **mPFC (Medial PFC)** | Theory of Mind | `TheoryOfMindAgent` - intent inference |
| **Basal Ganglia** | Procedural memory | `BasalGangliaAgent` - habit learning |

### 1.2 Key Principles

1. **Complementary Learning Systems (CLS)**: Rapid hippocampal encoding + slow neocortical consolidation
2. **Pattern Separation**: Distinct representations for similar memories (DG-CA3 circuit)
3. **Memory Reconsolidation**: Memories are updated when retrieved
4. **Emotion-Enhanced Memory**: Amygdala modulation of memory strength
5. **Sleep-like Consolidation**: Background processes for memory optimization

---

## 2. System Architecture

### 2.1 High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BrainInspiredCoordinator                           │
│                         (Central Executive / PFC)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Input Processing Layer                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │ InputAnalyzer│  │EntityExtract │  │ TemporalExpressionParser │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Memory Encoding Layer                           │   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │Hippocampus │  │ Amygdala   │  │ Prefrontal │  │   Basal    │     │   │
│  │  │  Agent     │  │  Agent     │  │   Agent    │  │  Ganglia   │     │   │
│  │  │            │  │            │  │            │  │   Agent    │     │   │
│  │  │ Episodic   │  │ Emotional  │  │  Working   │  │ Procedural │     │   │
│  │  │  Memory    │  │  Tagging   │  │  Memory    │  │   Memory   │     │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘     │   │
│  │        │               │               │               │             │   │
│  └────────┼───────────────┼───────────────┼───────────────┼─────────────┘   │
│           │               │               │               │                 │
│           ▼               ▼               ▼               ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Memory Consolidation Layer                        │   │
│  │                                                                       │   │
│  │  ┌────────────────────┐  ┌────────────────────┐                      │   │
│  │  │   Temporal Lobe    │  │     StoryArc       │                      │   │
│  │  │      Agent         │  │  (Timeline Index)  │                      │   │
│  │  │                    │  │                    │                      │   │
│  │  │  Semantic Memory   │  │  Temporal Events   │                      │   │
│  │  │  Knowledge Graph   │  │  Entity Timelines  │                      │   │
│  │  └────────────────────┘  └────────────────────┘                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Memory Retrieval Layer                          │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │ Hybrid Search│  │  KG Query    │  │   Theory of Mind         │   │   │
│  │  │ (BM25+Vector)│  │  Reasoning   │  │   (Intent Inference)     │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
User Input
    │
    ▼
┌──────────────────────┐
│  1. Input Analysis   │  Parse entities, time expressions, intent
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  2. Memory Encoding  │  Store in Hippocampus + Emotional tagging
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  3. Index Update     │  Update StoryArc timeline + KG relations
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  4. Memory Retrieval │  Hybrid search + ToM intent analysis
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  5. Response Gen     │  LLM reasoning with retrieved context
└──────────┬───────────┘
           │
           ▼
     Response
```

---

## 3. Core Components

### 3.1 Memory Encoding (Hippocampus)

The hippocampus implements:

**Pattern Separation**
```python
class PatternSeparator:
    """
    Inspired by Dentate Gyrus (DG) pattern separation.
    Creates orthogonal representations for similar inputs.
    """
    def separate(self, input_pattern: np.ndarray) -> np.ndarray:
        # Sparse coding to maximize separation
        return self._sparse_encode(input_pattern)
```

**Event Segmentation**
```python
class HippocampalEventGraph:
    """
    Models event boundaries for episodic memory.
    Research basis: Zacks & Tversky (2001) Event Structure
    """
    def detect_event_boundary(self, content: str) -> bool:
        # Detect significant state changes
        ...
```

### 3.2 Memory Consolidation (Hippocampus → Temporal Lobe)

Implements the Complementary Learning Systems theory:

```python
class ConsolidationPipeline:
    """
    Two-stage memory consolidation:
    1. Rapid encoding in Hippocampus (episodic)
    2. Slow consolidation to Temporal Lobe (semantic)

    Consolidation criteria:
    - hit_count >= threshold (accessed multiple times)
    - confidence >= threshold (high quality)
    - emotion_intensity affects priority (amygdala modulation)
    """

    async def consolidate(self, memory: EpisodicMemory) -> SemanticMemory:
        # Extract semantic facts
        facts = await self._extract_semantic_facts(memory)

        # Update knowledge graph
        await self.temporal_lobe.add_to_kg(facts)

        # Mark as consolidated
        memory.metadata['consolidated'] = True
```

### 3.3 Temporal Reasoning (StoryArc)

Novel contribution for temporal question answering:

```python
class StoryArcManager:
    """
    Timeline-based memory indexing for temporal reasoning.

    Key innovations:
    1. Entity-centric timelines (not just chronological)
    2. Event type classification
    3. Temporal relation inference

    Addresses LoCoMo 'temporal' category weakness.
    """

    def __init__(self):
        self.entity_timelines: Dict[str, List[Event]] = {}
        self.event_index: Dict[str, Event] = {}

    async def query_event_time(
        self,
        entity: str,
        event_keywords: List[str]
    ) -> Dict:
        """
        Query when an event occurred for an entity.
        Returns formatted date with confidence score.
        """
        timeline = self.entity_timelines.get(entity.lower(), [])
        matching_events = self._fuzzy_match_events(timeline, event_keywords)
        return self._format_temporal_response(matching_events)
```

### 3.4 Theory of Mind (mPFC)

Intent inference and adversarial detection:

```python
class TheoryOfMindAgent:
    """
    Models user mental state for intent inference.

    Capabilities:
    1. Intent classification (recall, confirmation, test, etc.)
    2. Adversarial query detection
    3. False presupposition identification
    4. Belief state tracking

    Research basis: Premack & Woodruff (1978), Baron-Cohen et al. (1985)
    """

    async def analyze_query(self, query: str, memories: List) -> Dict:
        # Classify intent type
        intent = await self._classify_intent(query)

        # Detect adversarial patterns
        if intent in ['confirmation', 'leading_question']:
            is_adversarial = await self._detect_adversarial(query, memories)

        return {
            'intent_type': intent,
            'is_adversarial': is_adversarial,
            'suggested_strategy': self._get_response_strategy(intent)
        }
```

---

## 4. Memory Types & Storage

### 4.1 Multi-Store Architecture

| Store | Brain Region | Data Type | Persistence |
|-------|--------------|-----------|-------------|
| Episodic Memory | Hippocampus | Events, experiences | JSON + SQLite |
| Semantic Memory | Temporal Lobe | Facts, knowledge | SQLite + KG |
| Working Memory | Prefrontal | Active context | In-memory |
| Procedural Memory | Basal Ganglia | Habits, patterns | JSON |
| Emotional Tags | Amygdala | Affect associations | JSON |

### 4.2 Knowledge Graph Schema

```
Node Types:
  - Person: {name, attributes, first_seen, last_seen}
  - Location: {name, type, coordinates}
  - Event: {type, date, participants}
  - Concept: {name, category}

Edge Types:
  - KNOWS: Person → Person
  - VISITED: Person → Location
  - PARTICIPATED_IN: Person → Event
  - OCCURRED_AT: Event → Location
  - HAS_ATTRIBUTE: Entity → Concept
```

---

## 5. Background Processes

### 5.1 Consolidation Scheduler

```python
class BackgroundMemoryProcessManager:
    """
    Manages autonomous memory processes (like sleep consolidation).

    Processes:
    1. Consolidation: Hippocampus → Temporal Lobe (every 30 min)
    2. Forgetting: Remove low-value memories (every 1 hour)
    3. Reconsolidation: Strengthen accessed memories (every 15 min)

    Load-aware scheduling prevents resource exhaustion.
    """

    async def run_consolidation_cycle(self):
        # Select candidates based on hit_count, confidence, emotion
        candidates = await self._select_consolidation_candidates()

        for memory in candidates:
            # Extract semantic facts
            # Update knowledge graph
            # Mark as consolidated
            await self._consolidate_memory(memory)
```

### 5.2 Adaptive Memory Shaping

```python
class AdaptiveMemoryShapingManager:
    """
    Event-driven memory optimization.

    Triggers:
    - New memory stored → Update indexes
    - Memory retrieved → Boost strength (reconsolidation)
    - Negative feedback → Mark for review
    - High emotion → Priority consolidation
    """
```

---

## 6. Retrieval Pipeline

### 6.1 Hybrid Search

```python
class HybridRetriever:
    """
    Multi-strategy retrieval combining:
    1. BM25 keyword matching
    2. Dense vector similarity (FAISS)
    3. Knowledge graph traversal
    4. Timeline-based temporal search

    Fusion: RRF (Reciprocal Rank Fusion)
    """

    async def retrieve(self, query: str, top_k: int = 10) -> List[Memory]:
        # Parallel retrieval from all sources
        bm25_results = await self._bm25_search(query)
        vector_results = await self._vector_search(query)
        kg_results = await self._kg_search(query)
        temporal_results = await self._temporal_search(query)

        # Fuse with RRF
        return self._reciprocal_rank_fusion([
            bm25_results,
            vector_results,
            kg_results,
            temporal_results
        ])
```

### 6.2 Query Understanding

```python
class InputAnalyzer:
    """
    Analyzes query to determine optimal retrieval strategy.

    Query types:
    - factual: "What is X?" → KG + Semantic
    - episodic: "When did I...?" → Timeline + Episodic
    - temporal: "How long since...?" → StoryArc
    - adversarial: "You said X, right?" → ToM verification
    """
```

---

## 7. Evaluation Results

### 7.1 LoCoMo Benchmark

| Model | Overall | Single-hop | Multi-hop | Temporal | Adversarial |
|-------|---------|------------|-----------|----------|-------------|
| MemOS (baseline) | 73.31% | 79.2% | 68.4% | 65.1% | 75.3% |
| BMAM V1 | 71.86% | 77.5% | 66.8% | 62.3% | 74.1% |
| **BMAM V2** | **75.38%** | **82.1%** | **71.3%** | **69.2%** | **78.5%** |

### 7.2 Ablation Study

| Configuration | Accuracy | Delta |
|---------------|----------|-------|
| Full BMAM V2 | 75.38% | - |
| - StoryArc | 72.15% | -3.23% |
| - Theory of Mind | 73.42% | -1.96% |
| - Hybrid Retrieval | 71.89% | -3.49% |
| - Consolidation | 73.78% | -1.60% |

---

## 8. Scalability & Performance

### 8.1 Memory Capacity

- Default capacity: 20,000 episodic memories
- Automatic forgetting maintains quality
- Consolidation compresses to semantic facts

### 8.2 Latency

| Operation | P50 | P99 |
|-----------|-----|-----|
| Memory encoding | 150ms | 450ms |
| Retrieval (top-10) | 80ms | 250ms |
| Full response | 800ms | 2.5s |

### 8.3 Resource Usage

- Memory: ~500MB base + 1KB per episodic memory
- Storage: ~100KB per 1000 memories (JSON compressed)
- API calls: 1-3 per user interaction (cached embeddings)

---

## 9. Future Directions

1. **Multimodal Memory**: Image and audio encoding
2. **Distributed Agents**: Multi-user memory isolation
3. **Neuromorphic Computing**: SNN-based implementation
4. **Continual Learning**: Online model adaptation
5. **Metacognition**: Self-monitoring and error correction

---

## References

1. McClelland, J. L., McNaughton, B. L., & O'Reilly, R. C. (1995). Why there are complementary learning systems in the hippocampus and neocortex.
2. Squire, L. R., & Zola, S. M. (1996). Structure and function of declarative and nondeclarative memory systems.
3. Zacks, J. M., & Tversky, B. (2001). Event structure in perception and conception.
4. Premack, D., & Woodruff, G. (1978). Does the chimpanzee have a theory of mind?
5. Nader, K., & Hardt, O. (2009). A single standard for memory: the case for reconsolidation.
