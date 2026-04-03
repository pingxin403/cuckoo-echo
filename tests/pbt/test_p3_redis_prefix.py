"""Property 3: Redis key prefix isolation.

# Feature: cuckoo-echo, Property 3: Redis 缓存 Key 前缀隔离
**Validates: Requirements 1.6**
"""

from hypothesis import given, settings, HealthCheck, strategies as st

from shared.db import lock_key, ratelimit_key


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(tenant_id=st.uuids(), user_id=st.uuids())
def test_ratelimit_key_prefix(tenant_id, user_id):
    """Every ratelimit key starts with 'cuckoo:' and contains tenant + user IDs."""
    key = ratelimit_key(str(tenant_id), str(user_id))
    assert key.startswith("cuckoo:")
    assert str(tenant_id) in key
    assert str(user_id) in key


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(thread_id=st.uuids())
def test_lock_key_prefix(thread_id):
    """Every lock key starts with 'cuckoo:' and contains the thread ID."""
    key = lock_key(str(thread_id))
    assert key.startswith("cuckoo:")
    assert str(thread_id) in key
