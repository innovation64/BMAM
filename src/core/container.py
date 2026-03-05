"""
Dependency Injection Container
依赖注入容器

Manages object lifecycle and dependency resolution
管理对象生命周期和依赖解析
"""

from typing import TypeVar, Type, Callable, Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
import threading
from enum import Enum

T = TypeVar('T')


class Lifecycle(Enum):
    """Component lifecycle strategies / 组件生命周期策略"""
    TRANSIENT = "transient"      # New instance each time / 每次创建新实例
    SINGLETON = "singleton"      # Single instance (thread-safe) / 单例（线程安全）
    SCOPED = "scoped"           # One per scope (e.g., per request) / 每个作用域一个


class IFactory(Protocol[T]):
    """Factory protocol for object creation / 对象创建的工厂协议"""
    def __call__(self, container: 'Container') -> T:
        ...


class Registration:
    """
    Registration metadata for a component
    组件的注册元数据
    """

    def __init__(
        self,
        interface: Type,
        implementation: Type = None,
        factory: Callable = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
        instance: Any = None
    ):
        self.interface = interface
        self.implementation = implementation
        self.factory = factory
        self.lifecycle = lifecycle
        self.instance = instance
        self._lock = threading.RLock()

    def create_instance(self, container: 'Container') -> Any:
        """
        Create instance based on lifecycle strategy
        基于生命周期策略创建实例
        """

        if self.lifecycle == Lifecycle.SINGLETON:
            if self.instance is None:
                with self._lock:
                    if self.instance is None:  # Double-checked locking
                        self.instance = self._create(container)
            return self.instance

        elif self.lifecycle == Lifecycle.TRANSIENT:
            return self._create(container)

        else:
            raise NotImplementedError(f"Lifecycle {self.lifecycle} not supported")

    def _create(self, container: 'Container') -> Any:
        """Internal creation logic / 内部创建逻辑"""
        if self.factory:
            return self.factory(container)
        elif self.implementation:
            return self.implementation()
        else:
            raise ValueError(f"No factory or implementation for {self.interface}")


