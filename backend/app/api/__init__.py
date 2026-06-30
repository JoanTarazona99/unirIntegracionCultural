"""
API module for KubGU Assistant.

Contains routes, models, and dependencies.
"""

from .dependencies import (
    get_rag_module,
    get_translator,
    get_conversation_memory,
    get_cache,
    get_phrases_db,
    get_rate_limiter,
    check_rate_limit,
    get_tts_available,
    get_stt_available,
    get_audio_dirs,
)
from .models import (
    UserProfile,
    PhraseResponse,
    QueryRequest,
    StreamRequest,
    ChatResponse,
    TranslationRequest,
    TTSRequest,
)

__all__ = [
    # dependencies
    "get_rag_module",
    "get_translator",
    "get_conversation_memory",
    "get_cache",
    "get_phrases_db",
    "get_rate_limiter",
    "check_rate_limit",
    "get_tts_available",
    "get_stt_available",
    "get_audio_dirs",
    # models
    "UserProfile",
    "PhraseResponse",
    "QueryRequest",
    "StreamRequest",
    "ChatResponse",
    "TranslationRequest",
    "TTSRequest",
]
