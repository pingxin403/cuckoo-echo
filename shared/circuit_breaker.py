"""Circuit breaker pattern for resilient error handling."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit is open and rejecting calls."""
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    timeout: float = 60.0
    half_open_max_calls: int = 3
    _failure_count: int = field(default=0)
    _last_failure_time: float = field(default=0.0)
    _state: CircuitState = field(default=CircuitState.CLOSED)
    _half_open_calls: int = field(default=0)
    _success_count: int = field(default=0)
    _total_calls: int = field(default=0)
    _total_failures: int = field(default=0)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("circuit_breaker_transition", name=self.name, from_state="OPEN", to_state="HALF_OPEN")
        return self._state

    def _record_success(self) -> None:
        self._failure_count = 0
        self._total_calls += 1
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._success_count = 0
                logger.info("circuit_breaker_closed", name=self.name)

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._total_failures += 1
        self._total_calls += 1
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened_from_half_open", name=self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened", name=self.name, failure_count=self._failure_count)

    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError(f"Circuit {self.name} is HALF_OPEN and max calls reached")
            self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def get_stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "success_rate": (self._total_calls - self._total_failures) / max(self._total_calls, 1),
        }

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        logger.info("circuit_breaker_reset", name=self.name)