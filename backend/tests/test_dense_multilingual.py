"""Focused tests for multilingual dense retrieval."""

import numpy as np
import pytest

from retrieval import Chunk
from retrieval.dense import DenseRetriever


class _QueryModel:
    """Return deterministic vectors for original and expanded query variants."""

    def encode(self, texts, **kwargs):
        query = texts[0]
        if "программы" in query or "образование" in query:
            return np.array([[1.0, 0.1, 0.5]])
        return np.array([[0.8, 1.0, 0.1]])


@pytest.mark.parametrize(
    ("query", "expected_terms"),
    [
        ("programas educación SPbU", {"программы", "образование"}),
        ("programs education SPbU", {"программы", "образование"}),
    ],
)
def test_dense_retrieval_with_expansion(query, expected_terms):
    """Dense ES/EN->RU expansion promotes a relevant Russian document."""
    chunks = [
        Chunk(
            id="spbu::0",
            source="Saint Petersburg State University",
            title="Образовательные программы",
            content="Бакалавриат, магистратура и аспирантура.",
            metadata={"aliases": ["SPbU", "СПбГУ"], "language": "ru"},
        ),
        Chunk(
            id="other::0",
            source="Other",
            title="Programs",
            content="General programs directory.",
            metadata={"language": "en"},
        ),
        Chunk(
            id="unrelated::0",
            source="Unrelated",
            title="Housing",
            content="Dormitory contact details.",
            metadata={"language": "en"},
        ),
    ]
    retriever = DenseRetriever(enable_cache=False, rrf_k=60)
    retriever._model = _QueryModel()
    retriever._chunks = chunks
    retriever._embeddings = np.identity(3)

    results = retriever.search(query, top_k=3)

    assert results
    assert results[0].chunk.id == "spbu::0"
    assert any(result.chunk.metadata.get("language") == "ru" for result in results)

    trace = results[0].trace
    assert expected_terms.issubset(set(trace["query_expanded"].split()))
    assert trace["query_original"] == query
    assert trace["rank_original"] == 2
    assert trace["rank_expanded"] == 1
    assert trace["rrf_score"] == pytest.approx(1 / 62 + 1 / 61)
    assert {hit["variant"] for hit in trace["query_hits"]} == {
        "original",
        "expanded",
    }