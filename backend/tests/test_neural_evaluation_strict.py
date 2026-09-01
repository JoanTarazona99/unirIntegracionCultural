"""Offline tests for strict neural retrieval evaluation safeguards."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from eval.evaluator import unavailable_method, write_results
from eval.retrieval_evaluation import (
    _activation_metadata,
    _build_verified_retriever,
    _enable_offline_mode,
    _fallback_count,
    _finalize_method_result,
    _unavailable_reason,
    _validate_semantic_configuration,
    run,
)
from retrieval.base import RetrievalResult
from retrieval.chunks import Chunk
from retrieval.rerank import CrossEncoderReranker


def _result(chunk_id="doc::0"):
    return RetrievalResult(
        chunk=Chunk(chunk_id, "source", "title", "content"),
        score=0.5,
    )


def test_neural_methods_require_semantic_search_enabled(monkeypatch):
    monkeypatch.delenv("ENABLE_SEMANTIC_SEARCH", raising=False)
    with pytest.raises(RuntimeError, match="must be exactly '1'.*dense"):
        _validate_semantic_configuration(["keyword", "dense"])

    monkeypatch.setenv("ENABLE_SEMANTIC_SEARCH", "true")
    with pytest.raises(RuntimeError, match="hybrid_rerank"):
        _validate_semantic_configuration(["hybrid_rerank"])


def test_run_aborts_before_neural_evaluation_when_semantic_is_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC_SEARCH", "0")
    args = SimpleNamespace(methods=["dense"])

    with pytest.raises(RuntimeError, match="must be exactly '1'"):
        run(args)


def test_lexical_methods_do_not_require_semantic_search(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC_SEARCH", "0")
    _validate_semantic_configuration(["keyword", "bm25"])


def test_offline_mode_preserves_external_semantic_setting(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC_SEARCH", "1")
    _enable_offline_mode()
    assert __import__("os").environ["ENABLE_SEMANTIC_SEARCH"] == "1"


def test_evaluator_builds_only_reranking_in_strict_mode():
    fake = SimpleNamespace(
        _dense_active=True,
        dense=SimpleNamespace(model_name="dense-model"),
        reranker=SimpleNamespace(
            MODEL_VARIANTS={},
            DEFAULT_MODEL="reranker-model",
            _ensure_model=lambda model: True,
        ),
    )
    with patch("retrieval.build_retriever", return_value=fake) as build:
        _build_verified_retriever("hybrid_rerank", None, [], [])
        assert build.call_args.kwargs["strict_reranker"] is True

        _build_verified_retriever("hybrid", None, [], [])
        assert build.call_args.kwargs["strict_reranker"] is False


def test_dense_preflight_failure_is_not_executed():
    dense = SimpleNamespace(_embeddings=None, model_name="dense-model")
    reason = _unavailable_reason("dense", dense, [])
    metadata = _activation_metadata("dense", dense)
    result = unavailable_method("dense", reason, 3, activation=metadata)

    assert result["status"] == "not_executed"
    assert result["requested_method"] == "dense"
    assert result["effective_method"] == "none"
    assert result["dense_active"] is False
    assert result["models"]["dense"] == "dense-model"
    assert result["fallback_count"] == 0


@pytest.mark.parametrize("method", ["hybrid", "hybrid_rerank"])
def test_hybrid_with_inactive_dense_blocks_bm25_fallback(method):
    hybrid = SimpleNamespace(
        _dense_active=False,
        dense=SimpleNamespace(model_name="dense-model"),
        reranker=None,
    )
    reason = _unavailable_reason(method, hybrid, [])
    metadata = _activation_metadata(method, hybrid)
    result = unavailable_method(method, reason, 3, activation=metadata)

    assert "reporting a BM25 fallback as hybrid is disabled" in reason
    assert metadata["effective_method"] == "bm25_fallback_blocked"
    assert metadata["dense_active"] is False
    assert metadata["fallback_count"] == 1
    assert result["status"] == "not_executed"
    assert result["fallback_count"] == 1


def test_fallback_count_is_zero_without_observed_activation_fallback():
    assert _fallback_count("keyword", None) == 0
    assert _fallback_count("bm25", None) == 0
    assert _fallback_count("dense", SimpleNamespace(_embeddings=None)) == 0
    assert _fallback_count("hybrid", SimpleNamespace(_dense_active=True)) == 0


def test_strict_reranker_propagates_model_load_failure():
    reranker = CrossEncoderReranker(strict=True, auto_language=False)
    with patch("retrieval.rerank._CE_AVAILABLE", True), patch(
        "retrieval.rerank.CrossEncoder", side_effect=OSError("missing model")
    ):
        with pytest.raises(RuntimeError, match="Failed to load cross-encoder"):
            reranker.rerank("query", [_result()])

    assert "missing model" in reranker._last_error
    assert reranker._prediction_count == 0


def test_strict_reranker_propagates_prediction_failure():
    reranker = CrossEncoderReranker(strict=True, auto_language=False)
    reranker._model = MagicMock()
    reranker._model.predict.side_effect = ValueError("prediction failed")
    reranker._current_model = reranker.model_name

    with pytest.raises(RuntimeError, match="prediction failed"):
        reranker.rerank("query", [_result()])

    assert "prediction failed" in reranker._last_error
    assert reranker._prediction_count == 0


def test_non_strict_reranker_preserves_production_fallback():
    original = [_result()]
    reranker = CrossEncoderReranker(strict=False, auto_language=False)
    reranker._model = MagicMock()
    reranker._model.predict.side_effect = ValueError("prediction failed")
    reranker._current_model = reranker.model_name

    assert reranker.rerank("query", original) == original
    assert reranker._prediction_count == 0


def test_successful_strict_reranking_records_model_and_predictions():
    reranker = CrossEncoderReranker(strict=True, auto_language=False)
    reranker._model = MagicMock()
    reranker._model.predict.return_value = [0.2, 0.8]
    reranker._current_model = reranker.model_name
    reranker._loaded_models.add(reranker.model_name)

    reranker.rerank("query", [_result("doc::0"), _result("doc::1")])

    assert reranker._models_used == {reranker.model_name}
    assert reranker._prediction_count == 2
    assert reranker._last_error is None


def test_hybrid_rerank_without_predictions_is_not_executed():
    retriever = SimpleNamespace(
        _dense_active=True,
        dense=SimpleNamespace(model_name="dense-model"),
        reranker=SimpleNamespace(
            model_name="reranker-model",
            _prediction_count=0,
            _loaded_models={"reranker-model"},
            _models_used=set(),
            _last_error=None,
        ),
    )
    evaluated = {
        "retrieval_error_count": 0,
        "queries": [],
    }
    result = _finalize_method_result(
        "hybrid_rerank", retriever, evaluated, 2
    )

    assert result["status"] == "not_executed"
    assert result["effective_method"] == "hybrid_without_reranking_blocked"
    assert result["reranker_active"] is False
    assert result["fallback_count"] == 0


@pytest.mark.parametrize(
    ("method", "retriever"),
    [
        ("keyword", SimpleNamespace()),
        ("bm25", SimpleNamespace()),
        ("dense", SimpleNamespace(_embeddings=object(), model_name="dense-model")),
        (
            "hybrid",
            SimpleNamespace(
                _dense_active=True,
                dense=SimpleNamespace(model_name="dense-model"),
                reranker=None,
            ),
        ),
        (
            "hybrid_rerank",
            SimpleNamespace(
                _dense_active=True,
                dense=SimpleNamespace(model_name="dense-model"),
                reranker=SimpleNamespace(
                    model_name="reranker-model",
                    _prediction_count=1,
                    _loaded_models={"reranker-model"},
                    _models_used={"reranker-model"},
                    _last_error=None,
                ),
            ),
        ),
    ],
)
def test_completed_method_records_zero_fallback(method, retriever):
    evaluated = {
        "status": "completed",
        "retrieval_error_count": 0,
        "queries": [],
    }

    result = _finalize_method_result(method, retriever, evaluated, 2)

    assert result["status"] == "completed"
    assert result["fallback_count"] == 0


def test_not_executed_activation_metadata_serializes(tmp_path):
    activation = {
        "effective_method": "bm25_fallback_blocked",
        "dense_active": False,
        "reranker_active": False,
        "models": {
            "dense": "dense-model",
            "reranker_configured": "reranker-model",
            "reranker_loaded": [],
            "reranker_used": [],
        },
        "reranker_prediction_count": 0,
        "fallback_count": 1,
        "activation_error": "model unavailable",
    }
    result = unavailable_method(
        "hybrid_rerank",
        "dense inactive",
        2,
        activation=activation,
        errors=["model unavailable"],
    )
    report = {"run": {"run_id": "strict_state"}, "results": [result]}
    paths = write_results(report, tmp_path)
    payload = json.loads(
        open(paths["json"], encoding="utf-8").read()
    )["results"][0]

    assert payload["status"] == "not_executed"
    assert payload["requested_method"] == "hybrid_rerank"
    assert payload["effective_method"] == "bm25_fallback_blocked"
    assert payload["dense_active"] is False
    assert payload["reranker_active"] is False
    assert payload["fallback_count"] == 1
    assert payload["models"]["dense"] == "dense-model"
    assert payload["errors"] == ["model unavailable"]
    summary = open(paths["summary_csv"], encoding="utf-8").read()
    assert "hybrid_rerank,bm25_fallback_blocked,not_executed" in summary