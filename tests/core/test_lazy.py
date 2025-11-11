"""
Tests for Lazy Initialization
延迟初始化测试
"""

import pytest
import threading
from BMAM.src.core.lazy import Lazy, lazy, lazy_property


class ExpensiveResource:
    """Mock expensive resource for testing"""
    creation_count = 0

    def __init__(self):
        ExpensiveResource.creation_count += 1
        self.instance_id = id(self)
        self.value = "expensive_value"


class TestLazy:
    """Test suite for Lazy class"""

    def setup_method(self):
        """Reset counter before each test"""
        ExpensiveResource.creation_count = 0

    def test_lazy_defers_creation(self):
        """Test lazy wrapper does not create instance immediately"""
        lazy_resource = Lazy(lambda: ExpensiveResource())

        # Instance should not be created yet
        assert ExpensiveResource.creation_count == 0
        assert not lazy_resource.is_initialized

    def test_lazy_creates_on_first_access(self):
        """Test lazy wrapper creates instance on first value access"""
        lazy_resource = Lazy(lambda: ExpensiveResource())

        # Access value
        resource = lazy_resource.value

        assert ExpensiveResource.creation_count == 1
        assert lazy_resource.is_initialized
        assert isinstance(resource, ExpensiveResource)

    def test_lazy_caches_instance(self):
        """Test lazy wrapper returns same instance on repeated access"""
        lazy_resource = Lazy(lambda: ExpensiveResource())

        # Access multiple times
        resource1 = lazy_resource.value
        resource2 = lazy_resource.value
        resource3 = lazy_resource.value

        # Should only create once
        assert ExpensiveResource.creation_count == 1
        assert resource1 is resource2
        assert resource2 is resource3
        assert resource1.instance_id == resource2.instance_id

    def test_lazy_reset(self):
        """Test lazy wrapper can be reset"""
        lazy_resource = Lazy(lambda: ExpensiveResource())

        # Create instance
        resource1 = lazy_resource.value
        assert ExpensiveResource.creation_count == 1

        # Reset
        lazy_resource.reset()
        assert not lazy_resource.is_initialized

        # Create new instance
        resource2 = lazy_resource.value
        assert ExpensiveResource.creation_count == 2
        assert resource1 is not resource2

    def test_lazy_thread_safety(self):
        """Test lazy wrapper is thread-safe"""
        lazy_resource = Lazy(lambda: ExpensiveResource())
        instances = []
        lock = threading.Lock()

        def access_lazy():
            resource = lazy_resource.value
            with lock:
                instances.append(resource)

        # Create multiple threads accessing simultaneously
        threads = [threading.Thread(target=access_lazy) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should only create one instance
        assert ExpensiveResource.creation_count == 1
        # All threads should get the same instance
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance


class TestLazyFunction:
    """Test suite for lazy() convenience function"""

    def setup_method(self):
        """Reset counter before each test"""
        ExpensiveResource.creation_count = 0

    def test_lazy_function_creates_wrapper(self):
        """Test lazy() function creates Lazy wrapper"""
        lazy_resource = lazy(lambda: ExpensiveResource())

        assert isinstance(lazy_resource, Lazy)
        assert not lazy_resource.is_initialized

    def test_lazy_function_works_same_as_class(self):
        """Test lazy() function behaves same as Lazy class"""
        lazy_resource = lazy(lambda: ExpensiveResource())

        resource = lazy_resource.value

        assert ExpensiveResource.creation_count == 1
        assert lazy_resource.is_initialized


class TestLazyProperty:
    """Test suite for lazy_property decorator"""

    def setup_method(self):
        """Reset counter before each test"""
        ExpensiveResource.creation_count = 0

    def test_lazy_property_decorator(self):
        """Test lazy_property decorator defers creation"""

        class MyClass:
            @lazy_property
            def expensive_resource(self):
                return ExpensiveResource()

        obj = MyClass()

        # Property should not be created yet
        assert ExpensiveResource.creation_count == 0

    def test_lazy_property_creates_on_access(self):
        """Test lazy_property creates value on first access"""

        class MyClass:
            @lazy_property
            def expensive_resource(self):
                return ExpensiveResource()

        obj = MyClass()

        # Access property
        resource = obj.expensive_resource

        assert ExpensiveResource.creation_count == 1
        assert isinstance(resource, ExpensiveResource)

    def test_lazy_property_caches_value(self):
        """Test lazy_property caches value across accesses"""

        class MyClass:
            @lazy_property
            def expensive_resource(self):
                return ExpensiveResource()

        obj = MyClass()

        # Access multiple times
        resource1 = obj.expensive_resource
        resource2 = obj.expensive_resource
        resource3 = obj.expensive_resource

        # Should only create once
        assert ExpensiveResource.creation_count == 1
        assert resource1 is resource2
        assert resource2 is resource3

    def test_lazy_property_per_instance(self):
        """Test lazy_property creates separate values per instance"""

        class MyClass:
            @lazy_property
            def expensive_resource(self):
                return ExpensiveResource()

        obj1 = MyClass()
        obj2 = MyClass()

        resource1 = obj1.expensive_resource
        resource2 = obj2.expensive_resource

        # Should create one per instance
        assert ExpensiveResource.creation_count == 2
        assert resource1 is not resource2

    def test_lazy_property_with_self_reference(self):
        """Test lazy_property can access self"""

        class MyClass:
            def __init__(self, value):
                self.value = value

            @lazy_property
            def derived_value(self):
                return f"derived_{self.value}"

        obj = MyClass("test")
        result = obj.derived_value

        assert result == "derived_test"

    def test_multiple_lazy_properties(self):
        """Test multiple lazy properties in same class"""

        class MyClass:
            @lazy_property
            def resource1(self):
                return ExpensiveResource()

            @lazy_property
            def resource2(self):
                return ExpensiveResource()

        obj = MyClass()

        r1 = obj.resource1
        r2 = obj.resource2

        assert ExpensiveResource.creation_count == 2
        assert r1 is not r2


class TestLazyUseCases:
    """Test real-world use cases for lazy initialization"""

    def test_lazy_singleton_pattern(self):
        """Test using Lazy for singleton pattern"""
        _instance = None

        def get_resource():
            nonlocal _instance
            if _instance is None:
                _instance = Lazy(lambda: ExpensiveResource())
            return _instance.value

        # Multiple calls should return same instance
        r1 = get_resource()
        r2 = get_resource()

        assert r1 is r2

    def test_lazy_config_loading(self):
        """Test lazy loading of configuration"""

        class Config:
            def __init__(self):
                self.loaded = True

        class Application:
            def __init__(self):
                self._config = Lazy(lambda: Config())

            @property
            def config(self):
                return self._config.value

        app = Application()

        # Config not loaded yet
        assert not app._config.is_initialized

        # Access config
        config = app.config
        assert config.loaded
        assert app._config.is_initialized

    def test_lazy_dependency_injection(self):
        """Test lazy initialization in dependency injection"""

        class Database:
            def __init__(self):
                self.connected = True

        class Service:
            def __init__(self):
                self._db = Lazy(lambda: Database())

            def execute(self):
                # Database only created when actually needed
                return self._db.value.connected

        service = Service()
        assert not service._db.is_initialized

        result = service.execute()
        assert result is True
        assert service._db.is_initialized


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
