#!/usr/bin/env python3
"""BMAM Memory Middleware — uvicorn entry point.

Usage:
    python run_api.py                          # defaults: 0.0.0.0:8100
    BMAM_API_PORT=9000 python run_api.py       # custom port
    BMAM_API_KEY=secret python run_api.py      # enable auth
"""

import sys
from pathlib import Path

# Ensure project root is importable
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import uvicorn

from src.api.app import create_app
from src.api.config import get_api_settings


def main():
    settings = get_api_settings()
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
