"""Tests for request-model input validation added in the security hardening pass."""

import pytest
from pydantic import ValidationError

from app.api.models import (
    ProceduralRequest,
    ProcedureStep,
    QueryRequest,
    StreamRequest,
    TranslationRequest,
    TTSRequest,
    _validate_non_empty_text,
    SUPPORTED_LANGUAGES,
)


def test_query_request_strips_whitespace():
    req = QueryRequest(query="  hola  ", user_id="u1")
    assert req.query == "hola"


def test_query_request_rejects_empty():
    with pytest.raises(ValidationError):
        QueryRequest(query="   ", user_id="u1")


def test_stream_request_rejects_empty():
    with pytest.raises(ValidationError):
        StreamRequest(query="")


def test_translation_request_rejects_empty():
    with pytest.raises(ValidationError):
        TranslationRequest(text="")


def test_tts_request_rejects_empty():
    with pytest.raises(ValidationError):
        TTSRequest(text="  ")


def test_validate_non_empty_text_enforces_max_length():
    with pytest.raises(ValueError):
        _validate_non_empty_text("x" * 2001)


def test_validate_non_empty_text_accepts_valid():
    assert _validate_non_empty_text("  valid  ") == "valid"


def test_procedure_step_validates_evidence_fields():
    step = ProcedureStep(
        step_number=1,
        title="Presentar documentos",
        description="Entrega los documentos en la oficina responsable.",
        required_documents=["Pasaporte"],
        deadline_days=7,
        responsible_entity="МВД РФ",
        source_url="https://мвд.рф",
        source_title="Registro migratorio",
        evidence_confidence=0.9,
        evidence_chunk_ids=["МВД РФ::0"],
    )
    assert step.evidence_chunk_ids == ["МВД РФ::0"]


def test_procedure_step_rejects_non_http_source():
    with pytest.raises(ValidationError):
        ProcedureStep(
            step_number=1,
            title="Paso",
            description="Descripción",
            source_url="not-a-url",
            source_title="Fuente",
            evidence_confidence=0.8,
        )


def test_procedural_request_rejects_empty_query():
    with pytest.raises(ValidationError):
        ProceduralRequest(query="   ")


def test_procedural_request_rejects_unsupported_language():
    with pytest.raises(ValidationError):
        ProceduralRequest(query="How do I register?", language="ja")


def test_procedural_language_contract_matches_enumerated_codes():
    assert tuple(SUPPORTED_LANGUAGES) == (
        "es", "en", "ru", "fr", "de", "zh", "ar", "vi", "hy", "kk", "pt", "it", "tr"
    )
