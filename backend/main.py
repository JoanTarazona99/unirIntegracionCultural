import sys
import json
import os
import io
import uuid
import time
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator

# Add backend to path for app imports
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import settings
from app.config.logging_config import configure_logging, get_logger
from app.middleware.logging_middleware import LoggingMiddleware

from enhanced_rag import EnhancedRAGModule
from translator import create_translator
from personalization import get_conversation_memory, ConversationMemory
from cache_module import get_rag_cache, LRUCache, cache_rag_query, get_cached_rag_query

# ==================== APPLICATION INITIALIZATION ====================
configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Backend para soporte inteligente a estudiantes extranjeros",
    version=settings.app_version,
    debug=settings.debug
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

logger.info(
    "app_startup",
    app_name=settings.app_name,
    version=settings.app_version,
    environment=settings.environment
)

# Inicializar módulo RAG mejorado e traductor multiidioma
rag_module = EnhancedRAGModule()
translator = create_translator()

# Initialize conversation memory
conversation_memory = get_conversation_memory(max_history=10)

# Initialize cache
cache = get_rag_cache(max_entries=settings.cache_max_entries, default_ttl=settings.cache_ttl_seconds)

# Check TTS/STT availability
TTS_AVAILABLE = False
STT_AVAILABLE = False
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
    logger.info("feature_enabled", service="TTS", provider="gTTS")
except ImportError:
    logger.warning("feature_disabled", service="TTS", reason="gTTS not installed")

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
    logger.info("feature_enabled", service="STT", provider="Google Speech Recognition")
except ImportError:
    logger.warning("feature_disabled", service="STT", reason="SpeechRecognition not installed")

# ==================== RATE LIMITER ====================

