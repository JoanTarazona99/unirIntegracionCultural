"""
Factory to build a configured retriever from a mode string.

Modes:
- ``keyword``       : legacy keyword search baseline (requires ``library``)
- ``bm25``          : BM25 sparse retriever
- ``dense``         : dense embedding retriever
- ``hybrid``        : BM25 + dense fused with RRF
- ``hybrid_rerank`` : hybrid followed by a cross-encoder reranker
"""

from __future__ import annotations

from typing import List, Optional

from .base import BaseRetriever
from .baseline import KeywordBaselineRetriever
from .chunks import Chunk
from .dense import DenseRetriever
from .hybrid import HybridRetriever
from .rerank import CrossEncoderReranker
from .sparse import BM25Retriever


def build_retriever(
    mode: str,
    chunks: List[Chunk],
    *,
    library=None,
    dense_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    rrf_k: int = 60,
) -> BaseRetriever:
    """Construct and index a retriever for the requested mode."""
    mode = (mode or "bm25").strip().lower()

    if mode == "keyword":
        if library is None:
            raise ValueError("keyword mode requires the document library instance")
        retriever: BaseRetriever = KeywordBaselineRetriever(library)
    elif mode == "bm25":
        retriever = BM25Retriever()
    elif mode == "dense":
        retriever = DenseRetriever(model_name=dense_model)
    elif mode in ("hybrid", "hybrid_rerank"):
        reranker: Optional[CrossEncoderReranker] = None
        if mode == "hybrid_rerank":
            reranker = CrossEncoderReranker(model_name=reranker_model)
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(model_name=dense_model),
            reranker=reranker,
            rrf_k=rrf_k,
        )
    else:
        raise ValueError(f"Unknown retrieval mode: {mode}")

    retriever.index(chunks)
    return retriever
