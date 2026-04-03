# Production Deployment Guide

This guide covers deploying Cuckoo-Echo to a production Kubernetes environment.

## Environment Variables Checklist

| Variable | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (via PgBouncer) | `postgresql://user:pass@pgbouncer:6432/cuckoo` |
| `REDIS_URL` | ✅ | Redis connection string | `redis://:pass@redis-cluster:6379/0` |
| `MILVUS_URI` | ✅ | Milvus gRPC endpoint | `http://milvus-proxy:19530` |
| `MINIO_ENDPOINT` | ✅ | MinIO/S3-compatible endpoint | `minio.storage:9000` |
| `MINIO_ACCESS_KEY` | ✅ | MinIO access key | — |
| `MINIO_SECRET_KEY` | ✅ | MinIO secret key | — |
| `MINIO_BUCKET` | ✅ | Object storage bucket name | `cuckoo-echo` |
| `LLM_API_KEY` | ✅ | LLM provider API key | `sk-...` |
| `LLM_API_BASE` | ❌ | Custom LLM API base URL | `https://api.deepseek.com/v1` |
| `LLM_PRIMARY_MODEL` | ❌ | Primary LLM model name | `deepseek-chat` |
| `LLM_FALLBACK_MODEL` | ❌ | Fallback LLM model name | `qwen-plus` |
| `LANGFUSE_PUBLIC_KEY` | ❌ | Langfuse observability public key | — |
| `LANGFUSE_SECRET_KEY` | ❌ | Langfuse observability secret key | — |
| `LANGFUSE_HOST` | ❌ | Langfuse host URL | `https://langfuse.example.com` |
| `ENVIRONMENT` | ❌ | Runtime environment | `production` |
| `LOG_LEVEL` | ❌ | Logging level | `INFO` |

## LLM API Key Configuration

