"""Evidence-checked procedural recommendation endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import check_rate_limit, get_procedural_service
from app.api.models import ProceduralRecommendation, ProceduralRequest
from app.domain.exceptions import AppError, RAGError, ValidationError

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