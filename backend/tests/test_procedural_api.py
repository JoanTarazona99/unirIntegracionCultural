"""API and orchestration tests for procedural recommendations."""

from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError

from app.api.models import (
    ProceduralFeedback,
    ProceduralFeedbackStored,
    ProceduralFeedbackSummary,
    ProceduralRecommendation,
    ProceduralRequest,
)
from app.api.routes.procedural import (
    get_procedural_feedback_summary,
    get_procedural_recommendation,
    router,
    submit_procedural_feedback,
)
from app.services.procedural_service import DuplicateFeedbackError, ProceduralService
from enhanced_rag import EnhancedRAGModule
from starlette.requests import Request


class _FakeProfileService:
    def __init__(self, profile=None):
        self.profile = profile

    def get_profile(self, user_id):
        if self.profile is None:
            return {"user_id": user_id, "exists": False}
        return {"user_id": user_id, "exists": True, "profile": {"profile": self.profile}}


class _FakeRAGService:
    def __init__(self, sufficient=True):
        self.sufficient = sufficient
        self.last_query = None

    def retrieve_evidence(self, query, *, correlation_id=None):
        self.last_query = query
        return {
            "search_mode": "keyword",
            "evidence_assessment": {
                "sufficient": self.sufficient,
                "reasons": [] if self.sufficient else ["query_relevance_below_threshold"],
            },
            "results": [
                {
                    "id": "МВД РФ::0",
                    "source": "МВД РФ",
                    "source_url": "https://мвд.рф",
                    "title": "Registro migratorio",
                    "relevance": 0.9,
                    "content": """
                    PROCESO:
                    1. Presenta la solicitud de registro.
                    DOCUMENTOS:
                    - Pasaporte
                    - Visa
                    PLAZO: Dentro de 7 días
                    ORGANISMO: МВД РФ
                    """,
                }
            ],
        }

    def retrieve_evidence_adaptive(self, query, language, *, correlation_id=None):
        self.adaptive_language = language
        payload = self.retrieve_evidence(query, correlation_id=correlation_id)
        payload["search_mode"] = "adaptive_weighted_rrf"
        payload["adaptive_retrieval"] = {
            "translated_targets": ["es"] if language == "fr" else []
        }
        return payload


class _FakeTranslator:
    def __init__(self, *, lose_critical=False):
        self.lose_critical = lose_critical

    def translate_text(self, text, target_language="en", source_language="es"):
        if source_language == "fr" and target_language == "es":
            return "¿Cómo hago el registro migratorio?"
        if source_language == "de" and target_language == "en":
            return "How do I complete migration registration?"
        if self.lose_critical and "7" in text:
            return "translated deadline without its number"
        return f"[{target_language}] {text}"


def test_service_returns_clarification_for_missing_profile():
    service = ProceduralService(_FakeRAGService(), _FakeProfileService())
    result = service.recommend(
        ProceduralRequest(query="¿Cómo hago el registro migratorio?"),
        correlation_id="corr-clarify",
    )
    assert result.status == "needs_clarification"
    assert result.clarification_questions
    assert result.steps == []


def test_service_returns_grounded_complete_recommendation():
    service = ProceduralService(_FakeRAGService(), _FakeProfileService())
    request = ProceduralRequest(
        query="¿Cómo hago el registro migratorio?",
        profile={"country": "Vietnam", "visa_type": "student", "russian_level": "A1"},
    )
    result = service.recommend(request, correlation_id="corr-complete")
    assert result.status == "complete"
    assert result.evidence_sufficient is True
    assert result.steps[0].source_url == "https://мвд.рф"


def test_service_abstains_when_global_evidence_is_insufficient():
    service = ProceduralService(_FakeRAGService(sufficient=False), _FakeProfileService())
    request = ProceduralRequest(
        query="¿Cómo hago el registro migratorio?",
        profile={"country": "Vietnam", "visa_type": "student"},
    )
    result = service.recommend(request, correlation_id="corr-abstain")
    assert result.status == "abstained"
    assert result.steps == []
    assert result.abstention_reason == "query_relevance_below_threshold"


