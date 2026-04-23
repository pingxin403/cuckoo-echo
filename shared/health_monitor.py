"""Service health monitoring with circuit breaker states and error rate tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ServiceHealth:
    status: ServiceStatus
    latency_ms: float = 0.0
    error_rate: float = 0.0
    last_check: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthResponse:
    status: ServiceStatus
    timestamp: str
    services: dict[str, ServiceHealth]
    circuit_breakers: dict[str, CircuitBreakerState]
    error_rates: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "services": {
                name: {
                    "status": h.status.value,
                    "latency_ms": h.latency_ms,
                    "error_rate": h.error_rate,
                    "last_check": h.last_check.isoformat(),
                    "details": h.details,
                }
                for name, h in self.services.items()
            },
            "circuit_breakers": {
                name: state.value for name, state in self.circuit_breakers.items()
            },
            "error_rates": self.error_rates,
        }


class HealthMonitor:
    def __init__(self):
        self._services: dict[str, ServiceHealth] = {}
        self._circuit_breakers: dict[str, CircuitBreakerState] = {}
        self._total_requests = 0
        self._failed_requests = 0
        self._start_time = time.time()

    async def check_milvus(self) -> ServiceHealth:
        from shared.milvus_client import milvus_client

        start = time.perf_counter()
        try:
            if milvus_client and hasattr(milvus_client, "client"):
                milvus_client.client.collection_exists("knowledge_chunks")
            latency = (time.perf_counter() - start) * 1000
            return ServiceHealth(
                status=ServiceStatus.HEALTHY,
                latency_ms=latency,
                details={"collection_count": 1},
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("milvus_health_check_failed", error=str(e))
            return ServiceHealth(
                status=ServiceStatus.DEGRADED,
                latency_ms=latency,
                error_rate=1.0,
                details={"error": str(e)[:100]},
            )

    async def check_redis(self) -> ServiceHealth:
        from shared.redis_client import get_redis

        start = time.perf_counter()
        try:
            redis = await get_redis()
            await redis.ping()
            latency = (time.perf_counter() - start) * 1000
            return ServiceHealth(
                status=ServiceStatus.HEALTHY,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("redis_health_check_failed", error=str(e))
            return ServiceHealth(
                status=ServiceStatus.DEGRADED,
                latency_ms=latency,
                error_rate=1.0,
                details={"error": str(e)[:100]},
            )

    async def check_embedding(self) -> ServiceHealth:
        from shared.embedding_service import embedding_service

        start = time.perf_counter()
        try:
            if embedding_service is None:
                return ServiceHealth(
                    status=ServiceStatus.DEGRADED,
                    latency_ms=0,
                    details={"error": "embedding_service not initialized"},
                )
            await embedding_service.embed("health check")
            latency = (time.perf_counter() - start) * 1000
            status = ServiceStatus.HEALTHY if latency < 1000 else ServiceStatus.DEGRADED
            return ServiceHealth(
                status=status,
                latency_ms=latency,
                details={"model": "sentence-transformers"},
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("embedding_health_check_failed", error=str(e))
            return ServiceHealth(
                status=ServiceStatus.UNHEALTHY,
                latency_ms=latency,
                error_rate=1.0,
                details={"error": str(e)[:100]},
            )

    async def check_database(self) -> ServiceHealth:
        from shared.db import db_pool

        start = time.perf_counter()
        try:
            if db_pool is None:
                return ServiceHealth(
                    status=ServiceStatus.DEGRADED,
                    latency_ms=0,
                    details={"error": "db_pool not initialized"},
                )
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            latency = (time.perf_counter() - start) * 1000
            return ServiceHealth(
                status=ServiceStatus.HEALTHY,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("database_health_check_failed", error=str(e))
            return ServiceHealth(
                status=ServiceStatus.DEGRADED,
                latency_ms=latency,
                error_rate=1.0,
                details={"error": str(e)[:100]},
            )

    def update_circuit_breaker(self, name: str, state: CircuitBreakerState) -> None:
        self._circuit_breakers[name] = state

    def record_request(self, success: bool) -> None:
        self._total_requests += 1
        if not success:
            self._failed_requests += 1

    def compute_error_rate(self) -> float:
        if self._total_requests == 0:
            return 0.0
        return self._failed_requests / self._total_requests

    async def get_health(self) -> HealthResponse:
        services = {}

        services["milvus"] = await self.check_milvus()
        services["redis"] = await self.check_redis()
        services["embedding"] = await self.check_embedding()
        services["database"] = await self.check_database()

        critical_unhealthy = sum(
            1 for s in services.values() if s.status == ServiceStatus.UNHEALTHY
        )
        critical_degraded = sum(
            1 for s in services.values() if s.status == ServiceStatus.DEGRADED
        )

        if critical_unhealthy > 0:
            overall = ServiceStatus.UNHEALTHY
        elif critical_degraded > 1:
            overall = ServiceStatus.UNHEALTHY
        elif critical_degraded > 0:
            overall = ServiceStatus.DEGRADED
        else:
            overall = ServiceStatus.HEALTHY

        return HealthResponse(
            status=overall,
            timestamp=datetime.utcnow().isoformat() + "Z",
            services=services,
            circuit_breakers=self._circuit_breakers.copy(),
            error_rates={
                "total_requests": float(self._total_requests),
                "failed_requests": float(self._failed_requests),
                "error_rate": self.compute_error_rate(),
            },
        )


health_monitor = HealthMonitor()