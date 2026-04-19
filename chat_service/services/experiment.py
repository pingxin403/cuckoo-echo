"""Experiment service for A/B testing."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from typing import Optional

import structlog

from shared.config import get_settings
from shared.db import tenant_db_context
from shared.redis_client import get_redis

log = structlog.get_logger()

EXPERIMENT_TYPES = ["prompt", "model", "feature"]
EXPERIMENT_STATUSES = ["draft", "running", "paused", "completed"]


class ExperimentVariant:
    """Represents an experiment variant with weight."""

    def __init__(self, id: str, weight: int):
        self.id = id
        self.weight = weight


class Experiment:
    """Represents an A/B test experiment."""

    def __init__(
        self,
        id: str,
        name: str,
        experiment_type: str,
        variants: list[ExperimentVariant],
        metric: str,
        status: str = "draft",
        tenant_id: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.experiment_type = experiment_type
        self.variants = variants
        self.metric = metric
        self.status = status
        self.tenant_id = tenant_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.experiment_type,
            "variants": [{"id": v.id, "weight": v.weight} for v in self.variants],
            "metric": self.metric,
            "status": self.status,
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Experiment:
        variants = [
            ExperimentVariant(v["id"], v["weight"]) for v in data.get("variants", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            experiment_type=data["type"],
            variants=variants,
            metric=data["metric"],
            status=data.get("status", "draft"),
            tenant_id=data.get("tenant_id"),
        )


async def create_experiment(
    db_pool,
    name: str,
    experiment_type: str,
    variants: list[dict],
    metric: str,
    tenant_id: str,
) -> Experiment:
    """Create a new experiment.
    
    Args:
        db_pool: AsyncPG connection pool
        name: Experiment name
        experiment_type: Type (prompt, model, feature)
        variants: List of variant dicts with id and weight
        metric: Metric to track
        tenant_id: Tenant identifier
    
    Returns:
        Created Experiment
    """
    experiment_id = str(uuid.uuid4())
    experiment = Experiment(
        id=experiment_id,
        name=name,
        experiment_type=experiment_type,
        variants=[ExperimentVariant(v["id"], v["weight"]) for v in variants],
        metric=metric,
        tenant_id=tenant_id,
    )

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                """
                INSERT INTO experiment (
                    id, name, type, variants, metric, status,
                    tenant_id, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                uuid.UUID(experiment_id),
                name,
                experiment_type,
                json.dumps(variants),
                metric,
                "draft",
                uuid.UUID(tenant_id),
            )

    log.info(
        "experiment_created",
        experiment_id=experiment_id,
        name=name,
        tenant_id=tenant_id,
    )

    return experiment


async def get_experiment(
    db_pool,
    experiment_id: str,
    tenant_id: str,
) -> Optional[Experiment]:
    """Get an experiment by ID.
    
    Args:
        db_pool: AsyncPG connection pool
        experiment_id: Experiment identifier
        tenant_id: Tenant identifier
    
    Returns:
        Experiment or None
    """
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            result = await conn.fetchrow(
                """
                SELECT id, name, type, variants, metric, status, tenant_id
                FROM experiment
                WHERE id = $1 AND tenant_id = $2
                """,
                uuid.UUID(experiment_id),
                uuid.UUID(tenant_id),
            )

            if result:
                return Experiment(
                    id=str(result["id"]),
                    name=result["name"],
                    experiment_type=result["type"],
                    variants=[
                        ExperimentVariant(v["id"], v["weight"])
                        for v in result["variants"]
                    ],
                    metric=result["metric"],
                    status=result["status"],
                )
            return None


async def list_experiments(
    db_pool,
    tenant_id: str,
    status: Optional[str] = None,
) -> list[Experiment]:
    """List experiments for a tenant.
    
    Args:
        db_pool: AsyncPG connection pool
        tenant_id: Tenant identifier
        status: Optional status filter
    
    Returns:
        List of Experiments
    """
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            if status:
                results = await conn.fetch(
                    """
                    SELECT id, name, type, variants, metric, status, tenant_id
                    FROM experiment
                    WHERE tenant_id = $1 AND status = $2
                    ORDER BY created_at DESC
                    """,
                    uuid.UUID(tenant_id),
                    status,
                )
            else:
                results = await conn.fetch(
                    """
                    SELECT id, name, type, variants, metric, status, tenant_id
                    FROM experiment
                    WHERE tenant_id = $1
                    ORDER BY created_at DESC
                    """,
                    uuid.UUID(tenant_id),
                )

            experiments = []
            for row in results:
                experiments.append(
                    Experiment(
                        id=str(row["id"]),
                        name=row["name"],
                        experiment_type=row["type"],
                        variants=[
                            ExperimentVariant(v["id"], v["weight"])
                            for v in row["variants"]
                        ],
                        metric=row["metric"],
                        status=row["status"],
                    )
                )

            return experiments


async def update_experiment_status(
    db_pool,
    experiment_id: str,
    status: str,
    tenant_id: str,
) -> Optional[Experiment]:
    """Update experiment status.
    
    Args:
        db_pool: AsyncPG connection pool
        experiment_id: Experiment identifier
        status: New status (draft, running, paused, completed)
        tenant_id: Tenant identifier
    
    Returns:
        Updated Experiment or None
    """
    if status not in EXPERIMENT_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                """
                UPDATE experiment
                SET status = $1, updated_at = NOW()
                WHERE id = $2 AND tenant_id = $3
                """,
                status,
                uuid.UUID(experiment_id),
                uuid.UUID(tenant_id),
            )

    log.info(
        "experiment_status_updated",
        experiment_id=experiment_id,
        status=status,
    )

    return await get_experiment(db_pool, experiment_id, tenant_id)


