"""
Cross-encoder reranker (optional).

Reranks candidate chunks with a multilingual cross-encoder for higher precision.
Guarded import keeps the stack usable on CPU-only setups without the model; when
unavailable, the reranker is a no-op that preserves the input order.
"""

from __future__ import annotations

from typing import List

from .base import RetrievalResult, minmax_normalize

try:
    from sentence_transformers import CrossEncoder

    _CE_AVAILABLE = True
except (ImportError, OSError, Exception):  # pragma: no cover - optional/heavy dep
    CrossEncoder = None  # type: ignore
    _CE_AVAILABLE = False


class CrossEncoderReranker:
    """Reorders retrieval candidates using a cross-encoder relevance model."""

    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
        self.model_name = model_name
        self._model = None

    def is_available(self) -> bool:
        return _CE_AVAILABLE

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        if not _CE_AVAILABLE:
            return False
        try:
            self._model = CrossEncoder(self.model_name)
            return True
        except BaseException:  # noqa: BLE001
            self._model = None
            return False

    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        if not results or not self._ensure_model():
            return results
        pairs = [(query, r.chunk.text) for r in results]
        try:
            scores = list(self._model.predict(pairs))
        except BaseException:  # noqa: BLE001
            return results
        norm = minmax_normalize([float(s) for s in scores])
        reranked = [
            RetrievalResult(chunk=r.chunk, score=score)
            for r, score in zip(results, norm)
        ]
        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked
