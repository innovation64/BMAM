"""
Pytest configuration and shared fixtures for BMAM tests.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment
os.environ.setdefault('BMAM_TEST_MODE', 'true')
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-testing')


# ============================================================================
# Async Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Services
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(return_value=Mock(
        choices=[Mock(message=Mock(content="Test response"))]
    ))
    return client


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service"""
    service = AsyncMock()
    service.encode_text = AsyncMock(return_value=[0.1] * 1536)
    service.encode_batch = AsyncMock(return_value=[[0.1] * 1536])
    service.dimension = 1536
    return service


@pytest.fixture
def mock_kg_builder():
    """Create a mock knowledge graph builder"""
    builder = Mock()
    builder.extract_from_text = AsyncMock(return_value=([], []))
    builder.add_entity = Mock()
    builder.add_relation = Mock()
    return builder


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_memories():
    """Create sample memories for testing"""
    return [
        {
            "id": "mem_001",
            "content": "Met Sarah at the coffee shop on May 5th",
            "entities": ["Sarah", "coffee shop"],
            "timestamp": datetime(2024, 5, 5, 14, 30),
            "importance": 0.8,
            "metadata": {
                "event_time": "2024-05-05",
                "speaker": "user"
            }
        },
        {
            "id": "mem_002",
            "content": "Sarah mentioned she loves hiking",
            "entities": ["Sarah"],
            "timestamp": datetime(2024, 5, 5, 14, 35),
            "importance": 0.6,
            "metadata": {
                "event_time": "2024-05-05",
                "speaker": "user"
            }
        },
        {
            "id": "mem_003",
            "content": "Tom's birthday party was last Saturday",
            "entities": ["Tom"],
            "timestamp": datetime(2024, 5, 10, 10, 0),
            "importance": 0.7,
            "metadata": {
                "event_time": "2024-05-04",
                "event_type": "birthday"
            }
        },
    ]


@pytest.fixture
def sample_story_arc_events():
    """Create sample StoryArc events"""
    return [
        {
            "event_id": "evt_001",
            "entity": "Sarah",
            "event_date": date(2024, 5, 5),
            "event_type": "meeting",
            "description": "First meeting at coffee shop"
        },
        {
            "event_id": "evt_002",
            "entity": "Sarah",
            "event_date": date(2024, 5, 10),
            "event_type": "activity",
            "description": "Hiking trip together"
        },
        {
            "event_id": "evt_003",
            "entity": "Tom",
            "event_date": date(2024, 5, 4),
            "event_type": "birthday",
            "description": "Birthday celebration"
        },
    ]


@pytest.fixture
def sample_kg_relations():
    """Create sample knowledge graph relations"""
    return [
        {"source": "Sarah", "relation": "likes", "target": "hiking"},
        {"source": "Sarah", "relation": "works_at", "target": "Tech Company"},
        {"source": "Tom", "relation": "friend_of", "target": "Sarah"},
        {"source": "User", "relation": "met", "target": "Sarah"},
    ]


# ============================================================================
# Coordinator Fixtures
# ============================================================================

@pytest.fixture
def minimal_coordinator():
    """Create a minimal coordinator for unit testing"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

        coordinator = BrainInspiredCoordinator(
            enable_persistence=False,
            enable_background_processes=False
        )
        return coordinator


@pytest.fixture
async def initialized_coordinator(minimal_coordinator):
    """Create an initialized coordinator"""
    await minimal_coordinator.initialize()
    yield minimal_coordinator
    await minimal_coordinator.shutdown()


# ============================================================================
# Temporary Data Directory
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure"""
    data_dir = tmp_path / "data"
    (data_dir / "state").mkdir(parents=True)
    (data_dir / "memory").mkdir(parents=True)
    (data_dir / "cache").mkdir(parents=True)

    return data_dir


@pytest.fixture
def mock_paths(temp_data_dir):
    """Mock BMAMPaths to use temporary directory"""
    with patch('src.utils.paths.BMAMPaths.DATA_DIR', temp_data_dir):
        with patch('src.utils.paths.BMAMPaths.STATE_DIR', temp_data_dir / "state"):
            with patch('src.utils.paths.BMAMPaths.MEMORY_DIR', temp_data_dir / "memory"):
                yield temp_data_dir


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require real API access"
    )


# ============================================================================
# Skip Conditions
# ============================================================================

@pytest.fixture
def skip_without_api_key():
    """Skip test if no real API key is available"""
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key or api_key == 'test-key-for-testing':
        pytest.skip("Real OpenAI API key required")


# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Any cleanup code here
    pass
