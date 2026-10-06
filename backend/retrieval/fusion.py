"""Reciprocal Rank Fusion (RRF) for combining multiple ranked result lists."""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Tuple

from .base import RetrievalResult


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


def weighted_reciprocal_rank_fusion(
    results_by_channel: Mapping[str, List[RetrievalResult]],
    weights: Mapping[str, float],
    *,
    k: int = 60,
    top_k: Optional[int] = None,
) -> List[RetrievalResult]:
    """Fuse rankings with channel weights and one contribution per chunk/channel."""
    if k <= 0:
        raise ValueError("k must be greater than zero")

    scores: Dict[str, float] = {}
    result_by_id: Dict[str, RetrievalResult] = {}
    channel_ranks: Dict[str, Dict[str, int]] = {}
    channel_raw_scores: Dict[str, Dict[str, float]] = {}

    for channel, results in results_by_channel.items():
        if channel not in weights:
            raise ValueError(f"Missing weight for channel: {channel}")
        weight = float(weights[channel])
        if weight < 0:
            raise ValueError(f"Channel weight must be non-negative: {channel}")

        ranks: Dict[str, int] = {}
        raw_scores: Dict[str, float] = {}
        for result in results:
            chunk_id = result.chunk.id
            if chunk_id in ranks:
                continue
            rank = len(ranks) + 1
            ranks[chunk_id] = rank
            raw_scores[chunk_id] = float(result.score)
            result_by_id.setdefault(chunk_id, result)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank)
        channel_ranks[channel] = ranks
        channel_raw_scores[channel] = raw_scores

    ordered_ids = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    if top_k is not None:
        ordered_ids = ordered_ids[:max(0, top_k)]

    fused = []
    for chunk_id in ordered_ids:
        contributions = {
            channel: {
                "rank": ranks[chunk_id],
                "weight": float(weights[channel]),
                "contribution": float(weights[channel]) / (k + ranks[chunk_id]),
                "raw_score": channel_raw_scores[channel][chunk_id],
            }
            for channel, ranks in channel_ranks.items()
            if chunk_id in ranks
        }
        fused.append(
            RetrievalResult(
                chunk=result_by_id[chunk_id].chunk,
                score=scores[chunk_id],
                trace={
                    "fusion": "weighted_rrf",
                    "rrf_k": k,
                    "chunk_id": chunk_id,
                    "channels": contributions,
                },
            )
        )
    return fused
