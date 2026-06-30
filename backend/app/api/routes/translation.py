"""
Translation and language routes.
"""

from fastapi import APIRouter, HTTPException, Depends

from app.api.models import TranslationRequest
from app.api.dependencies import get_translation_service
from app.domain.exceptions import TranslationError

router = APIRouter()


@router.get("/api/languages")
async def get_languages(translation_service = Depends(get_translation_service)):
    """Obtener lista de idiomas disponibles."""
    try:
        languages = translation_service.get_supported_languages()
        return {
            "supported_languages": languages,
            "default_language": "es",
            "total_languages": len(languages)
        }
    except TranslationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting languages: {str(e)}")


@router.post("/api/translate")
async def translate(
    request: TranslationRequest,
    translation_service = Depends(get_translation_service)
):
    """Traducir texto entre idiomas."""
    try:
        translated_text = translation_service.translate(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language
        )
        return {
            "original_text": request.text,
            "translated_text": translated_text,
            "source_language": request.source_language,
            "target_language": request.target_language,
            "status": "success"
        }
    except TranslationError as e:
        return {
            "error": str(e),
            "status": "error"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }
