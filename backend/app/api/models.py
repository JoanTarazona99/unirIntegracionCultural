"""
Pydantic models for KubGU Assistant API.

Contains request/response schemas used across all endpoints.
"""

from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict


def _validate_non_empty_text(value: str, max_length: int = 2000) -> str:
    """Shared validator: strip, reject empty, enforce a maximum length."""
    if not isinstance(value, str):
        raise ValueError("must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be empty")
    if len(stripped) > max_length:
        raise ValueError(f"must not exceed {max_length} characters")
    return stripped


class UserProfile(BaseModel):
    """User profile with language and visa information."""
    user_id: str
    name: str
    country: str
    native_language: str
    visa_type: str  # "student", "study_visit"
    academic_level: str  # "bachelor", "master", "phd"
    housing_type: str  # "dorm", "private_apartment"
    russian_level: str  # "A1", "A2", "B1", "B2", "C1"


class PhraseResponse(BaseModel):
    """Response model for Russian phrases."""
    id: int
    russian: str
    transliteration: str
    english: str
    audio_url: Optional[str] = None


class QueryRequest(BaseModel):
    """Chat/search query request."""
    query: str
    user_id: str
    language: str = "es"
    target_language: Optional[str] = None
    session_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        return _validate_non_empty_text(v)


class StreamRequest(BaseModel):
    """Streaming chat request."""
    query: str
    session_id: Optional[str] = None
    language: str = "ru"

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        return _validate_non_empty_text(v)


class RetrievalScore(BaseModel):
    """Per-source retrieval score for AI transparency."""
    source: str
    title: Optional[str] = None
    score: float


class AIMetrics(BaseModel):
    """AI/ML transparency metrics surfaced for each chat response.

    All fields are optional so the response stays backward compatible when a
    component (LLM, retriever, trust layer) is unavailable.
    """
    search_mode: Optional[str] = None          # keyword | bm25 | dense | hybrid | hybrid_rerank
    response_mode: Optional[str] = None         # llm | template | abstained
    retrieval_scores: List[RetrievalScore] = []
    faithfulness: Optional[float] = None        # lexical grounding estimate [0,1]
    grounded: Optional[bool] = None
    abstained: Optional[bool] = None
    latency_ms: Optional[Dict[str, float]] = None   # {retrieval, llm, total}
    tokens: Optional[Dict[str, float]] = None       # {input, output, per_sec}
    models_active: Optional[Dict[str, Optional[str]]] = None  # {llm, embedding, reranker}
    query_expansion: List[str] = []


class ChatResponse(BaseModel):
    """Chat response with translations and context."""
    query: str
    answer: str
    answer_original: str
    translations: Optional[Dict[str, str]] = None
    context: List[str]
    personalized_tips: List[str]
    language: str
    available_languages: List[str] = None
    search_mode: Optional[str] = None
    session_id: Optional[str] = None
    cached: bool = False
    cache_key: Optional[str] = None
    ai_metrics: Optional[AIMetrics] = None


class TranslationRequest(BaseModel):
    """Translation request."""
    text: str
    source_language: str = "es"
    target_language: str = "en"

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        return _validate_non_empty_text(v)


class TTSRequest(BaseModel):
    """Text-to-speech request."""
    text: str
    language: str = "ru"

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        return _validate_non_empty_text(v)


# ==================== PROFILE SERVICE MODELS ====================

class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    country: str
    visa_type: str = "student"
    academic_level: str = "bachelor"
    russian_level: str = "A1"


class ProfileResponse(BaseModel):
    """Profile response."""
    user_id: str
    exists: bool
    profile: Optional[Dict] = None
    message: Optional[str] = None


# ==================== AUDIO SERVICE MODELS ====================

class AudioTTSRequest(BaseModel):
    """Text-to-speech request via AudioService."""
    text: str
    language: str = "ru"

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        return _validate_non_empty_text(v)


class AudioSTTResponse(BaseModel):
    """Speech-to-text response."""
    success: bool
    transcription: Optional[str] = None
    confidence: Optional[float] = None
    language: str = "ru"
    message: Optional[str] = None


class AudioStatusResponse(BaseModel):
    """Audio service status response."""
    available: bool
    tts_available: bool
    stt_available: bool
    manager_type: Optional[str] = None
    error: Optional[str] = None
