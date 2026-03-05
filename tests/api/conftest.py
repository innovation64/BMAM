"""Shared fixtures for API tests — uses a mock coordinator."""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.api.app import create_app
from src.api.dependencies import set_adapter
from src.api.middleware_adapter import MiddlewareAdapter


# ---------------------------------------------------------------------------
# Lightweight stand-ins that mirror coordinator/memory_system shapes
# ---------------------------------------------------------------------------

@dataclass
class FakeMemoryItem:
    id: str = "mem-001"
    content: str = "I love hiking"
    memory_type: str = "episodic"
    importance: float = 0.7
    brain_region: str = "hippocampus"
    consolidation_level: int = 1
    access_frequency: int = 3
    timestamp: datetime = field(default_factory=datetime.now)
    emotion_tags: List[str] = field(default_factory=list)
    context_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeBrainRetrievalResult:
    memories: List[Dict[str, Any]] = field(default_factory=list)
    path_type: str = "fast"
    iterations: int = 1
    gaps_detected: List[Dict] = field(default_factory=list)
    confidence: float = 0.85
    retrieval_time_ms: float = 42.0
    debug_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeProcessingResult:
    response: str = "Hello! I remember you love hiking."
    routing_decision: Dict[str, Any] = field(default_factory=dict)
    agents_involved: List[str] = field(
        default_factory=lambda: ["hippocampus", "prefrontal"]
    )
    memories_retrieved: List[Dict[str, Any]] = field(default_factory=list)
    memory_stored: bool = True
    processing_time: float = 0.5
    agent_logs: Dict[str, List[Dict]] = field(default_factory=dict)
    insights: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    activation_trace: Optional[List[Dict[str, Any]]] = None
    memories_used: Optional[List[str]] = None


def _make_mock_coordinator():
    """Build a mock that quacks like BrainInspiredCoordinator."""
    coord = MagicMock()

    # --- Memory system & db_manager ---
    db_manager = MagicMock()
    db_manager.load_memory.return_value = FakeMemoryItem()
    db_manager.get_all_memories.return_value = [
        {
            "id": "mem-001",
            "content": "I love hiking",
            "memory_type": "episodic",
            "importance": 0.7,
            "brain_region": "hippocampus",
            "consolidation_level": 1,
            "access_frequency": 3,
            "timestamp": datetime.now().isoformat(),
            "emotion_tags": [],
            "context_tags": [],
            "metadata": {},
        }
    ]
    db_manager.get_memory_stats.return_value = {
        "total_memories": 42,
        "episodic_memories": 30,
        "semantic_memories": 12,
        "database_url": "sqlite:///test.db",
    }

    mem_sys = MagicMock()
    mem_sys.db_manager = db_manager
    mem_sys.update_memory = AsyncMock(return_value=True)
    mem_sys.delete_memory = AsyncMock(return_value=True)
    coord.memory_system = mem_sys

    # --- store ---
    coord.store_memory_with_timestamp = AsyncMock(
        return_value={"memory_id": "mem-new-001"}
    )

    # --- retrieve ---
    coord.smart_retrieve = AsyncMock(
        return_value=[
            {
                "id": "mem-001",
                "content": "I love hiking",
                "score": 0.92,
                "memory_type": "episodic",
                "brain_region": "hippocampus",
            }
        ]
    )
    coord.brain_retrieve = AsyncMock(
        return_value=FakeBrainRetrievalResult(
            memories=[
                {
                    "id": "mem-001",
                    "content": "I love hiking",
                    "score": 0.92,
                }
            ]
        )
    )

    # --- process ---
    coord.process_user_input = AsyncMock(
        return_value=FakeProcessingResult()
    )

    # --- consolidation / forgetting ---
    coord.consolidate_memories = AsyncMock(
        return_value={"consolidated": 5}
    )
    coord.trigger_forgetting = AsyncMock(
        return_value={"memories_forgotten": 2}
    )

    # --- feedback ---
    coord.apply_feedback = AsyncMock(
        return_value={
            "status": "applied",
            "query_type": "temporal",
            "reward": 0.8,
            "weight_delta": 0.015,
        }
    )

    # --- preferences ---
    coord.get_user_preferences = AsyncMock(
        return_value=["hiking", "mountains", "coffee"]
    )

    # --- health ---
    coord.get_feature_health.return_value = {
        "features": {"background_memory": True, "metacognition": True},
        "healthy_count": 7,
        "total_count": 7,
        "degraded_features": [],
        "health_percentage": 100.0,
    }

    # --- archives ---
    coord.export_memory_archive.return_value = {"path": "/tmp/archive.bma"}
    coord.load_memory_archive.return_value = {"memories_loaded": 10}

    return coord


@pytest.fixture()
def mock_coordinator():
    return _make_mock_coordinator()


@pytest.fixture()
def client(mock_coordinator):
    """FastAPI TestClient with the mock coordinator wired in."""
    app = create_app()
    adapter = MiddlewareAdapter(mock_coordinator)
    set_adapter(adapter)
    return TestClient(app)
