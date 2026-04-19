"""Experiment API routes for A/B testing."""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

log = structlog.get_logger()

router = APIRouter()


class VariantRequest(BaseModel):
    """Request model for experiment variant."""
    id: str = Field(..., description="Variant identifier")
    weight: int = Field(..., ge=0, le=100, description="Variant weight (0-100)")


class CreateExperimentRequest(BaseModel):
    """Request model for creating an experiment."""
    name: str = Field(..., description="Experiment name")
    experiment_type: str = Field(..., description="Type: prompt, model, or feature")
    variants: list[VariantRequest] = Field(..., description="List of variants with weights")
    metric: str = Field(..., description="Metric to track (e.g., conversion_rate)")


class ExperimentResponse(BaseModel):
    """Response model for an experiment."""
    id: str = Field(..., description="Experiment identifier")
    name: str = Field(..., description="Experiment name")
    experiment_type: str = Field(..., description="Experiment type")
    variants: list[VariantRequest] = Field(..., description="Experiment variants")
    metric: str = Field(..., description="Metric being tracked")
    status: str = Field(..., description="Experiment status")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")


class UpdateExperimentRequest(BaseModel):
    """Request model for updating an experiment."""
    status: Optional[str] = Field(None, description="New status")


class ExperimentResultsResponse(BaseModel):
    """Response model for experiment results."""
    experiment_id: str = Field(..., description="Experiment identifier")
    status: str = Field(..., description="Experiment status")
    results: dict = Field(..., description="Variant results")
    significance: float = Field(..., description="Statistical significance")


