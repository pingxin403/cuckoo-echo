"""Prometheus metrics for Cuckoo-Echo services."""
from __future__ import annotations

import structlog

log = structlog.get_logger()

# TTFT SLA thresholds in milliseconds per scenario
TTFT_SLA = {"text": 500, "rag": 1200, "multimodal": 3000}

# Lazy-loaded to avoid import errors when prometheus_client not installed
_instrumentator = None


def setup_prometheus(app, service_name: str = "cuckoo-echo"):
    """Instrument a FastAPI app with Prometheus metrics."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/metrics"],
        )
        instrumentator.instrument(app).expose(app, endpoint="/metrics")
        log.info("prometheus_enabled", service=service_name)
    except ImportError:
        log.info("prometheus_not_installed", msg="metrics endpoint disabled")


def check_ttft_sla(ttft_ms: float, scenario: str = "text"):
    """Log warning if TTFT exceeds 2x SLA threshold."""
    threshold = TTFT_SLA.get(scenario, 500) * 2
    if ttft_ms > threshold:
        log.warning(
            "ttft_sla_breach",
            ttft_ms=ttft_ms,
            scenario=scenario,
            threshold=threshold,
        )
