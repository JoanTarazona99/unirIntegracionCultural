"""
Hybrid retriever: BM25 (sparse) + dense embeddings fused with RRF, with an
optional cross-encoder reranking stage.

Design goals:
- CPU-first: works with BM25 alone if dense embeddings are unavailable.
- Graceful degradation: if dense fails to load, falls back to sparse-only.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import BaseRetriever, RetrievalResult
from .chunks import Chunk
from .dense import DenseRetriever
from .fusion import reciprocal_rank_fusion
from .rerank import CrossEncoderReranker
from .sparse import BM25Retriever
from .latency_monitor import LatencyMonitor


class HybridRetriever(BaseRetriever):
    """Combine sparse and dense retrieval via Reciprocal Rank Fusion."""

    name = "hybrid"

    def __init__(
        self,
        sparse: Optional[BM25Retriever] = None,
        dense: Optional[DenseRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
        enable_monitor: bool = True,
    ):
        self.sparse = sparse if sparse is not None else BM25Retriever()
        self.dense = dense
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.candidate_multiplier = candidate_multiplier
        self._chunks_by_id: Dict[str, Chunk] = {}
        self._dense_active = False
        self.monitor = LatencyMonitor() if enable_monitor else None

    def is_available(self) -> bool:
        return self.sparse.is_available()

    def index(self, chunks: List[Chunk]) -> None:
        self._chunks_by_id = {c.id: c for c in chunks}
        self.sparse.index(chunks)
        self._dense_active = False
        if self.dense is not None and self.dense.is_available():
            try:
                self.dense.index(chunks)
                # Consider dense active only if embeddings were actually built.
                self._dense_active = getattr(self.dense, "_embeddings", None) is not None
            except BaseException:  # noqa: BLE001
                self._dense_active = False

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        candidate_k = max(top_k * self.candidate_multiplier, top_k)
        
        # Measure BM25 stage
        if self.monitor:
            with self.monitor.measure_stage('bm25'):
                sparse_results = self.sparse.search(query, top_k=candidate_k)
        else:
            sparse_results = self.sparse.search(query, top_k=candidate_k)

        # Sparse-only path (dense unavailable): still allow optional reranking.
        if not self._dense_active or self.dense is None:
            results = sparse_results[:top_k] if self.reranker is None else sparse_results
            if self.reranker is not None:
                if self.monitor:
                    with self.monitor.measure_stage('rerank'):
                        results = self.reranker.rerank(query, sparse_results)[:top_k]
                else:
                    results = self.reranker.rerank(query, sparse_results)[:top_k]
            return results[:top_k]

        # Measure Dense stage
        if self.monitor:
            with self.monitor.measure_stage('dense'):
                dense_results = self.dense.search(query, top_k=candidate_k)
        else:
            dense_results = self.dense.search(query, top_k=candidate_k)

        # Measure Fusion stage
        if self.monitor:
            with self.monitor.measure_stage('fusion'):
                fused = reciprocal_rank_fusion(
                    [
                        [r.chunk.id for r in sparse_results],
                        [r.chunk.id for r in dense_results],
                    ],
                    k=self.rrf_k,
                )
        else:
            fused = reciprocal_rank_fusion(
                [
                    [r.chunk.id for r in sparse_results],
                    [r.chunk.id for r in dense_results],
                ],
                k=self.rrf_k,
            )

        fused_results = [
            RetrievalResult(chunk=self._chunks_by_id[cid], score=score)
            for cid, score in fused
            if cid in self._chunks_by_id
        ]

        if self.reranker is not None:
            # Rerank a slightly larger candidate pool for precision.
            pool = fused_results[:candidate_k]
            if self.monitor:
                with self.monitor.measure_stage('rerank'):
                    results = self.reranker.rerank(query, pool)[:top_k]
            else:
                results = self.reranker.rerank(query, pool)[:top_k]
            return results

        return fused_results[:top_k]