def test_procedural_endpoint_uses_server_correlation_id():
    class _EndpointService:
        def recommend(self, request, *, correlation_id):
            return ProceduralRecommendation(
                status="needs_clarification",
                procedure_type="other",
                classification_confidence=0.25,
                user_profile_context={},
                steps=[],
                evidence_sufficient=False,
                retrieval_mode="keyword",
                correlation_id=correlation_id,
                clarification_questions=["¿Qué trámite necesitas?"],
            )

    http_request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/procedural",
            "headers": [],
            "request_id": "server-correlation-id",
        }
    )
    coroutine = get_procedural_recommendation(
        ProceduralRequest(query="Necesito ayuda"),
        http_request,
        procedural_service=_EndpointService(),
        _="test",
    )
    with pytest.raises(StopIteration) as completed:
        coroutine.send(None)
    response = completed.value.value

    assert response.status == "needs_clarification"
    assert response.correlation_id == "server-correlation-id"


def test_procedural_router_exposes_post_endpoint():
    route = next(route for route in router.routes if route.path == "/api/procedural")
    assert "POST" in route.methods
    assert route.response_model is ProceduralRecommendation


def test_retrieval_only_enriches_keyword_results_with_chunk_ids():
    rag = EnhancedRAGModule(use_llm=False)
    payload = rag.retrieve_evidence("регистрация документы МВД")
    assert payload["results"]
    assert all(result.get("id") for result in payload["results"])


def test_service_translates_french_query_and_response_safely():
    rag_service = _FakeRAGService()
    service = ProceduralService(
        rag_service,
        _FakeProfileService(),
        _FakeTranslator(),
    )
    request = ProceduralRequest(
        query="Comment faire l'enregistrement migratoire ?",
        profile={"country": "France", "visa_type": "student"},
    )
    result = service.recommend(request, correlation_id="corr-fr")
    assert rag_service.last_query == "Comment faire l'enregistrement migratoire ?"
    assert rag_service.adaptive_language == "fr"
    assert result.status == "complete"
    assert result.detected_language == "fr"
    assert result.language == "fr"
    assert result.evidence_language == "es"
    assert result.translation_applied is True
    assert result.steps[0].description.startswith("[fr]")


def test_service_abstains_when_translation_loses_critical_information():
    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        _FakeTranslator(lose_critical=True),
    )
    request = ProceduralRequest(
        query="Wie mache ich die Registrierung?",
        profile={"country": "Deutschland", "visa_type": "student"},
    )
    result = service.recommend(request, correlation_id="corr-de")
    assert result.status == "abstained"
    assert result.steps == []
    assert result.abstention_reason == "response_translation_unavailable_or_unsafe"


def test_translation_integrity_rejects_added_or_removed_critical_values():
    assert ProceduralService.validate_translation_integrity(
        "Presentar en МВД dentro de 7 días: https://мвд.рф",
        "Submit to МВД within 7 days: https://мвд.рф",
    )
    assert not ProceduralService.validate_translation_integrity(
        "Presentar en МВД dentro de 7 días: https://мвд.рф",
        "Submit to МВД within 10 days: https://мвд.рф",
    )


def test_procedural_feedback_saving_creates_atomic_json_with_utc_timestamp(
    tmp_path, monkeypatch
):
    written_calls = []
    from app.services import procedural_service as ps_module

    original_atomic_write = ps_module.atomic_write_json

    def _recording_atomic_write(path, payload):
        written_calls.append((path, payload))
        return original_atomic_write(path, payload)

    monkeypatch.setattr(ps_module, "atomic_write_json", _recording_atomic_write)

    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path,
    )
    feedback = ProceduralFeedback(
        correlation_id="corr_feedback_001",
        procedure_type="registration",
        language="es",
        precision_score=5,
        completeness_score=4,
        usefulness_score=5,
        clarity_score=4,
        comments="Pasos claros y fuentes trazables",
        user_id="dev-self-eval",
    )

    stored = service.save_feedback(feedback)

    expected_file = tmp_path / "feedback_corr_feedback_001.json"
    assert expected_file.exists()
    assert len(written_calls) == 1
    assert written_calls[0][0] == expected_file
    assert stored.correlation_id == "corr_feedback_001"
    assert stored.timestamp_utc.endswith("+00:00")
    assert "path" not in stored.model_dump()

    disk_payload = json.loads(expected_file.read_text(encoding="utf-8"))
    assert disk_payload["correlation_id"] == "corr_feedback_001"
    assert disk_payload["procedure_type"] == "registration"
    assert disk_payload["language"] == "es"
    assert disk_payload["precision_score"] == 5
    assert disk_payload["completeness_score"] == 4
    assert disk_payload["usefulness_score"] == 5
    assert disk_payload["clarity_score"] == 4
    assert disk_payload["comments"] == "Pasos claros y fuentes trazables"
    assert disk_payload["user_id"] == "dev-self-eval"
    assert disk_payload["timestamp_utc"] == stored.timestamp_utc
    assert "path" not in disk_payload


