# BMAM Testing Guide

> Comprehensive testing documentation for the Brain-inspired Multi-Agent Memory Framework

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)

---

## Quick Start

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_hippocampus_agent.py

# Run specific test
pytest tests/unit/test_hippocampus_agent.py::TestEpisodicMemory::test_memory_creation
```

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_hippocampus_agent.py
│   ├── test_story_arc.py
│   ├── test_theory_of_mind.py
│   └── test_coordinator.py
├── integration/             # Integration tests
│   ├── test_real_coordinator_v2.py
│   ├── test_real_memory_system_v2.py
│   └── test_q2_temporal_reasoning.py
├── core/                    # Core module tests
│   ├── test_container.py
│   ├── test_config.py
│   └── test_lazy.py
└── test_*.py               # Legacy and benchmark tests
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with print statements visible
pytest -s

# Run and stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Test Selection

```bash
# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run tests matching a pattern
pytest -k "hippocampus"

# Run tests with specific marker
pytest -m "not slow"
pytest -m "integration"
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=src

# Generate HTML coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Generate XML coverage (for CI)
pytest --cov=src --cov-report=xml
```

---

## Writing Tests

### Unit Test Example

```python
"""
Unit tests for MyModule
"""

import pytest
from unittest.mock import Mock, AsyncMock

class TestMyClass:
    """Test MyClass functionality"""

    @pytest.fixture
    def my_instance(self):
        """Create instance for testing"""
        return MyClass()

    def test_basic_functionality(self, my_instance):
        """Test basic functionality"""
        result = my_instance.do_something()
        assert result is not None

    @pytest.mark.asyncio
    async def test_async_method(self, my_instance):
        """Test async method"""
        result = await my_instance.async_method()
        assert result["status"] == "success"
```

### Using Fixtures from conftest.py

```python
def test_with_mock_embedding(mock_embedding_service):
    """Test using mock embedding service"""
    # mock_embedding_service is automatically injected
    result = mock_embedding_service.encode_text("test")
    assert len(result) == 1536

def test_with_sample_data(sample_memories):
    """Test using sample memory data"""
    assert len(sample_memories) == 3
    assert sample_memories[0]["content"] == "Met Sarah at the coffee shop on May 5th"
```

### Mocking External Services

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mocked_llm():
    """Test with mocked LLM calls"""
    with patch('src.coordination.brain_coordinator.OpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=Mock(choices=[Mock(message=Mock(content="Test"))])
        )

        # Test code that uses LLM
        result = await some_function_that_calls_llm()
        assert result is not None
```

### Test Markers

```python
import pytest

@pytest.mark.slow
def test_slow_operation():
    """This test takes a long time"""
    pass

@pytest.mark.integration
def test_integration():
    """This is an integration test"""
    pass

@pytest.mark.requires_api
def test_with_real_api(skip_without_api_key):
    """This test requires real API access"""
    pass
```

---

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation.

| Module | Test File | Coverage |
|--------|-----------|----------|
| HippocampusAgent | `test_hippocampus_agent.py` | Memory creation, storage, retrieval |
| StoryArc | `test_story_arc.py` | Timeline indexing, temporal queries |
| TheoryOfMind | `test_theory_of_mind.py` | Intent detection, adversarial detection |
| Coordinator | `test_coordinator.py` | Initialization, processing, shutdown |

### Integration Tests (`tests/integration/`)

Test component interactions.

| Test File | Description |
|-----------|-------------|
| `test_real_coordinator_v2.py` | Full coordinator workflow |
| `test_real_memory_system_v2.py` | Memory system integration |
| `test_q2_temporal_reasoning.py` | Temporal reasoning pipeline |
| `test_kg_unified_sync.py` | Knowledge graph synchronization |

### Benchmark Tests

| Test File | Description |
|-----------|-------------|
| `test_locomo_benchmark.py` | LoCoMo benchmark evaluation |
| `test_phase5_optimization_benchmarks.py` | Performance benchmarks |

---

## Test Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| `src/agents/brain_regions/` | 60% | 80% |
| `src/coordination/` | 55% | 75% |
| `src/memory/` | 65% | 80% |
| `src/utils/` | 70% | 85% |
| **Overall** | **62%** | **80%** |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/unit/ -x -q
```

---

## Debugging Tests

### Using pytest-pdb

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of test
pytest --pdb-first
```

### Verbose Logging

```python
import logging

def test_with_logging(caplog):
    """Test with log capture"""
    with caplog.at_level(logging.DEBUG):
        # Run test
        pass

    assert "expected message" in caplog.text
```

### Async Debugging

```python
@pytest.mark.asyncio
async def test_async_debug():
    """Debug async test"""
    import asyncio

    # Add breakpoint
    # import pdb; pdb.set_trace()

    result = await some_async_function()
    assert result is not None
```

---

## Common Issues

### Issue: Tests hang indefinitely

**Solution**: Check for unawaited coroutines or infinite loops.

```python
# Wrong
result = async_function()  # Missing await

# Correct
result = await async_function()
```

### Issue: Mock not applied

**Solution**: Ensure patch path matches import path.

```python
# If module imports: from src.services import OpenAIService
# Patch at the usage location:
@patch('src.coordination.brain_coordinator.OpenAIService')
```

### Issue: Fixture not found

**Solution**: Check fixture scope and conftest.py location.

```python
# conftest.py must be in tests/ or above
# Fixture names must match exactly
```

---

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Mock external services**: Don't call real APIs in unit tests
3. **Use fixtures**: Share common setup via fixtures
4. **Clear naming**: `test_<action>_<expected_result>`
5. **One assertion focus**: Each test should verify one behavior
6. **Clean up**: Use fixtures with cleanup or `autouse`

---

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
