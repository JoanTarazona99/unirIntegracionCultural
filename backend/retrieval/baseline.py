"""
Keyword baseline retriever.

Wraps the existing ``OfficialDocumentLibrary._keyword_search`` so the current
production behaviour can be evaluated as the baseline against the new BM25 /
hybrid strategies on the same benchmark. Results are mapped back to stable chunk
IDs via a (source, title) lookup.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .base import BaseRetriever, RetrievalResult
from .chunks import Chunk


class KeywordBaselineRetriever(BaseRetriever):
    """Adapter over the legacy keyword search for baseline evaluation."""

    name = "keyword"

    def __init__(self, library):
        self._library = library
        self._chunks: List[Chunk] = []
        self._by_key: Dict[Tuple[str, str], Chunk] = {}

    def index(self, chunks: List[Chunk]) -> None:
        self._chunks = list(chunks)
        self._by_key = {(c.source, c.title.strip()): c for c in self._chunks}

    def _resolve_chunk(self, result: Dict) -> Optional[Chunk]:
        key = (result.get("source", ""), (result.get("title") or "").strip())
        chunk = self._by_key.get(key)
        if chunk is not None:
            return chunk
        # Fallback: match by title only.
        title = (result.get("title") or "").strip()
        for c in self._chunks:
            if c.title.strip() == title:
                return c
        return None

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        raw = self._library._keyword_search(query)
        results: List[RetrievalResult] = []
        seen = set()
        for item in raw:
            if item.get("search_mode") == "fallback":
                continue
            chunk = self._resolve_chunk(item)
            if chunk is None or chunk.id in seen:
                continue
            seen.add(chunk.id)
            results.append(
                RetrievalResult(chunk=chunk, score=float(item.get("relevance", 0.0)))
            )
            if len(results) >= top_k:
                break
        return results
