"""Tests for request-model input validation added in the security hardening pass."""

import pytest
from pydantic import ValidationError

from app.api.models import (
    QueryRequest,
    StreamRequest,
    TranslationRequest,
    TTSRequest,
    _validate_non_empty_text,
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
