"""Reciprocal Rank Fusion (RRF) for combining multiple ranked result lists."""

from __future__ import annotations

from typing import Dict, List, Tuple


def reciprocal_rank_fusion(
    rankings: List[List[str]], k: int = 60
) -> List[Tuple[str, float]]:
    """
    Fuse several ranked lists of chunk IDs using Reciprocal Rank Fusion.

    RRF score for an item = sum over lists of 1 / (k + rank), where ``rank`` is
    1-based. This is robust to score-scale differences between retrievers, which
    is why it is preferred over naive score addition for hybrid sparse+dense.

    Args:
        rankings: list of ranked chunk-id lists (best first).
        k: RRF constant; larger values flatten the contribution of top ranks.

    Returns:
        List of (chunk_id, fused_score) sorted by descending score.
    """
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
