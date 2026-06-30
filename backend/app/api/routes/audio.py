"""
Audio routes: TTS, STT, and file serving.
"""

import hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import io

from app.api.models import TTSRequest
from app.api.dependencies import get_audio_dirs, get_tts_available, get_stt_available

router = APIRouter()


def get_tts_cache_path(text: str, language: str, tts_cache_dir: Path) -> Path:
    """Generate cache file path from text + language hash."""
    text_hash = hashlib.md5(f"{text}:{language}".encode()).hexdigest()
    return tts_cache_dir / f"tts_{text_hash}_{language}.mp3"


@router.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech audio with caching.

    Supports languages:
    - 'ru' (Russian)
    - 'es' (Spanish)
    - 'en' (English)
    - 'fr' (French)
    - 'de' (German)
    - etc.

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
            'ru': 'ru',
            'es': 'es',
            'en': 'en',
            'fr': 'fr',
            'de': 'de',
            'pt': 'pt',
            'it': 'it',
            'zh': 'zh-CN',
            'ja': 'ja',
            'ko': 'ko',
            'ar': 'ar',
            'vi': 'vi',
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
        raise HTTPException(
            status_code=500,
            detail=f"TTS error: {str(e)}"
        )


@router.post("/api/tts/file")
async def text_to_speech_file(request: TTSRequest):
    """
    Convert text to speech and save as file (with caching).

    Returns: File path and audio URL
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

        # Map language codes
        lang_map = {
            'ru': 'ru',
            'es': 'es',
            'en': 'en',
            'fr': 'fr',
            'de': 'de',
        }

        gtts_lang = lang_map.get(request.language, request.language)

        # Create TTS and save to cache
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
        raise HTTPException(
            status_code=500,
            detail=f"TTS error: {str(e)}"
        )


@router.post("/api/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = "ru-RU"
):
    """
    Convert speech audio to text (Speech-to-Text).

    Accepts: WAV, FLAC, AIFF audio files
    Language codes: 'ru-RU' (Russian), 'es-ES' (Spanish), 'en-US' (English)

    Note: This is a placeholder implementation.
    For production, consider using:
    - Whisper (OpenAI)
    - Google Cloud Speech-to-Text
    - Azure Speech Services
    """
    if not get_stt_available():
        raise HTTPException(
            status_code=503,
            detail="STT service unavailable. Install SpeechRecognition: pip install SpeechRecognition"
        )

    try:
        import speech_recognition as sr
        
        # Read uploaded audio
        audio_data = await audio.read()

        # Initialize recognizer
        recognizer = sr.Recognizer()

        # Use AudioData from file
        with sr.AudioFile(io.BytesIO(audio_data)) as source:
            audio_content = recognizer.record(source)

        # Recognize speech using Google Speech Recognition
        text = recognizer.recognize_google(audio_content, language=language)

        return {
            "status": "success",
            "text": text,
            "language": language,
            "provider": "Google Speech Recognition",
            "note": "For better accuracy, consider using Whisper or cloud STT services"
        }

    except sr.UnknownValueError:
        raise HTTPException(
            status_code=400,
            detail="Could not understand audio. Please speak clearly."
        )
    except sr.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"STT service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"STT error: {str(e)}"
        )


@router.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio files."""
    dirs = get_audio_dirs()
    audio_dir = dirs["audio_dir"]
    
    filepath = audio_dir / filename
    if filepath.exists():
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Audio file not found")


@router.get("/api/audio/cache/{filename}")
async def get_cached_audio_file(filename: str):
    """Serve cached TTS audio files."""
    dirs = get_audio_dirs()
    tts_cache_dir = dirs["tts_cache_dir"]
    
    filepath = tts_cache_dir / filename
    if filepath.exists():
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Cached audio file not found")


@router.get("/api/audio-available")
async def check_audio_availability():
    """Check TTS/STT service availability."""
    tts_available = get_tts_available()
    stt_available = get_stt_available()
    
    return {
        "tts": {
            "available": tts_available,
            "provider": "gTTS" if tts_available else None,
            "languages": ["ru", "es", "en", "fr", "de", "pt", "it", "zh", "ja", "ko", "ar", "vi"] if tts_available else []
        },
        "stt": {
            "available": stt_available,
            "provider": "Google Speech Recognition" if stt_available else None,
            "languages": ["ru-RU", "es-ES", "en-US", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR"] if stt_available else []
        }
    }
