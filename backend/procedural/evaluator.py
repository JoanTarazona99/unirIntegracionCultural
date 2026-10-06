"""Quality evaluation and fail-closed policy for procedures."""

from __future__ import annotations

from typing import List

from app.api.models import (
    ProcedureEvaluation,
    ProceduralRecommendation,
    ProcedureTestCase,
)


class ProcedureEvaluator:
    """Evaluate structure and provenance without claiming human usefulness."""

    _REQUIRED_SLOTS = {
        "visa": ("documents", "deadline", "entity"),
        "registration": ("documents", "deadline", "entity"),
        "enrollment": ("documents", "deadline", "entity"),
        "housing": ("documents", "deadline", "entity"),
        "migration": ("documents", "deadline", "entity"),
        "other": (),
    }

    @staticmethod
    def evaluate_completeness(recommendation: ProceduralRecommendation) -> float:
        if not recommendation.steps:
            return 0.0
        completed = 0
        total = 0
        for step in recommendation.steps:
            values = (
                step.title,
                step.description,
                step.source_url,
                step.source_title,
                step.evidence_chunk_ids,
            )
            completed += sum(bool(value) for value in values)
            total += len(values)
        return completed / total

    @staticmethod
    def evaluate_evidence(recommendation: ProceduralRecommendation) -> float:
        if not recommendation.steps:
            return 0.0
        per_step = []
        for step in recommendation.steps:
            provenance = bool(
                step.source_url.startswith(("http://", "https://"))
                and step.source_title
                and step.evidence_chunk_ids
            )
            per_step.append(step.evidence_confidence if provenance else 0.0)
        return sum(per_step) / len(per_step)

    @staticmethod
    def evaluate_citation_validity(recommendation: ProceduralRecommendation) -> float:
        if not recommendation.steps:
            return 0.0
        valid = sum(
            bool(step.source_url and step.source_title and step.evidence_chunk_ids)
            for step in recommendation.steps
        )
        return valid / len(recommendation.steps)

    def evaluate_required_slots(self, recommendation: ProceduralRecommendation) -> float:
        required = self._REQUIRED_SLOTS.get(recommendation.procedure_type, ())
        if not required:
            return 1.0
        coverage = {
            "documents": any(step.required_documents for step in recommendation.steps),
            "deadline": any(
                step.deadline_days is not None or step.deadline_text
                for step in recommendation.steps
            ),
            "entity": any(step.responsible_entity for step in recommendation.steps),
        }
        return sum(bool(coverage[slot]) for slot in required) / len(required)

    def evaluate(self, recommendation: ProceduralRecommendation) -> ProcedureEvaluation:
        completeness = self.evaluate_completeness(recommendation)
        evidence = self.evaluate_evidence(recommendation)
        citations = self.evaluate_citation_validity(recommendation)
        slot_coverage = self.evaluate_required_slots(recommendation)
        reasons: List[str] = []
        if completeness < 1.0:
            reasons.append("incomplete_step_structure")
        if evidence < 0.6:
            reasons.append("insufficient_step_evidence")
        if citations < 1.0:
            reasons.append("invalid_or_missing_citations")
        if slot_coverage < 1.0:
            reasons.append("required_procedure_slots_missing")
        sufficient = not reasons and recommendation.procedure_type != "other"
        return ProcedureEvaluation(
            completeness=round(completeness, 3),
            evidence=round(evidence, 3),
            citation_validity=round(citations, 3),
            required_slot_coverage=round(slot_coverage, 3),
            sufficient=sufficient,
            reasons=reasons,
        )

    @staticmethod
    def generate_test_cases(procedure_type: str) -> List[ProcedureTestCase]:
        queries = {
            "visa": "¿Cómo solicito una visa de estudiante?",
            "registration": "¿Cómo hago el registro migratorio?",
            "enrollment": "¿Cómo completo la matrícula universitaria?",
            "housing": "¿Cómo solicito una residencia universitaria?",
            "migration": "¿Qué hago con mi tarjeta de migración?",
            "other": "Necesito ayuda con un trámite.",
        }
        expected = "needs_clarification" if procedure_type == "other" else "complete"
        return [
            ProcedureTestCase(
                case_id=f"procedural-{procedure_type}-001",
                procedure_type=procedure_type,
                query=queries[procedure_type],
                profile_context={},
                expected_status=expected,
            )
        ]