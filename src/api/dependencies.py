"""FastAPI dependency-injection providers."""

from typing import Optional

from src.api.middleware_adapter import MiddlewareAdapter

_adapter: MiddlewareAdapter | None = None
_voice_service = None


def set_adapter(adapter: MiddlewareAdapter) -> None:
    """Called once at startup from the lifespan handler."""
    global _adapter
    _adapter = adapter


def get_adapter() -> MiddlewareAdapter:
    """FastAPI ``Depends`` provider — returns the shared adapter instance."""
    if _adapter is None:
        raise RuntimeError(
            "MiddlewareAdapter not initialised. "
            "Did the application start correctly?"
        )
    return _adapter


def set_voice_service(service) -> None:
    """Called at startup to register the VoiceService singleton."""
    global _voice_service
    _voice_service = service


def get_voice_service():
    """Returns the shared VoiceService instance, or None if not configured."""
    return _voice_service
