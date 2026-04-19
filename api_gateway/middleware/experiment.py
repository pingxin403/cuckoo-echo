"""Experiment middleware for traffic splitting."""

from __future__ import annotations

import hashlib
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from chat_service.services.experiment import ExperimentVariant, assign_variant


class ExperimentMiddleware(BaseHTTPMiddleware):
    """Middleware to assign experiment variants to requests.
    
    Uses cookie-based consistent hashing to assign stable variants.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if no tenant
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # Get experiment ID from query or header
        experiment_id = request.query_params.get("experiment_id")
        if not experiment_id:
            experiment_id = request.headers.get("X-Experiment-ID")

        if experiment_id:
            # Get variants from request state (set by route handler)
            experiment = getattr(request.state, "experiment", None)
            if experiment and experiment.variants:
                variant_id = assign_variant(
                    tenant_id,
                    experiment_id,
                    experiment.variants,
                )

                # Set variant in state for downstream use
                request.state.experiment_variant = variant_id

                # Set cookie for client persistence
                response = await call_next(request)
                response.set_cookie(
                    f"experiment_{experiment_id}",
                    variant_id,
                    httponly=True,
                    samesite="lax",
                    max_age=30 * 24 * 60 * 60,  # 30 days
                )
                return response

        return await call_next(request)


def get_experiment_variant(request: Request, experiment_id: str) -> str:
    """Get the assigned variant for an experiment from cookie or assignment.
    
    Args:
        request: FastAPI request
        experiment_id: Experiment identifier
    
    Returns:
        Variant ID (default: control)
    """
    # Check cookie first
    cookie_key = f"experiment_{experiment_id}"
    variant = request.cookies.get(cookie_key)
    if variant:
        return variant

    # Check request state
    return getattr(request.state, "experiment_variant", "control")