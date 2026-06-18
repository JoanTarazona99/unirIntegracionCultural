from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
import io
from pathlib import Path
from enhanced_rag import EnhancedRAGModule
from translator import create_translator

app = FastAPI(
    title="Asistente de Integración Cultural - KubGU",
    description="Backend para soporte inteligente a estudiantes extranjeros",
    version="0.3.0"
)

# Inicializar módulo RAG mejorado e traductor multiidioma
rag_module = EnhancedRAGModule()
translator = create_translator()

# Check TTS/STT availability
TTS_AVAILABLE = False
STT_AVAILABLE = False
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
    print("[TTS] gTTS loaded - Text-to-Speech enabled")
except ImportError:
    print("[TTS] gTTS not available - TTS endpoint will return error")

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
    print("[STT] SpeechRecognition loaded - Speech-to-Text enabled")
except ImportError:
    print("[STT] SpeechRecognition not available - STT endpoint will return error")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Rutas de frases
@app.get("/api/phrases", response_model=List[PhraseResponse])
async def get_phrases(category: Optional[str] = None, limit: int = 10):
    """Obtener frases contextualizadas"""
    filtered = phrases_db

    if category:
        filtered = [p for p in filtered if p.get("category") == category]

    return filtered[:limit]

@app.get("/api/phrases/{phrase_id}")
async def get_phrase(phrase_id: int):
    """Obtener una frase específica"""
    for phrase in phrases_db:
        if phrase.get("id") == phrase_id:
            return phrase
    raise HTTPException(status_code=404, detail="Frase no encontrada")

# Rutas de usuario
@app.post("/api/users/profile")
async def create_user_profile(profile: UserProfile):
    """Crear perfil de usuario personalizado"""
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

# Rutas de búsqueda RAG
@app.post("/api/search")
async def search_documents(query: QueryRequest):
    """Búsqueda en documentos oficiales usando RAG mejorado con semantic search"""
    result = rag_module.search_and_generate(
        query.query,
        context_type=f"lang_{query.language}"
    )
    return result

@app.get("/api/search/sources")
async def get_rag_sources():
    """Obtener fuentes oficiales disponibles"""
    return {
        "sources": rag_module.document_library.list_sources(),
        "search_mode": rag_module.document_library.get_search_mode(),
        "description": "Fuentes de documentos oficiales integradas"
    }

# Rutas de chat
@app.post("/api/chat")
async def chat(request: QueryRequest):
    """Chat principal con soporte multiidioma y RAG"""
    try:
        # Idioma de respuesta (default: español)
        target_lang = request.language if request.language != "ru" else "es"

        # Buscar en el RAG (siempre en español primero)
        rag_result = rag_module.search_and_generate(
            request.query,
            context_type=f"chat_{target_lang}"
        )

        # Respuesta original en español
        answer_original = rag_result['response']

        # Traducir si el idioma no es español
        if target_lang != 'es':
            answer_translated = translator.translate_text(answer_original, target_lang)
        else:
            answer_translated = answer_original

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
    return {
        "supported_languages": translator.get_supported_languages(),
        "default_language": "es",
        "total_languages": len(translator.get_supported_languages())
    }

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

# ==================== TTS/STT ENDPOINTS ====================

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech audio

    Supports languages:
    - 'ru' (Russian)
    - 'es' (Spanish)
    - 'en' (English)
    - 'fr' (French)
    - 'de' (German)
    - etc.

    Returns: MP3 audio stream
    """
    if not TTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Install gTTS: pip install gTTS"
        )

    try:
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

        # Save to bytes buffer
        mp3_buffer = io.BytesIO()
        tts.write_to_fp(mp3_buffer)
        mp3_buffer.seek(0)

        # Return as streaming response
        return StreamingResponse(
            mp3_buffer,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{request.language}.mp3",
                "Content-Length": str(mp3_buffer.getbuffer().nbytes)
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
    Convert text to speech and save as file

    Returns: File path and audio URL
    """
    if not TTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Install gTTS: pip install gTTS"
        )

    try:
        import hashlib
        lang_map = {
            'ru': 'ru',
            'es': 'es',
            'en': 'en',
        }

        gtts_lang = lang_map.get(request.language, request.language)

        # Generate unique filename based on text hash
        text_hash = hashlib.md5(request.text.encode()).hexdigest()[:12]
        filename = f"tts_{text_hash}_{request.language}.mp3"
        filepath = audio_dir / filename

        # Create TTS and save
        tts = gTTS(text=request.text, lang=gtts_lang, slow=False)
        tts.save(str(filepath))

        return {
            "status": "success",
            "text": request.text,
            "language": request.language,
            "audio_url": f"/api/audio/{filename}",
            "file_path": str(filepath)
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
        "version": "0.3.0",
        "features": [
            "Semantic search with sentence-transformers",
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
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
