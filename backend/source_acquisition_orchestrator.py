"""Central policy for activating external source acquisition."""

from typing import Any, Dict, Optional

from trust.hallucination import EvidenceAssessment


def should_activate_external_search(
    evidence_assessment: Optional[EvidenceAssessment],
    grounding_result: Dict[str, Any],
    *,
    enable_external_search: bool = True,
) -> bool:
    """Return whether this query requires one external-search activation."""
    evidence_insufficient = (
        evidence_assessment is not None and not evidence_assessment.sufficient
    )
    return bool(
        enable_external_search
        and (evidence_insufficient or grounding_result.get("abstained", False))
    )


def external_search_activation_reason(
    evidence_assessment: Optional[EvidenceAssessment],
    grounding_result: Dict[str, Any],
) -> str:
    """Describe the conditions that caused an approved activation."""
    reasons = []
    if evidence_assessment is not None and not evidence_assessment.sufficient:
        reasons.append("insufficient_evidence")
    if grounding_result.get("abstained", False):
        reasons.append("grounding_abstained")
    return "+".join(reasons) or "not_activated"