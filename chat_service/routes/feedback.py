"""Feedback API routes for user feedback loop (👍/👎)."""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

log = structlog.get_logger()

router = APIRouter()


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    thread_id: str = Field(..., description="Thread identifier")
    message_id: str = Field(..., description="Message identifier")
    feedback_type: str = Field(..., description="Feedback type: 'thumbs_up' or 'thumbs_down'")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    success: bool = Field(..., description="Whether the feedback was recorded")
    feedback_state: Optional[str] = Field(
        None,
        description="Current feedback state: 'thumbs_up', 'thumbs_down', or None if removed"
    )


class FeedbackStatsResponse(BaseModel):
    """Response model for feedback statistics."""
    total: int = Field(..., description="Total feedback count")
    thumbs_up: int = Field(..., description="Thumbs up count")
    thumbs_down: int = Field(..., description="Thumbs down count")
    thumbs_up_percentage: Optional[float] = Field(
        None,
        description="Percentage of thumbs up (0-100)"
    )
    thumbs_down_percentage: Optional[float] = Field(
        None,
        description="Percentage of thumbs down (0-100)"
    )


@router.post("/v1/feedback", response_model=FeedbackResponse)
async def record_feedback(request: Request):
    """Record feedback for a message.
    
    Users can provide thumbs up (👍) or thumbs down (👎) feedback on AI responses.
    Clicking the same feedback button twice will toggle the feedback off (remove it).
    
    Args:
        request: FastAPI request with tenant_id in request.state
        
    Returns:
        FeedbackResponse with success status and current feedback state
        
    Raises:
        HTTPException 400: Invalid request (missing fields, invalid feedback_type)
        HTTPException 401: Unauthorized (invalid/missing API key)
        HTTPException 500: Database error
    """
    body = await request.json()
    
    # Validate required fields
    thread_id = body.get("thread_id")
    message_id = body.get("message_id")
    feedback_type = body.get("feedback_type")
    
    if not thread_id:
        raise HTTPException(status_code=400, detail="Missing required field: thread_id")
    
    if not message_id:
        raise HTTPException(status_code=400, detail="Missing required field: message_id")
    
    if not feedback_type:
        raise HTTPException(status_code=400, detail="Missing required field: feedback_type")
    
    # Validate feedback_type
    if feedback_type not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback_type: {feedback_type}. Must be 'thumbs_up' or 'thumbs_down'"
        )
    
    # Validate UUID format
    try:
        uuid.UUID(thread_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid thread_id format: {thread_id}")
    
    try:
        uuid.UUID(message_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid message_id format: {message_id}")
    
    # Get tenant_id from request.state (set by auth middleware)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    # Get user_id from request.state (should be set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # For now, use a default user_id if not available
        # In production, this should be set by the auth middleware
        user_id = "anonymous"
    
    # Get feedback service from app.state
    feedback_service = getattr(request.app.state, "feedback_service", None)
    if feedback_service is None:
        raise HTTPException(status_code=500, detail="Feedback service not initialized")
    
    try:
        # Store feedback
        feedback_state = await feedback_service.store_feedback(
            db_pool=request.app.state.db_pool,
            thread_id=thread_id,
            message_id=message_id,
            user_id=user_id,
            tenant_id=tenant_id,
            feedback_type=feedback_type,
        )
        
        log.info(
            "feedback_recorded",
            thread_id=thread_id,
            message_id=message_id,
            user_id=user_id,
            tenant_id=tenant_id,
            feedback_type=feedback_type,
            feedback_state=feedback_state,
        )
        
        return FeedbackResponse(success=True, feedback_state=feedback_state)
    
    except Exception as e:
        log.error(
            "feedback_storage_failed",
            thread_id=thread_id,
            message_id=message_id,
            user_id=user_id,
            tenant_id=tenant_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to store feedback: {str(e)}")


@router.get("/v1/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    request: Request,
    thread_id: Optional[str] = None,
    message_id: Optional[str] = None,
):
    """Get feedback statistics for a thread or message.
    
    Args:
        request: FastAPI request with tenant_id in request.state
        thread_id: Optional thread identifier to filter statistics
        message_id: Optional message identifier to filter statistics
        
    Returns:
        FeedbackStatsResponse with counts and percentages
        
    Raises:
        HTTPException 400: Invalid request (invalid UUID format)
        HTTPException 401: Unauthorized (invalid/missing API key)
        HTTPException 500: Database error
    """
    # Validate UUID format if provided
    if thread_id:
        try:
            uuid.UUID(thread_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail=f"Invalid thread_id format: {thread_id}")
    
    if message_id:
        try:
            uuid.UUID(message_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail=f"Invalid message_id format: {message_id}")
    
    # Get tenant_id from request.state (set by auth middleware)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing tenant_id")
    
    # Get feedback service from app.state
    feedback_service = getattr(request.app.state, "feedback_service", None)
    if feedback_service is None:
        raise HTTPException(status_code=500, detail="Feedback service not initialized")
    
    try:
        # Get statistics
        stats = await feedback_service.get_feedback_stats(
            db_pool=request.app.state.db_pool,
            tenant_id=tenant_id,
            thread_id=thread_id,
            message_id=message_id,
        )
        
        log.info(
            "feedback_stats_retrieved",
            tenant_id=tenant_id,
            thread_id=thread_id,
            message_id=message_id,
            total=stats["total"],
        )
        
        return FeedbackStatsResponse(**stats)
    
    except Exception as e:
        log.error(
            "feedback_stats_failed",
            tenant_id=tenant_id,
            thread_id=thread_id,
            message_id=message_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get feedback statistics: {str(e)}")
