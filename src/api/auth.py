"""Lightweight API-key authentication."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.api.config import get_api_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """Validate the API key if one is configured.

    When ``BMAM_API_KEY`` is empty (default), authentication is disabled
    and all requests are allowed through.
    """
    settings = get_api_settings()
    if not settings.api_key:
        return None
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
