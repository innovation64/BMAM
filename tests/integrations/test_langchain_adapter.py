"""Tests for the LangChain adapter — uses mock BMAM server."""

import importlib.util
import sys
from pathlib import Path

import pytest

_bmam_root = Path(__file__).resolve().parents[2]
_sdk_root = _bmam_root / "sdk"
for p in (_bmam_root, _sdk_root):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import set_adapter
from src.api.middleware_adapter import MiddlewareAdapter

# Load mock builder
_conftest_path = _bmam_root / "tests" / "api" / "conftest.py"
_spec = importlib.util.spec_from_file_location("_api_conftest", _conftest_path)
_api_conftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_api_conftest)
_make_mock_coordinator = _api_conftest._make_mock_coordinator

# Check if langchain-core is available
langchain_available = True
try:
    import langchain_core  # noqa: F401
except ImportError:
    langchain_available = False


@pytest.fixture()
def mock_server():
    """Start a mock BMAM API server and return a TestClient."""
    coord = _make_mock_coordinator()
    app = create_app()
    set_adapter(MiddlewareAdapter(coord))
    return TestClient(app), coord


@pytest.mark.skipif(
    not langchain_available, reason="langchain-core not installed"
)
class TestBMAMMemory:
    def test_load_memory_variables(self, mock_server, monkeypatch):
        test_client, _ = mock_server
        from src.integrations.langchain_adapter import BMAMMemory

        memory = BMAMMemory(
            bmam_url="http://testserver", user_id="test"
        )
        # Patch the client: create a BMAMClient and swap its httpx client
        from bmam_client import BMAMClient
        bmam_client = BMAMClient.__new__(BMAMClient)
        bmam_client._client = test_client
        object.__setattr__(memory, "_bmam_client", bmam_client)

        result = memory.load_memory_variables({"input": "hiking"})
        assert "history" in result
        assert "hiking" in result["history"]

    def test_save_context(self, mock_server, monkeypatch):
        test_client, coord = mock_server
        from src.integrations.langchain_adapter import BMAMMemory

        memory = BMAMMemory(
            bmam_url="http://testserver", user_id="test"
        )
        from bmam_client import BMAMClient
        bmam_client = BMAMClient.__new__(BMAMClient)
        bmam_client._client = test_client
        object.__setattr__(memory, "_bmam_client", bmam_client)

        memory.save_context(
            {"input": "I like mountains"},
            {"output": "That's great!"},
        )
        # Verify store was called
        assert coord.store_memory_with_timestamp.call_count >= 1


@pytest.mark.skipif(
    not langchain_available, reason="langchain-core not installed"
)
class TestBMAMChatMessageHistory:
    def test_messages_property(self, mock_server):
        test_client, _ = mock_server
        from src.integrations.langchain_adapter import BMAMChatMessageHistory

        history = BMAMChatMessageHistory(
            bmam_url="http://testserver", user_id="test"
        )
        history._client._client = test_client

        msgs = history.messages
        assert isinstance(msgs, list)

    def test_add_message(self, mock_server):
        test_client, coord = mock_server
        from langchain_core.messages import HumanMessage
        from src.integrations.langchain_adapter import BMAMChatMessageHistory

        history = BMAMChatMessageHistory(
            bmam_url="http://testserver", user_id="test"
        )
        history._client._client = test_client

        history.add_message(HumanMessage(content="hello"))
        assert coord.store_memory_with_timestamp.call_count >= 1
