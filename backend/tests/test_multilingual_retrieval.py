"""Focused tests for adaptive multilingual retrieval primitives."""

import math
import statistics
import time

import pytest

from app.services.rag_service import ADAPTIVE_CHANNEL_WEIGHTS, weighted_rrf
from app.services.rag_service import RAGService
from app.services.triage_service import TriageService, classify_procedure_type
from retrieval.base import RetrievalResult
from retrieval.chunks import Chunk


def _result(chunk_id: str, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        chunk=Chunk(
            id=chunk_id,
            source="test",
            title=chunk_id,
            content=f"Evidence for {chunk_id}",
        ),
        score=score,
    )


@pytest.mark.parametrize(
    ("query", "language", "expected_target"),
    [
        ("Comment demander un visa étudiant ?", "fr", "ru"),
        ("¿Cómo hago el registro migratorio?", "es", "ru"),
        ("How do I apply for university admission?", "en", "es"),
        ("Wie beantrage ich einen Wohnheimplatz?", "de", "es"),
    ],
)
def test_triage_routes_by_procedure_not_region(query, language, expected_target):
    decision = classify_procedure_type(query, language)
    assert decision["primary_target"] == expected_target
    assert decision["primary_target"] not in decision["secondary_targets"]
    assert set(decision["secondary_targets"]) | {decision["primary_target"]} == {
        "es", "en", "ru"
    }


def test_triage_rejects_unsupported_language():
    with pytest.raises(ValueError):
        TriageService().classify_procedure_type("student visa", "ja")


def test_weighted_rrf_deduplicates_within_and_across_channels():
    a = _result("a")
    b = _result("b")
    fused = weighted_rrf(
        {
            "dense_original": [a, a, b],
            "bm25_original": [b, a],
        },
        top_k=5,
    )
    assert [result.chunk.id for result in fused] == ["a", "b"]
    assert fused[0].trace["channels"]["dense_original"]["rank"] == 1
    assert fused[1].trace["channels"]["dense_original"]["rank"] == 2


def test_weighted_rrf_uses_channel_weights_not_raw_scores():
    low_raw = _result("preferred", score=0.01)
    high_raw = _result("other", score=999.0)
    fused = weighted_rrf(
        {
            "dense_original": [low_raw],
            "dense_es_translated": [high_raw],
        }
    )
    assert fused[0].chunk.id == "preferred"
    assert fused[0].score == pytest.approx(1.0 / 61)


def test_weighted_rrf_consensus_beats_single_channel_hit():
    consensus = _result("consensus")
    single = _result("single")
    fused = weighted_rrf(
        {
            "dense_original": [single, consensus],
            "dense_ru_translated": [consensus],
        }
    )
    assert fused[0].chunk.id == "consensus"
    assert ADAPTIVE_CHANNEL_WEIGHTS["dense_original"] == 1.0
    assert ADAPTIVE_CHANNEL_WEIGHTS["dense_ru_translated"] == 0.9


class _FakeRetriever:
    def __init__(self, results, available=True):
        self.results = results
        self.available = available
        self.queries = []

    def search(self, query, top_k=5):
        self.queries.append((query, top_k))
        return list(self.results)[:top_k]

    def is_available(self):
        return self.available


def test_enhanced_rag_runs_expected_adaptive_channels_without_models():
    from enhanced_rag import EnhancedRAGModule

    rag = EnhancedRAGModule.__new__(EnhancedRAGModule)
    rag._retrieval_config = {"top_k": 5, "rrf_k": 60}
    dense = _FakeRetriever([_result("dense")])
    bm25 = _FakeRetriever([_result("bm25")])
    rag._get_adaptive_retrievers = lambda: (dense, bm25)

    payload = rag.retrieve_adaptive_channels(
        "Comment demander un visa ?",
        "fr",
        translated_queries={"ru": "Как получить визу?"},
    )

    assert set(payload["channels"]) == {
        "dense_original",
        "dense_ru_translated",
    }
    assert dense.queries == [
        ("Comment demander un visa ?", 5),
        ("Как получить визу?", 5),
    ]
    assert bm25.queries == []


def test_enhanced_rag_adds_bm25_for_evidence_language():
    from enhanced_rag import EnhancedRAGModule

    rag = EnhancedRAGModule.__new__(EnhancedRAGModule)
    rag._retrieval_config = {"top_k": 5, "rrf_k": 60}
    dense = _FakeRetriever([])
    bm25 = _FakeRetriever([_result("bm25")])
    rag._get_adaptive_retrievers = lambda: (dense, bm25)

    payload = rag.retrieve_adaptive_channels("student visa", "en")
    assert "dense_original" in payload["channels"]
    assert "bm25_original" in payload["channels"]


