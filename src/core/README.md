# Core Infrastructure - Quick Reference

**Status:** Production Ready ✅
**Test Coverage:** 57/57 tests passing (100%)

---

## Quick Start

```python
# Import core components
from BMAM.src.core import Container, BMAMConfig, Lazy
from BMAM.src.core.interfaces import IMemorySystem, IAgent, IMessageBus

# Load configuration
config = BMAMConfig.from_env()

# Setup dependency injection
container = Container()
container.register_instance(BMAMConfig, config)
container.register(IMemorySystem, AdvancedMemorySystem)

# Resolve dependencies
memory = container.resolve(IMemorySystem)
```

---

## 1. Dependency Injection Container

### Basic Usage

```python
from BMAM.src.core import Container, Lifecycle

container = Container()

# Register interface to implementation
container.register(IMemorySystem, AdvancedMemorySystem, Lifecycle.SINGLETON)

# Register with factory
container.register_factory(
    IMessageBus,
    lambda c: MessageBus(queue_size=100)
)

# Register instance
config = BMAMConfig.from_env()
container.register_instance(BMAMConfig, config)

# Resolve
memory = container.resolve(IMemorySystem)
```

### Lifecycle Strategies

- **`Lifecycle.SINGLETON`** - Single instance, created once, cached (default)
- **`Lifecycle.TRANSIENT`** - New instance every time
- **`Lifecycle.SCOPED`** - One instance per scope (e.g., per request)

### Scoped Containers

```python
# Create scope
scope = container.create_scope()

# Register scope-specific instances
scope.register_instance(str, "request_id_123")

# Resolves from scope first, falls back to parent
service = scope.resolve(IService)
```

### Global Container

```python
from BMAM.src.core import get_container, reset_container

# Get global instance
container = get_container()

# Reset for testing
reset_container()
```

---

## 2. Configuration Management

### Loading Configuration

```python
from BMAM.src.core import BMAMConfig, get_config

# From environment variables
config = BMAMConfig.from_env()

# For testing
test_config = BMAMConfig.for_testing()

# Global cached instance
config = get_config()
```

### Accessing Configuration

```python
# Memory system config
embedding_model = config.memory.embedding_model
cache_enabled = config.memory.enable_cache
vector_db_path = config.memory.vector_db_index_path

# Agent config
llm_model = config.agent.default_model
timeout = config.agent.llm_call_timeout
max_retries = config.agent.max_retries

# Coordinator config
learning_enabled = config.coordinator.enable_learning
max_agents = config.coordinator.max_concurrent_agents
```

### Environment Variables

Set these before calling `from_env()`:

```bash
# Memory System
export EMBEDDING_MODEL=text-embedding-3-small
export EMBEDDING_DIMENSION=1536
export ENABLE_EMBEDDING_CACHE=true

# Agent System
export DEFAULT_MODEL=gpt-4o-mini
export MAX_TOKENS=1500
export LLM_CALL_TIMEOUT=30.0

# Coordinator
export ENABLE_LEARNING=true
export MAX_CONCURRENT_AGENTS=10

# Environment
export BMAM_ENV=production
export OPENAI_API_KEY=sk-...
export LOG_LEVEL=INFO
```

---

## 3. Lazy Initialization

### Lazy Wrapper

```python
from BMAM.src.core import Lazy

# Create lazy instance
memory_system = Lazy(lambda: AdvancedMemorySystem())

# Not created yet...
print(memory_system.is_initialized)  # False

# Access value (creates now)
system = memory_system.value
print(memory_system.is_initialized)  # True

# Subsequent accesses return cached instance
system2 = memory_system.value  # Same instance
```

### Lazy Property Decorator

```python
from BMAM.src.core import lazy_property

class Application:
    @lazy_property
    def config(self):
        return BMAMConfig.from_env()

    @lazy_property
    def memory_system(self):
        return AdvancedMemorySystem()

app = Application()
# Nothing created yet

# First access creates and caches
config = app.config  # Created now
config2 = app.config  # Cached
```

### Reset for Testing

```python
lazy_resource = Lazy(lambda: ExpensiveResource())

resource1 = lazy_resource.value
lazy_resource.reset()  # Reset to uninitialized

resource2 = lazy_resource.value  # New instance
```

---

## 4. Core Interfaces

### Memory System Interfaces

```python
from BMAM.src.core.interfaces import (
    IMemorySystem,
    IMemoryStorer,
    IMemoryRetriever,
    IEmbeddingService,
    IVectorDatabase,
    Memory
)

class MyMemorySystem(IMemorySystem):
    async def store_memory(self, content: str, metadata: Dict, importance: float) -> str:
        # Implementation
        pass

    async def retrieve(self, query: str, k: int, **filters) -> List[Memory]:
        # Implementation
        pass

    async def search_memories(self, query: str, search_type: str, k: int) -> List[Dict]:
        # Implementation
        pass
```

### Agent Interfaces

```python
from BMAM.src.core.interfaces import IAgent, AgentMessage

class MyAgent(IAgent):
    @property
    def agent_id(self) -> str:
        return "my_agent"

    @property
    def brain_region(self) -> str:
        return "custom_region"

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        # Process message
        return {"success": True}

    async def initialize(self):
        # Setup resources
        pass

    async def shutdown(self):
        # Cleanup
        pass
```

### Message Bus Interface

```python
from BMAM.src.core.interfaces import IMessageBus, AgentMessage

class MyMessageBus(IMessageBus):
    async def publish(self, message: AgentMessage):
        # Publish message
        pass

    async def subscribe(self, message_type: str, handler):
        # Register handler
        pass

    async def start(self):
        # Start processing
        pass

    async def stop(self):
        # Stop processing
        pass
```

