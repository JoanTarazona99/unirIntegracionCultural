"""
Retrieval package for KubGU-RAG.

Provides a modular, CPU-first retrieval stack that can be composed into several
strategies (keyword baseline, BM25, dense, hybrid, hybrid+rerank) and evaluated
against a domain benchmark.

Public entry points:
    build_chunks_from_library(library) -> List[Chunk]
    build_retriever(mode, chunks, ...) -> BaseRetriever
"""

from .chunks import Chunk, build_chunks_from_library, build_chunks_from_flat, tokenize
from .base import BaseRetriever, RetrievalResult
from .sparse import BM25Retriever
from .dense import DenseRetriever
from .hybrid import HybridRetriever
from .factory import build_retriever

__all__ = [
    "Chunk",
    "build_chunks_from_library",
    "build_chunks_from_flat",
    "tokenize",
    "BaseRetriever",
    "RetrievalResult",
    "BM25Retriever",
    "DenseRetriever",
    "HybridRetriever",
    "build_retriever",
]
