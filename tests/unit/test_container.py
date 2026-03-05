"""
Tests for BMContainer — lightweight name-based DI container.
轻量级名称键 DI 容器测试

Task 2.3: Validate register / resolve / has / reset semantics.
"""

import threading
import pytest

from src.core.container import (
    BMContainer,
    get_bm_container,
    reset_bm_container,
)


# ── BMContainer unit tests ─────────────────────────────────────────


class TestBMContainerBasics:
    """Core register / resolve / has / reset behaviour."""

    def test_register_and_resolve(self):
        """Registered instances can be resolved by name."""
        c = BMContainer()
        c.register('greeting', 'hello')
        assert c.resolve('greeting') == 'hello'

    def test_resolve_returns_same_object(self):
        """resolve() returns the exact same object, not a copy."""
        c = BMContainer()
        obj = {'key': 'value'}
        c.register('obj', obj)
        assert c.resolve('obj') is obj

    def test_has_returns_true_for_registered(self):
        c = BMContainer()
        c.register('x', 42)
        assert c.has('x') is True

    def test_has_returns_false_for_missing(self):
        c = BMContainer()
        assert c.has('missing') is False

    def test_resolve_unregistered_raises_key_error(self):
        c = BMContainer()
        with pytest.raises(KeyError, match="not registered"):
            c.resolve('nope')

    def test_register_requires_string_name(self):
        c = BMContainer()
        with pytest.raises(TypeError, match="must be a string"):
            c.register(123, 'bad')  # type: ignore[arg-type]

    def test_overwrite_registration(self):
        """Re-registering the same name replaces the value."""
        c = BMContainer()
        c.register('val', 'first')
        c.register('val', 'second')
        assert c.resolve('val') == 'second'


class TestBMContainerReset:
    """reset() clears all registrations for test isolation."""

    def test_reset_clears_all(self):
        c = BMContainer()
        c.register('a', 1)
        c.register('b', 2)
        c.reset()
        assert c.has('a') is False
        assert c.has('b') is False

    def test_len_after_reset(self):
        c = BMContainer()
        c.register('a', 1)
        assert len(c) == 1
        c.reset()
        assert len(c) == 0


class TestBMContainerRepr:
    """__repr__ shows registered component names."""

    def test_repr_empty(self):
        c = BMContainer()
        assert 'BMContainer' in repr(c)

    def test_repr_with_components(self):
        c = BMContainer()
        c.register('alpha', 1)
        r = repr(c)
        assert 'alpha' in r


class TestBMContainerThreadSafety:
    """Concurrent register / resolve must not corrupt state."""

    def test_concurrent_register_and_resolve(self):
        c = BMContainer()
        errors: list = []

        def writer(idx: int):
            try:
                c.register(f'item_{idx}', idx)
            except Exception as exc:
                errors.append(exc)

        def reader(idx: int):
            try:
                # May or may not be registered yet — that is fine.
                c.has(f'item_{idx}')
            except Exception as exc:
                errors.append(exc)

        threads = []
        for i in range(20):
            threads.append(
                threading.Thread(target=writer, args=(i,))
            )
            threads.append(
                threading.Thread(target=reader, args=(i,))
            )

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # All 20 items should have been written
        for i in range(20):
            assert c.has(f'item_{i}')


# ── Module-level singleton tests ───────────────────────────────────


class TestBMContainerSingleton:
    """get_bm_container / reset_bm_container module-level helpers."""

    def setup_method(self):
        reset_bm_container()

    def teardown_method(self):
        reset_bm_container()

    def test_get_returns_same_instance(self):
        c1 = get_bm_container()
        c2 = get_bm_container()
        assert c1 is c2

    def test_reset_creates_fresh_instance(self):
        c1 = get_bm_container()
        c1.register('temp', 'value')
        reset_bm_container()
        c2 = get_bm_container()
        assert c1 is not c2
        assert c2.has('temp') is False

    def test_reset_is_idempotent(self):
        """Calling reset twice in a row does not raise."""
        reset_bm_container()
        reset_bm_container()
        c = get_bm_container()
        assert isinstance(c, BMContainer)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
