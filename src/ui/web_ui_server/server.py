"""
Web UI Server Lifecycle
服务器生命周期管理和广播功能
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


class LifecycleMixin:
    """服务器生命周期管理和广播功能"""

    async def animation_loop(self, ws: web.WebSocketResponse):
        """Send animation updates to client (adaptive FPS)."""
        try:
            while ws in self.websockets:
                # Update UI state
                ui_state = self.ui.update()

                char_state = ui_state['character'].state.value

                # Send to client
                await ws.send_json({
                    'type': 'animation_update',
                    'character': {
                        'state': char_state,
                        'emotion': ui_state['character'].emotion.value,
                        'eye_openness': ui_state['character'].eye_openness,
                        'mouth_openness': ui_state['character'].mouth_openness,
                        'head_tilt': ui_state['character'].head_tilt,
                        'body_bounce': ui_state['character'].body_bounce,
                        'arm_position': ui_state['character'].arm_position
                    },
                    'waveform': ui_state['waveform'],
                    'chat_bubble': ui_state['chat_bubble']
                })

                # Adaptive FPS: 30 when active, 10 when idle
                if char_state in ('speaking', 'listening'):
                    await asyncio.sleep(1 / 30)
                else:
                    await asyncio.sleep(1 / 10)

        except Exception as e:
            logger.error(f"Animation loop error: {e}")

    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all WebSocket clients"""
        if self.websockets:
            await asyncio.gather(
                *[ws.send_json(data) for ws in self.websockets],
                return_exceptions=True
            )

    async def start(self):
        """Start the web server"""
        if not WEB_AVAILABLE:
            logger.error("Web dependencies not available")
            return False

        try:
            self.app = web.Application()
            self.setup_routes(self.app)

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            logger.info(f"Web UI server started at http://{self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            return False

    async def stop(self):
        """Stop the web server"""
        # Close all WebSocket connections
        for ws in list(self.websockets):
            await ws.close()

        # Stop the site
        if self.site:
            await self.site.stop()

        # Cleanup runner
        if self.runner:
            await self.runner.cleanup()

        # Cleanup voice interface
        self.voice.cleanup()

        logger.info("Web UI server stopped")
