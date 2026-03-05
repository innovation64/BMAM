"""LangChain integration — drop-in BaseMemory backed by BMAM's 5-brain-region retrieval.

Usage with LangChain::

    from src.integrations.langchain_adapter import BMAMMemory, BMAMChatMessageHistory

    memory = BMAMMemory(bmam_url="http://localhost:8100", user_id="demo")
    chain = ConversationChain(llm=llm, memory=memory)
    chain.run("What do you know about me?")

Requires: ``pip install langchain-core``
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.memory import BaseMemory
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
except ImportError:
    raise ImportError(
        "langchain-core is required for BMAMMemory. "
        "Install it with: pip install langchain-core"
    )

_sdk_root = Path(__file__).resolve().parents[1] / ".." / "sdk"
if str(_sdk_root) not in sys.path:
    sys.path.insert(0, str(_sdk_root))

from bmam_client import BMAMClient


class BMAMMemory(BaseMemory):
    """LangChain ``BaseMemory`` that uses BMAM for retrieval and storage.

    By default, retrieval uses ``smart_retrieve`` (semantic search).
    Set ``use_brain_retrieval=True`` to enable the full 5-brain-region
    distributed retrieval pipeline.
    """

    bmam_url: str = "http://localhost:8100"
    api_key: Optional[str] = None
    user_id: str = "default"
    memory_key: str = "history"
    input_key: str = "input"
    use_brain_retrieval: bool = False
    k: int = 5

    # Store client outside of Pydantic model fields
    _bmam_client: Optional[Any] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "_bmam_client", None)

    @property
    def client(self) -> BMAMClient:
        if self._bmam_client is None:
            object.__setattr__(
                self,
                "_bmam_client",
                BMAMClient(base_url=self.bmam_url, api_key=self.api_key),
            )
        return self._bmam_client

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(
        self, inputs: Dict[str, Any]
    ) -> Dict[str, str]:
        query = inputs.get(self.input_key, "")
        if not query:
            return {self.memory_key: ""}
        results = self.client.search(
            query,
            user_id=self.user_id,
            limit=self.k,
            use_brain_retrieval=self.use_brain_retrieval,
        )
        context = "\n".join(r.content for r in results.results)
        return {self.memory_key: context}

    def save_context(
        self, inputs: Dict[str, Any], outputs: Dict[str, str]
    ) -> None:
        user_input = inputs.get(self.input_key, "")
        ai_output = next(iter(outputs.values()), "")
        if user_input:
            self.client.add(
                content=f"user: {user_input}",
                user_id=self.user_id,
            )
        if ai_output:
            self.client.add(
                content=f"assistant: {ai_output}",
                user_id=self.user_id,
            )

    def clear(self) -> None:
        pass


class BMAMChatMessageHistory(BaseChatMessageHistory):
    """LangChain chat message history backed by BMAM memory.

    Provides ``messages`` property and ``add_message()`` for frameworks
    that consume ``BaseChatMessageHistory`` (e.g. ``RunnableWithMessageHistory``).
    """

    def __init__(
        self,
        bmam_url: str = "http://localhost:8100",
        user_id: str = "default",
        api_key: str | None = None,
    ):
        self._user_id = user_id
        self._client = BMAMClient(base_url=bmam_url, api_key=api_key)

    @property
    def messages(self) -> List[BaseMessage]:
        mem_list = self._client.get_all(user_id=self._user_id)
        msgs: List[BaseMessage] = []
        for m in mem_list.memories:
            content = m.content
            if content.startswith("user: "):
                msgs.append(HumanMessage(content=content[6:]))
            elif content.startswith("assistant: "):
                msgs.append(AIMessage(content=content[11:]))
            else:
                msgs.append(HumanMessage(content=content))
        return msgs

    def add_message(self, message: BaseMessage) -> None:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        self._client.add(
            content=f"{role}: {message.content}",
            user_id=self._user_id,
        )

    def clear(self) -> None:
        pass
