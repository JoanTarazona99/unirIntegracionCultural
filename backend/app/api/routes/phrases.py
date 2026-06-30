"""
Russian phrases routes.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from app.api.models import PhraseResponse
from app.api.dependencies import get_phrase_service
from app.domain.exceptions import ValidationError, AppError

router = APIRouter()


@router.get("/api/phrases", response_model=List[PhraseResponse])
async def get_phrases(
    category: Optional[str] = None,
    limit: int = 10,
    phrase_service = Depends(get_phrase_service)
):
    """Obtener frases contextualizadas."""
    try:
        phrases = phrase_service.list_phrases(category=category, limit=limit)
        return phrases
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading phrases: {str(e)}")


@router.get("/api/phrases/{phrase_id}")
async def get_phrase(
    phrase_id: int,
    phrase_service = Depends(get_phrase_service)
):
    """Obtener una frase específica."""
    try:
        phrase = phrase_service.get_phrase(phrase_id)
        if phrase is None:
            raise HTTPException(status_code=404, detail="Frase no encontrada")
        return phrase
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading phrase: {str(e)}")
