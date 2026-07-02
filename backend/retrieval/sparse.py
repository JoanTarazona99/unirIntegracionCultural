"""
BM25 sparse retriever.

Uses ``rank_bm25`` (pure Python + numpy, CPU-friendly, no model download) as a
strong lexical baseline that clearly improves over the hand-crafted keyword
synonym search currently in enhanced_rag.py. Includes lightweight multilingual
query expansion (Spanish/English -> Russian domain terms) so cross-lingual
queries still retrieve Russian source chunks.
"""

from __future__ import annotations

from typing import Dict, List

from .base import BaseRetriever, RetrievalResult, minmax_normalize
from .chunks import Chunk, tokenize

try:
    from rank_bm25 import BM25Okapi

    _BM25_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    BM25Okapi = None  # type: ignore
    _BM25_AVAILABLE = False


# Minimal cross-lingual domain expansion. This replaces the ad-hoc keyword map
# in enhanced_rag.py with a documented, retrieval-scoped table. Keys are ES/EN
# stems, values are Russian domain synonyms added to the query token stream.
DOMAIN_EXPANSION: Dict[str, List[str]] = {
    "registro": ["регистрация", "регистрации"],
    "registration": ["регистрация", "регистрации"],
    "visa": ["виза", "визы", "визовый"],
    "migracion": ["миграция", "миграционная", "миграционной"],
    "migration": ["миграция", "миграционная"],
    "dormitorio": ["общежитие", "общежития"],
    "dormitory": ["общежитие"],
    "vivienda": ["проживание", "жилье"],
    "housing": ["проживание", "жилье"],
    "profesor": ["преподаватель"],
    "clase": ["урок", "занятие"],
    "examen": ["экзамен", "экзамены"],
    "exam": ["экзамен"],
    "poliza": ["полис", "страхование"],
    "seguro": ["страхование", "полис"],
    "insurance": ["страхование", "полис"],
    "medico": ["медицинский", "врач"],
    "medical": ["медицинский"],
    "pasaporte": ["паспорт"],
    "passport": ["паспорт"],
    "documento": ["документ", "документы"],
    "document": ["документ", "документы"],
    "estudiante": ["студент", "студентов"],
    "student": ["студент", "студентов"],
    "ruso": ["русский", "язык"],
    "russian": ["русский", "язык"],
    "mfc": ["мфц"],
    "costo": ["стоимость", "цена"],
    "cost": ["стоимость", "цена"],
    "price": ["стоимость", "цена"],
}


def expand_query_tokens(tokens: List[str]) -> List[str]:
    """Append Russian domain synonyms for known ES/EN query stems."""
    expanded = list(tokens)
    for token in tokens:
        synonyms = DOMAIN_EXPANSION.get(token)
        if synonyms:
            expanded.extend(tokenize(" ".join(synonyms)))
    return expanded


class BM25Retriever(BaseRetriever):
    """Okapi BM25 retriever over chunk text with domain query expansion."""

    name = "bm25"

    def __init__(self, use_query_expansion: bool = True):
        self._chunks: List[Chunk] = []
        self._bm25 = None
        self._use_query_expansion = use_query_expansion

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

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        if self._bm25 is None or not self._chunks:
            return []
        tokens = tokenize(query)
        if self._use_query_expansion:
            tokens = expand_query_tokens(tokens)
        if not tokens:
            return []

        raw_scores = list(self._bm25.get_scores(tokens))
        ranked = sorted(
            range(len(raw_scores)), key=lambda i: raw_scores[i], reverse=True
        )
        ranked = [i for i in ranked if raw_scores[i] > 0][:top_k]
        if not ranked:
            return []

        norm = minmax_normalize([raw_scores[i] for i in ranked])
        return [
            RetrievalResult(chunk=self._chunks[idx], score=score)
            for idx, score in zip(ranked, norm)
        ]
