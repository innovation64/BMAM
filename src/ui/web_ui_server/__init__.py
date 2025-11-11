"""
Web UI Server Module
Web服务器模块 - 提供WebSocket和REST API接口

Package Structure:
- core.py: 核心类定义 (WebUIServerCore)
- handlers.py: HTTP请求处理器 (HTTPHandlersMixin)
- websocket.py: WebSocket连接处理 (WebSocketHandlerMixin)
- audio_handler.py: 音频处理 (AudioProcessingMixin)
- template_generator.py: HTML模板生成 (TemplateGeneratorMixin)
- routes.py: 路由配置 (RoutesMixin)
- server.py: 服务器生命周期 (LifecycleMixin)
- static/: 静态文件目录 (HTML, CSS, JS)
"""

import asyncio

from .core import WebUIServerCore
from .handlers import HandlersMixin
from .websocket import WebSocketMixin
from .audio_handler import AudioProcessingMixin
from .template_generator import TemplateGeneratorMixin
from .routes import RoutesMixin
from .server import LifecycleMixin


class WebUIServer(
    HandlersMixin,
    WebSocketMixin,
    AudioProcessingMixin,
    TemplateGeneratorMixin,
    RoutesMixin,
    LifecycleMixin,
    WebUIServerCore
):
    """
    Web UI服务器 - 整合所有功能的完整类

    继承顺序说明 (Method Resolution Order):
    1. HandlersMixin - HTTP请求处理
    2. WebSocketMixin - WebSocket连接和消息处理
    3. AudioProcessingMixin - 音频处理和格式转换
    4. TemplateGeneratorMixin - HTML模板生成和管理
    5. RoutesMixin - 路由配置和CORS设置
    6. LifecycleMixin - 服务器生命周期管理和广播
    7. WebUIServerCore - 核心类定义和初始化

    Mixins are checked in order for method resolution.
    Core class provides the __init__ and base attributes.
    """
    pass


# Convenience function for running the server
async def main():
    """Run the web UI server"""
    from src.coordination.brain_coordinator import BrainInspiredCoordinator

    # Initialize BMAM coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Create and start web server
    server = WebUIServer(coordinator)

    if await server.start():
        print(f"Voice Anime UI running at http://localhost:8080")
        print("Press Ctrl+C to stop")

        try:
            # Keep server running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await server.stop()
            await coordinator.stop_system()


__all__ = [
    'WebUIServer',
    'WebUIServerCore',
    'HandlersMixin',
    'WebSocketMixin',
    'AudioProcessingMixin',
    'TemplateGeneratorMixin',
    'RoutesMixin',
    'LifecycleMixin',
    'main',
]


if __name__ == "__main__":
    asyncio.run(main())
