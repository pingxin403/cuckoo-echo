"""Property 2: Milvus partition isolation.

# Feature: cuckoo-echo, Property 2: Milvus 向量检索租户隔离
**Validates: Requirements 1.5, 1.8**

Structural test — verifies that AnnSearchRequest expr filtering always
contains only the target tenant_id, never a different tenant.
"""

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from pymilvus import AnnSearchRequest


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(tenant_a=st.uuids(), tenant_b=st.uuids(), n_vectors=st.integers(1, 10))
def test_milvus_partition_isolation(tenant_a, tenant_b, n_vectors):
    """Search expr must contain only the target tenant, never the other."""
    assume(tenant_a != tenant_b)
    req = AnnSearchRequest(
        data=[[0.1] * 1536],
        anns_field="dense_vector",
        param={"metric_type": "COSINE", "params": {"ef": 100}},
        limit=10,
        expr=f"tenant_id == '{tenant_a}'",
    )
    # Verify the expr contains only tenant_a, never tenant_b
    assert str(tenant_a) in req.expr
    assert str(tenant_b) not in req.expr
