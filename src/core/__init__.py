"""
Core Infrastructure Package
核心基础设施包

Provides foundational components for dependency injection,
configuration, and lazy initialization.
提供依赖注入、配置和延迟初始化的基础组件。
"""

from .container import (
    Container,
    ContainerScope,
    Lifecycle,
    Registration,
    get_container,
    reset_container
)

from .config import (
    BMAMConfig,
    MemorySystemConfig,
    AgentConfig,
    CoordinatorConfig,
    get_config,
    reset_config
)

from .lazy import (
    Lazy,
    lazy,
    lazy_property
)

__all__ = [
    # Container
    'Container',
    'ContainerScope',
    'Lifecycle',
    'Registration',
    'get_container',
    'reset_container',
    # Config
    'BMAMConfig',
    'MemorySystemConfig',
    'AgentConfig',
    'CoordinatorConfig',
    'get_config',
    'reset_config',
    # Lazy
    'Lazy',
    'lazy',
    'lazy_property',
]