def test_adaptive_evidence_applies_score_and_coverage_thresholds(monkeypatch):
    from enhanced_rag import EnhancedRAGModule
    from trust.hallucination import EvidenceAssessment

    rag = EnhancedRAGModule.__new__(EnhancedRAGModule)
    rag._retrieval_config = {
        "top_k": 5,
        "query_relevance_threshold": 0.5,
        "query_entity_coverage_threshold": 1.0,
    }
    rag.render_adaptive_results = lambda results: [{
        "id": "a",
        "source": "test",
        "title": "visa",
        "content": "visa documents",
        "relevance": 0.9,
    }]

    def fake_assessment(*args, **kwargs):
        return EvidenceAssessment(
            query_relevance=1.0,
            query_term_coverage=0.6,
            query_entity_coverage=1.0,
            requested_slot_coverage=True,
            retrieval_confidence=1.0,
            sufficient=True,
            reasons=[],
            query_terms=["visa"],
            matched_terms=["visa"],
            missing_terms=[],
            query_entities={},
            matched_entities={},
            missing_entities={},
        )

    monkeypatch.setattr("trust.assess_evidence_sufficiency", fake_assessment)
    assessment = rag.evaluate_adaptive_evidence(["visa"], [_result("a")])
    assert assessment["sufficient"] is False
    assert "adaptive_coverage_below_threshold" in assessment["reasons"]


class _FakeTranslator:
    TRANSLATIONS = {
        "ru": "Как получить студенческую визу?",
        "es": "¿Cómo solicitar una visa de estudiante?",
        "en": "How to apply for a student visa?",
    }

    def translate_text(self, text, target_language="en", source_language="fr"):
        return self.TRANSLATIONS[target_language]


class _AdaptiveRAGModule:
    def __init__(self, sufficient_channel_count):
        self.sufficient_channel_count = sufficient_channel_count
        self.calls = []

    def retrieve_adaptive_channels(
        self, query, language, *, translated_queries=None, top_k=None
    ):
        translated_queries = translated_queries or {}
        self.calls.append(dict(translated_queries))
        channels = {"dense_original": [_result("original")]}
        for target in translated_queries:
            channels[f"dense_{target}_translated"] = [_result(f"{target}-hit")]
        return {
            "channels": channels,
            "dense_available": True,
            "bm25_available": True,
        }

    def fuse_adaptive_channels(self, channels, *, weights, top_k=None):
        return weighted_rrf(channels, weights, top_k=top_k)

    def evaluate_adaptive_evidence(self, query_variants, fused_results):
        channel_count = len({
            channel
            for result in fused_results
            for channel in result.trace["channels"]
        })
        return {
            "sufficient": channel_count >= self.sufficient_channel_count,
            "score": min(1.0, channel_count / self.sufficient_channel_count),
            "query_term_coverage": 1.0 if channel_count >= self.sufficient_channel_count else 0.2,
            "reasons": [] if channel_count >= self.sufficient_channel_count else ["insufficient"],
            "assessment_query": query_variants[-1],
        }

    @staticmethod
    def render_adaptive_results(results):
        return [result.chunk.to_result_dict(result.score, "adaptive_weighted_rrf") for result in results]


@pytest.mark.parametrize(
    ("sufficient_channels", "expected_level"),
    [(1, 1), (2, 2), (4, 3), (99, 4)],
)
def test_adaptive_fallback_levels(sufficient_channels, expected_level):
    module = _AdaptiveRAGModule(sufficient_channels)
    service = RAGService(module, translator=_FakeTranslator())
    result = service.retrieve_evidence_adaptive(
        "Comment demander un visa étudiant ?",
        "fr",
        correlation_id="adaptive-test",
    )
    assert result["adaptive_retrieval"]["completed_level"] == expected_level
    if expected_level == 4:
        assert result["adaptive_retrieval"]["abstention_reason"] == (
            "insufficient_multilingual_evidence"
        )
    else:
        assert result["evidence_assessment"]["sufficient"] is True


class _IntentChangingTranslator(_FakeTranslator):
    def translate_text(self, text, target_language="en", source_language="fr"):
        return {
            "ru": "Как получить общежитие?",
            "es": "¿Cómo solicitar residencia?",
            "en": "How to apply for housing?",
        }[target_language]


