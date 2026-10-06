"""
Pydantic models for KubGU Assistant API.

Contains request/response schemas used across all endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Literal, Optional


SUPPORTED_LANGUAGES = {
    "es": "español",
    "en": "English",
    "ru": "русский язык",
    "fr": "français",
    "de": "Deutsch",
    "zh": "中文 (chino simplificado)",
    "ar": "العربية (árabe)",
    "vi": "Tiếng Việt (vietnamita)",
    "hy": "հայերեն (armenio)",
    "kk": "қазақ тілі (kazajo)",
    "pt": "português",
    "it": "italiano",
    "tr": "Türkçe",
}
EVIDENCE_LANGUAGES = ("es", "en", "ru")
LanguageCode = Literal[
    "es", "en", "ru", "fr", "de", "zh", "ar", "vi", "hy", "kk", "pt", "it", "tr"
]


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
    sources_found: Optional[int] = None        # Number of sources found in RAG
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
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
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


# ==================== PROCEDURAL RECOMMENDATION MODELS ====================

ProcedureType = Literal[
    "visa",
    "registration",
    "enrollment",
    "housing",
    "migration",
    "other",
]
ProcedureStatus = Literal["complete", "needs_clarification", "abstained"]


class ProcedureStep(BaseModel):
    """One actionable step with field-level evidence traceability."""

    step_number: int = Field(ge=1)
    title: str
    description: str
    required_documents: List[str] = Field(default_factory=list)
    deadline_days: Optional[int] = Field(default=None, ge=0)
    deadline_text: Optional[str] = None
    responsible_entity: Optional[str] = None
    source_url: str
    source_title: str
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    evidence_chunk_ids: List[str] = Field(default_factory=list)
    source_version_id: Optional[str] = None

    @field_validator("title", "description", "source_title")
    @classmethod
    def validate_required_text(cls, value):
        return _validate_non_empty_text(value)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value):
        normalized = _validate_non_empty_text(value)
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        return normalized


class ProcedureClassification(BaseModel):
    """Classifier decision and the evidence needed to interpret it."""

    procedure_type: ProcedureType
    detected_language: LanguageCode
    confidence: float = Field(ge=0.0, le=1.0)
    matched_terms: List[str] = Field(default_factory=list)
    alternative_candidates: Dict[str, float] = Field(default_factory=dict)
    missing_profile_fields: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)


class ProceduralProfile(BaseModel):
    """Optional profile fields that can refine a procedural request."""

    country: Optional[str] = None
    visa_type: Optional[str] = None
    russian_level: Optional[str] = None
    academic_level: Optional[str] = None
    housing_type: Optional[str] = None


class ProceduralRequest(BaseModel):
    """Request for a personalized, evidence-checked procedure."""

    query: str
    user_id: Optional[str] = None
    language: Optional[LanguageCode] = None
    profile: Optional[ProceduralProfile] = None
    context: Dict[str, str] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value):
        return _validate_non_empty_text(value)


class ProceduralRecommendation(BaseModel):
    """Structured procedure or an explicit clarification/abstention response."""

    status: ProcedureStatus
    procedure_type: ProcedureType
    language: LanguageCode = "es"
    detected_language: LanguageCode = "es"
    evidence_language: Literal["es", "en", "ru"] = "es"
    translation_applied: bool = False
    classification_confidence: float = Field(ge=0.0, le=1.0)
    user_profile_context: Dict = Field(default_factory=dict)
    steps: List[ProcedureStep] = Field(default_factory=list)
    total_estimated_days: Optional[int] = Field(default=None, ge=0)
    warnings: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    evidence_sufficient: bool
    abstention_reason: Optional[str] = None
    retrieval_mode: str
    correlation_id: str


class ProcedureEvaluation(BaseModel):
    """Machine-readable quality assessment for one recommendation."""

    completeness: float = Field(ge=0.0, le=1.0)
    evidence: float = Field(ge=0.0, le=1.0)
    citation_validity: float = Field(ge=0.0, le=1.0)
    required_slot_coverage: float = Field(ge=0.0, le=1.0)
    sufficient: bool
    reasons: List[str] = Field(default_factory=list)


class ProcedureTestCase(BaseModel):
    """Deterministic scenario used to validate procedural behavior."""

    case_id: str
    procedure_type: ProcedureType
    query: str
    profile_context: Dict = Field(default_factory=dict)
    expected_status: ProcedureStatus


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
