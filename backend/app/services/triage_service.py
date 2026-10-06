"""Procedure-aware language routing for adaptive multilingual retrieval."""

from __future__ import annotations

from typing import Dict, List

from app.api.models import EVIDENCE_LANGUAGES, SUPPORTED_LANGUAGES
from procedural.classifier import ProcedureClassifier


PROCEDURE_PRIMARY_TARGET = {
    "visa": "ru",
    "registration": "ru",
    "migration": "ru",
    "enrollment": "es",
    "housing": "es",
    "other": "en",
}


class TriageService:
    """Select evidence languages from intent, never from user region."""

    def __init__(self, classifier: ProcedureClassifier | None = None):
        self.classifier = classifier or ProcedureClassifier()

    def classify_procedure_type(
        self,
        query: str,
        detected_language: str,
    ) -> Dict:
        if detected_language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {detected_language}")

        classification = self.classifier.classify(query, None)
        primary_target = PROCEDURE_PRIMARY_TARGET[classification.procedure_type]
        secondary_targets: List[str] = [
            language
            for language in EVIDENCE_LANGUAGES
            if language != primary_target
        ]
        requires_multilingual = (
            detected_language not in EVIDENCE_LANGUAGES
            or primary_target != detected_language
            or classification.confidence < 0.75
        )
        return {
            "procedure_type": classification.procedure_type,
            "primary_target": primary_target,
            "secondary_targets": secondary_targets,
            "requires_multilingual": requires_multilingual,
            "confidence": classification.confidence,
            "detected_language": detected_language,
        }


_default_triage_service = TriageService()


def classify_procedure_type(query: str, detected_language: str) -> Dict:
    """Classify one query using the default deterministic triage service."""
    return _default_triage_service.classify_procedure_type(query, detected_language)