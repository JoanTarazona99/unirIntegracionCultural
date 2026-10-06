"""Tests for deterministic procedural step extraction."""

from app.api.models import ProfileUpdateRequest
from procedural.generator import ProcedureGenerator


def _registration_chunk(relevance=0.9):
    return {
        "id": "МВД РФ::0",
        "source": "МВД РФ",
        "source_url": "https://мвд.рф",
        "title": "Registro migratorio",
        "relevance": relevance,
        "metadata": {"version_id": "v1"},
        "content": """
        PROCESO:
        1. Presenta la solicitud de registro.
        2. Recoge el comprobante de registro.

        DOCUMENTOS:
        - Pasaporte
        - Visa
        - Tarjeta de migración

        PLAZO: Dentro de 7 días
        ORGANISMO: МВД РФ o МФЦ
        """,
    }


def test_generator_creates_structured_steps():
    recommendation = ProcedureGenerator().generate_steps(
        "registration",
        [_registration_chunk()],
        ProfileUpdateRequest(country="Vietnam"),
        retrieval_mode="keyword",
        correlation_id="corr-1",
    )
    assert recommendation.status == "complete"
    assert len(recommendation.steps) == 2
    assert recommendation.steps[0].required_documents == [
        "Pasaporte", "Visa", "Tarjeta de migración"
    ]
    assert recommendation.steps[0].deadline_days == 7
    assert recommendation.steps[0].responsible_entity == "МВД РФ o МФЦ"
    assert recommendation.steps[0].evidence_chunk_ids == ["МВД РФ::0"]
    assert recommendation.steps[0].source_version_id == "v1"


def test_generator_abstains_when_confidence_is_low():
    recommendation = ProcedureGenerator().generate_steps(
        "registration",
        [_registration_chunk(relevance=0.2)],
        correlation_id="corr-low",
    )
    assert recommendation.status == "abstained"
    assert recommendation.steps == []
    assert recommendation.abstention_reason == "insufficient_step_evidence"


def test_generator_discards_untraceable_chunks():
    recommendation = ProcedureGenerator().generate_steps(
        "visa",
        [{"title": "Visa", "content": "DOCUMENTOS: pasaporte"}],
        correlation_id="corr-untraceable",
    )
    assert recommendation.status == "abstained"
    assert recommendation.warnings


def test_generator_stops_document_capture_at_unrelated_heading():
    chunk = _registration_chunk()
    chunk["content"] += """
    COSTOS:
    - 500 rublos
    """
    recommendation = ProcedureGenerator().generate_steps(
        "registration", [chunk], correlation_id="corr-headings"
    )
    assert "500 rublos" not in recommendation.steps[0].required_documents


def test_generator_preserves_legal_deadline_before_processing_time():
    chunk = _registration_chunk()
    chunk["content"] = chunk["content"].replace(
        "ORGANISMO: МВД РФ o МФЦ",
        "TIEMPO DE PROCESAMIENTO: 1-3 días\nORGANISMO: МВД РФ o МФЦ",
    )
    recommendation = ProcedureGenerator().generate_steps(
        "registration", [chunk], correlation_id="corr-deadline"
    )
    assert recommendation.steps[0].deadline_days == 7
    assert recommendation.steps[0].deadline_text == "Dentro de 7 días"