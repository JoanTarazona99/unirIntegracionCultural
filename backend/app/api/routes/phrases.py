"""
Russian phrases routes.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.api.models import PhraseResponse
from app.api.dependencies import get_phrases_db

router = APIRouter()


@router.get("/api/phrases", response_model=List[PhraseResponse])
async def get_phrases(category: Optional[str] = None, limit: int = 10):
    """Obtener frases contextualizadas."""
    try:
        phrases_db = get_phrases_db()
        filtered = phrases_db
        if category:
            filtered = [p for p in filtered if p.get("category") == category]
        return filtered[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading phrases: {str(e)}")


@router.get("/api/phrases/{phrase_id}")
async def get_phrase(phrase_id: int):
    """Obtener una frase específica."""
    try:
        phrases_db = get_phrases_db()
        for phrase in phrases_db:
            if phrase.get("id") == phrase_id:
                return phrase
        raise HTTPException(status_code=404, detail="Frase no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading phrase: {str(e)}")
