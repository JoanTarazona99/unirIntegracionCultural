"""
Lightweight, dependency-free faithfulness estimation.

For high-stakes domains an LLM-based faithfulness metric (e.g. RAGAS / NLI) is
ideal, but it requires an LLM and network access. This module provides a
CPU-only, deterministic lexical-overlap proxy that estimates how well an answer
is grounded in the retrieved context. It is used as an abstention signal and as
a cheap always-available complement to LLM-as-a-judge.
"""

from __future__ import annotations

import re
from typing import Iterable, List

# Reuse the retrieval tokenizer for consistent multilingual tokenization.
try:
    from retrieval.chunks import tokenize
except Exception:  # pragma: no cover - fallback if import path differs
    _TOKEN_RE = re.compile(r"\w+", re.UNICODE)

    def tokenize(text: str) -> List[str]:
        return _TOKEN_RE.findall((text or "").lower())


_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?", re.UNICODE)

# Very common tokens carry little grounding evidence; ignore them so overlap
# reflects content words. Small multilingual stoplist (ES/EN/RU).
_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "para", "por",
    "que", "con", "del", "se", "su", "es", "the", "a", "an", "of", "to", "in",
    "and", "or", "for", "is", "are", "you", "your", "и", "в", "на", "по", "с",
    "для", "не", "что", "как", "это",
}


def _content_tokens(text: str) -> List[str]:
    return [t for t in tokenize(text) if len(t) > 2 and t not in _STOPWORDS]


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_RE.findall(text or "") if s.strip()]


def sentence_support(sentence: str, context_tokens: set) -> float:
    """Fraction of a sentence's content tokens present in the context."""
    tokens = _content_tokens(sentence)
    if not tokens:
        return 1.0  # Nothing to verify (e.g. greeting) -> treat as supported.
    supported = sum(1 for t in set(tokens) if t in context_tokens)
    return supported / len(set(tokens))


def estimate_faithfulness(answer: str, contexts: Iterable[str]) -> float:
    """
    Estimate how faithful an answer is to the retrieved contexts.

    Returns a score in [0, 1]: the mean per-sentence content-token support of
    the answer against the union of context tokens. Higher = better grounded.
    """
    context_tokens = set()
    for ctx in contexts:
        context_tokens.update(_content_tokens(ctx))
    if not context_tokens:
        return 0.0

    sentences = _split_sentences(answer)
    if not sentences:
        return 0.0

    scores = [sentence_support(s, context_tokens) for s in sentences]
    return sum(scores) / len(scores)
