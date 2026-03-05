"""
LLM API Circuit Breaker
LLM API 熔断器

Prevents cascading failures when the LLM API is unavailable.
当 LLM API 不可用时防止级联故障。

State machine:
  CLOSED → OPEN (after failure_threshold consecutive failures)
  OPEN → HALF_OPEN (after cooldown_seconds)
  HALF_OPEN → CLOSED (on success) or OPEN (on failure)
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is open and requests are blocked."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for LLM API calls.

    Args:
        failure_threshold: Number of consecutive failures before opening circuit
        cooldown_seconds: Seconds to wait before transitioning from OPEN to HALF_OPEN
        name: Name for logging purposes
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        name: str = "llm_api"
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_blocked = 0
        self._state_changes = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may transition OPEN -> HALF_OPEN based on time)."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.cooldown_seconds:
                return CircuitState.HALF_OPEN
        return self._state

    async def call(self, coro):
        """
        Execute an async operation through the circuit breaker.

        Args:
            coro: The coroutine to execute

        Returns:
            The result of the coroutine

        Raises:
            CircuitBreakerError: If the circuit is open
        """
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                self._total_blocked += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Blocked after {self._failure_count} consecutive failures. "
                    f"Will retry after {self.cooldown_seconds}s cooldown."
                )

            if current_state == CircuitState.HALF_OPEN:
                # Materialize the time-based transition so _on_success/_on_failure
                # can inspect _state directly.
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit breaker '{self.name}': "
                    f"HALF_OPEN - attempting trial request"
                )

        self._total_calls += 1

        try:
            result = await coro
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self._state in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
                if self._failure_count > 0:
                    logger.info(
                        f"Circuit breaker '{self.name}': Reset after success "
                        f"(was at {self._failure_count} failures)"
                    )
                self._failure_count = 0
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self._state_changes += 1
                    logger.info(
                        f"Circuit breaker '{self.name}': HALF_OPEN -> CLOSED"
                    )

    async def _on_failure(self, error: Exception):
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._state_changes += 1
                logger.warning(
                    f"Circuit breaker '{self.name}': HALF_OPEN -> OPEN "
                    f"(trial request failed: {error})"
                )
            elif (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self.failure_threshold
            ):
                self._state = CircuitState.OPEN
                self._state_changes += 1
                logger.warning(
                    f"Circuit breaker '{self.name}': CLOSED -> OPEN "
                    f"(reached {self.failure_threshold} consecutive failures)"
                )

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self._failure_count,
            'total_calls': self._total_calls,
            'total_failures': self._total_failures,
            'total_blocked': self._total_blocked,
            'state_changes': self._state_changes,
            'failure_threshold': self.failure_threshold,
            'cooldown_seconds': self.cooldown_seconds,
        }

    def reset(self):
        """Reset the circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None


# Global circuit breaker instance
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
