"""
Text Web UI Server Lifecycle
文本模式生命周期管理 - 无动画循环, 无Voice清理
"""

import asyncio
import logging
from typing import Dict, Any

try:
    from aiohttp import web
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextLifecycleMixin:
    """Text-mode server lifecycle - simplified"""

    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all WebSocket clients"""
        if self.websockets:
            await asyncio.gather(
                *[ws.send_json(data) for ws in self.websockets],
                return_exceptions=True
            )

    async def start(self):
        """Start the text-mode web server"""
        if not WEB_AVAILABLE:
            logger.error("Web dependencies not available (aiohttp, aiohttp_cors)")
            return False

        try:
            self.app = web.Application()
            self.setup_routes(self.app)

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            logger.info(
                f"Text Web UI server started at http://{self.host}:{self.port}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start text web server: {e}")
            return False

    async def stop(self):
        """Stop the text-mode web server (no voice cleanup)"""
        for ws in list(self.websockets):
            await ws.close()

        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("Text Web UI server stopped")
