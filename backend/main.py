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
from personalization import get_conversation_memory, ConversationMemory, PersonalizationEngine
from audio_module import AudioManager
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

# Initialize personalization engine
personalization_engine = PersonalizationEngine()
logger.info("personalization_engine_initialized")

# Initialize audio manager
audio_manager = AudioManager()
logger.info("audio_manager_initialized")

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

# TTS Cache directory
tts_cache_dir = Path(__file__).parent.parent / "data" / "tts_cache"
tts_cache_dir.mkdir(parents=True, exist_ok=True)

# Cargar frases base
def load_phrases():
    phrases_file = Path(__file__).parent.parent / "data" / "phrases" / "base_phrases.json"
    if phrases_file.exists():
        with open(phrases_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

phrases_db = load_phrases()

# ==================== INCLUDE ROUTERS ====================
# Import all route routers
from app.api.routes import (
    health_router,
    phrases_router,
    profile_router,
    chat_router,
    translation_router,
    audio_router,
    info_router,
)

# Register all routers
app.include_router(health_router)
app.include_router(phrases_router)
app.include_router(profile_router)
app.include_router(chat_router)
app.include_router(translation_router)
app.include_router(audio_router)
app.include_router(info_router)

logger.info("routers_registered", count=7)

# ==================== DEPRECATED SECTION (TODO: REMOVE IN SPRINT 2) ====================
# All endpoint definitions have been moved to backend/app/api/routes/
# Legacy endpoint code removed during Sprint 1 Day 2 refactoring
# See app/api/routes/ for current route handlers

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
