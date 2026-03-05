"""System health and statistics endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import verify_api_key
from src.api.dependencies import get_adapter
from src.api.middleware_adapter import MiddlewareAdapter
from src.api.models.system import HealthResponse, SystemStatsResponse

router = APIRouter(
    prefix="/v1/system",
    tags=["system"],
    dependencies=[Depends(verify_api_key)],
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
)
async def health(
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Returns feature-level health status of the brain-inspired system."""
    try:
        return adapter.health()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Memory system statistics",
)
async def stats(
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Returns memory counts and database info."""
    try:
        return await adapter.stats()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
