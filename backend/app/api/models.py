"""
Pydantic models for KubGU Assistant API.

Contains request/response schemas used across all endpoints.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict


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


class StreamRequest(BaseModel):
    """Streaming chat request."""
    query: str
    session_id: Optional[str] = None
    language: str = "ru"


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


class TranslationRequest(BaseModel):
    """Translation request."""
    text: str
    source_language: str = "es"
    target_language: str = "en"


class TTSRequest(BaseModel):
    """Text-to-speech request."""
    text: str
    language: str = "ru"
