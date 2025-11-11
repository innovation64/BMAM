"""
Web UI Server WebSocket
WebSocket消息处理
"""

import asyncio
import json
import logging
from typing import Dict, Any
from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)


class WebSocketMixin:
    """WebSocket连接和消息处理"""

    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)

        try:
            # Send initial state
            await ws.send_json({
                'type': 'connected',
                'layout': self.ui.get_layout_spec()
            })

            # Start animation loop for this client
            animation_task = asyncio.create_task(
                self.animation_loop(ws)
            )

            # Handle incoming messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.handle_ws_message(ws, data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')

        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            animation_task.cancel()
            self.websockets.discard(ws)

        return ws

    async def handle_ws_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle WebSocket message from client"""
        msg_type = data.get('type')

        if msg_type == 'start_listening':
            # Notify client that listening started
            await ws.send_json({
                'type': 'listening_started',
                'message': 'Listening for audio...'
            })

        elif msg_type == 'stop_listening':
            self.voice.stop_listening()
            await ws.send_json({
                'type': 'listening_stopped',
                'message': 'Stopped listening'
            })

        elif msg_type == 'audio_data':
            # Handle audio data from browser (method from AudioProcessingMixin)
            await self.handle_browser_audio(ws, data)

        elif msg_type == 'text_input':
            text = data.get('text', '')
            response = await self.ui.process_voice_input(text.encode())
            await ws.send_json({
                'type': 'response',
                'text': response
            })

