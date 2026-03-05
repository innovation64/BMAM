"""
Web UI Server Core
Web服务器核心 - 类定义和路由设置
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

# Web framework dependencies
try:
    from aiohttp import web
    from aiohttp import WSMsgType
    import aiohttp_cors
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

from ..voice_anime_ui import VoiceAnimeUI, CharacterState, EmotionType
from ..voice_interface import VoiceInterface, VoiceCommandProcessor

logger = logging.getLogger(__name__)


class WebUIServerCore:
    """Web server core for the voice anime UI"""

    def __init__(self, bmam_coordinator, host: str = "0.0.0.0", port: int = 8080):
        self.coordinator = bmam_coordinator
        self.host = host
        self.port = port

        # UI components
        self.ui = VoiceAnimeUI(bmam_coordinator)
        self.voice = VoiceInterface()
        self.command_processor = VoiceCommandProcessor()

        # WebSocket connections
        self.websockets: Set[web.WebSocketResponse] = set()

        # Server state
        self.app = None
        self.runner = None
        self.site = None