class Container:
    """
    Dependency Injection Container
    依赖注入容器

    Features:
    - Interface-based registration / 基于接口的注册
    - Lifecycle management (singleton, transient) / 生命周期管理
    - Factory function support / 工厂函数支持
    - Thread-safe singleton creation / 线程安全的单例创建
    - Dependency resolution / 依赖解析

    Example:
        container = Container()
        container.register(IMemorySystem, AdvancedMemorySystem, Lifecycle.SINGLETON)
        container.register_factory(IMessageBus, lambda c: MessageBus(queue_size=100))

        memory = container.resolve(IMemorySystem)
    """

    def __init__(self):
        self._registrations: Dict[Type, Registration] = {}
        self._lock = threading.RLock()

        # Self-registration for factories that need container access
        self.register_instance(Container, self)

    def register(
        self,
        interface: Type[T],
        implementation: Type[T] = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
        factory: Callable = None
    ) -> 'Container':
        """
        Register a type mapping
        注册类型映射

        Args:
            interface: Interface type or abstract class / 接口类型或抽象类
            implementation: Concrete implementation class / 具体实现类
            lifecycle: Instance lifecycle strategy / 实例生命周期策略
            factory: Optional factory callable / 可选的工厂函数

        Returns:
            Self for fluent chaining / 返回自身以支持链式调用
        """
        with self._lock:
            self._registrations[interface] = Registration(
                interface=interface,
                implementation=implementation,
                factory=factory,
                lifecycle=lifecycle
            )
        return self

    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[[Optional['Container']], T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON
    ) -> 'Container':
        """
        Register a factory function
        注册工厂函数

        Args:
            interface: Interface type / 接口类型
            factory: Factory function returning instance / 返回实例的工厂函数
            lifecycle: Instance lifecycle strategy / 实例生命周期策略

        Returns:
            Self for fluent chaining / 返回自身以支持链式调用
        """
        with self._lock:
            self._registrations[interface] = Registration(
                interface=interface,
                factory=factory,
                lifecycle=lifecycle
            )
        return self

    def register_instance(
        self,
        interface: Type[T],
        instance: T
    ) -> 'Container':
        """
        Register a pre-created instance (always singleton)
        注册预创建的实例（始终为单例）

        Args:
            interface: Interface type / 接口类型
            instance: Pre-created instance / 预创建的实例

        Returns:
            Self for fluent chaining / 返回自身以支持链式调用
        """
        with self._lock:
            self._registrations[interface] = Registration(
                interface=interface,
                lifecycle=Lifecycle.SINGLETON,
                instance=instance
            )
        return self

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve an instance of the given interface
        解析给定接口的实例

        Args:
            interface: Interface type to resolve / 要解析的接口类型

        Returns:
            Instance of the registered implementation / 已注册实现的实例

        Raises:
            ValueError: If interface not registered / 如果接口未注册
        """
        with self._lock:
            if interface not in self._registrations:
                raise ValueError(f"Interface {interface} not registered")

            registration = self._registrations[interface]
            return registration.create_instance(self)

    def try_resolve(self, interface: Type[T]) -> Optional[T]:
        """
        Try to resolve an instance, return None if not registered
        尝试解析实例，如果未注册则返回None

        Args:
            interface: Interface type to resolve / 要解析的接口类型

        Returns:
            Instance or None if not registered / 实例或None（如果未注册）
        """
        try:
            return self.resolve(interface)
        except ValueError:
            return None

    def is_registered(self, interface: Type) -> bool:
        """
        Check if an interface is registered
        检查接口是否已注册
        """
        return interface in self._registrations

    def clear(self):
        """
        Clear all registrations (useful for testing)
        清除所有注册（用于测试）
        """
        with self._lock:
            self._registrations.clear()
            self.register_instance(Container, self)

    def create_scope(self) -> 'ContainerScope':
        """
        Create a scoped container (for request-scoped dependencies)
        创建作用域容器（用于请求范围的依赖）
        """
        return ContainerScope(parent=self)


class ContainerScope(Container):
    """
    Scoped container for request-level dependencies
    请求级别依赖的作用域容器

    Falls back to parent for unregistered types
    对于未注册的类型，回退到父容器
    """

    def __init__(self, parent: Container):
        super().__init__()
        self._parent = parent

    def resolve(self, interface: Type[T]) -> T:
        """Resolve from scope first, then parent / 先从作用域解析，然后从父容器"""
        try:
            return super().resolve(interface)
        except ValueError:
            return self._parent.resolve(interface)

    def is_registered(self, interface: Type) -> bool:
        """Check scope and parent / 检查作用域和父容器"""
        return super().is_registered(interface) or self._parent.is_registered(interface)


# Global container instance (lazy-initialized) / 全局容器实例（延迟初始化）
_global_container: Optional[Container] = None
_container_lock = threading.RLock()


def get_container() -> Container:
    """
    Get or create the global container instance
    获取或创建全局容器实例
    """
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = Container()
    return _global_container


def reset_container():
    """
    Reset global container (for testing)
    重置全局容器（用于测试）
    """
    global _global_container
    with _container_lock:
        _global_container = None


# ---------------------------------------------------------------------------
# BMContainer: Lightweight name-based Dependency Injection Container
# 轻量级基于名称的依赖注入容器
# ---------------------------------------------------------------------------

class BMContainer:
    """
    Lightweight DI container using string names as keys.
    轻量级依赖注入容器，使用字符串名称作为键。

    Designed to coexist with the existing type-based Container.
    Provides simple register/resolve semantics for wiring
    components together without relying on global singletons.

    Example::

        container = BMContainer()
        container.register('config', my_config)
        container.register('soul_state', my_soul_state)

        cfg = container.resolve('config')
        assert container.has('soul_state')

        container.reset()  # clear all for test isolation
    """

    def __init__(self) -> None:
        self._components: Dict[str, Any] = {}
        self._lock = threading.Lock()

    # -- public API --------------------------------------------------

    def register(self, name: str, instance: Any) -> None:
        """
        Register a component instance under *name*.
        注册一个组件实例。

        Args:
            name: Unique string key for the component.
            instance: The object to store.

        Raises:
            TypeError: If *name* is not a string.
        """
        if not isinstance(name, str):
            raise TypeError(
                f"name must be a string, got {type(name).__name__}"
            )
        with self._lock:
            self._components[name] = instance

    def resolve(self, name: str) -> Any:
        """
        Retrieve a previously registered component.
        获取已注册的组件。

        Args:
            name: The key used during registration.

        Returns:
            The registered instance.

        Raises:
            KeyError: If *name* was never registered.
        """
        with self._lock:
            if name not in self._components:
                raise KeyError(
                    f"Component '{name}' is not registered "
                    f"in BMContainer"
                )
            return self._components[name]

    def has(self, name: str) -> bool:
        """
        Check whether *name* is registered.
        检查组件是否已注册。
        """
        with self._lock:
            return name in self._components

    def reset(self) -> None:
        """
        Clear all registrations (useful for test isolation).
        清除所有注册（用于测试隔离）。
        """
        with self._lock:
            self._components.clear()

    def __len__(self) -> int:
        """Return the number of registered components."""
        with self._lock:
            return len(self._components)

    def __repr__(self) -> str:
        with self._lock:
            names = list(self._components.keys())
        return (
            f"BMContainer(components={names})"
        )


# -- Module-level singleton access for BMContainer --

_bm_container_instance: Optional[BMContainer] = None
_bm_container_lock = threading.Lock()


def get_bm_container() -> BMContainer:
    """
    Get or create the global BMContainer singleton.
    获取或创建全局 BMContainer 单例。
    """
    global _bm_container_instance
    if _bm_container_instance is None:
        with _bm_container_lock:
            if _bm_container_instance is None:
                _bm_container_instance = BMContainer()
    return _bm_container_instance


def reset_bm_container() -> None:
    """
    Reset the global BMContainer (for testing).
    重置全局 BMContainer（用于测试）。
    """
    global _bm_container_instance
    with _bm_container_lock:
        if _bm_container_instance is not None:
            _bm_container_instance.reset()
        _bm_container_instance = None