async def delete_experiment(
    db_pool,
    experiment_id: str,
    tenant_id: str,
) -> bool:
    """Delete an experiment.
    
    Args:
        db_pool: AsyncPG connection pool
        experiment_id: Experiment identifier
        tenant_id: Tenant identifier
    
    Returns:
        True if deleted
    """
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            result = await conn.execute(
                """
                DELETE FROM experiment
                WHERE id = $1 AND tenant_id = $2
                """,
                uuid.UUID(experiment_id),
                uuid.UUID(tenant_id),
            )

    log.info(
        "experiment_deleted",
        experiment_id=experiment_id,
    )

    return result == "DELETE 1"


def assign_variant(
    tenant_id: str,
    experiment_id: str,
    variants: list[ExperimentVariant],
) -> str:
    """Assign a variant based on hash.
    
    Uses consistent hashing: hash(tenant_id + experiment_id) % 100
    This ensures same user always gets same variant.
    
    Args:
        tenant_id: Tenant identifier
        experiment_id: Experiment identifier
        variants: List of variants with weights
    
    Returns:
        Variant ID
    """
    # Create stable hash from tenant_id + experiment_id
    hash_input = f"{tenant_id}:{experiment_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)

    # Normalize to 0-99
    bucket = hash_value % 100

    # Find variant by weight
    cumulative = 0
    for variant in variants:
        cumulative += variant.weight
        if bucket < cumulative:
            return variant.id

    # Fallback to first variant
    return variants[0].id if variants else "control"


async def track_metric(
    db_pool,
    experiment_id: str,
    variant_id: str,
    metric: str,
    value: float,
    tenant_id: str,
) -> None:
    """Track a metric for an experiment variant.
    
    Args:
        db_pool: AsyncPG connection pool
        experiment_id: Experiment identifier
        variant_id: Variant identifier
        metric: Metric name
        value: Metric value
        tenant_id: Tenant identifier
    """
    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            await conn.execute(
                """
                INSERT INTO experiment_metrics (
                    experiment_id, variant_id, metric, value,
                    tenant_id, created_at
                )
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                uuid.UUID(experiment_id),
                variant_id,
                metric,
                value,
                uuid.UUID(tenant_id),
            )

    log.debug(
        "experiment_metric_tracked",
        experiment_id=experiment_id,
        variant_id=variant_id,
        metric=metric,
        value=value,
    )


async def get_experiment_results(
    db_pool,
    experiment_id: str,
    tenant_id: str,
) -> Optional[dict]:
    """Get experiment results with statistical significance.
    
    Args:
        db_pool: AsyncPG connection pool
        experiment_id: Experiment identifier
        tenant_id: Tenant identifier
    
    Returns:
        Results dict with variant stats and significance
    """
    experiment = await get_experiment(db_pool, experiment_id, tenant_id)
    if not experiment:
        return None

    async with db_pool.acquire() as conn:
        async with tenant_db_context(conn, tenant_id):
            # Get metrics per variant
            results = await conn.fetch(
                """
                SELECT variant_id, metric, COUNT(*) as count, AVG(value) as avg
                FROM experiment_metrics
                WHERE experiment_id = $1
                GROUP BY variant_id, metric
                """,
                uuid.UUID(experiment_id),
            )

            variant_stats = {}
            control_count = 0
            control_avg = 0

            for row in results:
                variant_id = row["variant_id"]
                count = row["count"] or 0
                avg = row["avg"] or 0

                variant_stats[variant_id] = {
                    "count": count,
                    "avg": avg,
                }

                if variant_id == "control":
                    control_count = count
                    control_avg = avg

            # Calculate significance
            significance = 0.0
            if len(variant_stats) >= 2:
                significance = calculate_significance(
                    control_count,
                    control_avg,
                    variant_stats,
                )

    return {
        "experiment_id": experiment_id,
        "status": experiment.status,
        "results": variant_stats,
        "significance": significance,
    }


def calculate_significance(
    control_count: int,
    control_avg: float,
    variant_stats: dict,
) -> float:
    """Calculate statistical significance using simple Z-test.
    
    Args:
        control_count: Control sample size
        control_avg: Control average
        variant_stats: Dict of variant stats
    
    Returns:
        Significance (0-1)
    """
    if control_count < 30:
        return 0.0

    # Find non-control variant
    treatment = None
    for vid, stats in variant_stats.items():
        if vid != "control":
            treatment = stats
            break

    if not treatment or treatment["count"] < 30:
        return 0.0

    # Pooled standard error
    pooled_se = math.sqrt(
        (1 / control_count) + (1 / treatment["count"])
    )

    if pooled_se == 0:
        return 0.0

    # Z-score
    z = abs(control_avg - treatment["avg"]) / pooled_se

    # Convert to significance (approximate)
    if z > 2.576:
        return 0.99
    elif z > 1.96:
        return 0.95
    elif z > 1.645:
        return 0.90
    else:
        return min(0.85, z / 2)