class RateLimiter:
    """Simple in-memory rate limiter: max requests per IP per minute"""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}  # IP -> [timestamps]

    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed to make request"""
        now = time.time()

        # Get or create request list for IP
        if ip not in self._requests:
            self._requests[ip] = []

        # Remove old requests outside window
        self._requests[ip] = [
            ts for ts in self._requests[ip]
            if now - ts < self.window_seconds
        ]

        # Check if under limit
        if len(self._requests[ip]) < self.max_requests:
            self._requests[ip].append(now)
            return True

        return False

    def get_remaining(self, ip: str) -> int:
        """Get remaining requests for IP"""
        if ip not in self._requests:
            return self.max_requests

        now = time.time()
        valid_requests = [
            ts for ts in self._requests[ip]
            if now - ts < self.window_seconds
        ]
        return max(0, self.max_requests - len(valid_requests))

    def cleanup_old(self):
        """Clean up old entries (call periodically)"""
        now = time.time()
        for ip in list(self._requests.keys()):
            self._requests[ip] = [
                ts for ts in self._requests[ip]
                if now - ts < self.window_seconds
            ]
            if not self._requests[ip]:
                del self._requests[ip]


rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)

logger.info(
    "rate_limiter_initialized",
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(request: Request):
    """Dependency to check rate limit"""
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {rate_limiter.max_requests} requests per minute."
        )
    return ip


# ==================== CORS ====================
# CORS middleware - use explicit whitelist from settings (NO wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

logger.info(
    "cors_configured",
    allowed_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials
)

# Ruta raíz: redireccionar a frontend
@app.get("/")
async def root():
    return RedirectResponse(url="/frontend/index.html")

# Ruta para /frontend/: servir index.html
@app.get("/frontend/")
async def frontend_root():
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="index.html not found")

# Servir archivos estáticos (frontend)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")

# Audio directory for TTS output
audio_dir = Path(__file__).parent.parent / "data" / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)

# Modelos Pydantic
class UserProfile(BaseModel):
    user_id: str
    name: str
    country: str
    native_language: str
    visa_type: str  # "student", "study_visit"
    academic_level: str  # "bachelor", "master", "phd"
    housing_type: str  # "dorm", "private_apartment"
    russian_level: str  # "A1", "A2", "B1", "B2", "C1"

class PhraseResponse(BaseModel):
    id: int
    russian: str
    transliteration: str
    english: str
    audio_url: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    user_id: str
    language: str = "es"  # Idioma de respuesta deseado
    target_language: Optional[str] = None  # Idioma adicional para traducción
    session_id: Optional[str] = None  # Session ID for conversation history

class StreamRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    language: str = "ru"

class ChatResponse(BaseModel):
    query: str
    answer: str  # Respuesta en idioma solicitado
    answer_original: str  # Respuesta original en español
    translations: Optional[Dict[str, str]] = None  # Traducciones adicionales
    context: List[str]
    personalized_tips: List[str]
    language: str  # Idioma de la respuesta
    available_languages: List[str] = None  # Idiomas disponibles
    search_mode: Optional[str] = None  # 'semantic' or 'keyword'

class TranslationRequest(BaseModel):
    text: str
    source_language: str = "es"
    target_language: str = "en"

class TTSRequest(BaseModel):
    text: str
    language: str = "ru"  # 'ru' for Russian, 'es' for Spanish, 'en' for English

# Cargar frases base
def load_phrases():
    phrases_file = Path(__file__).parent.parent / "data" / "phrases" / "base_phrases.json"
    if phrases_file.exists():
        with open(phrases_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

phrases_db = load_phrases()

# Rutas de salud
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Asistente de Integración Cultural activo",
        "features": {
            "semantic_search": "available" if hasattr(rag_module.document_library, '_use_semantic') and rag_module.document_library._use_semantic else "keyword_fallback",
            "tts": "available" if TTS_AVAILABLE else "unavailable",
            "stt": "available" if STT_AVAILABLE else "unavailable"
        }
    }


# ==================== STATUS ENDPOINT ====================

@app.get("/api/status")
async def get_system_status():
    """
    Get comprehensive system status

    Returns status of all modules: RAG, LLM, TTS, STT, Cache
    """
    # RAG status
    semantic_available = hasattr(rag_module.document_library, '_use_semantic') and rag_module.document_library._use_semantic
    rag_status = {
        "available": True,
        "mode": rag_module.document_library.get_search_mode() if hasattr(rag_module.document_library, 'get_search_mode') else "keyword",
        "sources": len(rag_module.document_library.documents) if hasattr(rag_module, 'document_library') else 0
    }

    # LLM status
    llm_available = rag_module.is_llm_enabled() if hasattr(rag_module, 'is_llm_enabled') else False
    llm_status = {
        "available": llm_available,
        "model": rag_module.llm.model if llm_available and hasattr(rag_module, 'llm') and rag_module.llm else None,
        "provider": "ollama" if llm_available else None
    }

    # TTS status
    tts_status = {
        "available": TTS_AVAILABLE,
        "provider": "gTTS" if TTS_AVAILABLE else None,
        "languages": ["ru", "es", "en", "fr", "de", "pt", "it", "zh", "ja", "ko", "ar", "vi"] if TTS_AVAILABLE else []
    }

    # STT status
    stt_status = {
        "available": STT_AVAILABLE,
        "provider": "Google Speech Recognition" if STT_AVAILABLE else None,
        "languages": ["ru-RU", "es-ES", "en-US", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR"] if STT_AVAILABLE else []
    }

    # Cache status
    cache_stats = cache.get_stats()
    cache_status = {
        "available": True,
        "entries": cache_stats["entries"],
        "hits": cache_stats["hits"],
        "misses": cache_stats["misses"],
        "hit_rate": cache_stats["hit_rate_percent"]
    }

    # Conversation memory status
    conversation_status = {
        "available": True,
        "sessions": conversation_memory.get_session_count(),
        "max_history": 10
    }

    return {
        "version": "0.5.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "rag": rag_status,
        "llm": llm_status,
        "tts": tts_status,
        "stt": stt_status,
        "cache": cache_status,
        "conversation": conversation_status
    }

# Rutas de frases
@app.get("/api/phrases", response_model=List[PhraseResponse])
async def get_phrases(category: Optional[str] = None, limit: int = 10):
    """Obtener frases contextualizadas"""
    try:
        filtered = phrases_db
        if category:
            filtered = [p for p in filtered if p.get("category") == category]
        return filtered[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading phrases: {str(e)}")

@app.get("/api/phrases/{phrase_id}")
async def get_phrase(phrase_id: int):
    """Obtener una frase específica"""
    try:
        for phrase in phrases_db:
            if phrase.get("id") == phrase_id:
                return phrase
        raise HTTPException(status_code=404, detail="Frase no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading phrase: {str(e)}")

# Rutas de usuario
@app.post("/api/users/profile")
async def create_user_profile(profile: UserProfile):
    """Crear perfil de usuario personalizado"""
    try:
        return {
            "message": "Perfil creado exitosamente",
            "profile": profile,
            "personalization_factors": {
                "country": profile.country,
                "visa_type": profile.visa_type,
                "language_support": "Soportado",
                "recommended_phrases_count": 50
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating profile: {str(e)}")

# Rutas de búsqueda RAG
@app.post("/api/search")
async def search_documents(query: QueryRequest):
    """Búsqueda en documentos oficiales usando RAG mejorado con semantic search"""
    try:
        result = rag_module.search_and_generate(
            query.query,
            context_type=f"lang_{query.language}"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in RAG search: {str(e)}")

@app.get("/api/search/sources")
async def get_rag_sources():
    """Obtener fuentes oficiales disponibles"""
    try:
        return {
            "sources": rag_module.document_library.list_sources(),
            "search_mode": rag_module.document_library.get_search_mode(),
            "description": "Fuentes de documentos oficiales integradas"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")
@app.post("/api/chat")
async def chat(
    request: QueryRequest,
    http_request: Request,
    _: str = Depends(check_rate_limit)
):
    """Chat principal con soporte multiidioma, RAG y cache"""
    try:
        # Generate or use existing session
        session_id = request.session_id or str(uuid.uuid4())

        # Idioma de respuesta = el seleccionado por usuario
        target_lang = request.language

        # Try cache first
        cached_result = get_cached_rag_query(request.query, target_lang)
        if cached_result:
            # Return cached response
            cached_result['cached'] = True
            return cached_result

        # Buscar en el RAG - usar el idioma seleccionado directamente
        rag_result = rag_module.search_and_generate(
            request.query,
            context_type=f"chat_{target_lang}",
            language=target_lang,  # Usar el idioma seleccionado
            session_id=session_id
        )

        # Respuesta - usar directamente la del RAG en el idioma correcto
        answer_translated = rag_result['response']

        # Para referencia, guardar respuesta base
        answer_original = rag_result['response']

        # Add to conversation memory
        conversation_memory.add_message(session_id, 'user', request.query)
        conversation_memory.add_message(session_id, 'assistant', answer_translated)

        # Extraer contexto y fuentes
        context = []
        personalized_tips = []

        if rag_result['sources']:
            for source in rag_result['sources']:
                source_text = f"[{source['source']}] {source['title']}"
                content_text = source['content'][:200] + "..."

                # Traducir contexto si es necesario
                if target_lang != 'es':
                    source_text = translator.translate_text(source_text, target_lang)
                    content_text = translator.translate_text(content_text, target_lang)

                context.append(source_text)
                personalized_tips.append(content_text)

        # Crear respuesta con traducciones opcionales
        response = ChatResponse(
            query=request.query,
            answer=answer_translated,
            answer_original=answer_original,
            translations={target_lang: answer_translated} if target_lang != 'es' else None,
            context=context,
            personalized_tips=personalized_tips if personalized_tips else [
                "Consulte los documentos oficiales para más información" if target_lang == 'es' else
                translator.translate_text("Consulte los documentos oficiales para más información", target_lang)
            ],
            language=target_lang,
            available_languages=list(translator.get_supported_languages().keys()),
            search_mode=rag_result.get('search_mode', 'keyword')
        )

        # Cache the response
        response_dict = response.model_dump()
        cache_rag_query(request.query, target_lang, response_dict)

        return response
    except Exception as e:
        return ChatResponse(
            query=request.query,
            answer=f"Error al procesar la búsqueda: {str(e)}",
            answer_original=f"Error al procesar la búsqueda: {str(e)}",
            context=["Error"],
            personalized_tips=["Por favor, intente nuevamente"],
            language=request.language,
            available_languages=list(translator.get_supported_languages().keys()),
            search_mode="error"
        )

# Endpoint de idiomas disponibles
@app.get("/api/languages")
async def get_languages():
    """Obtener lista de idiomas disponibles"""
    try:
        return {
            "supported_languages": translator.get_supported_languages(),
            "default_language": "es",
            "total_languages": len(translator.get_supported_languages())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting languages: {str(e)}")

# Endpoint de traducción
@app.post("/api/translate")
async def translate(request: TranslationRequest):
    """Traducir texto entre idiomas"""
    try:
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

# ==================== STREAMING CHAT ENDPOINT ====================

@app.post("/api/chat/stream")
async def chat_stream(request: StreamRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE)

    Returns tokens as they are generated from the LLM.
    If LLM is not available, returns complete template response.

    Usage:
        POST /api/chat/stream
        {
            "query": "Tell me about registration",
            "session_id": "optional-session-id",
            "language": "ru"
        }

    Response: text/event-stream with tokens
    """
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from LLM stream"""
        full_response = ""

        try:
            # Add user message to memory
            conversation_memory.add_message(session_id, 'user', request.query)

            # Send session ID first
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # Stream from RAG module
            async for token in rag_module.generate_stream_async(
                query=request.query,
                context_type='stream_chat',
                language=request.language,
                session_id=session_id
            ):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'full_length': len(full_response)})}\n\n"

            # Add assistant response to memory
            conversation_memory.add_message(session_id, 'assistant', full_response)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history for a session"""
    try:
        history = conversation_memory.get_history(session_id)
        summary = conversation_memory.get_summary(session_id)
        return {
            "session_id": session_id,
            "history": history,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")


@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear conversation history for a session"""
    try:
        conversation_memory.clear_session(session_id)
        return {
            "status": "cleared",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")


@app.get("/api/chat/sessions")
async def list_chat_sessions():
    """List all active chat sessions"""
    try:
        return {
            "active_sessions": conversation_memory.get_session_count(),
            "total_messages": conversation_memory.get_message_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")

# ==================== TTS/STT ENDPOINTS ====================

# TTS Cache directory
tts_cache_dir = Path(__file__).parent.parent / "data" / "tts_cache"
tts_cache_dir.mkdir(parents=True, exist_ok=True)


def get_tts_cache_path(text: str, language: str) -> Path:
    """Generate cache file path from text + language hash"""
    import hashlib
    text_hash = hashlib.md5(f"{text}:{language}".encode()).hexdigest()
    return tts_cache_dir / f"tts_{text_hash}_{language}.mp3"


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech audio with caching

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
    if not TTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Install gTTS: pip install gTTS"
        )

    try:
        # Check cache first
        cache_path = get_tts_cache_path(request.text, request.language)
        if cache_path.exists():
            # Return cached file - much faster
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
            'ru': 'ru',      # Russian
            'es': 'es',      # Spanish
            'en': 'en',      # English
            'fr': 'fr',      # French
            'de': 'de',      # German
            'pt': 'pt',      # Portuguese
            'it': 'it',      # Italian
            'zh': 'zh-CN',   # Chinese
            'ja': 'ja',      # Japanese
            'ko': 'ko',      # Korean
            'ar': 'ar',      # Arabic
            'vi': 'vi',      # Vietnamese
        }

        gtts_lang = lang_map.get(request.language, request.language)

        # Create TTS object
        tts = gTTS(text=request.text, lang=gtts_lang, slow=False)

        # Save to cache file
        tts.save(str(cache_path))

        # Return cached file
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


@app.post("/api/tts/file")
async def text_to_speech_file(request: TTSRequest):
    """
    Convert text to speech and save as file (with caching)

    Returns: File path and audio URL
    """
    if not TTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Install gTTS: pip install gTTS"
        )

    try:
        # Check cache first
        cache_path = get_tts_cache_path(request.text, request.language)

        if cache_path.exists():
            # Return cached file info
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


@app.post("/api/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = "ru-RU"
):
    """
    Convert speech audio to text (Speech-to-Text)

    Accepts: WAV, FLAC, AIFF audio files
    Language codes: 'ru-RU' (Russian), 'es-ES' (Spanish), 'en-US' (English)

    Note: This is a placeholder implementation.
    For production, consider using:
    - Whisper (OpenAI)
    - Google Cloud Speech-to-Text
    - Azure Speech Services
    """
    if not STT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="STT service unavailable. Install SpeechRecognition: pip install SpeechRecognition"
        )

    try:
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


@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio files"""
    filepath = audio_dir / filename
    if filepath.exists():
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Audio file not found")


@app.get("/api/audio/cache/{filename}")
async def get_cached_audio_file(filename: str):
    """Serve cached TTS audio files"""
    filepath = tts_cache_dir / filename
    if filepath.exists():
        return FileResponse(
            filepath,
            media_type="audio/mpeg",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Cached audio file not found")


@app.get("/api/audio-available")
async def check_audio_availability():
    """Check TTS/STT service availability"""
    return {
        "tts": {
            "available": TTS_AVAILABLE,
            "provider": "gTTS" if TTS_AVAILABLE else None,
            "languages": ["ru", "es", "en", "fr", "de", "pt", "it", "zh", "ja", "ko", "ar", "vi"] if TTS_AVAILABLE else []
        },
        "stt": {
            "available": STT_AVAILABLE,
            "provider": "Google Speech Recognition" if STT_AVAILABLE else None,
            "languages": ["ru-RU", "es-ES", "en-US", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR"] if STT_AVAILABLE else []
        }
    }

# ==================== END TTS/STT ====================

# Información del proyecto
@app.get("/api/info")
async def get_project_info():
    return {
        "name": "Asistente Inteligente de Integración Cultural",
        "institution": "Kubán State University (KubGU)",
        "version": "0.5.0",
        "features": [
            "Semantic search with sentence-transformers",
            "LLM integration with Ollama (llama3, qwen2, mistral)",
            "Streaming chat via SSE",
            "Conversation memory per session",
            "Keyword fallback search",
            "Búsqueda RAG en documentos oficiales",
            "Base de 200+ frases contextualizadas",
            "Personalización por perfil de usuario",
            "Traducción multiidioma",
            "TTS (Text-to-Speech) via gTTS",
            "STT (Speech-to-Text) via Google Speech Recognition",
            "Interfaz web + Telegram bot"
        ],
        "search_mode": rag_module.document_library.get_search_mode()
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        "starting_uvicorn",
        host=settings.api_host,
        port=settings.api_port,
        environment=settings.environment
    )
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_config=None
    )