def test_procedural_feedback_summary_aggregates_multiple_feedbacks(tmp_path):
    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path,
    )

    items = [
        ProceduralFeedback(
            correlation_id="corr-1",
            procedure_type="visa",
            language="es",
            precision_score=5,
            completeness_score=4,
            usefulness_score=5,
            clarity_score=4,
            comments="Revisión preliminar visa ES",
            user_id="dev-1",
        ),
        ProceduralFeedback(
            correlation_id="corr-2",
            procedure_type="visa",
            language="ru",
            precision_score=3,
            completeness_score=4,
            usefulness_score=3,
            clarity_score=4,
            comments=None,
            user_id=None,
        ),
        ProceduralFeedback(
            correlation_id="corr-3",
            procedure_type="registration",
            language="es",
            precision_score=4,
            completeness_score=5,
            usefulness_score=4,
            clarity_score=5,
            comments="Registro completo",
            user_id="dev-1",
        ),
    ]
    for item in items:
        service.save_feedback(item)

    summary = service.get_feedback_summary()
    assert summary.total_feedbacks == 3
    assert summary.averages.precision == 4.0
    assert summary.averages.completeness == round(13 / 3, 3)
    assert summary.averages.usefulness == 4.0
    assert summary.averages.clarity == round(13 / 3, 3)

    assert set(summary.by_procedure_type.keys()) == {"registration", "visa"}
    assert summary.by_procedure_type["visa"].count == 2
    assert summary.by_procedure_type["visa"].averages.precision == 4.0
    assert summary.by_procedure_type["visa"].averages.completeness == 4.0
    assert summary.by_procedure_type["registration"].count == 1
    assert summary.by_procedure_type["registration"].averages.completeness == 5.0

    assert set(summary.by_language.keys()) == {"es", "ru"}
    assert summary.by_language["es"].count == 2
    assert summary.by_language["es"].averages.precision == 4.5
    assert summary.by_language["ru"].count == 1
    assert summary.by_language["ru"].averages.precision == 3.0


def test_procedural_feedback_summary_returns_zeros_when_empty(tmp_path):
    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path / "nonexistent",
    )
    summary = service.get_feedback_summary()
    assert summary.total_feedbacks == 0
    assert summary.averages.precision == 0.0
    assert summary.averages.completeness == 0.0
    assert summary.averages.usefulness == 0.0
    assert summary.averages.clarity == 0.0
    assert summary.by_procedure_type == {}
    assert summary.by_language == {}


@pytest.mark.parametrize(
    ("field_name", "invalid_score"),
    [
        ("precision_score", -1),
        ("precision_score", 6),
        ("completeness_score", -1),
        ("completeness_score", 6),
        ("usefulness_score", -2),
        ("usefulness_score", 10),
        ("clarity_score", -1),
        ("clarity_score", 6),
    ],
)
def test_procedural_feedback_validates_score_bounds(field_name, invalid_score):
    payload = {
        "correlation_id": "corr-bounds",
        "procedure_type": "enrollment",
        "language": "en",
        "precision_score": 3,
        "completeness_score": 3,
        "usefulness_score": 3,
        "clarity_score": 3,
        "comments": None,
        "user_id": None,
    }
    payload[field_name] = invalid_score
    with pytest.raises(PydanticValidationError):
        ProceduralFeedback(**payload)


def test_procedural_feedback_accepts_boundary_scores_zero_and_five():
    low = ProceduralFeedback(
        correlation_id="corr-zero",
        procedure_type="housing",
        language="ru",
        precision_score=0,
        completeness_score=0,
        usefulness_score=0,
        clarity_score=0,
        comments=None,
        user_id=None,
    )
    high = ProceduralFeedback(
        correlation_id="corr-five",
        procedure_type="migration",
        language="es",
        precision_score=5,
        completeness_score=5,
        usefulness_score=5,
        clarity_score=5,
        comments="Excelente",
        user_id="dev",
    )
    assert low.precision_score == 0
    assert high.clarity_score == 5


