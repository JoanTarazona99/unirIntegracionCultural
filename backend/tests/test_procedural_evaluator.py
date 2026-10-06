"""Tests for procedural quality and fail-closed evaluation."""

from procedural.evaluator import ProcedureEvaluator
from procedural.generator import ProcedureGenerator


def _complete_recommendation():
    chunk = {
        "id": "Госуслуги::2",
        "source": "Госуслуги",
        "source_url": "https://www.gosuslugi.ru",
        "title": "Visa de estudiante",
        "relevance": 0.9,
        "content": """
        PROCESO:
        1. Presenta la solicitud de visa.
        DOCUMENTOS:
        - Pasaporte
        - Invitación universitaria
        PLAZO: Dentro de 30 días
        ORGANISMO: Consulado de la Federación Rusa
        """,
    }
    return ProcedureGenerator().generate_steps("visa", [chunk], correlation_id="eval-1")


def test_evaluator_accepts_complete_grounded_procedure():
    evaluation = ProcedureEvaluator().evaluate(_complete_recommendation())
    assert evaluation.completeness == 1.0
    assert evaluation.citation_validity == 1.0
    assert evaluation.required_slot_coverage == 1.0
    assert evaluation.sufficient is True


def test_evaluator_rejects_missing_required_slots():
    recommendation = _complete_recommendation()
    recommendation.steps[0].required_documents = []
    recommendation.steps[0].deadline_days = None
    recommendation.steps[0].deadline_text = None
    evaluation = ProcedureEvaluator().evaluate(recommendation)
    assert evaluation.sufficient is False
    assert "required_procedure_slots_missing" in evaluation.reasons


def test_evaluator_generates_deterministic_case():
    cases = ProcedureEvaluator.generate_test_cases("housing")
    assert len(cases) == 1
    assert cases[0].case_id == "procedural-housing-001"
    assert cases[0].expected_status == "complete"