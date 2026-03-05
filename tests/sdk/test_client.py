"""Tests for BMAMClient using httpx transport to the FastAPI TestClient."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Ensure both BMAM root and SDK are importable
_bmam_root = Path(__file__).resolve().parents[2]
_sdk_root = _bmam_root / "sdk"
for p in (_bmam_root, _sdk_root):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import httpx
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import set_adapter
from src.api.middleware_adapter import MiddlewareAdapter

# Load mock builder from API test conftest via path (avoids package import issues)
_conftest_path = _bmam_root / "tests" / "api" / "conftest.py"
_spec = importlib.util.spec_from_file_location("_api_conftest", _conftest_path)
_api_conftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_api_conftest)
_make_mock_coordinator = _api_conftest._make_mock_coordinator

from bmam_client import BMAMClient
from bmam_client.exceptions import NotFoundError
from bmam_client.models import SearchResults, BrainRetrieveResult, ProcessResult


@pytest.fixture()
def sdk_client():
    """BMAMClient backed by a mock coordinator via Starlette TestClient."""
    coord = _make_mock_coordinator()
    app = create_app()
    adapter = MiddlewareAdapter(coord)
    set_adapter(adapter)

    # Use Starlette's TestClient which wraps the ASGI app properly
    test_client = TestClient(app)
    # Wire the BMAMClient to use the TestClient's internal httpx client
    client = BMAMClient.__new__(BMAMClient)
    client._client = test_client
    yield client, coord
    test_client.close()


class TestAdd:
    def test_add_content(self, sdk_client):
        client, _ = sdk_client
        mid = client.add(content="I love hiking", user_id="test")
        assert mid == "mem-new-001"

    def test_add_messages(self, sdk_client):
        client, _ = sdk_client
        mid = client.add(
            messages=[{"role": "user", "content": "hiking is fun"}],
            user_id="test",
        )
        assert isinstance(mid, str)


class TestSearch:
    def test_semantic_search(self, sdk_client):
        client, _ = sdk_client
        results = client.search("outdoor", user_id="test")
        assert isinstance(results, SearchResults)
        assert results.total >= 1

    def test_brain_search(self, sdk_client):
        client, _ = sdk_client
        results = client.search(
            "outdoor", use_brain_retrieval=True
        )
        assert results.retrieval_mode == "brain_distributed"


class TestGetAll:
    def test_list(self, sdk_client):
        client, _ = sdk_client
        mem_list = client.get_all()
        assert mem_list.total == 1


class TestGet:
    def test_get_existing(self, sdk_client):
        client, _ = sdk_client
        mem = client.get("mem-001")
        assert mem.content == "I love hiking"

    def test_get_not_found(self, sdk_client):
        client, coord = sdk_client
        coord.memory_system.db_manager.load_memory.return_value = None
        set_adapter(MiddlewareAdapter(coord))
        with pytest.raises(NotFoundError):
            client.get("nonexistent")


class TestBrainRetrieve:
    def test_retrieve(self, sdk_client):
        client, _ = sdk_client
        result = client.brain_retrieve("What happened?")
        assert isinstance(result, BrainRetrieveResult)
        assert result.confidence > 0


class TestProcess:
    def test_process(self, sdk_client):
        client, _ = sdk_client
        result = client.process("Tell me about my hobbies")
        assert isinstance(result, ProcessResult)
        assert result.success


class TestFeedback:
    def test_feedback(self, sdk_client):
        client, _ = sdk_client
        result = client.feedback(
            query_type="temporal", reward_signal=0.8
        )
        assert result.status == "applied"


class TestSystem:
    def test_health(self, sdk_client):
        client, _ = sdk_client
        h = client.health()
        assert h.status == "healthy"

    def test_stats(self, sdk_client):
        client, _ = sdk_client
        s = client.stats()
        assert s.total_memories == 42
