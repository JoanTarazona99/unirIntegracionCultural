"""Performance guardrails for offline keyword retrieval."""

import os
import time
import tracemalloc
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
SINGLE_QUERY_LIMIT_SECONDS = float(
    os.getenv("TEST_RETRIEVAL_LATENCY_LIMIT_SECONDS", "2.0")
)
MULTI_QUERY_LIMIT_SECONDS = float(
    os.getenv("TEST_RETRIEVAL_MULTI_LATENCY_LIMIT_SECONDS", "5.0")
)
MEMORY_LIMIT_MIB = float(os.getenv("TEST_RETRIEVAL_MEMORY_LIMIT_MIB", "500"))


@pytest.fixture(scope="module")
def warmed_spbu_rag():
    assert SPBU_STATE.is_dir(), f"Required SPbU snapshot is missing: {SPBU_STATE}"
    rag = EnhancedRAGModule(use_llm=False, project_root=SPBU_STATE)
    rag._retrieval_config["mode"] = "keyword"
    rag._retrieval_config["enable_external_search"] = False
    rag.search_and_generate(
        query="SPbU",
        context_type="chat",
        language="es",
        use_llm=False,
        allow_external=False,
    )
    return rag


def _search(rag, query, language="es"):
    return rag.search_and_generate(
        query=query,
        context_type="chat",
        language=language,
        use_llm=False,
        allow_external=False,
    )


def test_retrieval_latency(warmed_spbu_rag):
    start = time.perf_counter()
    result = _search(warmed_spbu_rag, "¿Qué programas ofrece SPbU?")
    elapsed = time.perf_counter() - start

    assert result["sources_found"] > 0
    assert elapsed < SINGLE_QUERY_LIMIT_SECONDS, (
        f"Keyword retrieval took {elapsed:.3f}s; "
        f"limit is {SINGLE_QUERY_LIMIT_SECONDS:.3f}s"
    )


def test_retrieval_incremental_memory_usage(warmed_spbu_rag):
    tracemalloc.start()
    try:
        result = _search(warmed_spbu_rag, "¿Qué programas ofrece SPbU?")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_mib = peak / (1024 * 1024)
    assert result["sources_found"] > 0
    assert peak_mib < MEMORY_LIMIT_MIB, (
        f"Keyword retrieval allocated {peak_mib:.2f} MiB at peak; "
        f"limit is {MEMORY_LIMIT_MIB:.2f} MiB"
    )


def test_multiple_queries_latency(warmed_spbu_rag):
    queries = [
        ("¿Qué programas ofrece SPbU?", "es"),
        ("What programs does SPbU offer?", "en"),
        ("программы образование СПБГУ курсы", "ru"),
    ]

    start = time.perf_counter()
    results = [
        _search(warmed_spbu_rag, query, language)
        for query, language in queries
    ]
    elapsed = time.perf_counter() - start

    assert all(result["sources_found"] > 0 for result in results)
    assert elapsed < MULTI_QUERY_LIMIT_SECONDS, (
        f"Three keyword queries took {elapsed:.3f}s; "
        f"limit is {MULTI_QUERY_LIMIT_SECONDS:.3f}s"
    )