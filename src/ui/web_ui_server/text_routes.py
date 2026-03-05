"""
Text Routes Mixin
文本模式路由配置 - 包含记忆搜索/统计端点
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from aiohttp import web
    import aiohttp_cors
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


class TextRoutesMixin:
    """Text-mode route configuration"""

    def setup_routes(self, app: web.Application):
        """Setup text-mode web routes"""
        static_dir = Path(__file__).parent / 'static'
        assets_dir = Path(__file__).parent / 'frontend' / 'dist' / 'assets'

        # Pages
        app.router.add_get('/', self.index_handler)
        app.router.add_static('/static', static_dir)
        if assets_dir.exists():
             app.router.add_static('/assets', assets_dir)

        # Core API
        app.router.add_post('/api/process', self.process_handler)
        app.router.add_get('/api/status', self.status_handler)

        # Memory API
        app.router.add_post('/api/memory/search', self.memory_search_handler)
        app.router.add_get('/api/memory/stats', self.memory_stats_handler)
        app.router.add_post('/api/memory/edit', self.edit_memory_handler)
        app.router.add_get('/api/memory/export', self.memory_export_handler)
        app.router.add_post('/api/memory/import', self.memory_import_handler)

        # Monitor API (slash style)
        app.router.add_get('/api/memory/state', self.memory_state_handler)
        app.router.add_get('/api/soul/state', self.soul_state_handler)
        app.router.add_get('/api/dataflow', self.dataflow_handler)
        app.router.add_get('/api/performance', self.performance_handler)
        app.router.add_get('/api/health', self.health_handler)
        app.router.add_get('/api/events/recent', self.recent_events_handler)
        app.router.add_get('/api/feedback/stats', self.feedback_stats_handler)

        # Monitor API aliases (underscore style - used by monitor.html)
        app.router.add_get('/api/memory_state', self.memory_state_handler)
        app.router.add_get('/api/soul_state', self.soul_state_handler)
        app.router.add_get('/api/recent_events', self.recent_events_handler)
        app.router.add_get('/api/feedback_stats', self.feedback_stats_handler)

        # WebSocket
        app.router.add_get('/ws', self.websocket_handler)

        # CORS
        self._setup_cors(app)

    def _setup_cors(self, app: web.Application):
        """Configure CORS"""
        if not WEB_AVAILABLE:
            return

        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        for route in list(app.router.routes()):
            cors.add(route)
