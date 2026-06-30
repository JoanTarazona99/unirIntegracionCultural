"""
Translation and language routes.
"""

from fastapi import APIRouter, HTTPException

from app.api.models import TranslationRequest
from app.api.dependencies import get_translator

router = APIRouter()


@router.get("/api/languages")
async def get_languages():
    """Obtener lista de idiomas disponibles."""
    try:
        translator = get_translator()
        return {
            "supported_languages": translator.get_supported_languages(),
            "default_language": "es",
            "total_languages": len(translator.get_supported_languages())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting languages: {str(e)}")


@router.post("/api/translate")
async def translate(request: TranslationRequest):
    """Traducir texto entre idiomas."""
    try:
        translator = get_translator()
        translated_text = translator.translate_text(
            request.text,
            request.target_language,
            request.source_language
        )
        return {
            "original_text": request.text,
            "translated_text": translated_text,
            "source_language": request.source_language,
            "target_language": request.target_language,
            "status": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }
