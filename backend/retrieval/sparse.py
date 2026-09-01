"""
BM25 sparse retriever.

Uses ``rank_bm25`` (pure Python + numpy, CPU-friendly, no model download) as a
strong lexical baseline that clearly improves over the hand-crafted keyword
synonym search currently in enhanced_rag.py. Includes lightweight multilingual
query expansion (Spanish/English -> Russian domain terms) so cross-lingual
queries still retrieve Russian source chunks.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .base import BaseRetriever, RetrievalResult
from .chunks import Chunk, tokenize
from .expansion import DEFAULT_EXPANSION_VERSION, LEXICAL_EXPANSIONS, expand_query
from .fusion import reciprocal_rank_fusion

try:
    from rank_bm25 import BM25Okapi

    _BM25_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    BM25Okapi = None  # type: ignore
    _BM25_AVAILABLE = False


DOMAIN_EXPANSION: Dict[str, List[str]] = {
    term: translations
    for language_table in LEXICAL_EXPANSIONS[DEFAULT_EXPANSION_VERSION].values()
    for term, translations in language_table.items()
}
DOMAIN_EXPANSION["mfc"] = ["мфц"]


def expand_query_tokens(tokens: List[str]) -> List[str]:
    """Append Russian domain synonyms for known ES/EN query stems."""
    return tokenize(expand_query(" ".join(tokens), "auto", "ru"))


class BM25Retriever(BaseRetriever):
    """Okapi BM25 retriever over chunk text with domain query expansion."""

    name = "bm25"

    def __init__(
        self,
        use_query_expansion: bool = True,
        rrf_k: int = 60,
        expansion_version: str = DEFAULT_EXPANSION_VERSION,
        candidate_multiplier: int = 1,
    ):
        self._chunks: List[Chunk] = []
        self._bm25 = None
        self._use_query_expansion = use_query_expansion
        self._rrf_k = rrf_k
        self._expansion_version = expansion_version
        self._candidate_multiplier = candidate_multiplier

    def is_available(self) -> bool:
        return _BM25_AVAILABLE

    def index(self, chunks: List[Chunk]) -> None:
        if not _BM25_AVAILABLE:
            raise RuntimeError(
                "rank_bm25 is not installed. Add 'rank-bm25' to requirements.txt."
            )
        self._chunks = list(chunks)
        corpus_tokens = [tokenize(c.text) for c in self._chunks]
        # BM25Okapi requires a non-empty corpus.
        if not corpus_tokens:
            corpus_tokens = [[""]]
        self._bm25 = BM25Okapi(corpus_tokens)

    def _rank(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        tokens = tokenize(query)
        if not tokens:
            return []
        raw_scores = list(self._bm25.get_scores(tokens))
        ranked = sorted(
            range(len(raw_scores)), key=lambda i: raw_scores[i], reverse=True
        )
        ranked = [i for i in ranked if raw_scores[i] > 0][:top_k]
        return [(idx, raw_scores[idx]) for idx in ranked]

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        if self._bm25 is None or not self._chunks:
            return []

        candidate_k = max(top_k * self._candidate_multiplier, top_k)
        original = self._rank(query, candidate_k)
        expanded_query = (
            expand_query(
                query,
                "auto",
                "ru",
                version=self._expansion_version,
            )
            if self._use_query_expansion
            else query
        )
        rankings = [[self._chunks[idx].id for idx, _ in original]]
        expanded: List[Tuple[int, float]] = []
        if expanded_query != query:
            original_token_count = len(tokenize(query))
            translated_query = " ".join(tokenize(expanded_query)[original_token_count:])
            expanded = self._rank(translated_query, candidate_k)
            rankings.append([self._chunks[idx].id for idx, _ in expanded])
        if not any(rankings):
            return []

        fused = reciprocal_rank_fusion(rankings, k=self._rrf_k)
        chunks_by_id = {chunk.id: chunk for chunk in self._chunks}
        original_ranks = {
            self._chunks[idx].id: rank
            for rank, (idx, _) in enumerate(original, start=1)
        }
        expanded_ranks = {
            self._chunks[idx].id: rank
            for rank, (idx, _) in enumerate(expanded, start=1)
        }
        results: List[RetrievalResult] = []
        for chunk_id, score in fused[:top_k]:
            query_hits = []
            if chunk_id in original_ranks:
                query_hits.append({
                    "variant": "original",
                    "query": query,
                    "rank": original_ranks[chunk_id],
                })
            if chunk_id in expanded_ranks:
                query_hits.append({
                    "variant": "expanded",
                    "query": translated_query,
                    "rank": expanded_ranks[chunk_id],
                })
            results.append(RetrievalResult(
                chunk=chunks_by_id[chunk_id],
                score=score,
                trace={
                    "fusion": "rrf",
                    "rrf_k": self._rrf_k,
                    "rrf_score": score,
                    "expansion_version": self._expansion_version,
                    "query_hits": query_hits,
                },
            ))
        return results
