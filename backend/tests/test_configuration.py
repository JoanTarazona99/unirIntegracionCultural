"""Validation tests for retrieval configuration."""

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


@pytest.fixture
def default_settings(monkeypatch):
    """Build settings without repository .env or retrieval environment overrides."""
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("RETRIEVAL_TOP_K", raising=False)
    monkeypatch.delenv("DENSE_MODEL", raising=False)
    return Settings(_env_file=None)


def test_settings_retrieval_defaults(default_settings):
    assert default_settings.retrieval_mode == "keyword"
    assert default_settings.retrieval_top_k == 5
    assert default_settings.dense_model == "paraphrase-multilingual-MiniLM-L12-v2"


@pytest.mark.parametrize(
    "mode",
    ["keyword", "bm25", "dense", "hybrid", "hybrid_rerank"],
)
def test_retrieval_mode_accepts_supported_values(mode):
    assert Settings(_env_file=None, retrieval_mode=mode).retrieval_mode == mode


def test_retrieval_mode_is_normalized():
    settings = Settings(_env_file=None, retrieval_mode="  DENSE  ")

    assert settings.retrieval_mode == "dense"


def test_retrieval_mode_rejects_unknown_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, retrieval_mode="invalid_mode")


@pytest.mark.parametrize("top_k", [0, -1, 21])
def test_retrieval_top_k_rejects_out_of_range_values(top_k):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, retrieval_top_k=top_k)


@pytest.mark.parametrize("top_k", [1, 5, 20])
def test_retrieval_top_k_accepts_supported_range(top_k):
    settings = Settings(_env_file=None, retrieval_top_k=top_k)

    assert settings.retrieval_top_k == top_k


def test_dense_model_rejects_empty_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, dense_model="")