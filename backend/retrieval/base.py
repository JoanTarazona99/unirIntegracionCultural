"""Base retriever interface and shared result type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .chunks import Chunk


@dataclass
class RetrievalResult:
    """A retrieved chunk together with its (normalized) relevance score."""

    chunk: Chunk
    score: float


class BaseRetriever:
    """
    Abstract retriever.

    Subclasses index a list of chunks and answer queries with a ranked list of
    ``RetrievalResult``. Scores are expected to be roughly comparable in [0, 1]
    so downstream fusion/thresholding behaves consistently.
    """

    name: str = "base"

    def index(self, chunks: List[Chunk]) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:  # pragma: no cover
        raise NotImplementedError

    def is_available(self) -> bool:
        """Whether this retriever can actually run (deps/model loaded)."""
        return True


def minmax_normalize(scores: List[float]) -> List[float]:
    """Scale scores to [0, 1]; returns all-1.0 when scores are constant."""
    if not scores:
        return []
    lo = min(scores)
    hi = max(scores)
    if hi <= lo:
        return [1.0 for _ in scores]
    span = hi - lo
    return [(s - lo) / span for s in scores]


def to_pairs(results: List[RetrievalResult]) -> List[Tuple[str, float]]:
    """Convenience: convert results to (chunk_id, score) tuples."""
    return [(r.chunk.id, r.score) for r in results]
