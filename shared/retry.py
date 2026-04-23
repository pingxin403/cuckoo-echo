"""Retry decorator with exponential backoff for resilient error handling."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, Type

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)


def calculate_delay(config: RetryConfig, attempt: int) -> float:
    delay = min(config.base_delay * (config.exponential_base ** attempt), config.max_delay)
    if config.jitter:
        delay = delay * (0.5 + random.random())
    return delay


def async_retry(
    config: Optional[RetryConfig] = None,
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
        )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(config, attempt)
                        logger.warning(
                            "retry_attempt",
                            func=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=config.max_attempts,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=config.max_attempts,
                            error=str(e),
                        )
            raise last_exception

        return wrapper

    return decorator


def sync_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(config, attempt)
                        logger.warning(
                            "retry_attempt",
                            func=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=config.max_attempts,
                            delay=delay,
                            error=str(e),
                        )
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=config.max_attempts,
                            error=str(e),
                        )
            raise last_exception

        return wrapper

    return decorator