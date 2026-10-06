"""Corpus-specific retrieval tests for several universities."""

from pathlib import Path

import pytest

from enhanced_rag import EnhancedRAGModule


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REAL_SOURCE_ROOT = REPOSITORY_ROOT / "artifacts" / "real-source-tests"


def _keyword_rag(project_root: Path) -> EnhancedRAGModule:
    rag = EnhancedRAGModule(use_llm=False, project_root=project_root)
    rag._retrieval_config["mode"] = "keyword"
    rag._retrieval_config["enable_external_search"] = False
    return rag


@pytest.fixture(scope="module")
def unam_rag():
    state = REAL_SOURCE_ROOT / "unam-20260901" / "state"
    assert state.is_dir(), f"Required UNAM snapshot is missing: {state}"
    return _keyword_rag(state)


@pytest.fixture(scope="module")
def uba_rag():
    state = REAL_SOURCE_ROOT / "uba-20260901" / "state"
    assert state.is_dir(), f"Required UBA snapshot is missing: {state}"
    return _keyword_rag(state)


@pytest.fixture(scope="module")
def kubgu_rag(tmp_path_factory):
    return _keyword_rag(tmp_path_factory.mktemp("kubgu-state"))


def _sources_for(rag: EnhancedRAGModule, query: str, language: str):
    result = rag.search_and_generate(
        query=query,
        context_type="chat",
        language=language,
        use_llm=False,
        allow_external=False,
    )
    assert result["search_mode"] == "keyword"
    assert result["sources_found"] > 0
    return result["sources"]


def test_unam_spanish_retrieval_uses_academic_snapshot(unam_rag):
    """The acquired UNAM offer snapshot is retrievable with a supported query."""
    sources = _sources_for(
        unam_rag,
        "Oferta académica UNAM licenciatura",
        "es",
    )

    assert any("UNAM" in source.get("source", "") for source in sources)


def test_uba_spanish_retrieval_uses_academic_snapshot(uba_rag):
    """The acquired UBA snapshot is retrievable with a supported query."""
    sources = _sources_for(
        uba_rag,
        "Oferta académica UBA carreras de grado",
        "es",
    )

    assert any(
        "UBA" in source.get("source", "")
        or "Universidad de Buenos Aires" in source.get("source", "")
        for source in sources
    )


def test_kubgu_russian_retrieval_uses_static_corpus(kubgu_rag):
    """The static КубГУ corpus is retrievable through a Russian query."""
    sources = _sources_for(
        kubgu_rag,
        "Какие программы предлагает КубГУ?",
        "ru",
    )

    assert any(
        "КубГУ" in source.get("source", "")
        or "Кубанский" in source.get("source", "")
        for source in sources
    )