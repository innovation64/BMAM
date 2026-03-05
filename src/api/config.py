"""API configuration — loaded from environment / .env."""

import logging
import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class APISettings(BaseSettings):
    """Settings for the BMAM REST API server."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = Field(default="0.0.0.0", alias="BMAM_API_HOST")
    port: int = Field(default=8100, alias="BMAM_API_PORT")
    cors_origins: List[str] = Field(
        default=["*"], alias="BMAM_CORS_ORIGINS"
    )
    api_key: str = Field(default="", alias="BMAM_API_KEY")
    debug: bool = Field(default=False, alias="BMAM_API_DEBUG")


_settings: APISettings | None = None


def get_api_settings() -> APISettings:
    global _settings
    if _settings is None:
        _settings = APISettings()
        if not _settings.api_key:
            logger.warning(
                "BMAM_API_KEY is not set — API endpoints are unprotected. "
                "Set BMAM_API_KEY in .env for production use."
            )
    return _settings
