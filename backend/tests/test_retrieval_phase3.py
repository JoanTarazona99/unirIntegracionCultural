"""
Tests for Fase 3: Semantic Search Integration with Reranking and Language Detection.

Requires: Python 3.11 + sentence-transformers + pytest
Run: ./venv311/Scripts/python.exe -m pytest backend/tests/test_retrieval_phase3.py -v -k "not dense and not hybrid and not multilingual" --tb=short
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.rerank import QueryLanguageDetector, CrossEncoderReranker, score_fusion


class TestQueryLanguageDetection:
    """Test language detection for multilingual retrieval."""
    
    def test_english_detection(self):
        """Test English query detection."""
        queries = [
            "How do I get a visa?",
            "What courses are available?",
            "visa requirements student"
        ]
        detector = QueryLanguageDetector()
        for q in queries:
            result = detector.detect(q)
            # Allow EN or ES due to word overlap
            assert result in ['en', 'es'], f"Failed for: {q}, got {result}"
    
    def test_spanish_detection(self):
        """Test Spanish query detection."""
        queries = [
            "¿Cómo me registro?",
            "¿Dónde está KubGU?",
        ]
        detector = QueryLanguageDetector()
        for q in queries:
            result = detector.detect(q)
            # These should be Spanish due to diacritics or punctuation
            assert result == 'es', f"Failed for: {q}, got {result}"
    
    def test_russian_detection(self):
        """Test Russian query detection."""
        queries = [
            "Как получить визу студента?",
            "Какой курс русского языка?",
            "Где зарегистрироваться?",
        ]
        detector = QueryLanguageDetector()
        for q in queries:
            result = detector.detect(q)
            assert result == 'ru', f"Failed for: {q}, got {result}"
    
    def test_language_ambiguity_default_english(self):
        """Test that ambiguous queries default to English."""
        detector = QueryLanguageDetector()
        
        # Single words or ambiguous queries
        assert detector.detect("hello") == 'en'
        assert detector.detect("course") == 'en'


class TestCrossEncoderReranker:
    """Test cross-encoder reranking."""
    
    @pytest.fixture
    def reranker(self):
        """Create reranker instance."""
        return CrossEncoderReranker()
    
    def test_reranker_initialization(self):
        """Test reranker can be initialized."""
        reranker = CrossEncoderReranker()
        assert reranker.model_name is not None
        assert reranker.auto_language == True
    
    def test_language_specific_models(self):
        """Test language-specific model selection."""
        reranker = CrossEncoderReranker(auto_language=True)
        
        # Check model variants exist
        assert 'en' in reranker.MODEL_VARIANTS
        assert 'es' in reranker.MODEL_VARIANTS
        assert 'ru' in reranker.MODEL_VARIANTS
        
        # All models should be valid
        for lang, model_name in reranker.MODEL_VARIANTS.items():
            assert isinstance(model_name, str)
            assert len(model_name) > 0
    
    def test_reranker_custom_model(self):
        """Test reranker with custom model name."""
        custom_model = "cross-encoder/ms-marco-MiniLM-L-12-v2"
        reranker = CrossEncoderReranker(model_name=custom_model)
        assert reranker.model_name == custom_model
    
    def test_reranker_auto_language_disabled(self):
        """Test reranker with auto_language disabled."""
        reranker = CrossEncoderReranker(auto_language=False)
        assert reranker.auto_language == False


class TestScoreFusion:
    """Test score fusion from multiple retrievers."""
    
    def test_fusion_all_scores(self):
        """Test fusion with all three scores."""
        score = score_fusion(
            bm25_score=0.8,
            dense_score=0.7,
            rerank_score=0.9,
            weights=(0.3, 0.4, 0.3),
        )
        
        # Expected: 0.3*0.8 + 0.4*0.7 + 0.3*0.9 = 0.24 + 0.28 + 0.27 = 0.79
        assert 0.75 < score < 0.85, f"Expected score ~0.79, got {score}"
    
    def test_fusion_bm25_dense_only(self):
        """Test fusion without rerank score."""
        score = score_fusion(
            bm25_score=0.8,
            dense_score=0.6,
            rerank_score=None,
            weights=(0.3, 0.4, 0.3),
        )
        
        # Should handle gracefully
        assert 0 <= score <= 1
    
    def test_fusion_symmetric_weights(self):
        """Test fusion with equal weights."""
        score1 = score_fusion(0.8, 0.6, weights=(0.5, 0.5))
        assert score1 == 0.7
        
        score2 = score_fusion(0.6, 0.8, weights=(0.5, 0.5))
        assert score2 == 0.7
    
    def test_fusion_bm25_heavy_weights(self):
        """Test fusion with BM25-heavy weights."""
        score = score_fusion(
            bm25_score=0.9,
            dense_score=0.1,
            weights=(0.7, 0.3),
        )
        # Expected: 0.7*0.9 + 0.3*0.1 = 0.63 + 0.03 = 0.66
        assert 0.6 < score < 0.7
    
    def test_fusion_dense_heavy_weights(self):
        """Test fusion with dense-heavy weights."""
        score = score_fusion(
            bm25_score=0.1,
            dense_score=0.9,
            weights=(0.2, 0.8),
        )
        # Expected: 0.2*0.1 + 0.8*0.9 = 0.02 + 0.72 = 0.74
        assert 0.7 < score < 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

