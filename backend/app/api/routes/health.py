"""
Health check and system status routes.
"""

from fastapi import APIRouter

from app.api.dependencies import get_rag_module, get_tts_available, get_stt_available

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    rag_module = get_rag_module()
    tts_available = get_tts_available()
    stt_available = get_stt_available()
    
    return {
        "status": "ok",
        "message": "Asistente de Integración Cultural activo",
        "features": {
            "semantic_search": "available" if hasattr(rag_module.document_library, '_use_semantic') and rag_module.document_library._use_semantic else "keyword_fallback",
            "tts": "available" if tts_available else "unavailable",
            "stt": "available" if stt_available else "unavailable"
        }
    }


@router.get("/api/status")
async def get_system_status():
    """
    Get comprehensive system status.

    Returns status of all modules: RAG, LLM, TTS, STT, Cache
    """
    rag_module = get_rag_module()
    cache = get_cache()
    conversation_memory = get_conversation_memory()
    tts_available = get_tts_available()
    stt_available = get_stt_available()
    
    from datetime import datetime
    
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
        "available": tts_available,
        "provider": "gTTS" if tts_available else None,
        "languages": ["ru", "es", "en", "fr", "de", "pt", "it", "zh", "ja", "ko", "ar", "vi"] if tts_available else []
    }

    # STT status
    stt_status = {
        "available": stt_available,
        "provider": "Google Speech Recognition" if stt_available else None,
        "languages": ["ru-RU", "es-ES", "en-US", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR"] if stt_available else []
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


# Import dependencies at bottom to avoid issues
from app.api.dependencies import get_cache, get_conversation_memory
