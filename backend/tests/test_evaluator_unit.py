"""Offline unit tests for benchmark, metrics and bootstrap behavior."""

from pathlib import Path

import pytest

from eval.benchmark import (
    BenchmarkValidationError,
    filter_benchmark,
    load_benchmark,
    summarize_benchmark,
)
from eval.evaluator import compute_metrics
from eval.metrics import hit_at_k, mrr, ndcg_at_k, precision_at_k, recall_at_k
from eval.statistics import paired_bootstrap

_FIXTURE = Path(__file__).parent / "fixtures" / "evaluation_synthetic.jsonl"


def test_metrics_at_multiple_cutoffs():
    values = compute_metrics(["x", "a", "b"], {"a", "b"}, [1, 3, 5])
    assert values["Hit@1"] == 0.0
    assert values["Hit@3"] == 1.0
    assert values["Recall@3"] == 1.0
    assert values["Precision@5"] == pytest.approx(2 / 5)
    assert values["MRR@3"] == 0.5
    assert values["nDCG@3"] < 1.0


def test_metrics_handle_empty_rankings_and_no_relevant_documents():
    assert hit_at_k([], {"a"}, 5) == 0.0
    assert recall_at_k([], {"a"}, 5) == 0.0
    assert precision_at_k([], {"a"}, 5) == 0.0
    assert mrr([], {"a"}) == 0.0
    assert ndcg_at_k([], {"a"}, 5) == 0.0
    assert recall_at_k(["a"], set(), 5) == 0.0
    assert ndcg_at_k(["a"], set(), 5) == 0.0


def test_precision_uses_requested_cutoff_as_denominator():
    assert precision_at_k(["a"], {"a"}, 5) == 0.2


def test_benchmark_loader_and_filters():
    items = load_benchmark(_FIXTURE, allow_unlabeled=True)
    summary = summarize_benchmark(items)
    assert summary == {
        "total_queries": 3,
        "labeled_queries": 2,
        "unlabeled_queries": 1,
        "languages": {"en": 2, "es": 1},
        "categories": {"housing": 1, "migration": 1, "other": 1},
        "relevance_labels": 3,
    }
    assert [item.id for item in filter_benchmark(items, language="es")] == ["s003"]
    assert [item.id for item in filter_benchmark(items, category="housing")] == ["s002"]


def test_benchmark_rejects_unlabeled_by_default():
    with pytest.raises(BenchmarkValidationError, match="has no relevant_chunk_ids"):
        load_benchmark(_FIXTURE)


def test_benchmark_rejects_duplicate_ids(tmp_path):
    benchmark = tmp_path / "duplicate.jsonl"
    benchmark.write_text(
        '{"id":"x","question":"q","lang":"en","category":"c","relevant_chunk_ids":["d"]}\n'
        '{"id":"x","question":"q2","lang":"en","category":"c","relevant_chunk_ids":["d"]}\n',
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkValidationError, match="Duplicate benchmark id"):
        load_benchmark(benchmark)


def test_paired_bootstrap_is_reproducible():
    baseline = {"q1": 0.0, "q2": 0.5, "q3": 1.0}
    candidate = {"q1": 0.5, "q2": 0.5, "q3": 1.0}
    first = paired_bootstrap(baseline, candidate, samples=500, seed=17)
    second = paired_bootstrap(baseline, candidate, samples=500, seed=17)
    assert first == second
    assert first["status"] == "computed"
    assert first["paired_query_count"] == 3


def test_paired_bootstrap_requires_pairs():
    result = paired_bootstrap({"a": 1.0}, {"b": 1.0}, samples=10, seed=1)
    assert result == {"status": "not_computed", "reason": "no paired observations"}
