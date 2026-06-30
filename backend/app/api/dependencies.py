"""
FastAPI dependencies for KubGU Assistant.

Exposes lazy imports of shared application state.
Uses late binding to avoid circular imports.
"""

from fastapi import HTTPException, Request
from typing import Optional


# Global state will be accessed lazily
_main_module = None
_rate_limiter_instance = None


def _get_main():
    """Lazy import of main module to avoid circular imports."""
    global _main_module
    if _main_module is None:
        import main as _main
        _main_module = _main
    return _main_module


def get_rag_module():
    """Get the RAG module instance."""
    return _get_main().rag_module


def get_translator():
    """Get the translator instance."""
    return _get_main().translator


def get_conversation_memory():
    """Get the conversation memory instance."""
    return _get_main().conversation_memory


def get_cache():
    """Get the cache instance."""
    return _get_main().cache


def get_phrases_db():
    """Get the phrases database."""
    return _get_main().phrases_db


def get_rate_limiter():
    """Get the rate limiter instance."""
    return _get_main().rate_limiter


def get_tts_available() -> bool:
    """Check if TTS is available."""
    return _get_main().TTS_AVAILABLE


def get_stt_available() -> bool:
    """Check if STT is available."""
    return _get_main().STT_AVAILABLE


def get_audio_dirs():
    """Get audio directories."""
    return {
        "audio_dir": _get_main().audio_dir,
        "tts_cache_dir": _get_main().tts_cache_dir
    }


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(request: Request) -> str:
    """Dependency to check rate limit."""
    rate_limiter = get_rate_limiter()
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {rate_limiter.max_requests} requests per minute."
        )
    return ip


# ============ SERVICES (Sprint 1 Day 3) ============

def get_rag_service():
    """Get RAG service instance.
    
    Service wraps EnhancedRAGModule for cleaner, testable interface.
    """
    from app.services.rag_service import RAGService
    rag_module = get_rag_module()
    return RAGService(rag_module)


def get_translation_service():
    """Get translation service instance.
    
    Service wraps MultiLanguageTranslator for cleaner, testable interface.
    """
    from app.services.translation_service import TranslationService
    translator = get_translator()
    return TranslationService(translator)


def get_phrase_service():
    """Get phrase service instance.
    
    Service wraps phrases database for cleaner, testable interface.
    """
    from app.services.phrase_service import PhraseService
    phrases_db = get_phrases_db()
    return PhraseService(phrases_db)


# ============ SERVICES (Sprint 2) ============

def get_conversation_service():
    """Get conversation service instance.
    
    Service wraps ConversationMemory for cleaner, testable interface.
    """
    from app.services.conversation_service import ConversationService
    conversation_memory = get_conversation_memory()
    return ConversationService(conversation_memory)


def get_cache_service():
    """Get cache service instance.
    
    Service wraps LRUCache for cleaner, testable interface.
    """
    from app.services.cache_service import CacheService
    cache = get_cache()
    return CacheService(cache)


# ============ SERVICES (Sprint 2 Phase 3) ============

def get_personalization_engine():
    """Get the personalization engine instance."""
    return _get_main().personalization_engine


def get_audio_manager():
    """Get the audio manager instance."""
    return _get_main().audio_manager


def get_profile_service():
    """Get profile service instance.
    
    Service wraps PersonalizationEngine for cleaner, testable interface.
    """
    from app.services.profile_service import ProfileService
    personalization_engine = get_personalization_engine()
    return ProfileService(personalization_engine)


def get_audio_service():
    """Get audio service instance.
    
    Service wraps AudioManager for cleaner, testable interface.
    """
    from app.services.audio_service import AudioService
    audio_manager = get_audio_manager()
    return AudioService(audio_manager)


# ============ SERVICES (Sprint 3 - Persistence) ============

def get_redis_client():
    """Get Redis client instance.
    
    Returns None if Redis not available.
    """
    return _get_main().redis_client


def get_redis_cache_service():
    """Get Redis cache service instance.
    
    Service wraps Redis client with automatic LRU fallback.
    If Redis unavailable, transparently uses in-memory LRU cache.
    """
    from app.services.redis_cache_service import RedisCacheService
    redis_client = get_redis_client()
    return RedisCacheService(redis_client)


def get_database_service():
    """Get database service instance.
    
    Service provides persistent storage for conversations and profiles.
    Supports: SQLite (default) → PostgreSQL (optional) → Memory (fallback)
    """
    return _get_main().database_service
