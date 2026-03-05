"""Asynchronous BMAM client (httpx.AsyncClient)."""

import json
from typing import Any, Dict

import httpx

from bmam_client.exceptions import (
    AuthError,
    BMAMError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from bmam_client.models import (
    ArchiveResult,
    BrainRetrieveResult,
    FeedbackResult,
    HealthStatus,
    Memory,
    MemoryList,
    ProcessResult,
    SearchResults,
    SystemStats,
)


class AsyncBMAMClient:
    """Async Python client for the BMAM Memory Middleware API.

    Example::

        async with AsyncBMAMClient("http://localhost:8100") as client:
            await client.add(content="I love hiking", user_id="u1")
            results = await client.search("outdoor", user_id="u1")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8100",
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise TimeoutError(str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ConnectionError(str(exc)) from exc

        if resp.status_code == 401:
            raise AuthError()
        if resp.status_code == 404:
            detail = "Not found"
            try:
                detail = resp.json().get("detail", detail)
            except (json.JSONDecodeError, ValueError):
                pass
            raise NotFoundError(detail)
        if resp.status_code == 422:
            detail = "Validation error"
            try:
                detail = resp.json().get("detail", detail)
            except (json.JSONDecodeError, ValueError):
                pass
            raise ValidationError(str(detail))
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError(
                retry_after=float(retry_after) if retry_after else None
            )
        if resp.status_code >= 500:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except (json.JSONDecodeError, ValueError):
                pass
            raise ServerError(str(detail), status_code=resp.status_code)
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except (json.JSONDecodeError, ValueError):
                pass
            raise BMAMError(str(detail), status_code=resp.status_code)
        return resp.json()

    # ------------------------------------------------------------------
    # Mem0-compatible interface
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        content: str | None = None,
        messages: list[dict] | None = None,
        user_id: str = "default",
        memory_type: str = "episodic",
        importance: float = 0.5,
        metadata: dict | None = None,
    ) -> str:
        body: Dict[str, Any] = {"user_id": user_id, "memory_type": memory_type, "importance": importance}
        if content:
            body["content"] = content
        if messages:
            body["messages"] = messages
        if metadata:
            body["metadata"] = metadata
        data = await self._request("POST", "/v1/memories/", json=body)
        return data["id"]

    async def search(
        self,
        query: str,
        *,
        user_id: str = "default",
        limit: int = 10,
        use_brain_retrieval: bool = False,
    ) -> SearchResults:
        data = await self._request(
            "POST",
            "/v1/memories/search/",
            json={
                "query": query,
                "user_id": user_id,
                "limit": limit,
                "use_brain_retrieval": use_brain_retrieval,
            },
        )
        return SearchResults(**data)

    async def get_all(
        self, *, user_id: str = "default", page: int = 1, page_size: int = 50
    ) -> MemoryList:
        data = await self._request(
            "GET",
            "/v1/memories/",
            params={"user_id": user_id, "page": page, "page_size": page_size},
        )
        return MemoryList(**data)

    async def get(self, memory_id: str) -> Memory:
        data = await self._request("GET", f"/v1/memories/{memory_id}")
        return Memory(**data)

    async def update(self, memory_id: str, *, data: str | None = None, **kwargs) -> dict:
        body: Dict[str, Any] = {}
        if data is not None:
            body["content"] = data
        body.update(kwargs)
        return await self._request("PUT", f"/v1/memories/{memory_id}", json=body)

    async def delete(self, memory_id: str) -> dict:
        return await self._request("DELETE", f"/v1/memories/{memory_id}")

    # ------------------------------------------------------------------
    # BMAM-exclusive interface
    # ------------------------------------------------------------------

    async def brain_retrieve(
        self,
        query: str,
        *,
        k: int = 10,
        activation_plan: dict | None = None,
        force_slow_path: bool = False,
    ) -> BrainRetrieveResult:
        body: Dict[str, Any] = {"query": query, "k": k, "force_slow_path": force_slow_path}
        if activation_plan:
            body["activation_plan"] = activation_plan
        data = await self._request("POST", "/v1/brain/retrieve/", json=body)
        return BrainRetrieveResult(**data)

    async def process(
        self,
        input_text: str,
        *,
        user_id: str = "default",
        context: dict | None = None,
    ) -> ProcessResult:
        body: Dict[str, Any] = {"input": input_text, "user_id": user_id}
        if context:
            body["context"] = context
        data = await self._request("POST", "/v1/brain/process/", json=body)
        return ProcessResult(**data)

    async def consolidate(
        self, *, strategy: str = "batch", evaluation_mode: bool = False
    ) -> dict:
        return await self._request(
            "POST",
            "/v1/brain/consolidate/",
            json={"strategy": strategy, "evaluation_mode": evaluation_mode},
        )

    async def forget(
        self, *, region: str | None = None, capacity_threshold: float = 0.8
    ) -> dict:
        body: Dict[str, Any] = {"capacity_threshold": capacity_threshold}
        if region:
            body["region"] = region
        return await self._request("POST", "/v1/brain/forget/", json=body)

    async def feedback(
        self,
        *,
        query_type: str,
        reward_signal: float,
        query: str | None = None,
        response: str | None = None,
    ) -> FeedbackResult:
        body: Dict[str, Any] = {
            "query_type": query_type,
            "reward_signal": reward_signal,
        }
        if query:
            body["query"] = query
        if response:
            body["response"] = response
        data = await self._request("POST", "/v1/brain/feedback/", json=body)
        return FeedbackResult(**data)

    async def get_preferences(
        self, query: str, *, user_id: str | None = None, k: int = 5
    ) -> list[str]:
        params: Dict[str, Any] = {"query": query, "k": k}
        if user_id:
            params["user_id"] = user_id
        data = await self._request("GET", "/v1/brain/preferences/", params=params)
        return data.get("preferences", [])

    async def export_archive(
        self,
        archive_name: str,
        *,
        description: str = "",
        tags: list[str] | None = None,
    ) -> ArchiveResult:
        body: Dict[str, Any] = {"archive_name": archive_name, "description": description}
        if tags:
            body["tags"] = tags
        data = await self._request("POST", "/v1/archives/export/", json=body)
        return ArchiveResult(**data)

    async def import_archive(
        self, archive_path: str, *, validate: bool = True, force: bool = False
    ) -> ArchiveResult:
        data = await self._request(
            "POST",
            "/v1/archives/import/",
            json={
                "archive_path": archive_path,
                "validate_archive": validate,
                "force": force,
            },
        )
        return ArchiveResult(**data)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    async def health(self) -> HealthStatus:
        data = await self._request("GET", "/v1/system/health")
        return HealthStatus(**data)

    async def stats(self) -> SystemStats:
        data = await self._request("GET", "/v1/system/stats")
        return SystemStats(**data)
