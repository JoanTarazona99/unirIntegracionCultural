"""Evidence-checked procedural recommendation and feedback endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import check_rate_limit, get_procedural_service
from app.api.models import (
    ProceduralFeedback,
    ProceduralFeedbackStored,
    ProceduralFeedbackSummary,
    ProceduralRecommendation,
    ProceduralRequest,
)
from app.config.logging_config import get_logger
from app.domain.exceptions import AppError, RAGError, ValidationError
from app.services.procedural_service import DuplicateFeedbackError

logger = get_logger(__name__)
router = APIRouter()


@router.post("/api/procedural", response_model=ProceduralRecommendation)
async def get_procedural_recommendation(
    request: ProceduralRequest,
    http_request: Request,
    procedural_service=Depends(get_procedural_service),
    _: str = Depends(check_rate_limit),
):
    """Return a complete procedure, clarification, or grounded abstention."""
    correlation_id = http_request.scope.get("request_id") or str(uuid.uuid4())
    try:
        return procedural_service.recommend(
            request,
            correlation_id=correlation_id,
        )
    except ValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (RAGError, AppError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/api/procedural/feedback", response_model=ProceduralFeedbackStored)
async def submit_procedural_feedback(
    feedback: ProceduralFeedback,
    procedural_service=Depends(get_procedural_service),
    _: str = Depends(check_rate_limit),
):
    """Store atomic evaluation feedback for a procedural response."""
    try:
        return procedural_service.save_feedback(feedback)
    except DuplicateFeedbackError as error:
        raise HTTPException(
            status_code=409,
            detail="Feedback already exists for this correlation_id",
        ) from error
    except ValidationError as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid feedback payload",
        ) from error
    except Exception as error:
        logger.error(
            "procedural_feedback_save_failed",
            correlation_id=feedback.correlation_id,
            error_type=type(error).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while saving feedback",
        ) from error


@router.get("/api/procedural/feedback/summary", response_model=ProceduralFeedbackSummary)
async def get_procedural_feedback_summary(
    procedural_service=Depends(get_procedural_service),
    _: str = Depends(check_rate_limit),
):
    """Return aggregated metrics across stored procedural feedback records."""
    try:
        return procedural_service.get_feedback_summary()
    except Exception as error:
        logger.error(
            "procedural_feedback_summary_failed",
            error_type=type(error).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while aggregating feedback summary",
        ) from error