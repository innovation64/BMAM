"""
Web UI Server Handlers
HTTP请求处理器
"""

import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from aiohttp import web
from src.coordination.soul_state import get_soul_state

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


    async def memory_state_handler(self, request):
        """Get memory system state"""
        try:
            # Get stats from coordinator
            stats = {
                'regions': [],
                'summary': {
                    'total_memories': 0,
                    'overall_usage': 0.0,
                    'active_regions': 0
                }
            }

            if hasattr(self.coordinator, 'brain_regions'):
                total_capacity = 0
                total_usage = 0
                active_count = 0

                for agent_id, agent in self.coordinator.brain_regions.items():
                    # Only include brain regions
                    if agent_id not in ['hippocampus', 'temporal_lobe', 'prefrontal', 'amygdala', 'basal_ganglia']:
                        continue

                    # Get capacity and usage
                    capacity = getattr(agent, 'capacity', 1000)
                    current = 0
                    if hasattr(agent, 'storage'):
                        current = len(agent.storage)
                    elif hasattr(agent, 'memory_store'):
                        current = len(agent.memory_store)
                    
                    usage_pct = (current / capacity * 100) if capacity > 0 else 0
                    
                    if usage_pct > 0:
                        active_count += 1

                    region_data = {
                        'id': agent_id,
                        'name': agent_id.replace('_', ' ').title(),
                        'capacity': capacity,
                        'current_count': current,
                        'usage_percentage': usage_pct,
                        'avg_importance': 0.5, # Placeholder
                        'total_stored': getattr(agent, 'total_stored', 0),
                        'total_evicted': getattr(agent, 'total_evicted', 0),
                        'memory_types': {}
                    }
                    stats['regions'].append(region_data)
                    
                    total_capacity += capacity
                    total_usage += current

                stats['summary']['total_memories'] = total_usage
                stats['summary']['overall_usage'] = (total_usage / total_capacity * 100) if total_capacity > 0 else 0
                stats['summary']['active_regions'] = active_count

            return web.json_response({
                'success': True,
                'data': stats
            })
        except Exception as e:
            logger.error(f"Memory state error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def soul_state_handler(self, request):
        """Get soul/emotion state"""
        try:
            soul = get_soul_state()
            state = soul.get_state()
            
            # Add weights if missing
            if 'weights' not in state:
                state['weights'] = {
                    'amygdala': 0.0,
                    'prefrontal': 0.0,
                    'basal_ganglia': 0.0
                }

            return web.json_response({
                'success': True,
                'data': state
            })
        except Exception as e:
            logger.error(f"Soul state error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def dataflow_handler(self, request):
        """Get data flow statistics"""
        try:
            # Mock data for now, or get from metrics collector if available
            data = {
                'total_events': 0,
                'event_type_counts': {},
                'flows': [],
                'top_flows': []
            }
            
            if hasattr(self.coordinator, 'metrics_collector'):
                # TODO: Implement real metrics collection
                pass

            return web.json_response({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Dataflow error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def performance_handler(self, request):
        """Get performance metrics"""
        try:
            data = {
                'total_calls': 0,
                'success_rate': 100.0,
                'avg_duration_ms': 0.0,
                'error_count': 0,
                'slowest_functions': []
            }
            
            if hasattr(self.coordinator, 'processing_stats'):
                stats = self.coordinator.processing_stats
                # Extract stats...
                
            return web.json_response({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Performance error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def health_handler(self, request):
        """Get system health"""
        try:
            return web.json_response({
                'success': True,
                'data': {
                    'health_score': 'GOOD' # Dynamic logic can be added later
                }
            })
        except Exception as e:
            logger.error(f"Health error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def recent_events_handler(self, request):
        """Get recent events"""
        try:
            events = []
            # TODO: Get from event log
            return web.json_response({
                'success': True,
                'data': events
            })
        except Exception as e:
            logger.error(f"Recent events error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def feedback_stats_handler(self, request):
        """Get learning feedback stats"""
        try:
            data = {
                'stats': [],
                'summary': {}
            }
            # TODO: Get from learning manager
            return web.json_response({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Feedback stats error: {e}")
            return web.json_response({'success': False, 'error': str(e)})
