"""
Audio routes: TTS, STT, and file serving (refactored with AudioService).

Handles both legacy endpoints and new service-oriented endpoints.
"""

import hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
import io

from app.api.models import TTSRequest, AudioTTSRequest, AudioSTTResponse, AudioStatusResponse
from app.api.dependencies import (
    get_audio_dirs, get_tts_available, get_stt_available, get_audio_service
)
from app.domain.exceptions import ValidationError, AppError

router = APIRouter()


def get_tts_cache_path(text: str, language: str, tts_cache_dir: Path) -> Path:
    """Generate cache file path from text + language hash."""
    text_hash = hashlib.md5(f"{text}:{language}".encode()).hexdigest()
    return tts_cache_dir / f"tts_{text_hash}_{language}.mp3"


# ==================== LEGACY ENDPOINTS (Backward Compatibility) ====================

@router.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech audio with caching (legacy endpoint).

    Supports languages:
    - 'ru' (Russian)
    - 'es' (Spanish)
    - 'en' (English)
    - 'fr' (French)
    - 'de' (German)

    Returns: MP3 audio stream
    Caches generated audio for faster repeated requests
    """
    if not get_tts_available():
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Install gTTS: pip install gTTS"
        )

    try:
        from gtts import gTTS
        
        dirs = get_audio_dirs()
        tts_cache_dir = dirs["tts_cache_dir"]
        
        # Check cache first
        cache_path = get_tts_cache_path(request.text, request.language, tts_cache_dir)
        if cache_path.exists():
            return FileResponse(
                cache_path,
                media_type="audio/mpeg",
                headers={
                    "X-Cache": "HIT",
                    "Content-Disposition": f"attachment; filename=speech_{request.language}.mp3"
                }
            )

        # Map language codes to gTTS format
        lang_map = {
            'ru': 'ru', 'es': 'es', 'en': 'en', 'fr': 'fr', 'de': 'de',
            'pt': 'pt', 'it': 'it', 'zh': 'zh-CN', 'ja': 'ja', 'ko': 'ko',
            'ar': 'ar', 'vi': 'vi',
        }

        gtts_lang = lang_map.get(request.language, request.language)

        # Create TTS object and save to cache
        tts = gTTS(text=request.text, lang=gtts_lang, slow=False)
        tts.save(str(cache_path))

        return FileResponse(
            cache_path,
            media_type="audio/mpeg",
            headers={
                "X-Cache": "MISS",
                "Content-Disposition": f"attachment; filename=speech_{request.language}.mp3"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@router.post("/api/tts/file")
async def text_to_speech_file(request: TTSRequest):
    """Convert text to speech and save as file (legacy endpoint)."""
    if not get_tts_available():
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Install gTTS: pip install gTTS"
        )

    try:
        from gtts import gTTS
        
        dirs = get_audio_dirs()
        tts_cache_dir = dirs["tts_cache_dir"]
        
        cache_path = get_tts_cache_path(request.text, request.language, tts_cache_dir)

        if cache_path.exists():
            return {
                "status": "success",
                "text": request.text,
                "language": request.language,
                "audio_url": f"/api/audio/cache/{cache_path.name}",
                "file_path": str(cache_path),
                "cached": True
            }

        lang_map = {
            'ru': 'ru', 'es': 'es', 'en': 'en', 'fr': 'fr', 'de': 'de',
        }

        gtts_lang = lang_map.get(request.language, request.language)

        tts = gTTS(text=request.text, lang=gtts_lang, slow=False)
        tts.save(str(cache_path))

        return {
            "status": "success",
            "text": request.text,
            "language": request.language,
            "audio_url": f"/api/audio/cache/{cache_path.name}",
            "file_path": str(cache_path),
            "cached": False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@router.get("/api/audio/cache/{filename}")
async def get_cached_audio(filename: str):
    """Serve cached audio files."""
    dirs = get_audio_dirs()
    tts_cache_dir = dirs["tts_cache_dir"]
    
    file_path = tts_cache_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== SERVICE-ORIENTED ENDPOINTS (Phase 3) ====================

@router.post("/api/audio/tts")
async def audio_tts(
    request: AudioTTSRequest,
    audio_service = Depends(get_audio_service)
) -> dict:
    """Convert text to speech using AudioService."""
    try:
        result = audio_service.text_to_speech(request.text, request.language)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in TTS: {str(e)}")


@router.post("/api/audio/stt")
async def audio_stt(
    file: UploadFile = File(...),
    audio_service = Depends(get_audio_service)
) -> AudioSTTResponse:
    """Convert speech to text using AudioService."""
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Use AudioService for STT
        result = audio_service.speech_to_text(temp_path)
        
        if result.get("success"):
            return AudioSTTResponse(**result)
        else:
            return AudioSTTResponse(
                success=False,
                message=result.get("message", "STT failed")
            )
            
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in STT: {str(e)}")


@router.get("/api/audio/status")
async def audio_status(
    audio_service = Depends(get_audio_service)
) -> AudioStatusResponse:
    """Get audio service status."""
    try:
        status = audio_service.get_status()
        return AudioStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting audio status: {str(e)}")
