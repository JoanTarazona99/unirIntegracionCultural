"""Validation for persisted examples and captured real-source diagnostics."""

import json
from pathlib import Path

from app.api.models import ProcedureEvaluation, ProceduralRecommendation
from procedural.evaluator import ProcedureEvaluator
from procedural.generator import ProcedureGenerator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "data" / "procedural" / "examples"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "procedural" / "real_source_negative_cases.json"


def test_three_persisted_examples_are_complete_and_traceable():
    manifest = json.loads((EXAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["examples"]) == 3
    assert manifest["llm_used"] is False
    assert manifest["network_used"] is False

    for entry in manifest["examples"]:
        payload = json.loads((EXAMPLES_DIR / entry["path"]).read_text(encoding="utf-8"))
        recommendation = ProceduralRecommendation(**payload["recommendation"])
        evaluation = ProcedureEvaluation(**payload["evaluation"])
        assert recommendation.status == "complete"
        assert recommendation.steps
        assert evaluation.sufficient is True
        assert all(step.evidence_chunk_ids for step in recommendation.steps)


def test_partial_real_source_diagnostics_fail_closed():
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    generator = ProcedureGenerator()
    evaluator = ProcedureEvaluator()

    for case in cases:
        recommendation = generator.generate_steps(
            case["procedure_type"],
            [
                {
                    "id": f"diagnostic::{case['case_id']}",
                    "source": case["source"],
                    "source_url": case["source_url"],
                    "title": case["source_title"],
                    "content": case["documented_excerpt"],
                    "evidence_confidence": 0.6,
                }
            ],
            correlation_id=case["case_id"],
        )
        evaluation = evaluator.evaluate(recommendation)
        assert case["expected_status"] == "abstained"
        assert evaluation.sufficient is False
        assert "required_procedure_slots_missing" in evaluation.reasons