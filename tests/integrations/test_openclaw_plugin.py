"""Tests for the OpenClaw/agent plugin — uses mock BMAM server."""

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

_conftest_path = _bmam_root / "tests" / "api" / "conftest.py"
_spec = importlib.util.spec_from_file_location("_api_conftest", _conftest_path)
_api_conftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_api_conftest)
_make_mock_coordinator = _api_conftest._make_mock_coordinator


@pytest.fixture()
def skill():
    """BMAMMemorySkill backed by a mock server."""
    coord = _make_mock_coordinator()
    app = create_app()
    set_adapter(MiddlewareAdapter(coord))
    test_client = TestClient(app)

    from src.integrations.openclaw_plugin import BMAMMemorySkill

    s = BMAMMemorySkill(bmam_url="http://testserver", user_id="test")
    s._client._client = test_client
    return s, coord


class TestRecall:
    def test_recall(self, skill):
        s, _ = skill
        results = s.recall("hiking", k=3)
        assert isinstance(results, list)
        assert len(results) >= 1
        assert "content" in results[0]


class TestRemember:
    def test_remember(self, skill):
        s, _ = skill
        mid = s.remember("I climbed Everest", importance=0.9)
        assert isinstance(mid, str)


class TestReflect:
    def test_reflect(self, skill):
        s, _ = skill
        result = s.reflect()
        assert isinstance(result, dict)


class TestToolDefinitions:
    def test_get_tools(self, skill):
        s, _ = skill
        tools = s.get_tools()
        assert len(tools) == 5
        names = [t["name"] for t in tools]
        assert "bmam_recall" in names
        assert "bmam_remember" in names
        assert "bmam_reflect" in names
        assert "bmam_transfer" in names
        assert "bmam_export" in names

    def test_execute_tool_recall(self, skill):
        s, _ = skill
        result = s.execute_tool("bmam_recall", query="hiking", k=2)
        assert isinstance(result, list)

    def test_execute_tool_remember(self, skill):
        s, _ = skill
        result = s.execute_tool("bmam_remember", content="test fact")
        assert isinstance(result, str)

    def test_execute_unknown_tool(self, skill):
        s, _ = skill
        with pytest.raises(ValueError, match="Unknown tool"):
            s.execute_tool("bmam_nonexistent")
