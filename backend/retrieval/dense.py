"""
Dense retriever using multilingual sentence embeddings.

Wraps ``sentence-transformers`` behind a guarded import so the whole retrieval
stack still runs on CPU-only machines without the model installed (BM25 remains
available). Cosine similarity is used for ranking.
"""

from __future__ import annotations

from typing import List, Optional

from .base import BaseRetriever, RetrievalResult
from .chunks import Chunk

try:
    import numpy as np

    _NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore
    _NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer

    _ST_AVAILABLE = True
except (ImportError, OSError, Exception):  # pragma: no cover - optional/heavy dep
    SentenceTransformer = None  # type: ignore
    _ST_AVAILABLE = False


class DenseRetriever(BaseRetriever):
    """Embedding-based retriever with cosine similarity."""

    name = "dense"

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self._model = None
        self._chunks: List[Chunk] = []
        self._embeddings = None
        self._loaded = False

    def is_available(self) -> bool:
        return _ST_AVAILABLE and _NUMPY_AVAILABLE

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        if not self.is_available():
            return False
        try:
            import warnings

            warnings.filterwarnings("ignore")
            self._model = SentenceTransformer(self.model_name)
            self._loaded = True
            return True
        except BaseException:  # noqa: BLE001 - CPU/model load can raise SystemError
            self._model = None
            self._loaded = False
            return False

    def index(self, chunks: List[Chunk]) -> None:
        self._chunks = list(chunks)
        if not self._ensure_model():
            self._embeddings = None
            return
        texts = [c.text for c in self._chunks] or [""]
        self._embeddings = self._model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        if self._embeddings is None or self._model is None or not self._chunks:
            return []
        query_emb = self._model.encode([query], convert_to_numpy=True)[0]

        # Cosine similarity.
        doc_norms = np.linalg.norm(self._embeddings, axis=1)
        q_norm = np.linalg.norm(query_emb)
        denom = doc_norms * q_norm
        denom[denom == 0] = 1e-9
        sims = (self._embeddings @ query_emb) / denom

        ranked = np.argsort(sims)[::-1][:top_k]
        return [
            RetrievalResult(chunk=self._chunks[int(i)], score=float(sims[int(i)]))
            for i in ranked
            if sims[int(i)] > 0
        ]
