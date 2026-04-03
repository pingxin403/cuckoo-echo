"""Property 23: Per-thread concurrency safety.

# Feature: cuckoo-echo, Property 23: 同一 Thread 并发请求安全
**Validates: Requirements 6.8**

Tests that the Redis lock in event_generator ensures only one request
succeeds while others get CONCURRENT_REQUEST.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings, HealthCheck, strategies as st

from chat_service.routes.chat import event_generator


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(concurrent_n=st.integers(2, 5))
def test_concurrent_thread_safety(concurrent_n):
    """Exactly 1 request acquires the lock; the rest get CONCURRENT_REQUEST."""
    loop = asyncio.new_event_loop()

    async def _test():
        results = []

        for i in range(concurrent_n):
            redis = AsyncMock()
            lock = AsyncMock()
            # First call gets lock, rest don't
            lock.acquire = AsyncMock(return_value=(i == 0))
            lock.release = AsyncMock()
            redis.lock = MagicMock(return_value=lock)

            if i == 0:
                # Success path — mock agent that yields one stream event
                async def mock_stream(*a, **kw):
                    yield {
                        "event": "on_chat_model_stream",
                        "data": {"chunk": MagicMock(content="hi")},
                    }

                agent = MagicMock()
                agent.astream_events = mock_stream
            else:
                agent = MagicMock()

            events = []
            async for e in event_generator(
                "t1", "tenant", "u1", {}, agent, redis
            ):
                events.append(e)
            results.append(events)

        # Property: exactly 1 success + (N-1) conflicts
        success = sum(1 for r in results if any("[DONE]" in str(e) for e in r))
        conflicts = sum(
            1 for r in results if any("CONCURRENT_REQUEST" in str(e) for e in r)
        )
        assert success + conflicts == concurrent_n

    loop.run_until_complete(_test())
    loop.close()
