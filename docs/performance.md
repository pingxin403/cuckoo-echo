# Performance Baseline

## TTFT SLA Targets

| Scenario     | P50 Target | P95 Target | P99 Target |
|-------------|-----------|-----------|-----------|
| Text chat   | 200ms     | 500ms     | 800ms     |
| RAG query   | 500ms     | 1200ms    | 2000ms    |
| Multimodal  | 1000ms    | 3000ms    | 5000ms    |

## Load Testing

Run load tests with Locust:

```bash
# Chat load test (1000 concurrent users)
locust -f tests/load/locustfile.py --host http://localhost:8000 --users 1000 --spawn-rate 50

# RAG load test
locust -f tests/load/rag_load.py --host http://localhost:8000 --users 500 --spawn-rate 25
```

## Alerting

TTFT breaches are logged when P95 exceeds 2x the SLA threshold per scenario.
See `shared/metrics.py` for `check_ttft_sla()` implementation.

## Load Test Results

> **Placeholder**: Run the load tests below and record results here after execution.

### Chat Endpoint (SSE Streaming)

| Metric         | Value   | Notes                        |
|---------------|---------|------------------------------|
| Concurrent Users | —     | Target: 100–1000             |
| TTFT P50       | —       | Target: < 200ms (text chat)  |
| TTFT P95       | —       | Target: < 500ms (text chat)  |
| TTFT P99       | —       | Target: < 800ms (text chat)  |
| Throughput     | — req/s | Measured at steady state      |
| Error Rate     | —       | Target: < 0.1%               |

### RAG Query

| Metric         | Value   | Notes                        |
|---------------|---------|------------------------------|
| Concurrent Users | —     | Target: 500                  |
| TTFT P50       | —       | Target: < 500ms              |
| TTFT P95       | —       | Target: < 1200ms             |
| TTFT P99       | —       | Target: < 2000ms             |
| Throughput     | — req/s | Measured at steady state      |

### How to Run

```bash
# Chat load test (100 users, ramp 10/s, 60s duration)
uv run locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 60s --host http://localhost:8000

# RAG load test
uv run locust -f tests/load/rag_load.py --headless -u 500 -r 25 -t 60s --host http://localhost:8000
```

Update this section with actual results after each load test execution.

## Metrics Endpoint

Prometheus metrics are exposed at `/metrics` on each service.
Grafana dashboards can scrape via the `ServiceMonitor` in `k8s/prometheus-servicemonitor.yaml`.
