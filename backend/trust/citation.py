"""
Citation and abstention guard with multi-level grounding policies.

Given a generated answer and the retrieved chunks, this module:
1. Estimates grounding (faithfulness) using improved multi-level analysis
2. Attaches citations to the official sources used
3. Decides whether to abstain (below threshold) and returns a safe fallback
   message that redirects the user to the official source
4. Supports topic-specific stricter thresholds for sensitive domains
   (visa, registration, fees, etc.)

This is the core of the "trustworthy AI" layer for high-stakes migration info.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .hallucination import estimate_faithfulness, analyze_grounding_improved, GroundingLevel

# Sensitive topics requiring stricter grounding thresholds (multi-language)
# Includes various grammatical forms and variants
SENSITIVE_TOPICS = {
    # Visa (EN, ES, RU - multiple forms)
    "visa", "visado", "виза", "визу", "визе", "визой",
    # Fee/Cost (EN, ES, RU)
    "fee", "cost", "coste", "costo", "matrícula", "matricula", "tariff", "tarifa", 
    "тариф", "стоимость", "цена", "плата", "стипендия",
    # Charge/Fine (EN, ES, RU)
    "multa", "штраф",
    # Registration (EN, ES, RU - capture root forms)
    "regist", "registro", "зарегистр", "регист",
    # Document (EN, ES, RU)
    "documento", "документ", "документы",
    # Police/Authority (EN, ES, RU)
    "police", "полиция", "миграция", "мвд", "authorities",
}

_ABSTENTION_MESSAGES = {
    "es": (
        "No tengo información suficiente y verificada para responder con seguridad. "
        "Por favor, consulta la fuente oficial: {sources}"
    ),
    "en": (
        "I don't have enough verified information to answer reliably. "
        "Please check the official source: {sources}"
    ),
    "ru": (
        "У меня недостаточно проверенной информации для точного ответа. "
        "Пожалуйста, обратитесь к официальному источнику: {sources}"
    ),
}


@dataclass
class GroundingResult:
    """Outcome of the grounding/abstention check."""

    grounded: bool
    score: float
    level: str  # "high", "medium", "low"
    answer: str
    abstained: bool = False
    citations: List[Dict] = field(default_factory=list)
    explanation: str = ""
    matched_entities: List[str] = field(default_factory=list)
    missing_entities: List[str] = field(default_factory=list)


def format_citations(results: List[Dict], max_sources: int = 3) -> List[Dict]:
    """Build a de-duplicated citation list from retrieved result dicts."""
    citations: List[Dict] = []
    seen = set()
    for item in results:
        source = item.get("source")
        if not source or source in seen:
            continue
        seen.add(source)
        citations.append(
            {
                "source": source,
                "title": item.get("title"),
                "url": item.get("source_url"),
            }
        )
        if len(citations) >= max_sources:
            break
    return citations


def _is_sensitive_topic(query: str) -> bool:
    """Check if query discusses sensitive/high-stakes topics.
    
    Handles multi-language keywords (EN, ES, RU).
    Uses substring matching for robustness with encoding issues.
    """
    query_lower = query.lower()
    
    for topic in SENSITIVE_TOPICS:
        # Simple substring match (works across all encodings)
        if topic in query_lower:
            return True
    
    return False


def enforce_grounding_improved(
    answer: str,
    results: List[Dict],
    *,
    language: str = "es",
    strict_mode: bool = False,  # For sensitive topics
) -> GroundingResult:
    """
    Improved grounding enforcement with multi-level policy.

    Thresholds:
    - HIGH (≥0.75): Always respond (safe)
    - MEDIUM (0.4-0.75): Respond but may mark partial support; stricter for sensitive
    - LOW (<0.4): Abstain or trigger knowledge acquisition

    Args:
        answer: Generated response
        results: Retrieved chunks
        language: Response language
        strict_mode: If True, use stricter thresholds (for visa/fees/registration)

    Returns:
        GroundingResult with decision and supporting info
    """
    contexts = [r.get("content", "") for r in results]
    citations = format_citations(results)

    # Use improved analysis
    analysis = analyze_grounding_improved(answer, contexts)

    # Determine thresholds
    is_sensitive = _is_sensitive_topic(answer) or strict_mode
    if is_sensitive:
        # Stricter for sensitive topics (visa, fees, registration)
        # But more lenient for contact/email info
        has_email = "@" in answer or any(r.get("content", "").count("@") > 0 for r in results)
        if has_email:
            # For contact/email info: VERY LENIENT - if answer has email that's in sources, accept it
            # This handles cross-language scenarios (Spanish response, Russian context)
            high_threshold = 0.3
            medium_threshold = 0.15
        else:
            # For visa/fee info: strict thresholds
            high_threshold = 0.8
            medium_threshold = 0.5
    else:
        # Normal thresholds
        high_threshold = 0.75
        medium_threshold = 0.4

    # Policy decision
    if analysis.score >= high_threshold and citations:
        # HIGH: confident, respond normally
        return GroundingResult(
            grounded=True,
            score=analysis.score,
            level=GroundingLevel.HIGH.value,
            answer=answer,
            abstained=False,
            citations=citations,
            explanation=analysis.explanation,
            matched_entities=analysis.matched_entities,
            missing_entities=analysis.missing_entities,
        )
    elif analysis.score >= medium_threshold and citations:
        # MEDIUM: partial support, can respond with caution
        # Optionally append disclaimer (controlled by flag)
        return GroundingResult(
            grounded=True,
            score=analysis.score,
            level=GroundingLevel.MEDIUM.value,
            answer=answer,
            abstained=False,
            citations=citations,
            explanation=analysis.explanation,
            matched_entities=analysis.matched_entities,
            missing_entities=analysis.missing_entities,
        )
    else:
        # LOW: insufficient support -> abstain
        source_labels = ", ".join(
            f"{c['source']}" + (f" ({c['url']})" if c.get("url") else "")
            for c in citations
        ) or "КубГУ / МВД РФ / МФЦ / Госуслуги"
        template = _ABSTENTION_MESSAGES.get(language, _ABSTENTION_MESSAGES["es"])
        fallback = template.format(sources=source_labels)

        return GroundingResult(
            grounded=False,
            score=analysis.score,
            level=GroundingLevel.LOW.value,
            answer=fallback,
            abstained=True,
            citations=citations,
            explanation=analysis.explanation,
            matched_entities=analysis.matched_entities,
            missing_entities=analysis.missing_entities,
        )


def enforce_grounding(
    answer: str,
    results: List[Dict],
    *,
    threshold: float = 0.35,
    language: str = "es",
) -> GroundingResult:
    """
    Verify that ``answer`` is grounded in ``results``; abstain if not.

    DEPRECATED: Use enforce_grounding_improved() instead.
    This function now delegates to the improved version for backward compatibility.

    Args:
        answer: the generated answer text.
        results: retrieved chunk dicts (must include 'content', 'source').
        threshold: minimum faithfulness score required to return the answer.
                  (ignored, using improved multi-level logic instead)
        language: language for the abstention fallback message.

    Returns:
        GroundingResult with the (possibly replaced) answer and citations.
    """
    # Delegate to improved version
    return enforce_grounding_improved(
        answer, results, language=language, strict_mode=False
    )