---

## 5. Testing Patterns

### Testing with DI Container

```python
import pytest
from BMAM.src.core import Container, BMAMConfig

@pytest.fixture
def test_container():
    container = Container()
    config = BMAMConfig.for_testing()
    container.register_instance(BMAMConfig, config)
    return container

def test_component(test_container):
    # Use container to inject dependencies
    component = test_container.resolve(IMyComponent)
    assert component is not None
```

### Testing with Mock Implementations

```python
class MockMemorySystem(IMemorySystem):
    def __init__(self):
        self.stored_memories = []
        self.retrieve_calls = []

    async def store_memory(self, content, metadata=None, importance=0.5):
        self.stored_memories.append(content)
        return f"mem_{len(self.stored_memories)}"

    async def retrieve(self, query, k=10, **filters):
        self.retrieve_calls.append(query)
        return []

# In test
def test_with_mock():
    container = Container()
    mock_memory = MockMemorySystem()
    container.register_instance(IMemorySystem, mock_memory)

    # Test component using mock
    component = MyComponent(container.resolve(IMemorySystem))
    await component.do_something()

    # Assert on mock
    assert len(mock_memory.stored_memories) == 1
```

### Testing Configuration

```python
def test_with_test_config():
    config = BMAMConfig.for_testing()

    # Test config has:
    # - In-memory database
    # - Disabled caching
    # - Short timeouts
    # - Disabled background processes

    assert config.memory.database_url == "sqlite:///:memory:"
    assert config.memory.enable_cache is False
    assert config.coordinator.enable_learning is False
```

---

## 6. Common Patterns

### Pattern 1: Singleton Service

```python
from BMAM.src.core import Lazy

_memory_system = Lazy(lambda: AdvancedMemorySystem())

def get_memory_system():
    return _memory_system.value
```

### Pattern 2: Factory with Dependencies

```python
def create_coordinator(container: Container):
    config = container.resolve(BMAMConfig)
    memory = container.resolve(IMemorySystem)
    message_bus = container.resolve(IMessageBus)

    return BrainInspiredCoordinator(
        config=config,
        memory_system=memory,
        message_bus=message_bus
    )

container.register_factory(
    BrainInspiredCoordinator,
    create_coordinator
)
```

### Pattern 3: Conditional Registration

```python
config = get_config()

if config.environment == "production":
    container.register(IMemorySystem, ProductionMemorySystem)
else:
    container.register(IMemorySystem, DevelopmentMemorySystem)
```

### Pattern 4: Configuration-Driven Setup

```python
def setup_container(config: BMAMConfig) -> Container:
    container = Container()
    container.register_instance(BMAMConfig, config)

    # Register based on config
    if config.memory.enable_cache:
        container.register(IEmbeddingService, CachedEmbeddingService)
    else:
        container.register(IEmbeddingService, DirectEmbeddingService)

    return container
```

---

## 7. Error Handling

### Container Errors

```python
# Unregistered interface
try:
    service = container.resolve(IUnregisteredService)
except ValueError as e:
    print(f"Error: {e}")  # "Interface IUnregisteredService not registered"

# Safe resolution
service = container.try_resolve(IUnregisteredService)  # Returns None
```

### Configuration Errors

```python
# Invalid environment variable
import os
os.environ['MAX_TOKENS'] = 'invalid'

try:
    config = BMAMConfig.from_env()
except ValueError as e:
    print(f"Configuration error: {e}")
```

---

## 8. Best Practices

### ✅ DO

- Use interfaces for all major components
- Register configuration as singleton
- Use `Lifecycle.SINGLETON` for expensive resources
- Reset global state in test fixtures
- Use `BMAMConfig.for_testing()` in tests
- Document dependencies in docstrings
- Use type hints everywhere

### ❌ DON'T

- Don't create global singletons (use container instead)
- Don't mutate config after creation (it's frozen)
- Don't import heavy modules at package level
- Don't resolve in constructors (inject instead)
- Don't access config directly (inject via DI)
- Don't skip type hints

---

## 9. Migration Guide

### Before (Old Pattern)

```python
# Global singleton with side effects
from src.memory.memory_system import memory_system

# Direct usage
result = await memory_system.search_memories("query")
```

### After (New Pattern)

```python
# Dependency injection
from BMAM.src.core import Container, BMAMConfig
from BMAM.src.core.interfaces import IMemorySystem

# Setup
container = Container()
config = BMAMConfig.from_env()
container.register_instance(BMAMConfig, config)
container.register(IMemorySystem, AdvancedMemorySystem)

# Inject dependency
class MyService:
    def __init__(self, memory: IMemorySystem):
        self._memory = memory

    async def search(self, query: str):
        return await self._memory.search_memories(query)

# Use
memory = container.resolve(IMemorySystem)
service = MyService(memory)
```

---

## 10. Performance Considerations

- **Container resolution:** O(1) for singletons (cached)
- **Lazy initialization:** Thread-safe, double-checked locking
- **Configuration:** Cached globally, loaded once
- **Scoped containers:** Minimal overhead, parent fallback

---

## Reference Documentation

- **Full Design:** `/Users/liyang/Desktop/testversion/ARCHITECTURE_REFACTOR_DESIGN.md`
- **Implementation Report:** `/Users/liyang/Desktop/testversion/PHASE_1_CORE_INFRASTRUCTURE_COMPLETE.md`
- **Test Suite:** `/Users/liyang/Desktop/testversion/BMAM/tests/core/`

---

**Version:** 1.0
**Last Updated:** 2025-11-10
**Status:** Production Ready ✅
