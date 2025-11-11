"""
Web UI Server Handlers
HTTP请求处理器
"""

import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from aiohttp import web

logger = logging.getLogger(__name__)


class HandlersMixin:
    """HTTP请求处理器"""

    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_path = Path(__file__).parent / 'static' / 'index.html'

        if not html_path.exists():
            # Generate default HTML if not exists
            html_content = self.generate_default_html()
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(html_content)

        return web.FileResponse(html_path)

    async def status_handler(self, request):
        """Get system status"""
        status = {
            'bmam_status': self.coordinator.get_system_status(),
            'ui_state': {
                'character_state': self.ui.character.current_state.value,
                'character_emotion': self.ui.character.current_emotion.value,
                'is_listening': self.ui.is_listening,
                'is_processing': self.ui.is_processing,
                'memory_count': len(self.ui.memory_panel.memory_conditions)
            },
            'websocket_connections': len(self.websockets)
        }
        return web.json_response(status)

    async def process_handler(self, request):
        """Process text input"""
        try:
            data = await request.json()
            text = data.get('text', '')

            # Check for voice command
            command_result = await self.command_processor.process_command(text, self.ui)

            if command_result['is_command']:
                return web.json_response(command_result)

            # Process through BMAM
            response = await self.ui.process_voice_input(text.encode())

            # Broadcast to WebSocket clients
            await self.broadcast_update({
                'type': 'response',
                'text': response,
                'timestamp': datetime.now().isoformat()
            })

            return web.json_response({
                'success': True,
                'response': response
            })

        except Exception as e:
            logger.error(f"Process error: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def edit_memory_handler(self, request):
        """Handle memory editing"""
        try:
            data = await request.json()
            index = data.get('index', 0)
            content = data.get('content', '')
            importance = data.get('importance', 0.5)

            success = self.ui.handle_memory_edit(index, content, importance)

            # Broadcast update
            await self.broadcast_update({
                'type': 'memory_update',
                'memories': [
                    {
                        'id': m.id,
                        'content': m.content,
                        'importance': m.importance,
                        'emotion_tags': m.emotion_tags,
                        'is_active': m.is_active
                    }
                    for m in self.ui.memory_panel.get_visible_memories()
                ]
            })

            return web.json_response({
                'success': success
            })

        except Exception as e:
            logger.error(f"Memory edit error: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def layout_handler(self, request):
        """Get UI layout specification"""
        layout_spec = self.ui.get_layout_spec()
        return web.json_response(layout_spec)

