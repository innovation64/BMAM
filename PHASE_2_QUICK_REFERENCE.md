# Phase 2 Quick Reference Guide
## Testing Infrastructure and Adapter Layer

---

## Quick Start

### 1. Import Testing Utilities

```python
# Import all mocks
from src.core.testing import (
    MockMemorySystem,
    MockAgent,
    MockMessageBus,
    MockEmbeddingService,
    MockVectorDatabase,
    TestContainer
)

# Import fixtures in tests
from src.core.testing.fixtures import (
    test_config,
    mock_memory_system,
    mock_agents,
    test_container
)
```

### 2. Import Adapters

```python
from src.core.adapters import (
    MemorySystemAdapter,
    EmbeddingServiceAdapter,
    VectorDatabaseAdapter,
    AgentAdapter,
    BrainRegionAgentAdapter
)
```

---

## Common Test Patterns

### Pattern 1: Simple Mock Test

```python
@pytest.mark.asyncio
async def test_with_mock(mock_memory_system):
    """Use mock from fixture"""

    # Store memory
    memory_id = await mock_memory_system.store_memory("Test")

    # Verify
    assert len(mock_memory_system.store_calls) == 1
    assert mock_memory_system.store_calls[0]['content'] == "Test"
```

### Pattern 2: TestContainer

```python
def test_with_container():
    """Use TestContainer for integrated testing"""

    with TestContainer() as container:
        # Register components
        container.register_agent('hippocampus')

        # Use container
        memory = container.memory_system
        agent = container.agents['hippocampus']

        # Test...

        # Verify
        container.verify_memory_stored(1)
```

### Pattern 3: Adapter Usage

```python
def test_with_adapter():
    """Wrap legacy code with adapter"""

    from src.memory.memory_system import AdvancedMemorySystem

    legacy = AdvancedMemorySystem()
    adapted = MemorySystemAdapter(legacy)

    # Use interface methods
    await adapted.store_memory("Test")
```

---

## Mock API Reference

### MockMemorySystem

```python
mock = MockMemorySystem()

# Store
memory_id = await mock.store_memory(content, metadata, importance)
ids = await mock.store_batch(memories)

# Retrieve
memories = await mock.retrieve(query, k, **filters)
memory = await mock.retrieve_by_id(memory_id)
memories = await mock.retrieve_by_ids(ids)

# Search
results = await mock.search_memories(query, search_type, k, threshold)

# Update/Delete
success = await mock.update_memory(memory_id, updates)
success = await mock.delete_memory(memory_id)

# Stats
stats = mock.get_system_stats()

# Verify calls
assert len(mock.store_calls) == 1
assert mock.store_calls[0]['content'] == "expected"
assert len(mock.retrieve_calls) == 2
```

### MockAgent

```python
mock = MockAgent(agent_id="test", brain_region="test")

# Properties
assert mock.agent_id == "test"
assert mock.brain_region == "test"

# Process
result = await mock.process_message(message)

# Lifecycle
await mock.initialize()
await mock.shutdown()

# Verify
assert len(mock.messages_received) == 1
assert mock.initialized is True
assert mock.shutdown_called is True
```

### MockMessageBus

```python
mock = MockMessageBus()

# Publish
await mock.publish(message)

# Subscribe
async def handler(msg):
    print(msg)

await mock.subscribe("type", handler)
await mock.unsubscribe("type", handler)

# Lifecycle
await mock.start()
await mock.stop()

# Verify
assert len(mock.published_messages) == 3
messages = [m for m in mock.published_messages if m.message_type == "store"]
```

### MockEmbeddingService

```python
mock = MockEmbeddingService(dimension=128)

# Encode
embedding = await mock.encode_text("hello")
embeddings = await mock.encode_batch(["a", "b", "c"])

# Properties
dim = mock.dimension  # 128

# Verify
assert len(mock.encode_text_calls) == 1
assert mock.encode_text_calls[0] == "hello"
```

### MockVectorDatabase

```python
mock = MockVectorDatabase()

# Add
vectors = [np.random.rand(128) for _ in range(3)]
metadata = [{'id': i} for i in range(3)]
ids = await mock.add_vectors(vectors, metadata)

# Search
results = await mock.search(query_vector, k=5, threshold=0.5)

# Delete
count = await mock.delete_vectors(ids)

# Stats
stats = mock.get_stats()

# Verify
assert len(mock.add_vectors_calls) == 1
assert len(mock.search_calls) == 2
```

---

## TestContainer API Reference

```python
container = TestContainer()

# Access mocks (properties)
container.memory_system
container.message_bus
container.embedding_service
container.vector_db
container.agents  # Dict[str, IAgent]

# Register agents
container.register_agent("hippocampus")
container.register_agent("custom", custom_agent_instance)
container.register_agents(["agent1", "agent2", "agent3"])

# Register custom components
container.register(IInterface, Implementation, lifecycle)
container.register_instance(IInterface, instance)

# Resolve
component = container.resolve(IInterface)
config = container.get_config()

# Verification helpers
container.verify_no_calls()
container.verify_memory_stored(expected_count=3)
container.verify_messages_published(expected_count=5)

# Get messages
messages = container.get_published_messages()
store_messages = container.get_published_messages("memory_store")

# Reset
container.reset()  # Clear all mocks and reset state

# Context manager
with TestContainer() as container:
    # Use container
    pass
    # Automatic cleanup
```