def test_procedural_feedback_rejects_unsafe_correlation_id():
    for invalid_id in ("../traversal", "id with spaces", "id/slash", "niño_1", "тест123", "a" * 129):
        with pytest.raises(PydanticValidationError):
            ProceduralFeedback(
                correlation_id=invalid_id,
                procedure_type="visa",
                language="es",
                precision_score=4,
                completeness_score=4,
                usefulness_score=4,
                clarity_score=4,
                comments=None,
                user_id=None,
            )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("precision_score", True),
        ("precision_score", False),
        ("completeness_score", True),
        ("usefulness_score", "4"),
        ("clarity_score", 4.0),
    ],
)
def test_procedural_feedback_rejects_boolean_and_coerced_scores(field_name, invalid_value):
    payload = {
        "correlation_id": "corr-strict-int",
        "procedure_type": "visa",
        "language": "es",
        "precision_score": 4,
        "completeness_score": 4,
        "usefulness_score": 4,
        "clarity_score": 4,
        "comments": None,
        "user_id": None,
    }
    payload[field_name] = invalid_value
    with pytest.raises(PydanticValidationError):
        ProceduralFeedback(**payload)


def test_procedural_feedback_enforces_comments_and_user_id_length_limits():
    valid = ProceduralFeedback(
        correlation_id="corr-lengths",
        procedure_type="visa",
        language="es",
        precision_score=4,
        completeness_score=4,
        usefulness_score=4,
        clarity_score=4,
        comments="c" * 2000,
        user_id="u" * 128,
    )
    assert len(valid.comments) == 2000
    assert len(valid.user_id) == 128

    with pytest.raises(PydanticValidationError):
        ProceduralFeedback(
            correlation_id="corr-comments-too-long",
            procedure_type="visa",
            language="es",
            precision_score=4,
            completeness_score=4,
            usefulness_score=4,
            clarity_score=4,
            comments="c" * 2001,
            user_id="u",
        )

    with pytest.raises(PydanticValidationError):
        ProceduralFeedback(
            correlation_id="corr-userid-too-long",
            procedure_type="visa",
            language="es",
            precision_score=4,
            completeness_score=4,
            usefulness_score=4,
            clarity_score=4,
            comments="ok",
            user_id="u" * 129,
        )


def test_procedural_feedback_rejects_duplicate_correlation_id_without_overwriting(tmp_path):
    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path,
    )
    first = ProceduralFeedback(
        correlation_id="corr-dup-1",
        procedure_type="visa",
        language="es",
        precision_score=5,
        completeness_score=5,
        usefulness_score=5,
        clarity_score=5,
        comments="First submission",
        user_id="user-1",
    )
    second = ProceduralFeedback(
        correlation_id="corr-dup-1",
        procedure_type="visa",
        language="es",
        precision_score=1,
        completeness_score=1,
        usefulness_score=1,
        clarity_score=1,
        comments="Second submission attempting overwrite",
        user_id="user-2",
    )

    first_stored = service.save_feedback(first)
    with pytest.raises(DuplicateFeedbackError):
        service.save_feedback(second)

    duplicate_coro = submit_procedural_feedback(
        second,
        procedural_service=service,
        _="test",
    )
    with pytest.raises(HTTPException) as exc_info:
        duplicate_coro.send(None)
    assert exc_info.value.status_code == 409

    saved_payload = json.loads(
        (tmp_path / "feedback_corr-dup-1.json").read_text(encoding="utf-8")
    )
    assert saved_payload["precision_score"] == 5
    assert saved_payload["comments"] == "First submission"
    assert saved_payload["timestamp_utc"] == first_stored.timestamp_utc


