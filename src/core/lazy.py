"""
Lazy Initialization Pattern
延迟初始化模式

Defer component creation until first use
延迟组件创建直到首次使用
"""

from typing import TypeVar, Generic, Callable, Optional
import threading

T = TypeVar('T')


class Lazy(Generic[T]):
    """
    Lazy initialization wrapper
    延迟初始化包装器

    Defers object creation until first access, then caches the result.
    延迟对象创建直到首次访问，然后缓存结果。

    Thread-safe for concurrent access.
    并发访问时线程安全。

    Example:
        # Without lazy - immediate initialization / 不使用延迟 - 立即初始化
        memory_system = AdvancedMemorySystem()  # Expensive! / 昂贵！

        # With lazy - deferred initialization / 使用延迟 - 延迟初始化
        memory_system = Lazy(lambda: AdvancedMemorySystem())
        # ... nothing created yet ... / ... 尚未创建 ...
        result = memory_system.value  # Now it's created / 现在创建
    """

    def __init__(self, factory: Callable[[], T]):
        """
        Initialize lazy wrapper
        初始化延迟包装器

        Args:
            factory: Factory function to create instance / 创建实例的工厂函数
        """
        self._factory = factory
        self._value: Optional[T] = None
        self._lock = threading.RLock()
        self._initialized = False

    @property
    def value(self) -> T:
        """
        Get the wrapped value, creating it if needed
        获取包装的值，如果需要则创建它

        Returns:
            The wrapped instance / 包装的实例
        """
        if not self._initialized:
            with self._lock:
                if not self._initialized:  # Double-checked locking
                    self._value = self._factory()
                    self._initialized = True
        return self._value

    @property
    def is_initialized(self) -> bool:
        """
        Check if value has been created
        检查值是否已创建
        """
        return self._initialized

    def reset(self):
        """
        Reset to uninitialized state (for testing)
        重置为未初始化状态（用于测试）
        """
        with self._lock:
            self._value = None
            self._initialized = False


# Convenience functions / 便利函数


def lazy(factory: Callable[[], T]) -> Lazy[T]:
    """
    Create a lazy wrapper (convenience function)
    创建延迟包装器（便利函数）
    """
    return Lazy(factory)


def lazy_property(factory: Callable[[], T]):
    """
    Decorator for lazy properties
    延迟属性装饰器

    Example:
        class MyClass:
            @lazy_property
            def expensive_resource(self):
                return ExpensiveResource()

        obj = MyClass()
        # expensive_resource not created yet / expensive_resource 尚未创建
        obj.expensive_resource  # Now it's created / 现在创建
        obj.expensive_resource  # Cached, same instance / 缓存，同一实例
    """

    attr_name = f'_lazy_{factory.__name__}'

    def getter(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, factory(self))
        return getattr(self, attr_name)

    return property(getter)