@router.post("/v1/experiments", response_model=ExperimentResponse)
async def create_experiment(request: Request):
    """Create a new A/B test experiment.
    
    Args:
        request: FastAPI request with tenant_id in request.state
    
    Returns:
        Created Experiment
        
    Raises:
        HTTPException 400: Invalid request
        HTTPException 401: Unauthorized
        HTTPException 500: Service error
    """
    body = await request.json()
    
    name = body.get("name")
    experiment_type = body.get("experiment_type")
    variants = body.get("variants", [])
    metric = body.get("metric")
    
    if not name:
        raise HTTPException(status_code=400, detail="Missing required field: name")
    
    if experiment_type not in ("prompt", "model", "feature"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid experiment_type: {experiment_type}. Must be prompt, model, or feature"
        )
    
    if not variants or len(variants) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 variants required"
        )
    
    if not metric:
        raise HTTPException(status_code=400, detail="Missing required field: metric")
    
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    experiment_service = getattr(request.app.state, "experiment_service", None)
    if experiment_service is None:
        raise HTTPException(status_code=500, detail="Experiment service not initialized")
    
    try:
        experiment = await experiment_service.create_experiment(
            db_pool=request.app.state.db_pool,
            name=name,
            experiment_type=experiment_type,
            variants=variants,
            metric=metric,
            tenant_id=tenant_id,
        )
        
        log.info(
            "experiment_created",
            experiment_id=experiment.id,
            name=name,
            tenant_id=tenant_id,
        )
        
        return ExperimentResponse(
            id=experiment.id,
            name=experiment.name,
            experiment_type=experiment.experiment_type,
            variants=[VariantRequest(id=v.id, weight=v.weight) for v in experiment.variants],
            metric=experiment.metric,
            status=experiment.status,
            tenant_id=experiment.tenant_id,
        )
    
    except Exception as e:
        log.error(
            "experiment_creation_failed",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to create experiment: {str(e)}")


@router.get("/v1/experiments", response_model=list[ExperimentResponse])
async def list_experiments(
    request: Request,
    status: Optional[str] = None,
):
    """List experiments for a tenant.
    
    Args:
        request: FastAPI request with tenant_id in request.state
        status: Optional status filter
    
    Returns:
        List of experiments
        
    Raises:
        HTTPException 401: Unauthorized
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    experiment_service = getattr(request.app.state, "experiment_service", None)
    if experiment_service is None:
        raise HTTPException(status_code=500, detail="Experiment service not initialized")
    
    try:
        experiments = await experiment_service.list_experiments(
            db_pool=request.app.state.db_pool,
            tenant_id=tenant_id,
            status=status,
        )
        
        return [
            ExperimentResponse(
                id=exp.id,
                name=exp.name,
                experiment_type=exp.experiment_type,
                variants=[VariantRequest(id=v.id, weight=v.weight) for v in exp.variants],
                metric=exp.metric,
                status=exp.status,
                tenant_id=exp.tenant_id,
            )
            for exp in experiments
        ]
    
    except Exception as e:
        log.error(
            "experiment_list_failed",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to list experiments: {str(e)}")


@router.get("/v1/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(request: Request, experiment_id: str):
    """Get an experiment by ID.
    
    Args:
        request: FastAPI request with tenant_id in request.state
        experiment_id: Experiment identifier
    
    Returns:
        Experiment details
        
    Raises:
        HTTPException 401: Unauthorized
        HTTPException 404: Not found
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    try:
        uuid.UUID(experiment_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid experiment_id format: {experiment_id}")
    
    experiment_service = getattr(request.app.state, "experiment_service", None)
    if experiment_service is None:
        raise HTTPException(status_code=500, detail="Experiment service not initialized")
    
    try:
        experiment = await experiment_service.get_experiment(
            db_pool=request.app.state.db_pool,
            experiment_id=experiment_id,
            tenant_id=tenant_id,
        )
        
        if not experiment:
            raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
        
        return ExperimentResponse(
            id=experiment.id,
            name=experiment.name,
            experiment_type=experiment.experiment_type,
            variants=[VariantRequest(id=v.id, weight=v.weight) for v in experiment.variants],
            metric=experiment.metric,
            status=experiment.status,
            tenant_id=experiment.tenant_id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "experiment_get_failed",
            experiment_id=experiment_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get experiment: {str(e)}")


@router.put("/v1/experiments/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(request: Request, experiment_id: str):
    """Update an experiment.
    
    Args:
        request: FastAPI request with tenant_id in request.state
        experiment_id: Experiment identifier
    
    Returns:
        Updated experiment
        
    Raises:
        HTTPException 400: Invalid request
        HTTPException 401: Unauthorized
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    body = await request.json()
    new_status = body.get("status")
    
    if new_status and new_status not in ("draft", "running", "paused", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {new_status}"
        )
    
    experiment_service = getattr(request.app.state, "experiment_service", None)
    if experiment_service is None:
        raise HTTPException(status_code=500, detail="Experiment service not initialized")
    
    try:
        if new_status:
            experiment = await experiment_service.update_experiment_status(
                db_pool=request.app.state.db_pool,
                experiment_id=experiment_id,
                status=new_status,
                tenant_id=tenant_id,
            )
            
            if not experiment:
                raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
            
            return ExperimentResponse(
                id=experiment.id,
                name=experiment.name,
                experiment_type=experiment.experiment_type,
                variants=[VariantRequest(id=v.id, weight=v.weight) for v in experiment.variants],
                metric=experiment.metric,
                status=experiment.status,
                tenant_id=experiment.tenant_id,
            )
        
        raise HTTPException(status_code=400, detail="No fields to update")
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "experiment_update_failed",
            experiment_id=experiment_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to update experiment: {str(e)}")


@router.delete("/v1/experiments/{experiment_id}")
async def delete_experiment(request: Request, experiment_id: str):
    """Delete an experiment.
    
    Args:
        request: FastAPI request with tenant_id in request.state
        experiment_id: Experiment identifier
    
    Returns:
        Success message
        
    Raises:
        HTTPException 401: Unauthorized
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    experiment_service = getattr(request.app.state, "experiment_service", None)
    if experiment_service is None:
        raise HTTPException(status_code=500, detail="Experiment service not initialized")
    
    try:
        deleted = await experiment_service.delete_experiment(
            db_pool=request.app.state.db_pool,
            experiment_id=experiment_id,
            tenant_id=tenant_id,
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
        
        log.info(
            "experiment_deleted",
            experiment_id=experiment_id,
        )
        
        return {"success": True, "message": f"Experiment {experiment_id} deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "experiment_delete_failed",
            experiment_id=experiment_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {str(e)}")


@router.get("/v1/experiments/{experiment_id}/results", response_model=ExperimentResultsResponse)
async def get_experiment_results(request: Request, experiment_id: str):
    """Get experiment results with statistical significance.
    
    Args:
        request: FastAPI request with tenant_id in request.state
        experiment_id: Experiment identifier
    
    Returns:
        Experiment results with variant stats
        
    Raises:
        HTTPException 401: Unauthorized
        HTTPException 404: Not found
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    experiment_service = getattr(request.app.state, "experiment_service", None)
    if experiment_service is None:
        raise HTTPException(status_code=500, detail="Experiment service not initialized")
    
    try:
        results = await experiment_service.get_experiment_results(
            db_pool=request.app.state.db_pool,
            experiment_id=experiment_id,
            tenant_id=tenant_id,
        )
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
        
        return ExperimentResultsResponse(
            experiment_id=results["experiment_id"],
            status=results["status"],
            results=results["results"],
            significance=results["significance"],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "experiment_results_failed",
            experiment_id=experiment_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")