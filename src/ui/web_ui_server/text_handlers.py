"""
Text Web UI Server Handlers
文本模式HTTP请求处理器 - 直接使用coordinator, 无VoiceAnimeUI依赖
"""

import logging
import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from aiohttp import web
from src.coordination.soul_state import get_soul_state

logger = logging.getLogger(__name__)


class TextHandlersMixin:
    """Text-mode HTTP handlers using coordinator directly"""

    async def index_handler(self, request):
        """Serve the new React Frontend"""
        # Serving from frontend/dist
        html_path = Path(__file__).parent / 'frontend' / 'dist' / 'index.html'
        if not html_path.exists():
            return web.Response(text="Frontend build not found. Run 'npm run build' in src/ui/web_ui_server/frontend", status=404)
        return web.FileResponse(html_path)

    async def status_handler(self, request):
        """Get system status via BrainService"""
        try:
            status_dto = self.brain_service.get_system_status()
            return web.json_response({
                'success': True,
                'data': asdict(status_dto),
                'websocket_connections': len(self.websockets)
            })
        except Exception as e:
            logger.error(f"Status error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def process_handler(self, request):
        """Process text input via coordinator directly"""
        try:
            data = await request.json()
            text = data.get('text', '')
            if not text:
                return web.json_response(
                    {'success': False, 'error': 'No text provided'}, status=400
                )

            result = await self.coordinator.process_user_input(text)

            response_data = {
                'success': result.success,
                'response': result.response,
                'agents_involved': result.agents_involved,
                'memories_retrieved': _serialize_memories(result.memories_retrieved),
                'processing_time': result.processing_time,
                'activation_trace': result.activation_trace or [],
                'routing_decision': result.routing_decision or {},
                'insights': result.insights or {},
            }

            await self.broadcast_update({
                'type': 'response',
                'text': result.response,
                'full_result': response_data,
                'timestamp': datetime.now().isoformat()
            })

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"Process error: {e}")
            return web.json_response(
                {'success': False, 'error': str(e)}, status=500
            )

    async def memory_search_handler(self, request):
        """Search memories via coordinator.smart_retrieve"""
        try:
            data = await request.json()
            query = data.get('query', '')
            k = data.get('k', 10)
            if not query:
                return web.json_response(
                    {'success': False, 'error': 'No query provided'}, status=400
                )

            results = await self.coordinator.smart_retrieve(query, k=k)
            return web.json_response({
                'success': True,
                'data': _serialize_memories(results)
            })
        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def memory_stats_handler(self, request):
        """Get brain region memory statistics via BrainService"""
        try:
            stats = self.brain_service.get_memory_stats()
            return web.json_response({
                'success': True,
                'data': [asdict(s) for s in stats]
            })
        except Exception as e:
            logger.error(f"Memory stats error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def edit_memory_handler(self, request):
        """Handle memory editing via BrainService"""
        try:
            data = await request.json()
            memory_id = data.get('memory_id', '')
            content = data.get('content', '')
            importance = data.get('importance', 0.5)

            success = await self.brain_service.update_memory(
                memory_id, content, importance
            )
            return web.json_response({'success': success})
        except Exception as e:
            logger.error(f"Memory edit error: {e}")
            return web.json_response(
                {'success': False, 'error': str(e)}, status=500
            )

    async def memory_state_handler(self, request):
        """Get memory system state (reused from original, fixed self.ui refs)"""
        try:
            stats = {
                'regions': [],
                'summary': {
                    'total_memories': 0,
                    'overall_usage': 0.0,
                    'active_regions': 0
                }
            }

            if hasattr(self.coordinator, 'agents'):
                total_capacity = 0
                total_usage = 0
                active_count = 0

                for agent_id, agent in self.coordinator.agents.items():
                    if not hasattr(agent, 'capacity'):
                        continue
                    capacity = getattr(agent, 'capacity', 0)
                    if capacity <= 0:
                        continue

                    current = 0
                    if hasattr(agent, 'storage'):
                        try:
                            current = len(agent.storage)
                        except TypeError:
                            current = 0
                    elif hasattr(agent, 'memory_store'):
                        try:
                            current = len(agent.memory_store)
                        except TypeError:
                            current = 0

                    usage_pct = (current / capacity * 100) if capacity > 0 else 0
                    if usage_pct > 0:
                        active_count += 1

                    stats['regions'].append({
                        'id': agent_id,
                        'name': agent_id.replace('_', ' ').title(),
                        'capacity': capacity,
                        'current_count': current,
                        'usage_percentage': usage_pct,
                        'total_stored': getattr(agent, 'total_stored', 0),
                        'total_evicted': getattr(agent, 'total_evicted', 0),
                    })
                    total_capacity += capacity
                    total_usage += current

                stats['summary']['total_memories'] = total_usage
                stats['summary']['overall_usage'] = (
                    (total_usage / total_capacity * 100) if total_capacity > 0 else 0
                )
                stats['summary']['active_regions'] = active_count

            return web.json_response({'success': True, 'data': stats})
        except Exception as e:
            logger.error(f"Memory state error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def soul_state_handler(self, request):
        """Get soul/emotion state"""
        try:
            soul = get_soul_state()
            state = await soul.async_get_state()
            if 'weights' not in state:
                state['weights'] = {
                    'amygdala': 0.0,
                    'prefrontal': 0.0,
                    'basal_ganglia': 0.0
                }
            return web.json_response({'success': True, 'data': state})
        except Exception as e:
            logger.error(f"Soul state error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def dataflow_handler(self, request):
        """Get data flow statistics"""
        try:
            data = {
                'total_events': 0,
                'event_type_counts': {},
                'flows': [],
                'top_flows': []
            }
            if hasattr(self.coordinator, 'metrics_collector'):
                mc = self.coordinator.metrics_collector
                stats = mc.get_statistics()
                data = {
                    'total_events': stats.get('total_requests', 0),
                    'event_type_counts': {
                        'memory_ops': stats.get('memory_operations', 0),
                        'kg_ops': stats.get('kg_operations', 0),
                        'consolidation_ops': stats.get('consolidation_operations', 0),
                        'forgetting_ops': stats.get('forgetting_operations', 0)
                    },
                    'flows': [],
                    'top_flows': mc.get_most_active_agents(5)
                }
            return web.json_response({'success': True, 'data': data})
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
            }
            if hasattr(self.coordinator, 'metrics_collector'):
                mc = self.coordinator.metrics_collector
                stats = mc.get_statistics()
                data = {
                    'total_calls': stats.get('total_requests', 0),
                    'success_rate': mc.get_success_rate(),
                    'avg_duration_ms': mc.get_average_response_time() * 1000,
                    'error_count': stats.get('failed_requests', 0),
                }
            return web.json_response({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Performance error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def health_handler(self, request):
        """Get system health"""
        try:
            return web.json_response({
                'success': True,
                'data': {'health_score': 'GOOD'}
            })
        except Exception as e:
            logger.error(f"Health error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def recent_events_handler(self, request):
        """Get recent events"""
        try:
            events = []
            if hasattr(self.coordinator, 'metrics_collector'):
                mc = self.coordinator.metrics_collector
                stats = mc.get_statistics()
                events.append({
                    'type': 'stats_snapshot',
                    'data': {
                        'total_requests': stats.get('total_requests', 0),
                        'success_rate': mc.get_success_rate(),
                        'avg_response_time': mc.get_average_response_time()
                    }
                })
                for agent, count in mc.get_most_active_agents(3):
                    events.append({
                        'type': 'agent_activity',
                        'agent': agent,
                        'activation_count': count
                    })
            return web.json_response({'success': True, 'data': events})
        except Exception as e:
            logger.error(f"Recent events error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def feedback_stats_handler(self, request):
        """Get learning feedback stats"""
        try:
            data = {'stats': [], 'summary': {}}

            if (hasattr(self.coordinator, 'learnable_router')
                    and self.coordinator.learnable_router):
                router = self.coordinator.learnable_router
                router_stats = router.get_statistics()
                data['summary']['learnable_router'] = {
                    'total_routes': router_stats.get('total_routes', 0),
                    'total_feedbacks': router_stats.get('total_feedbacks', 0),
                    'agent_success_rates': router_stats.get(
                        'agent_success_rates', {}
                    ),
                    'routing_distribution': router_stats.get(
                        'routing_distribution', {}
                    ),
                }

            if (hasattr(self.coordinator, 'prefrontal_feedback')
                    and self.coordinator.prefrontal_feedback):
                pf = self.coordinator.prefrontal_feedback
                if hasattr(pf, 'get_statistics'):
                    data['summary']['prefrontal_feedback'] = pf.get_statistics()

            try:
                from src.coordination.confidence_calibrator import (
                    get_confidence_calibrator,
                )
                calibrator = get_confidence_calibrator()
                calibrator_stats = {}
                for region, state in calibrator.region_states.items():
                    calibrator_stats[region] = {
                        'calibration_factor': state.calibration_factor,
                        'total_queries': state.total_queries,
                        'success_rate': state.success_rate()
                    }
                data['summary']['confidence_calibrator'] = calibrator_stats
            except Exception:
                pass

            return web.json_response({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Feedback stats error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def memory_export_handler(self, request):
        """Export memory as .bma.tar.gz archive"""
        try:
            import tarfile
            from src.utils.paths import BMAMPaths

            output_dir = BMAMPaths.EXPORTS_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            name = f"soul_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            report = await self.brain_service.export_memory(
                output_dir=output_dir,
                name=name,
                description="Exported via Text Web UI"
            )

            if report.success and report.archive_path and report.archive_path.exists():
                tar_path = output_dir / f"{name}.bma.tar.gz"
                with tarfile.open(tar_path, "w:gz") as tar:
                    tar.add(report.archive_path, arcname=report.archive_path.name)
                return web.FileResponse(
                    tar_path,
                    headers={
                        'Content-Disposition': (
                            f'attachment; filename="{name}.bma.tar.gz"'
                        )
                    }
                )

            return web.json_response({
                'success': False,
                'error': '; '.join(report.errors) if report.errors else 'Export failed'
            })
        except Exception as e:
            logger.error(f"Memory export error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    async def memory_import_handler(self, request):
        """Import memory from .bma.tar.gz archive"""
        try:
            import tarfile
            from src.utils.paths import BMAMPaths

            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != 'file':
                return web.json_response({
                    'success': False,
                    'error': 'No file uploaded. Use multipart/form-data with field "file"'
                })

            import_dir = BMAMPaths.IMPORTS_DIR
            import_dir.mkdir(parents=True, exist_ok=True)

            filename = (
                field.filename
                or f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bma.tar.gz"
            )
            tar_path = import_dir / filename

            with open(tar_path, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            extract_dir = (
                import_dir
                / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            extract_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(extract_dir)

            bma_dirs = list(extract_dir.glob("*.bma"))
            if not bma_dirs:
                return web.json_response({
                    'success': False,
                    'error': 'No .bma directory found in archive'
                })

            report = await self.brain_service.import_memory(bma_dirs[0])

            if report.success:
                return web.json_response({
                    'success': True,
                    'message': f'Imported {report.total_memories} memories',
                    'stats': {
                        'total_memories': report.total_memories,
                        'by_region': report.memories_by_region
                    }
                })

            return web.json_response({
                'success': False,
                'error': '; '.join(report.errors) if report.errors else 'Import failed'
            })
        except Exception as e:
            logger.error(f"Memory import error: {e}")
            return web.json_response({'success': False, 'error': str(e)})


def _serialize_memories(memories):
    """Serialize memory objects to JSON-safe dicts"""
    if not memories:
        return []
    result = []
    for m in memories:
        if isinstance(m, dict):
            result.append(m)
        else:
            result.append({
                'id': getattr(m, 'id', ''),
                'content': getattr(m, 'content', str(m)),
                'importance': getattr(m, 'importance', 0.5),
                'timestamp': getattr(m, 'timestamp', ''),
                'source': getattr(m, 'source', ''),
                'score': getattr(m, 'score', 0.0),
            })
    return result
