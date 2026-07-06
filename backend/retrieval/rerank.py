"""
Cross-encoder reranker (optional).

Reranks candidate chunks with a multilingual cross-encoder for higher precision.
Guarded import keeps the stack usable on CPU-only setups without the model; when
unavailable, the reranker is a no-op that preserves the input order.

Phase 3: Multilingualreranking, query language detection, and score fusion.
"""

from __future__ import annotations

from typing import List, Optional

from .base import RetrievalResult, minmax_normalize

try:
    from sentence_transformers import CrossEncoder

    _CE_AVAILABLE = True
except (ImportError, OSError, Exception):  # pragma: no cover - optional/heavy dep
    CrossEncoder = None  # type: ignore
    _CE_AVAILABLE = False


class QueryLanguageDetector:
    """Detect query language for multilingual retrieval routing."""
    
    @staticmethod
    def detect(query: str) -> str:
        """Detect query language.
        
        Returns:
            Language code: 'ru', 'es', or 'en'
        """
        query_lower = query.lower()
        
        # Check for Cyrillic (Russian) - highest priority
        cyrillic_count = sum(1 for c in query_lower if ord(c) >= 0x0400 and ord(c) <= 0x04FF)
        if cyrillic_count > len(query) * 0.3:  # >30% Cyrillic
            return 'ru'
        
        # Check for Spanish-specific diacritics (very high confidence)
        spanish_diacritics = {'á', 'é', 'í', 'ó', 'ú', 'ñ'}
        if any(c in query_lower for c in spanish_diacritics):
            return 'es'
        
        # Check for Spanish question marks
        if '¿' in query or '¡' in query:
            return 'es'
        
        # Check for Spanish keywords (full word match or significant substring)
        spanish_keywords = {
            'visado', 'cómo', 'dónde', 'cuál', 'cuánto', 'matrícula', 'matricula',
            'obtener', 'registración', 'registrarse', 'estudiante', 'curso', 'costo'
        }
        words = query_lower.split()
        word_set = set(words)
        
        # Count Spanish keyword matches
        spanish_matches = sum(1 for w in word_set if any(kw in w for kw in spanish_keywords))
        
        # If many Spanish keywords match, it's likely Spanish
        if spanish_matches >= 2:
            return 'es'
        
        return 'en'  # Default to English


class CrossEncoderReranker:
    """Reorders retrieval candidates using a cross-encoder relevance model."""

    # Multilingual model options
    MODEL_VARIANTS = {
        'en': 'cross-encoder/ms-marco-MiniLM-L-12-v2',  # English-optimized
        'es': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',  # Multilingual (includes ES)
        'ru': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',  # Multilingual (includes RU)
    }
    
    DEFAULT_MODEL = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'  # Multilingual fallback

    def __init__(self, model_name: Optional[str] = None, auto_language: bool = True):
        """Initialize reranker.
        
        Args:
            model_name: Specific model to use. If None, auto-detect or use default.
            auto_language: If True, auto-detect query language and select model.
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.auto_language = auto_language
        self._model = None
        self._current_model = None
        self._detector = QueryLanguageDetector()

    def is_available(self) -> bool:
        return _CE_AVAILABLE

    def _ensure_model(self, model_name: Optional[str] = None) -> bool:
        """Lazy-load model, optionally switching model if needed."""
        target_model = model_name or self.model_name
        
        # Switch model if needed
        if self._current_model != target_model:
            self._model = None
            self._current_model = None
        
        if self._model is not None:
            return True
        
        if not _CE_AVAILABLE:
            return False
        
        try:
            import warnings
            warnings.filterwarnings("ignore")
            self._model = CrossEncoder(target_model)
            self._current_model = target_model
            return True
        except BaseException:  # noqa: BLE001
            self._model = None
            self._current_model = None
            return False

    def rerank(self, query: str, results: List[RetrievalResult], top_k: Optional[int] = None) -> List[RetrievalResult]:
        """Rerank results using cross-encoder.
        
        Args:
            query: Query text
            results: Results to rerank
            top_k: Return top K (None = return all)
        
        Returns:
            Reranked results
        """
        if not results or not self._ensure_model():
            return results[:top_k] if top_k else results
        
        # Optionally select model by language
        if self.auto_language:
            lang = self._detector.detect(query)
            model_to_use = self.MODEL_VARIANTS.get(lang, self.DEFAULT_MODEL)
            if not self._ensure_model(model_to_use):
                model_to_use = self.model_name  # Fallback
                self._ensure_model(model_to_use)
        
        # Prepare pairs
        pairs = [(query, r.chunk.text) for r in results]
        
        try:
            scores = list(self._model.predict(pairs))
        except BaseException:  # noqa: BLE001
            return results[:top_k] if top_k else results
        
        # Normalize scores
        norm = minmax_normalize([float(s) for s in scores])
        
        # Create reranked results
        reranked = [
            RetrievalResult(chunk=r.chunk, score=score)
            for r, score in zip(results, norm)
        ]
        
        # Sort by score descending
        reranked.sort(key=lambda r: r.score, reverse=True)
        
        return reranked[:top_k] if top_k else reranked


def score_fusion(
    bm25_score: float,
    dense_score: float,
    rerank_score: Optional[float] = None,
    weights: tuple = (0.3, 0.4, 0.3),
) -> float:
    """Fuse scores from multiple retrievers.
    
    Args:
        bm25_score: BM25 score (0-1, normalized)
        dense_score: Dense retriever cosine similarity (0-1)
        rerank_score: Cross-encoder score (optional, 0-1 normalized)
        weights: (w_bm25, w_dense, w_rerank) weights
    
    Returns:
        Fused score (0-1)
    """
    if rerank_score is not None:
        return (
            weights[0] * bm25_score +
            weights[1] * dense_score +
            weights[2] * rerank_score
        )
    else:
        # Fallback: normalize and use only BM25 and dense
        total_weight = weights[0] + weights[1]
        w_bm25 = weights[0] / total_weight if total_weight > 0 else 0.5
        w_dense = weights[1] / total_weight if total_weight > 0 else 0.5
        return w_bm25 * bm25_score + w_dense * dense_score