Cuckoo-Echo uses [LiteLLM](https://docs.litellm.ai/) as the LLM gateway, supporting 100+ providers.

### DeepSeek

```bash
LLM_API_KEY=sk-your-deepseek-key
LLM_API_BASE=https://api.deepseek.com/v1
LLM_PRIMARY_MODEL=deepseek-chat
LLM_FALLBACK_MODEL=deepseek-chat
```

### Qwen (Alibaba Cloud)

```bash
LLM_API_KEY=sk-your-qwen-key
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_PRIMARY_MODEL=qwen-plus
LLM_FALLBACK_MODEL=qwen-turbo
```

### OpenAI

```bash
LLM_API_KEY=sk-your-openai-key
LLM_API_BASE=              # leave empty for default
LLM_PRIMARY_MODEL=gpt-4o
LLM_FALLBACK_MODEL=gpt-4o-mini
```

### Custom / Self-Hosted (OpenAI-compatible)

```bash
LLM_API_KEY=your-key
LLM_API_BASE=http://your-vllm-server:8000/v1
LLM_PRIMARY_MODEL=openai/your-model-name
LLM_FALLBACK_MODEL=openai/your-fallback-model
```

## PgBouncer Setup

Cuckoo-Echo requires PgBouncer in **transaction mode** because:
- `asyncpg` caches prepared statements by default, but PgBouncer transaction mode switches backend connections per transaction
- `SET LOCAL app.current_tenant` for RLS requires transaction-scoped connections

### Configuration (`pgbouncer.ini`)

```ini
[databases]
cuckoo = host=postgres port=5432 dbname=cuckoo

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3
server_reset_query = DISCARD ALL
```

### K8s ConfigMap

See `k8s/pgbouncer-configmap.yaml` for the Kubernetes ConfigMap definition.

Key points:
- `pool_mode = transaction` is mandatory for RLS `SET LOCAL` to work
- `statement_cache_size=0` is set in asyncpg connection params to avoid prepared statement conflicts
- `max_client_conn = 1000` supports up to 1000 concurrent application connections

## Milvus Cluster

### Recommended Topology

| Component | Replicas | Resources |
|---|---|---|
| Proxy | 2 | 2 CPU, 4Gi RAM |
| Query Node | 3 | 4 CPU, 16Gi RAM |
| Data Node | 2 | 2 CPU, 8Gi RAM |
| Index Node | 1 | 4 CPU, 8Gi RAM |
| etcd | 3 | 1 CPU, 2Gi RAM |
| MinIO | 1+ | Storage-dependent |

### Configuration Notes

- Set `num_partitions=64` for tenant partition key isolation
- HNSW index on `dense_vector` with `ef_construction=256`, `M=16`
- `SPARSE_INVERTED_INDEX` on `sparse_vector` for BM25
- Enable Chinese analyzer: `analyzer_params={"type": "chinese"}`
- Collection: `knowledge_chunks` with partition key on `tenant_id`

## Redis Cluster

### Production Setup

Use Redis Cluster (minimum 6 nodes: 3 masters + 3 replicas) for high availability.

```bash
REDIS_URL=redis://:password@redis-node-1:6379,redis-node-2:6379,redis-node-3:6379/0
```

### Key Namespacing

All Redis keys use the `cuckoo:` prefix:
- `cuckoo:ratelimit:{tenant_id}:{user_id}` — rate limiting counters
- `cuckoo:lock:{thread_id}` — concurrent request locks (TTL 90s)
- `cuckoo:cache:*` — semantic cache entries

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.28+
- `kubectl` configured with cluster access
- Container registry with built images
- Secrets created for database credentials, API keys

### 1. Create Namespace and Secrets

```bash
kubectl create namespace cuckoo-echo

kubectl create secret generic cuckoo-secrets -n cuckoo-echo \
  --from-literal=DATABASE_URL='postgresql://user:pass@pgbouncer:6432/cuckoo' \
  --from-literal=REDIS_URL='redis://:pass@redis:6379/0' \
  --from-literal=LLM_API_KEY='sk-your-key' \
  --from-literal=MINIO_ACCESS_KEY='access-key' \
  --from-literal=MINIO_SECRET_KEY='secret-key' \
  --from-literal=LANGFUSE_SECRET_KEY='lf-secret'
```

### 2. Deploy Infrastructure

```bash
# PgBouncer
kubectl apply -f k8s/pgbouncer-configmap.yaml -n cuckoo-echo

# Milvus — use Milvus Operator or Helm chart
helm install milvus milvus/milvus -n cuckoo-echo \
  --set cluster.enabled=true \
  --set queryNode.replicas=3
```

### 3. Run Migrations

```bash
kubectl run migrate --rm -it --image=your-registry/cuckoo-echo:latest \
  -n cuckoo-echo \
  --env="DATABASE_URL=postgresql://user:pass@pgbouncer:6432/cuckoo" \
  -- uv run alembic upgrade head
```

### 4. Deploy Application Services

```bash
kubectl apply -f k8s/api-gateway-deployment.yaml -n cuckoo-echo
kubectl apply -f k8s/chat-service-deployment.yaml -n cuckoo-echo
kubectl apply -f k8s/admin-service-deployment.yaml -n cuckoo-echo
kubectl apply -f k8s/knowledge-pipeline-deployment.yaml -n cuckoo-echo
```

### 5. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n cuckoo-echo

# Check service health
kubectl port-forward svc/api-gateway 8000:8000 -n cuckoo-echo
curl http://localhost:8000/health
```

### Service Scaling

| Service | Min Replicas | Max Replicas | Scale Metric |
|---|---|---|---|
| API Gateway | 2 | 20 | CPU 70% |
| Chat Service | 2 | 20 | CPU 70% |
| Admin Service | 1 | 5 | CPU 70% |
| Knowledge Pipeline | 1 | 1 | N/A (SKIP LOCKED) |

- Chat Service uses `terminationGracePeriodSeconds: 120` to allow in-flight SSE streams to complete
- Knowledge Pipeline runs as a single replica — `SELECT FOR UPDATE SKIP LOCKED` handles concurrency safely

## Monitoring Setup

### Prometheus

Deploy the ServiceMonitor for auto-discovery:

```bash
kubectl apply -f k8s/prometheus-servicemonitor.yaml -n cuckoo-echo
```

### Key Metrics

| Metric | Description | Alert Threshold |
|---|---|---|
| `http_request_duration_seconds` | Request latency histogram | P95 > 2s |
| `chat_ttft_seconds` | Time to first token | P95 > 1.2s |
| `llm_tokens_total` | Token consumption counter | — |
| `knowledge_pipeline_failed` | Failed document processing | > 0 |
| `asr_handoff_ms` | ASR to agent handoff latency | P95 > 500ms |

### Langfuse Integration

Set the following environment variables for LLM observability:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://langfuse.your-domain.com
```

Langfuse provides:
- Per-request trace visualization with `trace_id = thread_id`
- Token usage tracking per model
- Latency breakdown by LangGraph node
- Cost attribution per tenant

### Grafana Dashboards

Recommended dashboard panels:
1. Request rate and error rate by service
2. TTFT P50/P95/P99 histogram
3. Token consumption by tenant (daily/weekly)
4. RAG retrieval latency and cache hit rate
5. HITL escalation rate and resolution time
6. Knowledge pipeline processing queue depth
