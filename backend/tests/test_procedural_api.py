"""API and orchestration tests for procedural recommendations."""

import pytest

from app.api.models import ProceduralRecommendation, ProceduralRequest
from app.api.routes.procedural import get_procedural_recommendation, router
from app.services.procedural_service import ProceduralService
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