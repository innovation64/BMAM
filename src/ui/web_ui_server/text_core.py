"""
Text Web UI Server Core
文本模式Web服务器核心 - 无Voice/Anime依赖
"""

import logging
from typing import Set

try:
    from aiohttp import web
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

from src.services.brain_service import BrainService

logger = logging.getLogger(__name__)


class TextUIServerCore:
    """Text-mode web server core - uses BrainService as backend"""

    def __init__(self, bmam_coordinator, host: str = "0.0.0.0", port: int = 8080):
        self.coordinator = bmam_coordinator
        self.host = host
        self.port = port

        # API facade (no VoiceAnimeUI)
        self.brain_service = BrainService(bmam_coordinator)

        # WebSocket connections
        self.websockets: Set[web.WebSocketResponse] = set()

        # Server state
        self.app = None
        self.runner = None
        self.site = None
