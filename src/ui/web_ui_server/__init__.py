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
# Convenience function for running the server
async def main():
    """Run the web UI server"""
    # Imports for V3 HRM Coordinator
    from src.core.container import get_container
    from src.core.config import get_config
    from src.memory.memory_system.registration import register_memory_system_components
    from src.core.interfaces.memory_interface import IMemorySystem
    from src.agents.brain_regions import (
        HippocampusAgent,
        TemporalLobeAgent,
        PrefrontalAgent,
        AmygdalaAgent,
        BasalGangliaAgent
    )
    from src.coordination.coordinator_v3_hrm import BrainInspiredCoordinatorV3_HRM

    # Initialize Container and Config
    container = get_container()
    config = get_config()
    
    # Register Memory System
    if not container.is_registered(IMemorySystem):
        register_memory_system_components(container)
    memory_system = container.resolve(IMemorySystem)

    # Initialize Brain Regions
    # Note: We need to handle dependencies manually here as per V3 requirements
    # 1. Temporal Lobe (needs memory system)
    temporal_lobe = TemporalLobeAgent(
        memory_system=memory_system,
        capacity=70000
    )
    
    # 2. Hippocampus (needs temporal lobe and memory system)
    hippocampus = HippocampusAgent(
        temporal_lobe_agent=temporal_lobe,
        memory_system=memory_system,
        capacity=20000
    )
    
    # 3. Prefrontal (needs nothing specific, maybe coordinator later)
    prefrontal = PrefrontalAgent(capacity=10)
    
    # 4. Amygdala (needs hippocampus and temporal lobe)
    amygdala = AmygdalaAgent(
        hippocampus_agent=hippocampus,
        temporal_lobe_agent=temporal_lobe,
        capacity=1000
    )
    
    # 5. Basal Ganglia
    basal_ganglia = BasalGangliaAgent(capacity=500)

    agents = {
        'hippocampus': hippocampus,
        'temporal_lobe': temporal_lobe,
        'prefrontal': prefrontal,
        'amygdala': amygdala,
        'basal_ganglia': basal_ganglia
    }

    components = {
        'memory_system': memory_system,
        'agents': agents,
        'message_bus': None # Optional
    }

    # Initialize BMAM coordinator
    coordinator = BrainInspiredCoordinatorV3_HRM(
        container=container,
        config=config,
        components=components
    )
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