def test_adaptive_retrieval_rejects_translation_that_changes_intent():
    module = _AdaptiveRAGModule(99)
    service = RAGService(module, translator=_IntentChangingTranslator())
    result = service.retrieve_evidence_adaptive(
        "Comment demander un visa étudiant ?",
        "fr",
        correlation_id="intent-change",
    )
    assert result["adaptive_retrieval"]["translated_targets"] == []
    assert result["adaptive_retrieval"]["translation_failures"] == ["en", "es", "ru"]
    assert result["adaptive_retrieval"]["completed_level"] == 4


class _SearchRAGModule(_AdaptiveRAGModule):
    def __init__(self, *, dense_available):
        super().__init__(sufficient_channel_count=1)
        self.dense_available = dense_available
        self.generated_kwargs = None

    def retrieve_adaptive_channels(
        self, query, language, *, translated_queries=None, top_k=None
    ):
        payload = super().retrieve_adaptive_channels(
            query,
            language,
            translated_queries=translated_queries,
            top_k=top_k,
        )
        payload["dense_available"] = self.dense_available
        return payload

    def search_and_generate(self, **kwargs):
        self.generated_kwargs = kwargs
        return {
            "response": "answer",
            "sources_found": len(kwargs.get("retrieved_results") or []),
            "sources": kwargs.get("retrieved_results") or [],
            "response_mode": "template",
        }


def test_search_uses_precomputed_adaptive_results_when_dense_available():
    module = _SearchRAGModule(dense_available=True)
    service = RAGService(module, translator=_FakeTranslator())
    result = service.search("student visa", language="en")
    assert module.generated_kwargs["retrieval_mode_override"] == "adaptive_weighted_rrf"
    assert module.generated_kwargs["retrieved_results"]
    assert module.generated_kwargs["allow_external"] is False
    assert result["adaptive_retrieval"]["dense_available"] is True


def test_search_preserves_legacy_path_when_dense_unavailable():
    module = _SearchRAGModule(dense_available=False)
    service = RAGService(module, translator=_FakeTranslator())
    result = service.search("student visa", language="en")
    assert module.generated_kwargs.get("retrieved_results") is None
    assert result["adaptive_retrieval"]["legacy_fallback"] is True


PROCEDURE_TERMS = {
    "es": {"visa": "visa", "registration": "registro", "enrollment": "matrícula", "housing": "vivienda", "migration": "migración"},
    "en": {"visa": "visa", "registration": "registration", "enrollment": "enrollment", "housing": "housing", "migration": "migration"},
    "ru": {"visa": "виза", "registration": "регистрация", "enrollment": "поступление", "housing": "общежитие", "migration": "миграция"},
    "fr": {"visa": "visa", "registration": "enregistrement", "enrollment": "inscription", "housing": "logement", "migration": "migration"},
    "de": {"visa": "Visum", "registration": "Anmeldung", "enrollment": "Einschreibung", "housing": "Wohnheim", "migration": "Migration"},
    "zh": {"visa": "签证", "registration": "登记", "enrollment": "入学", "housing": "住宿", "migration": "移民"},
    "ar": {"visa": "تأشيرة", "registration": "تسجيل", "enrollment": "التحاق", "housing": "سكن", "migration": "هجرة"},
    "vi": {"visa": "thị thực", "registration": "đăng ký", "enrollment": "nhập học", "housing": "nhà ở", "migration": "di trú"},
    "hy": {"visa": "վիզա", "registration": "գրանցում", "enrollment": "ընդունելություն", "housing": "հանրակացարան", "migration": "միգրացիա"},
    "kk": {"visa": "виза", "registration": "тіркеу", "enrollment": "қабылдау", "housing": "жатақхана", "migration": "көші-қон"},
    "pt": {"visa": "visto", "registration": "registro", "enrollment": "matrícula", "housing": "moradia", "migration": "migração"},
    "it": {"visa": "visto", "registration": "registrazione", "enrollment": "iscrizione", "housing": "alloggio", "migration": "migrazione"},
    "tr": {"visa": "vize", "registration": "kayıt", "enrollment": "kabul", "housing": "yurt", "migration": "göç"},
}

LANGUAGE_PREFIX = {
    "es": "Necesito información sobre",
    "en": "I need information about",
    "ru": "Мне нужна информация:",
    "fr": "Comment faire",
    "de": "Wie funktioniert",
    "zh": "如何办理",
    "ar": "كيف أطلب",
    "vi": "Làm thế nào",
    "hy": "Ինչպե՞ս կատարել",
    "kk": "Қалай жасауға болады",
    "pt": "Como faço",
    "it": "Come fare",
    "tr": "Nasıl yapılır",
}


