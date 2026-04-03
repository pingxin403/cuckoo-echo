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

## Metrics Endpoint

Prometheus metrics are exposed at `/metrics` on each service.
Grafana dashboards can scrape via the `ServiceMonitor` in `k8s/prometheus-servicemonitor.yaml`.
