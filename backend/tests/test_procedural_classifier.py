"""Unit tests for deterministic procedural classification."""

import pytest

from app.api.models import ProfileUpdateRequest
from procedural.classifier import ProcedureClassifier
from procedural.language import ProcedureLanguageRouter


@pytest.fixture
def classifier():
    return ProcedureClassifier()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("¿Cómo solicito la visa de estudiante?", "visa"),
        ("What documents do I need for migration registration?", "registration"),
        ("Как поступить в университет?", "enrollment"),
        ("Necesito solicitar una residencia universitaria", "housing"),
        ("¿Qué hago si pierdo la tarjeta de migración?", "migration"),
    ],
)
def test_classifier_detects_supported_procedures(classifier, query, expected):
    result = classifier.classify(query, None)
    assert result.procedure_type == expected
    assert result.confidence > 0.7


def test_classifier_reports_profile_fields_without_changing_intent(classifier):
    profile = ProfileUpdateRequest(
        country="Vietnam",
        visa_type="student",
        academic_level="bachelor",
        russian_level="A1",
    )
    result = classifier.classify("¿Cómo renuevo mi visa?", profile)
    assert result.procedure_type == "visa"
    assert result.missing_profile_fields == []


def test_classifier_requests_clarification_for_ambiguous_query(classifier):
    result = classifier.classify("Necesito ayuda con mis trámites", None)
    assert result.procedure_type == "other"
    assert result.confidence < 0.6
    assert result.clarification_questions


def test_classifier_requests_missing_registration_context(classifier):
    result = classifier.classify("Necesito hacer el registro migratorio", None)
    assert result.procedure_type == "registration"
    assert result.missing_profile_fields == ["country", "visa_type"]


@pytest.mark.parametrize(
    ("query", "language", "procedure_type"),
    [
        ("Comment demander un visa étudiant ?", "fr", "visa"),
        ("Wie beantrage ich ein Studentenvisum?", "de", "visa"),
        ("Como faço o registro migratório?", "pt", "registration"),
    ],
)
def test_classifier_detects_additional_languages(
    classifier, query, language, procedure_type
):
    result = classifier.classify(query, None)
    assert result.detected_language == language
    assert result.procedure_type == procedure_type
    assert result.confidence > 0.7


def test_language_router_covers_every_contract_language():
    assert set(ProcedureLanguageRouter.EVIDENCE_LANGUAGE_BY_QUERY) == {
        "es", "en", "ru", "fr", "de", "zh", "ar", "vi", "hy", "kk", "pt", "it", "tr"
    }


@pytest.mark.parametrize(
    ("query", "language"),
    [
        ("¿Cómo solicito una visa de estudiante?", "es"),
        ("How do I apply for a student visa?", "en"),
        ("Как получить студенческую визу?", "ru"),
        ("Comment demander un visa étudiant ?", "fr"),
        ("Wie beantrage ich ein Studentenvisum?", "de"),
        ("如何申请学生签证？", "zh"),
        ("كيف أطلب تأشيرة طالب؟", "ar"),
        ("Làm thế nào để xin thị thực sinh viên?", "vi"),
        ("Ինչպե՞ս դիմել ուսանողական վիզայի համար։", "hy"),
        ("Студенттік визаны қалай алуға болады?", "kk"),
        ("Como solicito um visto de estudante?", "pt"),
        ("Come richiedere un visto per studenti?", "it"),
        ("Öğrenci vizesi için nasıl başvururum?", "tr"),
    ],
)
def test_classifier_detects_every_supported_language(classifier, query, language):
    result = classifier.classify(query, None)
    assert result.detected_language == language
    assert result.procedure_type == "visa"