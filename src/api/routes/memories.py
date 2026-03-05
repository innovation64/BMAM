"""Memory CRUD endpoints — Mem0-compatible ``add / get / get_all / update / delete``."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from src.api.auth import verify_api_key
from src.api.dependencies import get_adapter
from src.api.middleware_adapter import MiddlewareAdapter
from src.api.models.memory import (
    MemoryCreateRequest,
    MemoryCreateResponse,
    MemoryListResponse,
    MemoryResponse,
    MemoryUpdateRequest,
)

router = APIRouter(
    prefix="/v1/memories",
    tags=["memories"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/",
    response_model=MemoryCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a new memory",
)
async def create_memory(
    body: MemoryCreateRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Mem0 ``add()`` equivalent.

    Accepts either ``messages`` (Mem0 format) or direct ``content``.
    """
    try:
        return await adapter.add(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.get(
    "/",
    response_model=MemoryListResponse,
    summary="List all memories",
)
async def list_memories(
    user_id: str = Query(default="default"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Mem0 ``get_all()`` equivalent with pagination."""
    return await adapter.get_all(
        user_id=user_id, page=page, page_size=page_size
    )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a single memory",
)
async def get_memory(
    memory_id: str,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Mem0 ``get()`` equivalent."""
    result = await adapter.get(memory_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )
    return result


@router.put(
    "/{memory_id}",
    response_model=dict,
    summary="Update a memory",
)
async def update_memory(
    memory_id: str,
    body: MemoryUpdateRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Mem0 ``update()`` equivalent."""
    ok = await adapter.update(memory_id, body)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )
    return {"message": "Memory updated", "id": memory_id}


@router.delete(
    "/{memory_id}",
    response_model=dict,
    summary="Delete a memory",
)
async def delete_memory(
    memory_id: str,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Mem0 ``delete()`` equivalent (soft delete)."""
    ok = await adapter.delete(memory_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )
    return {"message": "Memory deleted", "id": memory_id}
