"""Paired, deterministic bootstrap utilities for retrieval comparisons."""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Mapping, Sequence


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute a quantile of an empty sample")
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def paired_bootstrap(
    baseline: Mapping[str, float],
    candidate: Mapping[str, float],
    *,
    samples: int = 10000,
    seed: int = 42,
    confidence: float = 0.95,
) -> dict:
    """Bootstrap the paired mean difference ``candidate - baseline``."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    ids = sorted(set(baseline) & set(candidate))
    if not ids:
        return {"status": "not_computed", "reason": "no paired observations"}

    differences = [float(candidate[item_id]) - float(baseline[item_id]) for item_id in ids]
    observed = sum(differences) / len(differences)
    generator = random.Random(seed)
    bootstrapped = []
    for _ in range(samples):
        draw = [differences[generator.randrange(len(differences))] for _ in ids]
        bootstrapped.append(sum(draw) / len(draw))
    bootstrapped.sort()

    alpha = 1.0 - confidence
    lower = _quantile(bootstrapped, alpha / 2.0)
    upper = _quantile(bootstrapped, 1.0 - alpha / 2.0)
    non_positive = sum(value <= 0.0 for value in bootstrapped)
    non_negative = sum(value >= 0.0 for value in bootstrapped)
    p_value = min(1.0, 2.0 * min(non_positive, non_negative) / samples)
    return {
        "status": "computed",
        "paired_query_count": len(ids),
        "observed_difference": observed,
        "confidence": confidence,
        "confidence_interval": [lower, upper],
        "p_value_two_sided": p_value,
        "samples": samples,
        "seed": seed,
    }


def metric_by_query(result: Mapping, metric: str) -> Dict[str, float]:
    """Extract labeled per-query values for one metric from an evaluation."""
    return {
        query["id"]: float(query["metrics"][metric])
        for query in result.get("queries", [])
        if query.get("metrics") is not None and metric in query["metrics"]
    }


def compare_bm25_with_best_hybrid(
    results: Iterable[Mapping],
    *,
    samples: int = 10000,
    seed: int = 42,
) -> dict:
    """Compare BM25 with the completed hybrid having the best nDCG@5."""
    completed = {
        result["method"]: result
        for result in results
        if result.get("status") == "completed"
    }
    baseline = completed.get("bm25")
    candidates = [
        result
        for name, result in completed.items()
        if name in {"hybrid", "hybrid_rerank"}
        and "nDCG@5" in result.get("aggregate", {})
    ]
    if baseline is None:
        return {"status": "not_computed", "reason": "BM25 was not completed"}
    if not candidates:
        return {
            "status": "not_computed",
            "reason": "no genuine hybrid method was completed",
        }

    candidate = max(candidates, key=lambda result: result["aggregate"]["nDCG@5"])
    comparisons = {}
    for metric in ("MRR@5", "nDCG@5"):
        comparisons[metric] = paired_bootstrap(
            metric_by_query(baseline, metric),
            metric_by_query(candidate, metric),
            samples=samples,
            seed=seed,
        )
    return {
        "status": "computed",
        "baseline": "bm25",
        "candidate": candidate["method"],
        "comparisons": comparisons,
        "limitation": "A 36-query benchmark has limited statistical power.",
    }