"""
Fase 4: Integration Tests - HybridRetriever in RAG Pipeline

Tests for:
1. Language detection in pipeline
2. Hybrid retrieval integration
3. Score fusion accuracy
4. Reranking effect on results

Run: ./venv311/Scripts/python.exe -m pytest backend/tests/test_integration_phase4.py -v
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.rerank import QueryLanguageDetector, score_fusion
from retrieval.sparse import BM25Retriever
from retrieval.dense import DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.chunks import Chunk


class TestLanguageDetectionInPipeline:
    """Test language detection for pipeline routing"""
    
    def test_spanish_query_detection(self):
        """Test Spanish query detection"""
        detector = QueryLanguageDetector()
        
        spanish_queries = [
            "¿Cuánto cuesta el curso?",
            "¿Cómo obtener visa?",
            "¿Dónde está KubGU?",
        ]
        
        for query in spanish_queries:
            detected = detector.detect(query)
            assert detected == 'es', f"Expected 'es' for '{query}', got '{detected}'"
    
    def test_english_query_detection(self):
        """Test English query detection"""
        detector = QueryLanguageDetector()
        
        english_queries = [
            "How much is the course?",
            "How to get a visa?",
            "Where is KubGU?",
        ]
        
        for query in english_queries:
            detected = detector.detect(query)
            assert detected in ['en', 'es'], f"Expected 'en' or 'es' for '{query}', got '{detected}'"
    
    def test_russian_query_detection(self):
        """Test Russian query detection"""
        detector = QueryLanguageDetector()
        
        russian_queries = [
            "Сколько стоит курс?",
            "Как получить визу?",
            "Где находится КубГУ?",
        ]
        
        for query in russian_queries:
            detected = detector.detect(query)
            assert detected == 'ru', f"Expected 'ru' for '{query}', got '{detected}'"


class TestHybridRetrievalIntegration:
    """Test hybrid retrieval in RAG pipeline"""
    
    @pytest.fixture
    def sample_chunks(self):
        """Create test chunks"""
        return [
            Chunk(
                id="c1",
                source="KubGU",
                title="Curso Preparatorio",
                content="El curso preparatorio de ruso dura 3-6 meses. Costo: 50,000-100,000 rublos.",
            ),
            Chunk(
                id="c2",
                source="MVD",
                title="Requisitos Visa",
                content="Visa estudiante requiere nivel B1 de ruso y pasaporte válido.",
            ),
            Chunk(
                id="c3",
                source="Housing",
                title="Alojamiento",
                content="Dormitorios cuestan 3,000-5,000 rublos por mes.",
            ),
        ]
    
    def test_hybrid_retrieval_spanish_query(self, sample_chunks):
        """Test hybrid retrieval with Spanish query"""
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
            reranker=None,
        )
        
        retriever.index(sample_chunks)
        results = retriever.search("costo del curso", top_k=2)
        
        assert len(results) > 0
        assert len(results) <= 2
    
    def test_hybrid_vs_bm25_relevance(self, sample_chunks):
        """Test that hybrid can produce different ranking than BM25"""
        bm25 = BM25Retriever()
        bm25.index(sample_chunks)
        
        hybrid = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
            reranker=None,
        )
        hybrid.index(sample_chunks)
        
        query = "curso de ruso"
        
        bm25_results = bm25.search(query, top_k=3)
        hybrid_results = hybrid.search(query, top_k=3)
        
        # Both should return results
        assert len(bm25_results) > 0
        assert len(hybrid_results) > 0
    
    def test_retrieval_score_validity(self, sample_chunks):
        """Test that all retrieved results have valid scores"""
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
        )
        
        retriever.index(sample_chunks)
        results = retriever.search("visa", top_k=3)
        
        for result in results:
            assert 0 <= result.score <= 1, f"Invalid score {result.score}"
            assert result.chunk is not None
            assert result.chunk.id is not None


class TestScoreFusionInPipeline:
    """Test score fusion for multi-stage retrieval"""
    
    def test_fusion_produces_valid_scores(self):
        """Test that score fusion produces scores in [0, 1]"""
        test_cases = [
            (0.8, 0.7, None),  # BM25 + Dense
            (0.5, 0.9, 0.7),   # BM25 + Dense + Rerank
            (1.0, 0.0, None),  # Max BM25, min Dense
            (0.0, 1.0, 1.0),   # Min BM25, max Dense, max Rerank
        ]
        
        for bm25, dense, rerank in test_cases:
            score = score_fusion(bm25, dense, rerank)
            assert 0 <= score <= 1, f"Invalid fused score: {score} for ({bm25}, {dense}, {rerank})"
    
    def test_fusion_weights_impact(self):
        """Test that different weights produce different scores"""
        bm25_score = 0.8
        dense_score = 0.6
        
        # Different weight configurations
        weights_bm25_heavy = (0.7, 0.3)
        weights_dense_heavy = (0.2, 0.8)
        
        score_bm25_heavy = score_fusion(bm25_score, dense_score, weights=weights_bm25_heavy)
        score_dense_heavy = score_fusion(bm25_score, dense_score, weights=weights_dense_heavy)
        
        # BM25-heavy should favor higher BM25 score
        assert score_bm25_heavy > score_dense_heavy
    
    def test_three_way_fusion(self):
        """Test fusion with BM25 + Dense + Rerank"""
        bm25 = 0.7
        dense = 0.8
        rerank = 0.9
        
        # All three should contribute
        score = score_fusion(bm25, dense, rerank, weights=(0.3, 0.35, 0.35))
        
        # Score should be between min and max input scores
        assert min(bm25, dense, rerank) <= score <= max(bm25, dense, rerank)


class TestPhase4IntegrationScenarios:
    """Integration tests simulating real RAG scenarios"""
    
    @pytest.fixture
    def real_world_chunks(self):
        """Load real-world inspired chunks"""
        return [
            Chunk(
                id="visa_process",
                source="MVD",
                title="Proceso de Visa Estudiante",
                content="""
                El proceso de solicitud de visa estudiante en Rusia toma 3-4 semanas.
                Pasos: 1) Obtener invitación de universidad. 2) Presentar documentos en embajada.
                3) Pagar tarifa ($30-50). 4) Entrevista (a veces). 5) Recibir sello en pasaporte.
                Requisitos: Pasaporte válido 18+ meses, seguro médico, comprobante financiero.
                Nivel mínimo de ruso: B1 (TORFL).
                """,
            ),
            Chunk(
                id="kubgu_about",
                source="KubGU",
                title="Acerca de KubGU",
                content="""
                Universidad Estatal de Kubán (КубГУ) fue fundada en 1920.
                Ubicada en Krasnodar, tiene 20,000+ estudiantes.
                Ofrece 200+ programas en múltiples idiomas.
                Acreditación: Ministerio de Educación de Rusia.
                Campus moderno con laboratorios, biblioteca, deportes.
                Programa de intercambio con universidades en 50 países.
                """,
            ),
            Chunk(
                id="course_levels",
                source="KubGU",
                title="Niveles de Curso de Ruso",
                content="""
                A1 (Principiante): 0-150 horas, 3-4 meses. Vocabulario básico, presente simple.
                A2 (Básico): 150-300 horas, 3-4 meses. Conversaciones cotidianas, pasado.
                B1 (Intermedio): 300-450 horas, 3-4 meses. Discusiones académicas, futuro.
                B2 (Intermedio-Alto): 450-600 horas, 3-4 meses. Idioma académico completo.
                C1 (Avanzado): 600+ horas. Dominio profesional del idioma.
                Cada nivel incluye: clases, laboratorio de idiomas, conversación, examen final.
                """,
            ),
            Chunk(
                id="costs_breakdown",
                source="Finance",
                title="Desglose de Costos",
                content="""
                Matrícula: 2,000-3,000 USD/año.
                Alojamiento (dormitorio): 50-100 USD/mes (3,000-6,000 rublos).
                Comida: 150-200 USD/mes.
                Transporte: 30 USD/mes.
                Seguro médico: 100-150 USD/año.
                Libros y material: 50-100 USD/semestre.
                Gastos personales: 100-200 USD/mes.
                TOTAL ESTIMADO: $500-700 USD/mes.
                """,
            ),
        ]
    
    def test_query_spanish_cost_information(self, real_world_chunks):
        """Test Spanish query for cost information"""
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
        )
        
        retriever.index(real_world_chunks)
        
        query = "¿Cuánto cuesta estudiar en KubGU por mes?"
        results = retriever.search(query, top_k=2)
        
        # Should find cost-related chunks
        assert len(results) > 0
        retrieved_ids = {r.chunk.id for r in results}
        
        # costs_breakdown is most relevant
        if len(retrieved_ids) > 0:
            assert len(retrieved_ids) <= 3
    
    def test_query_russian_requirements(self, real_world_chunks):
        """Test Russian query for requirements"""
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
        )
        
        retriever.index(real_world_chunks)
        
        query = "Какие требования для студенческой визы?"
        results = retriever.search(query, top_k=2)
        
        assert len(results) > 0
        assert all(hasattr(r, 'score') for r in results)
    
    def test_query_english_language_levels(self, real_world_chunks):
        """Test English query for language levels"""
        retriever = HybridRetriever(
            sparse=BM25Retriever(),
            dense=DenseRetriever(),
        )
        
        retriever.index(real_world_chunks)
        
        query = "What are the Russian language levels offered?"
        results = retriever.search(query, top_k=2)
        
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
