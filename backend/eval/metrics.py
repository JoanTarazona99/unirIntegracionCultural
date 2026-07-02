"""
Information-retrieval metrics for evaluating the retrieval stack.

All functions take:
- ``retrieved``: ranked list of chunk IDs (best first)
- ``relevant``: set/collection of gold-relevant chunk IDs

These are pure-Python and dependency-free so evaluation runs on any CPU machine.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence


def _as_set(relevant: Iterable[str]) -> set:
    return set(relevant)


def hit_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """1.0 if any relevant item is in the top-k, else 0.0."""
    rel = _as_set(relevant)
    return 1.0 if any(cid in rel for cid in retrieved[:k]) else 0.0


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of relevant items retrieved within the top-k."""
    rel = _as_set(relevant)
    if not rel:
        return 0.0
    top = retrieved[:k]
    found = sum(1 for cid in rel if cid in top)
    return found / len(rel)


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of top-k results that are relevant."""
    if k <= 0:
        return 0.0
    rel = _as_set(relevant)
    top = retrieved[:k]
    if not top:
        return 0.0
    hits = sum(1 for cid in top if cid in rel)
    return hits / min(k, len(top))


def mrr(retrieved: Sequence[str], relevant: Iterable[str]) -> float:
    """Reciprocal rank of the first relevant item (0 if none)."""
    rel = _as_set(relevant)
    for idx, cid in enumerate(retrieved, start=1):
        if cid in rel:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k (binary relevance)."""
    rel = _as_set(relevant)
    if not rel:
        return 0.0
    dcg = 0.0
    for idx, cid in enumerate(retrieved[:k], start=1):
        if cid in rel:
            dcg += 1.0 / math.log2(idx + 1)
    ideal_hits = min(len(rel), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0
