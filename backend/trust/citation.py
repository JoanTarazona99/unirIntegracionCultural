"""
Citation and abstention guard.

Given a generated answer and the retrieved chunks, this module:
1. Estimates grounding (faithfulness) of the answer in the sources.
2. Attaches citations to the official sources used.
3. Decides whether to abstain (below threshold) and returns a safe fallback
   message that redirects the user to the official source.

This is the core of the "trustworthy AI" layer for high-stakes migration info.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .hallucination import estimate_faithfulness

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
    answer: str
    abstained: bool = False
    citations: List[Dict] = field(default_factory=list)


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


def enforce_grounding(
    answer: str,
    results: List[Dict],
    *,
    threshold: float = 0.35,
    language: str = "es",
) -> GroundingResult:
    """
    Verify that ``answer`` is grounded in ``results``; abstain if not.

    Args:
        answer: the generated answer text.
        results: retrieved chunk dicts (must include 'content', 'source').
        threshold: minimum faithfulness score required to return the answer.
        language: language for the abstention fallback message.

    Returns:
        GroundingResult with the (possibly replaced) answer and citations.
    """
    contexts = [r.get("content", "") for r in results]
    citations = format_citations(results)
    score = estimate_faithfulness(answer, contexts)

    if score >= threshold and citations:
        return GroundingResult(
            grounded=True,
            score=score,
            answer=answer,
            abstained=False,
            citations=citations,
        )

    # Abstain: build a safe fallback pointing to official sources.
    source_labels = ", ".join(
        f"{c['source']}" + (f" ({c['url']})" if c.get("url") else "")
        for c in citations
    ) or "КубГУ / МВД РФ / МФЦ / Госуслуги"
    template = _ABSTENTION_MESSAGES.get(language, _ABSTENTION_MESSAGES["es"])
    fallback = template.format(sources=source_labels)

    return GroundingResult(
        grounded=False,
        score=score,
        answer=fallback,
        abstained=True,
        citations=citations,
    )
