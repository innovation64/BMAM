"""Tests for circuit breaker"""

import asyncio
import pytest
from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
)


@pytest.fixture
def breaker():
    return CircuitBreaker(
        failure_threshold=3, cooldown_seconds=0.1, name="test"
    )


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_starts_closed(self, breaker):
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self, breaker):
        async def success():
            return "ok"

        result = await breaker.call(success())
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self, breaker):
        async def fail():
            raise RuntimeError("api error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_blocks_when_open(self, breaker):
        async def fail():
            raise RuntimeError("api error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        with pytest.raises(CircuitBreakerError):

            async def success():
                return "ok"

            await breaker.call(success())

    @pytest.mark.asyncio
    async def test_half_open_after_cooldown(self, breaker):
        async def fail():
            raise RuntimeError("api error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        await asyncio.sleep(0.15)  # Wait for cooldown
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_recovers_on_success_in_half_open(self, breaker):
        async def fail():
            raise RuntimeError("api error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        await asyncio.sleep(0.15)

        async def success():
            return "recovered"

        result = await breaker.call(success())
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self, breaker):
        """HALF_OPEN state transitions back to OPEN on failure."""
        async def fail():
            raise RuntimeError("api error")

        # Trip the breaker
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        assert breaker.state == CircuitState.OPEN

        # Wait for cooldown to reach HALF_OPEN
        await asyncio.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Fail during HALF_OPEN -> should go back to OPEN
        with pytest.raises(RuntimeError):
            await breaker.call(fail())

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_stats(self, breaker):
        stats = breaker.get_stats()
        assert stats['state'] == 'closed'
        assert stats['failure_count'] == 0
        assert stats['total_calls'] == 0
        assert stats['total_failures'] == 0
        assert stats['total_blocked'] == 0
        assert stats['failure_threshold'] == 3
        assert stats['cooldown_seconds'] == 0.1

    @pytest.mark.asyncio
    async def test_stats_after_failures(self, breaker):
        """Stats reflect failures and blocked calls correctly."""
        async def fail():
            raise RuntimeError("api error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        # One blocked call
        with pytest.raises(CircuitBreakerError):
            async def success():
                return "ok"
            await breaker.call(success())

        stats = breaker.get_stats()
        assert stats['state'] == 'open'
        assert stats['failure_count'] == 3
        assert stats['total_calls'] == 3
        assert stats['total_failures'] == 3
        assert stats['total_blocked'] == 1
        assert stats['state_changes'] == 1

    @pytest.mark.asyncio
    async def test_reset(self, breaker):
        """Reset returns breaker to initial CLOSED state."""
        async def fail():
            raise RuntimeError("api error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker):
        """A success before threshold resets the failure counter."""
        async def fail():
            raise RuntimeError("api error")

        # 2 failures (below threshold of 3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(fail())

        assert breaker._failure_count == 2
        assert breaker.state == CircuitState.CLOSED

        # Success resets the counter
        async def success():
            return "ok"

        await breaker.call(success())
        assert breaker._failure_count == 0
        assert breaker.state == CircuitState.CLOSED