def _diagnostic_best_score(channels, top_k=5):
    """Non-production baseline demonstrating why raw scores are unsafe."""
    by_id = {}
    for results in channels.values():
        for result in results:
            previous = by_id.get(result.chunk.id)
            if previous is None or result.score > previous.score:
                by_id[result.chunk.id] = result
    return sorted(by_id.values(), key=lambda result: result.score, reverse=True)[:top_k]


def _rank_metrics(rankings, relevant_ids):
    hits = []
    ndcgs = []
    abstentions = 0
    for ranking, relevant_id in zip(rankings, relevant_ids):
        ids = [result.chunk.id for result in ranking[:5]]
        if relevant_id in ids:
            rank = ids.index(relevant_id) + 1
            hits.append(1.0)
            ndcgs.append(1.0 / math.log2(rank + 1))
        else:
            hits.append(0.0)
            ndcgs.append(0.0)
            abstentions += 1
    return {
        "hit_at_5": sum(hits) / len(hits),
        "ndcg_at_5": sum(ndcgs) / len(ndcgs),
        "abstention_rate": abstentions / len(hits),
    }


def _p95(samples):
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def test_separate_65_query_procedural_benchmark(capsys):
    triage = TriageService()
    weighted_rankings = []
    best_score_rankings = []
    single_rankings = []
    relevant_ids = []
    level_one_latency = []
    level_three_latency = []

    cases = [
        (language, procedure_type, f"{LANGUAGE_PREFIX[language]} {term}")
        for language, terms in PROCEDURE_TERMS.items()
        for procedure_type, term in terms.items()
    ]
    assert len(cases) == 65

    for case_index, (language, procedure_type, query) in enumerate(cases):
        decision = triage.classify_procedure_type(query, language)
        assert decision["procedure_type"] == procedure_type, (
            language,
            query,
            decision,
        )

        gold_id = f"gold::{procedure_type}"
        relevant_ids.append(gold_id)
        original = [_result(f"original-distractor::{case_index}", 0.95)]
        if case_index % 2 == 0:
            original.extend([
                _result(f"original-extra::{case_index}", 0.9),
                _result(f"original-extra-2::{case_index}", 0.8),
                _result(f"original-extra-3::{case_index}", 0.7),
                _result(gold_id, 0.4),
            ])
        primary_channel = f"dense_{decision['primary_target']}_translated"
        secondary_target = decision["secondary_targets"][0]
        secondary_channel = f"dense_{secondary_target}_translated"
        channels = {
            "dense_original": original,
            primary_channel: [
                _result(f"primary-distractor::{case_index}", 0.99),
                _result(gold_id, 0.2),
            ],
            secondary_channel: [
                _result(gold_id, 0.1),
                _result(f"secondary-distractor::{case_index}", 0.98),
            ],
        }

        started = time.perf_counter()
        single_rankings.append(list(original[:5]))
        level_one_latency.append(time.perf_counter() - started)

        started = time.perf_counter()
        weighted_rankings.append(weighted_rrf(channels, top_k=5))
        level_three_latency.append(time.perf_counter() - started)
        best_score_rankings.append(_diagnostic_best_score(channels))

    weighted_metrics = _rank_metrics(weighted_rankings, relevant_ids)
    best_score_metrics = _rank_metrics(best_score_rankings, relevant_ids)
    single_metrics = _rank_metrics(single_rankings, relevant_ids)
    metrics = {
        "query_count": len(cases),
        "weighted_rrf": weighted_metrics,
        "diagnostic_best_score": best_score_metrics,
        "single_channel": single_metrics,
        "level_1_latency_p95_seconds": _p95(level_one_latency),
        "level_3_latency_p95_seconds": _p95(level_three_latency),
    }
    print(metrics)

    assert weighted_metrics["ndcg_at_5"] > best_score_metrics["ndcg_at_5"]
    assert best_score_metrics["ndcg_at_5"] > single_metrics["ndcg_at_5"]
    assert weighted_metrics["hit_at_5"] == 1.0
    assert weighted_metrics["abstention_rate"] == 0.0
    assert metrics["level_1_latency_p95_seconds"] < 3.0
    assert metrics["level_3_latency_p95_seconds"] < 5.0