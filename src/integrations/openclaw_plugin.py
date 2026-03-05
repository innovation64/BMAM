"""OpenClaw plugin — provides recall / remember / reflect tools for any agent framework.

Usage::

    from src.integrations.openclaw_plugin import BMAMMemorySkill

    skill = BMAMMemorySkill(bmam_url="http://localhost:8100")
    tools = skill.get_tools()
    result = skill.execute_tool("recall", query="outdoor hobbies", k=5)

This plugin follows a generic tool-definition pattern that works with
OpenClaw, AutoGen, CrewAI, and any framework that accepts tool dicts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_sdk_root = Path(__file__).resolve().parents[1] / ".." / "sdk"
if str(_sdk_root) not in sys.path:
    sys.path.insert(0, str(_sdk_root))

from bmam_client import BMAMClient


class BMAMMemorySkill:
    """Agent skill that exposes BMAM memory as callable tools.

    Provides five core capabilities:
    - **recall**: Retrieve relevant memories (pre-action hook)
    - **remember**: Store new information (post-action hook)
    - **reflect**: Trigger memory consolidation (periodic)
    - **transfer**: Import another agent's memory archive
    - **export**: Export own memory for transfer
    """

    name: str = "bmam_memory"

    def __init__(
        self,
        bmam_url: str = "http://localhost:8100",
        user_id: str = "default",
        api_key: str | None = None,
    ):
        self.user_id = user_id
        self._client = BMAMClient(
            base_url=bmam_url, api_key=api_key
        )

    # ------------------------------------------------------------------
    # Core tools
    # ------------------------------------------------------------------

    def recall(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve memories relevant to a query."""
        results = self._client.search(
            query, user_id=self.user_id, limit=k, use_brain_retrieval=True
        )
        return [
            {
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "type": r.memory_type,
            }
            for r in results.results
        ]

    def remember(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        """Store a new memory. Returns the memory ID."""
        return self._client.add(
            content=content,
            user_id=self.user_id,
            importance=importance,
            metadata=metadata,
        )

    def reflect(self) -> Dict[str, Any]:
        """Trigger memory consolidation (analogous to a sleep cycle)."""
        return self._client.consolidate()

    def transfer(self, archive_path: str) -> Dict[str, Any]:
        """Import another agent's memory archive."""
        result = self._client.import_archive(archive_path)
        return {"success": result.success, "message": result.message}

    def export(self, archive_name: str) -> Dict[str, Any]:
        """Export this agent's memory as a portable archive."""
        result = self._client.export_archive(archive_name)
        return {"success": result.success, "details": result.details}

    # ------------------------------------------------------------------
    # Tool definitions (framework-agnostic)
    # ------------------------------------------------------------------

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions compatible with OpenClaw / AutoGen / CrewAI."""
        return [
            {
                "name": "bmam_recall",
                "description": (
                    "Retrieve relevant memories from the agent's brain-inspired "
                    "memory system. Use before answering questions that may "
                    "require past context."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in memory",
                        },
                        "k": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "bmam_remember",
                "description": (
                    "Store important information in long-term memory. "
                    "Use after learning new facts, user preferences, or events."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "What to remember",
                        },
                        "importance": {
                            "type": "number",
                            "description": "Importance 0-1",
                            "default": 0.5,
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "bmam_reflect",
                "description": (
                    "Trigger memory consolidation to strengthen important "
                    "memories and prune irrelevant ones. Use periodically."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "bmam_transfer",
                "description": "Import memories from another agent's archive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "archive_path": {
                            "type": "string",
                            "description": "Path to the .bma archive file",
                        },
                    },
                    "required": ["archive_path"],
                },
            },
            {
                "name": "bmam_export",
                "description": "Export this agent's memories as a portable archive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "archive_name": {
                            "type": "string",
                            "description": "Name for the archive",
                        },
                    },
                    "required": ["archive_name"],
                },
            },
        ]

    def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a tool by name. Routes to the corresponding method."""
        dispatch = {
            "bmam_recall": lambda **kw: self.recall(**kw),
            "bmam_remember": lambda **kw: self.remember(**kw),
            "bmam_reflect": lambda **kw: self.reflect(),
            "bmam_transfer": lambda **kw: self.transfer(**kw),
            "bmam_export": lambda **kw: self.export(**kw),
        }
        handler = dispatch.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        return handler(**kwargs)