---

## Adapter API Reference

### MemorySystemAdapter

```python
from src.memory.memory_system import AdvancedMemorySystem
from src.core.adapters import MemorySystemAdapter

legacy = AdvancedMemorySystem()
adapter = MemorySystemAdapter(legacy)

# Use IMemorySystem interface
memory_id = await adapter.store_memory(content, metadata, importance)
memories = await adapter.retrieve(query, k=10)
results = await adapter.search_memories(query, search_type="semantic")

# Access legacy system
legacy_system = adapter.legacy_system
```

### EmbeddingServiceAdapter

```python
from src.memory.memory_system import EmbeddingService
from src.core.adapters import EmbeddingServiceAdapter

legacy = EmbeddingService()
adapter = EmbeddingServiceAdapter(legacy)

# Use IEmbeddingService interface
embedding = await adapter.encode_text("hello")
embeddings = await adapter.encode_batch(["a", "b"])
dimension = adapter.dimension
```

### VectorDatabaseAdapter

```python
from src.memory.memory_system import FAISSVectorDatabase
from src.core.adapters import VectorDatabaseAdapter

legacy = FAISSVectorDatabase(dimension=1536)
adapter = VectorDatabaseAdapter(legacy)

# Use IVectorDatabase interface
ids = await adapter.add_vectors(vectors, metadata)
results = await adapter.search(query_vector, k=10)
count = await adapter.delete_vectors(ids)
```

### AgentAdapter

```python
from src.agents.brain_regions import HippocampusAgent
from src.core.adapters import BrainRegionAgentAdapter

legacy = HippocampusAgent(...)
adapter = BrainRegionAgentAdapter(
    legacy,
    agent_id="hippocampus",
    brain_region="hippocampus"
)

# Use IAgent interface
result = await adapter.process_message(message)
await adapter.initialize()
await adapter.shutdown()
```

---

## Fixture Reference

### Configuration

```python
def test_with_config(test_config):
    """Use test configuration"""
    assert test_config.environment == "test"
    assert test_config.memory.enable_cache is False
```

### Mock Components

```python
def test_with_mocks(
    mock_memory_system,
    mock_message_bus,
    mock_agent,
    mock_agents,  # Dict of 5 agents
    mock_embedding_service,
    mock_vector_db
):
    """All mocks available as fixtures"""
    pass
```

### Containers

```python
def test_with_container(test_container):
    """Pre-configured container"""
    memory = test_container.memory_system
    # test...

def test_with_agents(test_container_with_agents):
    """Container with 5 brain region agents"""
    assert len(test_container_with_agents.agents) == 5
```

### Helpers

```python
def test_with_data(sample_memories):
    """List of sample memory dicts"""
    assert len(sample_memories) == 3

async def test_with_populated(populated_memory_system):
    """Memory system with data already stored"""
    results = await populated_memory_system.retrieve("query")
    assert len(results) > 0
```

### Parametrized

```python
async def test_various_k(mock_memory_system, k_values):
    """Runs with k=1, k=5, k=10"""
    results = await mock_memory_system.retrieve("query", k=k_values)
    assert len(results) <= k_values

async def test_search_types(mock_memory_system, search_types):
    """Runs with semantic, hybrid, keyword"""
    results = await mock_memory_system.search_memories(
        "query",
        search_type=search_types
    )
```

---

## Common Assertions

### Memory System

```python
# Verify storage
assert len(mock.store_calls) == 1
assert mock.store_calls[0]['content'] == "expected"
assert mock.store_calls[0]['importance'] == 0.8

# Verify retrieval
assert len(mock.retrieve_calls) == 1
assert mock.retrieve_calls[0]['query'] == "test query"
assert mock.retrieve_calls[0]['k'] == 5

# Verify search
assert len(mock.search_calls) == 1
assert mock.search_calls[0]['search_type'] == "semantic"
```

### Agent

```python
# Verify messages
assert len(agent.messages_received) == 1
msg = agent.messages_received[0]
assert msg.sender == "test"
assert msg.message_type == "request"

# Verify lifecycle
assert agent.initialized is True
assert agent.shutdown_called is True
```

### Message Bus

```python
# Verify publishing
assert len(bus.published_messages) == 3

# Filter by type
store_msgs = [m for m in bus.published_messages
              if m.message_type == "store"]
assert len(store_msgs) == 2

# Verify state
assert bus.started is True
assert bus.stopped is False
```

---

## Test Examples

### Example 1: Unit Test

