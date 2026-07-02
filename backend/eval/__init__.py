"""Evaluation package for KubGU-RAG (retrieval metrics + benchmark harness)."""

from .metrics import recall_at_k, precision_at_k, mrr, ndcg_at_k, hit_at_k
from .benchmark import BenchmarkItem, load_benchmark

__all__ = [
    "recall_at_k",
    "precision_at_k",
    "mrr",
    "ndcg_at_k",
    "hit_at_k",
    "BenchmarkItem",
    "load_benchmark",
]
