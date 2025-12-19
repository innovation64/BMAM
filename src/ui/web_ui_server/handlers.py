"""
Web UI Server Handlers
HTTP请求处理器
"""

import logging
import json
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

            if hasattr(self.coordinator, 'agents'):
                total_capacity = 0
                total_usage = 0
                active_count = 0

                for agent_id, agent in self.coordinator.agents.items():
                    # Skip if no capacity attribute (functional agents without storage)
                    if not hasattr(agent, 'capacity'):
                        continue

                    # Get capacity and usage
                    capacity = getattr(agent, 'capacity', 0)
                    if capacity <= 0:
                        continue
                        
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
            # 🔥 2025-12-16: 使用真实的 MetricsCollector 数据
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
            # 🔥 2025-12-16: 使用真实的 MetricsCollector 数据
            data = {
                'total_calls': 0,
                'success_rate': 100.0,
                'avg_duration_ms': 0.0,
                'error_count': 0,
                'slowest_functions': []
            }

            if hasattr(self.coordinator, 'metrics_collector'):
                mc = self.coordinator.metrics_collector
                stats = mc.get_statistics()
                data = {
                    'total_calls': stats.get('total_requests', 0),
                    'success_rate': mc.get_success_rate(),
                    'avg_duration_ms': mc.get_average_response_time() * 1000,  # 转换为毫秒
                    'error_count': stats.get('failed_requests', 0),
                    'slowest_functions': []  # 可扩展
                }

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
            # 🔥 2025-12-16: 从 MetricsCollector 获取最近事件
            events = []

            if hasattr(self.coordinator, 'metrics_collector'):
                mc = self.coordinator.metrics_collector
                # 获取最近的请求统计
                stats = mc.get_statistics()
                events.append({
                    'type': 'stats_snapshot',
                    'data': {
                        'total_requests': stats.get('total_requests', 0),
                        'success_rate': mc.get_success_rate(),
                        'avg_response_time': mc.get_average_response_time()
                    }
                })

                # 获取最活跃的 agents
                top_agents = mc.get_most_active_agents(3)
                for agent, count in top_agents:
                    events.append({
                        'type': 'agent_activity',
                        'agent': agent,
                        'activation_count': count
                    })

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
            # 🔥 2025-12-16: 从 LearnableRouter 获取反馈统计
            data = {
                'stats': [],
                'summary': {}
            }

            # 从 LearnableRouter 获取统计
            if hasattr(self.coordinator, 'learnable_router') and self.coordinator.learnable_router:
                router = self.coordinator.learnable_router
                router_stats = router.get_statistics()
                data['summary']['learnable_router'] = {
                    'total_routes': router_stats.get('total_routes', 0),
                    'total_feedbacks': router_stats.get('total_feedbacks', 0),
                    'agent_success_rates': router_stats.get('agent_success_rates', {}),
                    'routing_distribution': router_stats.get('routing_distribution', {})
                }

            # 从 PrefrontalFeedback 获取统计
            if hasattr(self.coordinator, 'prefrontal_feedback') and self.coordinator.prefrontal_feedback:
                pf = self.coordinator.prefrontal_feedback
                if hasattr(pf, 'get_statistics'):
                    data['summary']['prefrontal_feedback'] = pf.get_statistics()

            # 从 ConfidenceCalibrator 获取统计
            try:
                from src.coordination.confidence_calibrator import get_confidence_calibrator
                calibrator = get_confidence_calibrator()
                calibrator_stats = {}
                for region, state in calibrator.region_states.items():
                    calibrator_stats[region] = {
                        'calibration_factor': state.calibration_factor,
                        'total_queries': state.total_queries,
                        'success_rate': state.success_rate
                    }
                data['summary']['confidence_calibrator'] = calibrator_stats
            except Exception:
                pass

            return web.json_response({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"Feedback stats error: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    # 🔥 2025-12-15: 灵魂导出导入API (跨平台迁移)
    async def memory_export_handler(self, request):
        """导出完整记忆体 (灵魂迁移) - 返回 .bma.tar.gz 归档"""
        try:
            import tarfile
            import tempfile
            from src.memory.memory_transfer import MemoryTransferSystem

            # 获取coordinator
            coordinator = getattr(self.ui, 'coordinator', None)
            if not coordinator:
                return web.json_response({
                    'success': False,
                    'error': 'Coordinator not available'
                })

            transfer = MemoryTransferSystem(coordinator)

            # 🔥 使用 BMAMPaths 统一路径管理
            from src.utils.paths import BMAMPaths
            output_dir = BMAMPaths.EXPORTS_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            name = f"soul_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            report = await transfer.export_memory(
                output_dir=output_dir,
                name=name,
                description="Exported via Web UI"
            )

            if report.success and report.archive_path and report.archive_path.exists():
                # 将 .bma 目录打包成 tar.gz
                tar_path = output_dir / f"{name}.bma.tar.gz"
                with tarfile.open(tar_path, "w:gz") as tar:
                    tar.add(report.archive_path, arcname=report.archive_path.name)

                # 返回文件下载
                return web.FileResponse(
                    tar_path,
                    headers={
                        'Content-Disposition': f'attachment; filename="{name}.bma.tar.gz"'
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
        """导入完整记忆体 (灵魂迁移) - 接收 .bma.tar.gz 归档"""
        try:
            import tarfile
            import tempfile
            from src.memory.memory_transfer import MemoryTransferSystem

            # 获取coordinator
            coordinator = getattr(self.ui, 'coordinator', None)
            if not coordinator:
                return web.json_response({
                    'success': False,
                    'error': 'Coordinator not available'
                })

            # 接收上传的文件
            reader = await request.multipart()
            field = await reader.next()

            if field is None or field.name != 'file':
                return web.json_response({
                    'success': False,
                    'error': 'No file uploaded. Use multipart/form-data with field name "file"'
                })

            # 🔥 使用 BMAMPaths 统一路径管理
            from src.utils.paths import BMAMPaths
            import_dir = BMAMPaths.IMPORTS_DIR
            import_dir.mkdir(parents=True, exist_ok=True)

            filename = field.filename or f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bma.tar.gz"
            tar_path = import_dir / filename

            # 写入文件
            with open(tar_path, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            # 解压 tar.gz
            extract_dir = import_dir / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            extract_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(extract_dir)

            # 找到 .bma 目录
            bma_dirs = list(extract_dir.glob("*.bma"))
            if not bma_dirs:
                return web.json_response({
                    'success': False,
                    'error': 'No .bma directory found in archive'
                })

            bma_path = bma_dirs[0]

            # 执行导入
            transfer = MemoryTransferSystem(coordinator)
            report = await transfer.import_memory(
                archive_path=bma_path,
                create_backup=True,
                validate_before_import=True
            )

            if report.success:
                return web.json_response({
                    'success': True,
                    'message': f'Successfully imported {report.total_memories} memories',
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
