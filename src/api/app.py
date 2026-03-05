"""FastAPI application factory with lifespan-managed coordinator."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_api_settings
from src.api.dependencies import set_adapter, set_voice_service
from src.api.middleware_adapter import MiddlewareAdapter
from src.api.routes import archives, brain, memories, search, system, websocket

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the BrainInspiredCoordinator and VoiceService at startup."""
    logger.info("BMAM API starting — initialising coordinator ...")
    voice_service = None
    try:
        from src.coordination.brain_coordinator_refactored import (
            BrainInspiredCoordinator,
        )

        coordinator = BrainInspiredCoordinator()
        adapter = MiddlewareAdapter(coordinator)
        set_adapter(adapter)

        # Try to initialise VoiceService (optional — fails gracefully)
        try:
            from src.services.voice_config import VoiceConfig
            from src.services.voice_service import VoiceService

            config = VoiceConfig.from_env()
            voice_service = VoiceService(config)
            set_voice_service(voice_service)
            logger.info("VoiceService initialised (tts=%s)", config.tts_backend.value)
        except Exception as ve:
            logger.warning("VoiceService not available: %s", ve)
            set_voice_service(None)

        logger.info("BMAM API ready")
    except Exception as exc:
        logger.critical("Failed to initialise coordinator: %s", exc, exc_info=True)
        raise
    yield
    # Shutdown
    if voice_service:
        await voice_service.close()
    logger.info("BMAM API shutting down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_api_settings()

    app = FastAPI(
        title="BMAM Memory Middleware",
        description=(
            "Brain-inspired Multi-Agent Memory system — "
            "Mem0-compatible REST API with 5-brain-region distributed "
            "retrieval, StoryArc timeline reasoning, KG multi-hop, "
            "and soul transfer."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — tighten for production via BMAM_CORS_ORIGINS env var
    origins = settings.cors_origins
    allow_credentials = origins != ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )

    app.include_router(memories.router)
    app.include_router(search.router)
    app.include_router(brain.router)
    app.include_router(system.router)
    app.include_router(archives.router)
    app.include_router(websocket.router)

    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "BMAM Memory Middleware",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app
