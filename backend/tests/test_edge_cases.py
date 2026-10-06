"""Edge-case tests for the internal retrieval and generation pipeline."""

from pathlib import Path

import pytest

from enhanced_rag import EnhancedRAGModule


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPBU_STATE = (
    REPOSITORY_ROOT
    / "artifacts"
    / "real-source-tests"
    / "spbu-20260901"
    / "state"
)


@pytest.fixture(scope="module")
def spbu_rag():
    assert SPBU_STATE.is_dir(), f"Required SPbU snapshot is missing: {SPBU_STATE}"
    rag = EnhancedRAGModule(use_llm=False, project_root=SPBU_STATE)
    rag._retrieval_config["mode"] = "keyword"
    rag._retrieval_config["enable_external_search"] = False
    return rag


def _assert_result_contract(result):
    assert isinstance(result, dict)
    assert isinstance(result.get("response"), str)
    assert isinstance(result.get("sources"), list)
    assert isinstance(result.get("sources_found"), int)
    assert result["sources_found"] >= len(result["sources"])


def _search(spbu_rag, query, language="es"):
    return spbu_rag.search_and_generate(
        query=query,
        context_type="chat",
        language=language,
        use_llm=False,
        allow_external=False,
    )


def test_empty_query_returns_structured_result_without_crashing(spbu_rag):
    _assert_result_contract(_search(spbu_rag, ""))


def test_very_short_query_returns_structured_result(spbu_rag):
    result = _search(spbu_rag, "SPbU")

    _assert_result_contract(result)
    assert result["sources_found"] > 0


def test_very_long_query_returns_structured_result(spbu_rag):
    long_query = "programas educación cursos " * 200

    _assert_result_contract(_search(spbu_rag, long_query))


@pytest.mark.parametrize(
    "query",
    [
        "SPbU @#$%",
        "programas ^&*()",
        "educación 🎓📚",
        'SPbU <script>alert("x")</script>',
    ],
)
def test_special_characters_return_structured_result(spbu_rag, query):
    _assert_result_contract(_search(spbu_rag, query))


@pytest.mark.parametrize(
    ("query", "language"),
    [
        ("programas educación", "es"),
        ("SPbU München", "es"),
        ("Universität Straßburg", "es"),
        ("программы образование", "ru"),
    ],
)
def test_unicode_queries_return_structured_result(spbu_rag, query, language):
    _assert_result_contract(_search(spbu_rag, query, language))