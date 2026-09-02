"""
Dense retriever using multilingual sentence embeddings.

Wraps ``sentence-transformers`` behind a guarded import so the whole retrieval
stack still runs on CPU-only machines without the model installed (BM25 remains
available). Cosine similarity is used for ranking.
"""

from __future__ import annotations

from typing import Dict, List

from .base import BaseRetriever, RetrievalResult
from .chunks import Chunk
from .embedding_cache import EmbeddingCache
from .expansion import DEFAULT_EXPANSION_VERSION, expand_query
from .fusion import reciprocal_rank_fusion

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
    """Embedding-based retriever with lexical expansion and RRF fusion."""

    name = "dense"

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        enable_cache: bool = True,
        use_query_expansion: bool = True,
        rrf_k: int = 60,
        expansion_version: str = DEFAULT_EXPANSION_VERSION,
    ):
        self.model_name = model_name
        self._model = None
        self._chunks: List[Chunk] = []
        self._embeddings = None
        self._loaded = False
        self.enable_cache = enable_cache
        self.cache = EmbeddingCache(ttl=3600, max_size=10000) if enable_cache else None
        self._use_query_expansion = use_query_expansion
        self._rrf_k = rrf_k
        self._expansion_version = expansion_version

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

    def embed_query(self, query: str):
        """Encode one query, reusing the configured embedding cache."""
        if self.cache is not None:
            cached_emb = self.cache.get(query)
            if cached_emb is not None:
                return cached_emb
        query_embedding = self._model.encode([query], convert_to_numpy=True)[0]
        if self.cache is not None:
            self.cache.set(query, query_embedding)
        return query_embedding

    def _retrieve_by_embedding(self, query_embedding, top_k: int) -> List[RetrievalResult]:
        """Rank indexed chunks by cosine similarity to an encoded query."""
        doc_norms = np.linalg.norm(self._embeddings, axis=1)
        q_norm = np.linalg.norm(query_embedding)
        denom = doc_norms * q_norm
        denom[denom == 0] = 1e-9
        sims = (self._embeddings @ query_embedding) / denom

        ranked = np.argsort(sims)[::-1][:top_k]
        return [
            RetrievalResult(chunk=self._chunks[int(i)], score=float(sims[int(i)]))
            for i in ranked
            if sims[int(i)] > 0
        ]

    def _rrf_fusion(
        self,
        results_original: List[RetrievalResult],
        results_expanded: List[RetrievalResult],
        *,
        query_original: str,
        query_expanded: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """Fuse original and expanded query rankings with traceable RRF scores."""
        rankings = [[result.chunk.id for result in results_original]]
        if results_expanded:
            rankings.append([result.chunk.id for result in results_expanded])
        fused = reciprocal_rank_fusion(rankings, k=self._rrf_k)

        result_by_id: Dict[str, RetrievalResult] = {
            result.chunk.id: result
            for result in [*results_original, *results_expanded]
        }
        original_ranks = {
            result.chunk.id: rank
            for rank, result in enumerate(results_original, start=1)
        }
        expanded_ranks = {
            result.chunk.id: rank
            for rank, result in enumerate(results_expanded, start=1)
        }

        results: List[RetrievalResult] = []
        for chunk_id, score in fused[:top_k]:
            query_hits = []
            if chunk_id in original_ranks:
                query_hits.append({
                    "variant": "original",
                    "query": query_original,
                    "rank": original_ranks[chunk_id],
                })
            if chunk_id in expanded_ranks:
                query_hits.append({
                    "variant": "expanded",
                    "query": query_expanded,
                    "rank": expanded_ranks[chunk_id],
                })
            results.append(RetrievalResult(
                chunk=result_by_id[chunk_id].chunk,
                score=score,
                trace={
                    "fusion": "rrf",
                    "rrf_k": self._rrf_k,
                    "rrf_score": score,
                    "expansion_version": self._expansion_version,
                    "query_original": query_original,
                    "query_expanded": query_expanded,
                    "rank_original": original_ranks.get(chunk_id),
                    "rank_expanded": expanded_ranks.get(chunk_id),
                    "query_hits": query_hits,
                },
            ))
        return results

    def search(
        self,
        query: str,
        top_k: int = 5,
        **kwargs,
    ) -> List[RetrievalResult]:
        if self._embeddings is None or self._model is None or not self._chunks:
            return []

        query_original = query
        source_language = kwargs.get("source_language", "auto")
        query_expanded = (
            expand_query(
                query,
                source_language,
                "ru",
                version=self._expansion_version,
            )
            if self._use_query_expansion
            else query
        )

        embedding_original = self.embed_query(query_original)
        results_original = self._retrieve_by_embedding(embedding_original, top_k)
        results_expanded: List[RetrievalResult] = []
        if query_expanded != query_original:
            embedding_expanded = self.embed_query(query_expanded)
            results_expanded = self._retrieve_by_embedding(embedding_expanded, top_k)

        return self._rrf_fusion(
            results_original,
            results_expanded,
            query_original=query_original,
            query_expanded=query_expanded,
            top_k=top_k,
        )
