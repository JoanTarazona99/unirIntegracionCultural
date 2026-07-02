"""Tests for IR metrics and benchmark loading."""

from pathlib import Path

import pytest

from eval.metrics import hit_at_k, mrr, ndcg_at_k, precision_at_k, recall_at_k

_BENCHMARK = (
    Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "benchmark.jsonl"
)


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], {"b"}, 5) == 1.0
    assert recall_at_k(["a", "b", "c"], {"z"}, 5) == 0.0
    assert recall_at_k(["a", "b"], {"a", "b"}, 1) == 0.5


def test_precision_at_k():
    assert precision_at_k(["a", "b"], {"a"}, 2) == 0.5
    assert precision_at_k([], {"a"}, 5) == 0.0


def test_mrr():
    assert mrr(["x", "a"], {"a"}) == 0.5
    assert mrr(["a", "x"], {"a"}) == 1.0
    assert mrr(["x", "y"], {"a"}) == 0.0


def test_ndcg_at_k_perfect_and_zero():
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 2) == pytest.approx(1.0)
    assert ndcg_at_k(["x", "y"], {"a"}, 2) == 0.0


def test_hit_at_k():
    assert hit_at_k(["a", "b"], {"b"}, 5) == 1.0
    assert hit_at_k(["a", "b"], {"z"}, 5) == 0.0


def test_benchmark_loads_and_references_valid_chunks():
    from eval.benchmark import load_benchmark
    from retrieval import build_chunks_from_library
    from enhanced_rag import OfficialDocumentLibrary

    items = load_benchmark(_BENCHMARK)
    assert len(items) >= 20

    valid_ids = {c.id for c in build_chunks_from_library(OfficialDocumentLibrary())}
    for item in items:
        for cid in item.relevant_chunk_ids:
            assert cid in valid_ids, f"{item.id} references unknown chunk {cid}"
