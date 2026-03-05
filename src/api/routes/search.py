"""Search endpoint — semantic / brain-distributed memory retrieval."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import verify_api_key
from src.api.dependencies import get_adapter
from src.api.middleware_adapter import MiddlewareAdapter
from src.api.models.search import SearchRequest, SearchResponse

router = APIRouter(
    prefix="/v1/memories",
    tags=["search"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/search/",
    response_model=SearchResponse,
    summary="Search memories",
)
async def search_memories(
    body: SearchRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Mem0 ``search()`` equivalent.

    Set ``use_brain_retrieval: true`` to enable the full 5-brain-region
    distributed retrieval pipeline (BMAM exclusive feature).
    """
    try:
        return await adapter.search(body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
