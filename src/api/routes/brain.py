"""Brain-specific endpoints — BMAM-exclusive capabilities."""

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.auth import verify_api_key
from src.api.dependencies import get_adapter
from src.api.middleware_adapter import MiddlewareAdapter
from src.api.models.brain import (
    BrainRetrieveRequest,
    BrainRetrieveResponse,
    ConsolidateRequest,
    FeedbackRequest,
    FeedbackResponse,
    ForgetRequest,
    PreferencesResponse,
    ProcessInputRequest,
    ProcessInputResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/brain",
    tags=["brain"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/retrieve/",
    response_model=BrainRetrieveResponse,
    summary="5-brain-region distributed retrieval",
)
async def brain_retrieve(
    body: BrainRetrieveRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Activate all 5 brain regions for collaborative memory retrieval."""
    try:
        return await adapter.brain_retrieve(body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/process/",
    response_model=ProcessInputResponse,
    summary="Full brain processing pipeline",
)
async def process_input(
    body: ProcessInputRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Run the complete brain-inspired processing pipeline on user input."""
    try:
        return await adapter.process_input(body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/consolidate/",
    summary="Trigger memory consolidation",
)
async def consolidate(
    body: ConsolidateRequest | None = None,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Trigger memory consolidation (analogous to sleep-based replay)."""
    try:
        return await adapter.consolidate(body or ConsolidateRequest())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/forget/",
    summary="Trigger memory forgetting",
)
async def forget(
    body: ForgetRequest | None = None,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Trigger capacity-based memory forgetting / pruning."""
    try:
        return await adapter.forget(body or ForgetRequest())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/feedback/",
    response_model=FeedbackResponse,
    summary="Submit learning feedback",
)
async def feedback(
    body: FeedbackRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Submit reinforcement learning feedback for query routing weights."""
    try:
        return await adapter.apply_feedback(body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/preferences/",
    response_model=PreferencesResponse,
    summary="Get user preferences",
)
async def get_preferences(
    query: str = Query(..., min_length=1),
    user_id: str | None = Query(default=None),
    k: int = Query(default=5, ge=1, le=50),
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Retrieve user preferences relevant to a query."""
    try:
        return await adapter.get_preferences(query=query, user_id=user_id, k=k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/health/components",
    summary="Get component health status",
)
async def get_component_health(
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Get health status of all BMAM components with criticality levels."""
    try:
        coordinator = adapter.coordinator
    except Exception:
        raise HTTPException(
            status_code=503, detail="Coordinator not initialized"
        )
    if coordinator is None:
        raise HTTPException(
            status_code=503, detail="Coordinator not initialized"
        )
    return coordinator.get_component_health()


@router.post("/chat/stream", summary="Stream chat response via SSE")
async def chat_stream(
    body: ProcessInputRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Stream processing response via Server-Sent Events.

    Phases pushed:
    1. ``query_analysis`` -- Initial query analysis
    2. ``retrieval``      -- Memory retrieval results
    3. ``generation``     -- Final response generation (chunked)
    4. ``done``           -- Completion with metadata
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        coordinator = adapter.coordinator
        if coordinator is None:
            yield _sse({"phase": "error", "error": "Coordinator not initialized"})
            return

        user_input = body.input
        context = body.context or {}
        context["user_id"] = body.user_id or "default"
        context["streaming"] = True

        # Phase 1: Query Analysis
        yield _sse({
            "phase": "query_analysis",
            "status": "started",
            "message": "Analyzing query...",
        })

        try:
            # Run the full brain processing pipeline
            result = await coordinator.process_user_input(
                user_input=user_input,
                context=context,
            )

            # Phase 2: Retrieval info
            memories_count = (
                len(result.memories_retrieved)
                if result.memories_retrieved
                else 0
            )
            yield _sse({
                "phase": "retrieval",
                "status": "completed",
                "memories_found": memories_count,
                "agents_involved": result.agents_involved,
            })

            await asyncio.sleep(0)  # yield control

            # Phase 3: Generation — stream the response in chunks
            response_text = result.response
            chunk_size = 50  # characters per chunk
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i : i + chunk_size]
                yield _sse({
                    "phase": "generation",
                    "status": "streaming",
                    "chunk": chunk,
                })
                await asyncio.sleep(0.01)  # small delay for streaming effect

            # Phase 4: Done — final event with metadata
            yield _sse({
                "phase": "done",
                "success": result.success,
                "processing_time": result.processing_time,
                "memory_stored": result.memory_stored,
            })

        except Exception as exc:
            logger.error("chat_stream failed: %s", exc, exc_info=True)
            yield _sse({"phase": "error", "error": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    """Format a dict as a single SSE ``data:`` frame."""
    return f"data: {json.dumps(data)}\n\n"
