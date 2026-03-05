"""
Tests for Dependency Injection Container
依赖注入容器测试
"""

import pytest
import threading
from typing import Protocol
from src.core.container import (
    Container,
    ContainerScope,
    Lifecycle,
    get_container,
    reset_container
)


# Test interfaces and implementations
class IService(Protocol):
    """Test service interface"""
    def get_value(self) -> str:
        ...


class ServiceImpl:
    """Test service implementation"""
    def __init__(self):
        self.value = "test_value"
        self.instance_id = id(self)

    def get_value(self) -> str:
        return self.value


class ServiceWithDependency:
    """Test service with dependency"""
    def __init__(self, dependency: ServiceImpl):
        self.dependency = dependency


class TestContainer:
    """Test suite for Container class"""

    def test_container_initialization(self):
        """Test container can be created"""
        container = Container()
        assert container is not None
        assert container.is_registered(Container)

    def test_register_and_resolve_singleton(self):
        """Test singleton registration and resolution"""
        container = Container()
        container.register(IService, ServiceImpl, Lifecycle.SINGLETON)

        # First resolution
        service1 = container.resolve(IService)
        assert isinstance(service1, ServiceImpl)

        # Second resolution should return same instance
        service2 = container.resolve(IService)
        assert service1 is service2
        assert service1.instance_id == service2.instance_id

    def test_register_and_resolve_transient(self):
        """Test transient registration creates new instances"""
        container = Container()
        container.register(IService, ServiceImpl, Lifecycle.TRANSIENT)

        # Each resolution should create new instance
        service1 = container.resolve(IService)
        service2 = container.resolve(IService)

        assert isinstance(service1, ServiceImpl)
        assert isinstance(service2, ServiceImpl)
        assert service1 is not service2
        assert service1.instance_id != service2.instance_id

    def test_register_factory(self):
        """Test factory registration"""
        container = Container()

        call_count = 0

        def factory(c):
            nonlocal call_count
            call_count += 1
            return ServiceImpl()

        container.register_factory(IService, factory, Lifecycle.SINGLETON)

        # Factory should be called once for singleton
        service1 = container.resolve(IService)
        service2 = container.resolve(IService)

        assert call_count == 1
        assert service1 is service2

    def test_register_instance(self):
        """Test instance registration"""
        container = Container()
        instance = ServiceImpl()

        container.register_instance(IService, instance)

        resolved = container.resolve(IService)
        assert resolved is instance

    def test_resolve_unregistered_raises_error(self):
        """Test resolving unregistered interface raises ValueError"""
        container = Container()

        with pytest.raises(ValueError, match="not registered"):
            container.resolve(IService)

    def test_try_resolve_unregistered_returns_none(self):
        """Test try_resolve returns None for unregistered interface"""
        container = Container()

        result = container.try_resolve(IService)
        assert result is None

    def test_is_registered(self):
        """Test is_registered method"""
        container = Container()

        assert not container.is_registered(IService)

        container.register(IService, ServiceImpl)

        assert container.is_registered(IService)

    def test_clear(self):
        """Test clear method"""
        container = Container()
        container.register(IService, ServiceImpl)

        assert container.is_registered(IService)

        container.clear()

        assert not container.is_registered(IService)
        # Container should still be self-registered
        assert container.is_registered(Container)

    def test_fluent_api(self):
        """Test fluent chaining of registrations"""
        container = Container()

        result = (container
                  .register(IService, ServiceImpl)
                  .register_factory(str, lambda c: "test")
                  .register_instance(int, 42))

        assert result is container
        assert container.is_registered(IService)
        assert container.is_registered(str)
        assert container.is_registered(int)

    def test_thread_safety_singleton(self):
        """Test singleton creation is thread-safe"""
        container = Container()
        container.register(IService, ServiceImpl, Lifecycle.SINGLETON)

        instances = []
        lock = threading.Lock()

        def resolve_service():
            service = container.resolve(IService)
            with lock:
                instances.append(service)

        # Create multiple threads resolving simultaneously
        threads = [threading.Thread(target=resolve_service) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance


class TestContainerScope:
    """Test suite for ContainerScope class"""

    def test_scope_creation(self):
        """Test scope can be created from parent"""
        parent = Container()
        scope = parent.create_scope()

        assert isinstance(scope, ContainerScope)
        assert scope._parent is parent

    def test_scope_resolve_from_parent(self):
        """Test scope falls back to parent for unregistered types"""
        parent = Container()
        parent.register(IService, ServiceImpl)

        scope = parent.create_scope()

        # Should resolve from parent
        service = scope.resolve(IService)
        assert isinstance(service, ServiceImpl)

    def test_scope_override_parent(self):
        """Test scope can override parent registrations"""
        parent = Container()
        parent.register_instance(str, "parent_value")

        scope = parent.create_scope()
        scope.register_instance(str, "scope_value")

        # Scope should return its own value
        assert scope.resolve(str) == "scope_value"
        # Parent should still have original value
        assert parent.resolve(str) == "parent_value"

    def test_scope_is_registered(self):
        """Test is_registered checks both scope and parent"""
        parent = Container()
        parent.register(IService, ServiceImpl)

        scope = parent.create_scope()

        # Should find in parent
        assert scope.is_registered(IService)

        # Should find scope-specific registrations
        scope.register_instance(str, "test")
        assert scope.is_registered(str)
        assert not parent.is_registered(str)


class TestGlobalContainer:
    """Test suite for global container functions"""

    def test_get_container_singleton(self):
        """Test get_container returns singleton"""
        reset_container()  # Ensure clean state

        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_reset_container(self):
        """Test reset_container creates new instance"""
        reset_container()

        container1 = get_container()
        container1.register_instance(str, "test")

        reset_container()

        container2 = get_container()

        # Should be different instance
        assert container1 is not container2
        # New container should not have old registrations
        assert not container2.is_registered(str)


class TestFactoryWithContainerAccess:
    """Test factories that need container access"""

    def test_factory_can_access_container(self):
        """Test factory can resolve dependencies from container"""
        container = Container()

        # Register a dependency
        container.register_instance(str, "dependency_value")

        # Register a service that uses the dependency
        def factory(c):
            dep = c.resolve(str)
            service = ServiceImpl()
            service.value = dep
            return service

        container.register_factory(IService, factory)

        service = container.resolve(IService)
        assert service.value == "dependency_value"

    def test_factory_composition(self):
        """Test complex factory composition"""
        container = Container()

        container.register(ServiceImpl, ServiceImpl, Lifecycle.SINGLETON)

        def create_service_with_dep(c):
            dependency = c.resolve(ServiceImpl)
            return ServiceWithDependency(dependency)

        container.register_factory(
            ServiceWithDependency,
            create_service_with_dep
        )

        service = container.resolve(ServiceWithDependency)
        assert isinstance(service.dependency, ServiceImpl)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