def test_procedural_feedback_concurrent_submissions_allow_exactly_one_winner(tmp_path):
    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path,
    )

    def _submit(index: int):
        item = ProceduralFeedback(
            correlation_id="corr-concurrent-race",
            procedure_type="registration",
            language="es",
            precision_score=index % 6,
            completeness_score=4,
            usefulness_score=4,
            clarity_score=4,
            comments=f"worker-{index}",
            user_id=f"u-{index}",
        )
        return service.save_feedback(item)

    successes = []
    duplicates = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_submit, idx) for idx in range(8)]
        for future in futures:
            try:
                successes.append(future.result())
            except DuplicateFeedbackError:
                duplicates += 1

    assert len(successes) == 1
    assert duplicates == 7
    assert not list(tmp_path.glob(".feedback_*.lock"))
    summary = service.get_feedback_summary()
    assert summary.total_feedbacks == 1


def test_procedural_feedback_summary_tracks_invalid_files_and_propagates_io_errors(
    tmp_path, monkeypatch
):
    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path,
    )
    service.save_feedback(
        ProceduralFeedback(
            correlation_id="corr-valid-1",
            procedure_type="visa",
            language="es",
            precision_score=4,
            completeness_score=4,
            usefulness_score=4,
            clarity_score=4,
            comments=None,
            user_id=None,
        )
    )
    # 1. Corrupt JSON syntax
    (tmp_path / "feedback_corrupt.json").write_text("{not-valid-json", encoding="utf-8")
    # 2. Incompatible JSON root type (list instead of dict)
    (tmp_path / "feedback_list.json").write_text("[1, 2, 3]", encoding="utf-8")
    # 3. Incompatible schema (missing timestamp_utc / score out of range)
    (tmp_path / "feedback_bad_schema.json").write_text(
        json.dumps(
            {
                "correlation_id": "bad_schema",
                "procedure_type": "visa",
                "language": "es",
                "precision_score": 99,
                "completeness_score": 4,
                "usefulness_score": 4,
                "clarity_score": 4,
            }
        ),
        encoding="utf-8",
    )

    summary = service.get_feedback_summary()
    assert summary.total_feedbacks == 1
    assert summary.invalid_files_skipped == 3

    # Verify operational I/O errors are NOT silently counted as invalid files
    from pathlib import Path as _Path

    original_read_text = _Path.read_text

    def _failing_read_text(self, *args, **kwargs):
        if self.name == "feedback_corr-valid-1.json":
            raise PermissionError("Simulated OS permission failure")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(_Path, "read_text", _failing_read_text)
    with pytest.raises(PermissionError):
        service.get_feedback_summary()

    summary_coro = get_procedural_feedback_summary(
        procedural_service=service,
        _="test",
    )
    with pytest.raises(HTTPException) as exc_info:
        summary_coro.send(None)
    assert exc_info.value.status_code == 500
    assert "Simulated OS permission failure" not in exc_info.value.detail


def test_procedural_feedback_endpoints_and_routes(tmp_path):
    post_route = next(
        route for route in router.routes if route.path == "/api/procedural/feedback"
    )
    summary_route = next(
        route
        for route in router.routes
        if route.path == "/api/procedural/feedback/summary"
    )
    assert "POST" in post_route.methods
    assert post_route.response_model is ProceduralFeedbackStored
    assert "GET" in summary_route.methods
    assert summary_route.response_model is ProceduralFeedbackSummary

    service = ProceduralService(
        _FakeRAGService(),
        _FakeProfileService(),
        feedback_dir=tmp_path,
    )
    feedback = ProceduralFeedback(
        correlation_id="corr-endpoint-1",
        procedure_type="enrollment",
        language="es",
        precision_score=4,
        completeness_score=5,
        usefulness_score=4,
        clarity_score=5,
        comments="Evaluación por endpoint",
        user_id="developer",
    )

    post_coro = submit_procedural_feedback(
        feedback,
        procedural_service=service,
        _="test",
    )
    with pytest.raises(StopIteration) as post_done:
        post_coro.send(None)
    stored = post_done.value.value
    assert stored.correlation_id == "corr-endpoint-1"
    assert "path" not in stored.model_dump()

    summary_coro = get_procedural_feedback_summary(
        procedural_service=service,
        _="test",
    )
    with pytest.raises(StopIteration) as summary_done:
        summary_coro.send(None)
    summary = summary_done.value.value
    assert summary.total_feedbacks == 1
    assert summary.invalid_files_skipped == 0
    assert "evaluation_scope" not in summary.model_dump()
    assert summary.averages.precision == 4.0
    assert summary.by_procedure_type["enrollment"].count == 1
    assert summary.by_language["es"].count == 1