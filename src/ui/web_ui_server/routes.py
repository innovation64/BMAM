"""
Routes Mixin
路由配置 - 负责设置Web路由和CORS
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Web framework dependencies
try:
    from aiohttp import web
    import aiohttp_cors
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


class RoutesMixin:
    """Web路由配置和CORS设置"""

    def setup_routes(self, app: web.Application):
        """设置Web路由"""
        # Static files
        app.router.add_get('/', self.index_handler)
        app.router.add_static('/static', Path(__file__).parent / 'static')

        # API endpoints
        app.router.add_get('/api/status', self.status_handler)
        app.router.add_post('/api/process', self.process_handler)
        app.router.add_post('/api/memory/edit', self.edit_memory_handler)
        app.router.add_get('/api/layout', self.layout_handler)

        # WebSocket
        app.router.add_get('/ws', self.websocket_handler)

        # Setup CORS
        self.setup_cors(app)

    def setup_cors(self, app: web.Application):
        """配置CORS (跨域资源共享)"""
        if not WEB_AVAILABLE:
            logger.warning("Web dependencies not available, skipping CORS setup")
            return

        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })

        # Add CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)

        logger.debug("CORS configured for all routes")
