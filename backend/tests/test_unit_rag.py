"""
Tests unitarios para los componentes RAG del KubGU Assistant.
Proyecto: unirIntegracionCultural
Módulo: enhanced_rag.py (+ paquete retrieval/)
Cobertura objetivo: SemanticSearchEngine, BM25Retriever, HybridRetriever,
                    EnhancedRAGModule, OfficialDocumentLibrary

Ejecución OFFLINE: no requiere Ollama, Redis ni descarga de modelos.
- sentence-transformers se mockea (enhanced_rag.SentenceTransformer).
- rank_bm25 es dependencia pura de Python (CPU) ya disponible; se usa real.
- El LLM (Ollama) se desactiva con EnhancedRAGModule(use_llm=False).

NOTE (nombres reales vs. enunciado):
- SemanticSearchEngine.__init__(self, model_name=...)  NO recibe documents.
  build_index(self, documents) -> bool ; search(self, query, top_k) -> List[Tuple[Dict, float]].
- SentenceTransformer se importa dentro de enhanced_rag solo si
  ENABLE_SEMANTIC_SEARCH=1; por eso se parchea con create=True junto al flag
  enhanced_rag.SEMANTIC_SEARCH_AVAILABLE.
- BM25Retriever vive en retrieval.sparse; su método es search(query, top_k) y
  devuelve List[RetrievalResult] (no retrieve()->List[Tuple]). BM25Okapi se
  importa en retrieval.sparse (no en enhanced_rag).
- HybridRetriever vive en retrieval.hybrid: __init__(sparse, dense, reranker,
  rrf_k, ...) y search(query, top_k) -> List[RetrievalResult]. La fusión RRF está
  en retrieval.fusion.reciprocal_rank_fusion.
- EnhancedRAGModule expone search_and_generate(query, ...) (no search(query,
  session_id)); devuelve un dict con 'response', 'sources', 'sources_found',
  'response_mode'. La abstención se realiza vía trust.enforce_grounding y marca
  response_mode == 'abstained'.
- OfficialDocumentLibrary carga las fuentes КубГУ, МВД РФ, МФЦ, Госуслуги y FAQ
  (РЖД / аэропорт no están en enhanced_rag.py, sino en data/rag_database.json).
"""

import pytest
import numpy as np
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import enhanced_rag
from enhanced_rag import (
    SemanticSearchEngine,
    OfficialDocumentLibrary,
    EnhancedRAGModule,
)
from retrieval.base import RetrievalResult
from retrieval.chunks import Chunk, build_chunks_from_flat, build_chunks_from_library
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.sparse import BM25Retriever
from retrieval.hybrid import HybridRetriever
from retrieval.dense import DenseRetriever
from retrieval.rerank import CrossEncoderReranker
from retrieval.factory import build_retriever
from retrieval.baseline import KeywordBaselineRetriever

# rank_bm25 es opcional; si faltara, los tests de BM25/Hybrid se omiten.
_BM25_AVAILABLE = BM25Retriever().is_available()
bm25_required = pytest.mark.skipif(
    not _BM25_AVAILABLE, reason="rank_bm25 no está instalado"
)


# ── FIXTURES ──────────────────────────────────────────────────────────────
@pytest.fixture
def sample_documents():
    """5 documentos realistas del dominio КубГУ.

    Incluye los campos del enunciado (id, text, source, section) y también
    title/content/source_url, que son los que consumen realmente
    SemanticSearchEngine.build_index y build_chunks_from_flat.
    """
    docs = [
        {
            "source": "МВД РФ",
            "title": "Регистрация по месту пребывания",
            "content": (
                "Регистрация иностранных студентов проводится в течение 7 дней "
                "после прибытия. Необходимые документы: паспорт, виза, "
                "миграционная карта."
            ),
            "source_url": "https://мвд.рф",
        },
        {
            "source": "КубГУ",
            "title": "Общежитие и проживание",
            "content": (
                "Общежитие для иностранных студентов. Стоимость проживания "
                "150-300 рублей в месяц. Комендантский час 23:00."
            ),
            "source_url": "https://kubsu.ru",
        },
        {
            "source": "МФЦ",
            "title": "Медицинская страховка",
            "content": (
                "Полис обязательного медицинского страхования ОМС. "
                "Медицинское страхование обязательно для всех студентов."
            ),
            "source_url": "https://mfc.krasnodar.ru",
        },
        {
            "source": "КубГУ",
            "title": "Студенческий билет",
            "content": (
                "Студенческий билет выдаётся после зачисления и даёт доступ "
                "к библиотеке, корпусам и электронным сервисам университета."
            ),
            "source_url": "https://kubsu.ru",
        },
        {
            "source": "МВД РФ",
            "title": "Разрешение на проживание",
            "content": (
                "Разрешение на временное проживание. Продление визы подаётся "
                "за месяц до истечения. Студенческая виза действует один год."
            ),
            "source_url": "https://мвд.рф",
        },
    ]
    # Enriquecer con los campos del enunciado (id, text, section).
    for i, d in enumerate(docs):
        d["id"] = f"test::{i}"
        d["section"] = d["title"]
        d["text"] = f"{d['title']} {d['content']}"
    return docs


@pytest.fixture
def sample_chunks(sample_documents):
    """Objetos Chunk construidos desde los documentos de prueba."""
    return build_chunks_from_flat(sample_documents)


@pytest.fixture(scope="module")
def official_library():
    """Instancia real de OfficialDocumentLibrary (modo keyword, offline)."""
    return OfficialDocumentLibrary()


def _vec384(*first_values):
    """Vector de dimensión 384 con los primeros componentes fijados."""
    v = np.zeros(384, dtype=float)
    for i, val in enumerate(first_values):
        v[i] = val
    return v


# ── GRUPO A: SemanticSearchEngine ─────────────────────────────────────────
class TestSemanticSearchEngine:
    """Motor de búsqueda semántica (sentence-transformers mockeado)."""

    def test_build_index_creates_embeddings(self, sample_documents):
        """build_index debe generar una matriz de embeddings (n, 384)."""
        with patch("enhanced_rag.SEMANTIC_SEARCH_AVAILABLE", True), \
                patch("enhanced_rag.SentenceTransformer", create=True) as MockST:
            model = MagicMock()
            model.encode.return_value = np.ones((len(sample_documents), 384))
            MockST.return_value = model

            engine = SemanticSearchEngine()
            assert engine._initialized is True

            ok = engine.build_index(sample_documents)
            assert ok is True
            assert engine.embeddings.shape == (len(sample_documents), 384)
            assert len(engine.documents) == len(sample_documents)

    def test_search_returns_k_results(self, sample_documents):
        """search debe devolver como máximo top_k pares (doc, score)."""
        with patch("enhanced_rag.SEMANTIC_SEARCH_AVAILABLE", True), \
                patch("enhanced_rag.SentenceTransformer", create=True) as MockST:
            model = MagicMock()
            # Todos los vectores iguales -> similitud coseno = 1.0 (supera 0.3).
            model.encode.side_effect = lambda x, **kw: np.ones((len(x), 384))
            MockST.return_value = model

            engine = SemanticSearchEngine()
            engine.build_index(sample_documents)

            results = engine.search("регистрация", top_k=3)
            assert len(results) == 3
            for doc, score in results:
                assert isinstance(doc, dict)
                assert isinstance(score, float)

    def test_search_empty_query_returns_empty(self):
        """Sin índice construido (modo offline), search devuelve lista vacía.

        NOTE: SemanticSearchEngine no tiene guarda explícita de query vacía;
        se verifica el contrato de resultado vacío cuando el índice no está
        disponible (embeddings is None), que también cubre el caso offline.
        """
        engine = SemanticSearchEngine()  # sin modelo -> _initialized False
        assert engine.search("", top_k=5) == []
        assert engine.search("регистрация", top_k=5) == []

    def test_search_ranks_by_cosine_similarity(self, sample_documents):
        """Los resultados deben ordenarse por similitud coseno descendente."""
        with patch("enhanced_rag.SEMANTIC_SEARCH_AVAILABLE", True), \
                patch("enhanced_rag.SentenceTransformer", create=True) as MockST:
            model = MagicMock()
            MockST.return_value = model

            engine = SemanticSearchEngine()
            # Embeddings controlados: doc0 alineado con la consulta, luego doc1, doc2.
            engine.documents = sample_documents[:3]
            engine.embeddings = np.array([
                _vec384(1.0, 0.0),          # coseno con query = 1.0
                _vec384(0.8, 0.6),          # coseno = 0.8
                _vec384(0.5, 0.866025),     # coseno = 0.5
            ])
            model.encode.return_value = np.array([_vec384(1.0, 0.0)])  # query

            results = engine.search("регистрация", top_k=3)
            assert len(results) == 3
            scores = [s for _, s in results]
            assert scores == sorted(scores, reverse=True)
            assert results[0][0] is sample_documents[0]


# ── GRUPO B: BM25Retriever ────────────────────────────────────────────────
@bm25_required
class TestBM25Retriever:
    """Recuperador léxico BM25 (retrieval.sparse)."""

    def test_bm25_retrieves_relevant_documents(self, sample_chunks):
        """Una consulta debe recuperar primero el chunk temáticamente relevante."""
        retriever = BM25Retriever()
        retriever.index(sample_chunks)

        results = retriever.search("регистрация", top_k=3)
        assert len(results) >= 1
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert "регистрац" in results[0].chunk.text.lower()

    def test_bm25_empty_corpus_returns_empty(self):
        """Con un corpus vacío, search debe devolver una lista vacía."""
        retriever = BM25Retriever()
        retriever.index([])
        assert retriever.search("регистрация", top_k=5) == []

    def test_bm25_scores_decrease_monotonically(self, sample_chunks):
        """Los scores devueltos deben ser monótonamente no crecientes."""
        retriever = BM25Retriever()
        retriever.index(sample_chunks)

        results = retriever.search("регистрация документы виза проживание", top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ── GRUPO C: HybridRetriever / RRF ────────────────────────────────────────
@bm25_required
class TestHybridRetriever:
    """Fusión híbrida BM25 + denso mediante Reciprocal Rank Fusion."""

    def test_rrf_fusion_combines_both_retrievers(self, sample_chunks):
        """La fusión debe incluir documentos aportados por ambos recuperadores."""
        sparse = BM25Retriever()
        # Denso mockeado: reporta disponible y aporta un chunk concreto.
        dense = MagicMock()
        dense.is_available.return_value = True
        dense._embeddings = object()  # hace que HybridRetriever lo active
        dense.search.return_value = [
            RetrievalResult(chunk=sample_chunks[2], score=0.95),  # МФЦ (denso)
        ]

        hybrid = HybridRetriever(sparse=sparse, dense=dense)
        hybrid.index(sample_chunks)

        results = hybrid.search("регистрация", top_k=5)
        ids = {r.chunk.id for r in results}
        assert len(results) >= 1
        # Contribución del recuperador denso presente en la fusión.
        assert sample_chunks[2].id in ids

    def test_rrf_document_appearing_in_both_ranks_higher(self):
        """Un documento presente en ambas listas debe puntuar más alto (RRF)."""
        fused = reciprocal_rank_fusion(
            [["a", "b", "x"], ["b", "c", "x"]], k=60
        )
        scores = dict(fused)
        # "b" aparece en ambas listas y en posiciones altas -> mayor score.
        assert fused[0][0] == "b"
        assert scores["b"] > scores["a"]
        assert scores["b"] > scores["c"]

    def test_hybrid_returns_at_most_k_results(self, sample_chunks):
        """search nunca debe devolver más de top_k resultados."""
        hybrid = HybridRetriever(sparse=BM25Retriever(), dense=None)
        hybrid.index(sample_chunks)

        results = hybrid.search("регистрация проживание виза документы", top_k=2)
        assert len(results) <= 2


# ── GRUPO D: EnhancedRAGModule ────────────────────────────────────────────
class TestEnhancedRAGModule:
    """Orquestador RAG (modo template, sin LLM)."""

    def test_rag_returns_answer_and_sources(self):
        """search_and_generate devuelve una respuesta y una lista de fuentes.

        NOTE: el método real es search_and_generate y las claves son
        'response' y 'sources' (no 'answer'/'confidence').
        """
        rag = EnhancedRAGModule(use_llm=False)
        out = rag.search_and_generate("Регистрация иностранцев", language="ru")

        assert isinstance(out["response"], str) and out["response"].strip()
        assert isinstance(out["sources"], list)
        assert out["sources_found"] >= 1

    def test_rag_abstains_when_confidence_below_threshold(self):
        """Con guarda de citación activa y baja confianza, el sistema se abstiene."""
        rag = EnhancedRAGModule(use_llm=False)
        rag._retrieval_config["citation_guard"] = True
        rag._retrieval_config["abstention_threshold"] = 0.35

        abstained = SimpleNamespace(
            answer="Недостаточно проверенной информации.",
            grounded=False,
            score=0.10,
            abstained=True,
            citations=[],
        )
        with patch("trust.enforce_grounding", return_value=abstained):
            out = rag.search_and_generate("qwerty zxcvbnm", language="ru")

        assert out["response_mode"] == "abstained"
        assert out["response"] == "Недостаточно проверенной информации."
        assert out["grounding"]["abstained"] is True
        assert out["grounding"]["score"] < 0.35

    def test_rag_fallback_mode_without_llm(self):
        """Sin LLM disponible, la respuesta se genera en modo template.

        Se desactiva el traductor (TRANSLATOR_AVAILABLE) para garantizar
        ejecución 100% offline sin llamadas de red.
        """
        rag = EnhancedRAGModule(use_llm=False)
        assert rag.is_llm_enabled() is False

        with patch("enhanced_rag.TRANSLATOR_AVAILABLE", False):
            out = rag.search_and_generate("Общежитие", language="es")
        assert out["response_mode"] == "template"
        assert isinstance(out["response"], str) and out["response"].strip()


# ── GRUPO E: OfficialDocumentLibrary ──────────────────────────────────────
class TestOfficialDocumentLibrary:
    """Biblioteca de documentos oficiales."""

    def test_library_loads_documents_on_init(self):
        """Al instanciarse, debe cargar el diccionario de documentos oficiales."""
        library = OfficialDocumentLibrary()
        assert isinstance(library.documents, dict)
        assert len(library.documents) >= 5
        assert "КубГУ" in library.documents
        # Cada fuente contiene secciones no vacías.
        for source, doc in library.documents.items():
            assert doc.get("sections"), f"Fuente sin secciones: {source}"

    def test_list_sources_returns_known_sources(self):
        """list_sources debe incluir las fuentes oficiales conocidas.

        NOTE: en enhanced_rag.py las fuentes son КубГУ, МВД РФ, МФЦ,
        Госуслуги y FAQ.
        """
        library = OfficialDocumentLibrary()
        sources = library.list_sources()
        assert isinstance(sources, list)
        for expected in ["КубГУ", "МВД РФ", "МФЦ", "Госуслуги", "FAQ"]:
            assert expected in sources


# ── GRUPO F: DenseRetriever (retrieval.dense) ────────────────────────
class TestDenseRetriever:
    """Recuperador denso (sentence-transformers mockeado)."""

    def test_dense_index_builds_embeddings(self, sample_chunks):
        """index debe construir una matriz de embeddings (n, 384)."""
        with patch("retrieval.dense._ST_AVAILABLE", True), \
                patch("retrieval.dense.SentenceTransformer", create=True) as MockST:
            model = MagicMock()
            model.encode.side_effect = lambda x, **kw: np.random.rand(len(x), 384)
            MockST.return_value = model

            retriever = DenseRetriever()
            assert retriever.is_available() is True
            retriever.index(sample_chunks)
            assert retriever._embeddings is not None
            assert retriever._embeddings.shape == (len(sample_chunks), 384)

    def test_dense_search_returns_ranked_results(self, sample_chunks):
        """search debe devolver RetrievalResult ordenados por similitud."""
        with patch("retrieval.dense._ST_AVAILABLE", True), \
                patch("retrieval.dense.SentenceTransformer", create=True) as MockST:
            model = MagicMock()
            model.encode.side_effect = lambda x, **kw: np.random.rand(len(x), 384)
            MockST.return_value = model

            retriever = DenseRetriever()
            retriever.index(sample_chunks)
            results = retriever.search("регистрация", top_k=3)
            assert len(results) <= 3
            assert all(isinstance(r, RetrievalResult) for r in results)
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_dense_ranks_by_cosine_similarity(self, sample_chunks):
        """El documento alineado con la consulta debe quedar primero."""
        retriever = DenseRetriever()
        retriever._model = MagicMock()
        retriever._model.encode.return_value = np.array([_vec384(1.0, 0.0)])
        retriever._chunks = sample_chunks[:3]
        retriever._embeddings = np.array([
            _vec384(1.0, 0.0),          # coseno = 1.0
            _vec384(0.8, 0.6),          # coseno = 0.8
            _vec384(0.5, 0.866025),     # coseno = 0.5
        ])
        results = retriever.search("запрос", top_k=3)
        assert len(results) == 3
        assert results[0].chunk is sample_chunks[0]
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_dense_unavailable_returns_empty(self, sample_chunks):
        """Sin sentence-transformers, el retriever degrada a resultado vacío."""
        with patch("retrieval.dense._ST_AVAILABLE", False):
            retriever = DenseRetriever()
            assert retriever.is_available() is False
            retriever.index(sample_chunks)
            assert retriever._embeddings is None
            assert retriever.search("регистрация", top_k=5) == []


# ── GRUPO G: _keyword_search (fallback de enhanced_rag) ────────────────
class TestKeywordSearchFallback:
    """Búsqueda por palabras clave con expansión de sinónimos (degradación)."""

    def test_keyword_search_finds_relevant(self, official_library):
        """Una consulta en ruso recupera secciones relevantes (modo keyword)."""
        results = official_library._keyword_search("регистрация")
        assert len(results) >= 1
        assert all(r["relevance"] > 0.3 for r in results)
        assert results[0]["search_mode"] == "keyword"
        top_text = (results[0]["title"] + results[0]["content"]).lower()
        assert "регистрац" in top_text

    def test_keyword_search_synonym_expansion(self, official_library):
        """Una consulta en español se expande a sinónimos rusos y recupera docs."""
        results = official_library._keyword_search("registro de migracion")
        assert any(r["search_mode"] == "keyword" for r in results)
        assert any(
            "регистрац" in (r["title"] + r["content"]).lower()
            or "миграцион" in (r["title"] + r["content"]).lower()
            for r in results
        )

    def test_keyword_search_no_match_returns_fallback(self, official_library):
        """Sin coincidencias, se devuelve una única entrada de tipo 'fallback'."""
        results = official_library._keyword_search("xyzzy qwerty zzz")
        assert len(results) == 1
        assert results[0]["search_mode"] == "fallback"


# ── GRUPO H: CrossEncoderReranker (retrieval.rerank) ─────────────────
class TestCrossEncoderReranker:
    """Re-ranker cross-encoder (modelo mockeado)."""

    def test_rerank_reorders_by_cross_encoder_score(self, sample_chunks):
        """rerank debe reordenar los candidatos según el score del cross-encoder."""
        with patch("retrieval.rerank._CE_AVAILABLE", True), \
                patch("retrieval.rerank.CrossEncoder", create=True) as MockCE:
            model = MagicMock()
            model.predict.return_value = [0.1, 0.9, 0.5]
            MockCE.return_value = model

            reranker = CrossEncoderReranker()
            assert reranker.is_available() is True
            inputs = [
                RetrievalResult(chunk=sample_chunks[0], score=0.9),
                RetrievalResult(chunk=sample_chunks[1], score=0.5),
                RetrievalResult(chunk=sample_chunks[2], score=0.3),
            ]
            reranked = reranker.rerank("регистрация", inputs)
            assert reranked[0].chunk is sample_chunks[1]   # score 0.9
            assert reranked[-1].chunk is sample_chunks[0]  # score 0.1
            scores = [r.score for r in reranked]
            assert scores == sorted(scores, reverse=True)

    def test_rerank_noop_when_unavailable(self, sample_chunks):
        """Sin cross-encoder disponible, rerank preserva la lista de entrada."""
        with patch("retrieval.rerank._CE_AVAILABLE", False):
            reranker = CrossEncoderReranker()
            assert reranker.is_available() is False
            inputs = [
                RetrievalResult(chunk=sample_chunks[0], score=0.5),
                RetrievalResult(chunk=sample_chunks[1], score=0.9),
            ]
            out = reranker.rerank("q", inputs)
            assert out is inputs

    def test_rerank_empty_results_returns_empty(self):
        """rerank sobre una lista vacía devuelve una lista vacía."""
        reranker = CrossEncoderReranker()
        assert reranker.rerank("q", []) == []


# ── GRUPO I: factory + baseline ───────────────────────────────
class TestFactoryAndBaseline:
    """Fábrica de retrievers y baseline por palabras clave."""

    @bm25_required
    def test_build_retriever_bm25(self, sample_chunks):
        """build_retriever('bm25') devuelve un BM25Retriever ya indexado."""
        retriever = build_retriever("bm25", sample_chunks)
        assert isinstance(retriever, BM25Retriever)
        results = retriever.search("регистрация", top_k=3)
        assert len(results) >= 1

    def test_build_retriever_unknown_mode_raises(self, sample_chunks):
        """Un modo desconocido debe lanzar ValueError."""
        with pytest.raises(ValueError):
            build_retriever("modo_inexistente", sample_chunks)

    def test_keyword_baseline_maps_results_to_chunks(self, official_library):
        """El baseline mapea los resultados keyword a chunks con IDs estables."""
        chunks = build_chunks_from_library(official_library)
        retriever = KeywordBaselineRetriever(official_library)
        retriever.index(chunks)
        results = retriever.search("регистрация", top_k=5)
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all("::" in r.chunk.id for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