```python
import pytest
from src.core.testing import MockMemorySystem, MockAgent
from src.core.interfaces import AgentMessage

@pytest.mark.asyncio
async def test_agent_interaction():
    """Test agent stores memory"""

    memory = MockMemorySystem()
    agent = MockAgent("test_agent", "test_region")

    # Simulate agent processing
    message = AgentMessage(
        sender="user",
        receiver="test_agent",
        message_type="store",
        content={'text': 'Remember this'}
    )

    result = await agent.process_message(message)
    await memory.store_memory("Remember this")

    # Verify
    assert result['success'] is True
    assert len(agent.messages_received) == 1
    assert len(memory.store_calls) == 1
```

### Example 2: Integration Test

```python
from src.core.testing import TestContainer

@pytest.mark.asyncio
async def test_system_integration():
    """Test full system with mocks"""

    with TestContainer() as container:
        # Setup
        container.register_agents([
            'hippocampus',
            'temporal_lobe',
            'prefrontal'
        ])

        # Test system
        coordinator = build_coordinator(container)
        result = await coordinator.process_input("test query")

        # Verify
        container.verify_memory_stored(expected_count=3)
        container.verify_messages_published(expected_count=6)

        # Detailed verification
        messages = container.get_published_messages("memory_store")
        assert len(messages) == 3
        assert all(m.sender.startswith('agent') for m in messages)
```

### Example 3: Parametrized Test

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("k,expected_max", [
    (1, 1),
    (5, 5),
    (10, 10),
    (100, 10)  # Only 10 memories stored
])
async def test_retrieval_limits(mock_memory_system, k, expected_max):
    """Test retrieval respects k parameter"""

    # Store 10 memories
    for i in range(10):
        await mock_memory_system.store_memory(f"Memory {i}")

    # Retrieve with k
    results = await mock_memory_system.retrieve("query", k=k)

    # Verify
    assert len(results) <= expected_max
    assert len(results) <= k
```

---

## File Structure

```
BMAM/
├── src/core/
│   ├── testing/                    # Testing Infrastructure
│   │   ├── __init__.py            (47 lines)
│   │   ├── mock_factories.py      (524 lines)
│   │   ├── test_container.py      (250 lines)
│   │   └── fixtures.py            (325 lines)
│   │
│   └── adapters/                   # Adapter Layer
│       ├── __init__.py            (26 lines)
│       ├── memory_system_adapter.py      (319 lines)
│       ├── embedding_service_adapter.py  (172 lines)
│       ├── vector_database_adapter.py    (207 lines)
│       └── agent_adapter.py              (225 lines)
│
└── tests/core/
    ├── testing/
    │   └── test_mock_factories.py  (28 tests)
    │
    └── adapters/
        └── test_adapters.py        (22 tests)
```

---

## Running Tests

```bash
# Run all Phase 2 tests
pytest tests/core/testing/ tests/core/adapters/ -v

# Run specific test file
pytest tests/core/testing/test_mock_factories.py -v

# Run specific test class
pytest tests/core/adapters/test_adapters.py::TestMemorySystemAdapter -v

# Run specific test
pytest tests/core/testing/test_mock_factories.py::TestMockAgent::test_properties -v

# Run with coverage
pytest tests/core/ --cov=src/core/testing --cov=src/core/adapters

# Run async tests only
pytest tests/core/ -k asyncio -v
```

---

## Troubleshooting

### Issue: Import Error

```python
# Wrong
from BMAM.src.core.testing import MockMemorySystem

# Correct
from src.core.testing import MockMemorySystem
```

### Issue: Async Test Not Running

```python
# Missing decorator
def test_async():  # Wrong
    await mock.store_memory("test")

# Correct
@pytest.mark.asyncio
async def test_async():  # Correct
    await mock.store_memory("test")
```

### Issue: Mock Not Tracking Calls

```python
# Reset after setup
async def test_with_setup(populated_memory_system):
    # This has stored data but calls are tracked
    # Reset call tracking if needed
    populated_memory_system.store_calls.clear()

    # Now test fresh
    await populated_memory_system.store_memory("new")
    assert len(populated_memory_system.store_calls) == 1
```

### Issue: Adapter Fallback Not Working

```python
# Make sure methods are set to None, not missing
legacy.process_message = None  # Triggers fallback
# Not: delattr(legacy, 'process_message')  # hasattr still True
```

---

## Best Practices

1. **Use Fixtures** - Don't create mocks manually in tests
2. **Reset State** - Use TestContainer context manager for auto-cleanup
3. **Verify Calls** - Check both call count and call content
4. **Async/Await** - Always use `@pytest.mark.asyncio` for async tests
5. **Type Hints** - Keep type hints for IDE support
6. **Docstrings** - Document what each test verifies
7. **Parametrize** - Use parametrized tests for variations
8. **Isolation** - Each test should be independent

---

## Quick Checklist

- [ ] Import mocks from `src.core.testing`
- [ ] Use `@pytest.mark.asyncio` for async tests
- [ ] Use fixtures instead of manual mock creation
- [ ] Verify both call count and content
- [ ] Use TestContainer for integration tests
- [ ] Reset mocks between tests (or use context manager)
- [ ] Check adapters handle both sync and async legacy code
- [ ] Document test purpose in docstring

---

**Phase 2 Status:** ✅ COMPLETE - 50/50 tests passing
