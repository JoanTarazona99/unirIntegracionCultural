"""Tests for the retrieval stack (chunks, BM25, RRF fusion, factory)."""

import pytest

from retrieval import build_chunks_from_library, build_retriever
from retrieval.chunks import tokenize
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.sparse import BM25Retriever, expand_query_tokens


@pytest.fixture(scope="module")
def library():
    from enhanced_rag import OfficialDocumentLibrary
    return OfficialDocumentLibrary()


@pytest.fixture(scope="module")
def chunks(library):
    return build_chunks_from_library(library)


def test_chunks_have_stable_ids(chunks):
    assert len(chunks) > 0
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))  # unique
    assert all("::" in cid for cid in ids)


def test_tokenize_handles_cyrillic():
    tokens = tokenize("Регистрация visa 7 дней")
    assert "регистрация" in tokens
    assert "visa" in tokens
    assert "дней" in tokens


def test_query_expansion_adds_russian_synonyms():
    expanded = expand_query_tokens(tokenize("registro visa"))
    assert "регистрация" in expanded
    assert "виза" in expanded


def test_bm25_retrieves_registration_chunk(chunks):
    retriever = BM25Retriever()
    retriever.index(chunks)
    # 'registro' is a known cross-lingual expansion stem -> maps to регистрация.
    results = retriever.search("¿Dónde hago el registro migratorio?", top_k=5)
    assert results
    assert any(r.chunk.source == "МВД РФ" for r in results)


def test_rrf_fusion_prefers_consensus():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]], k=60)
    ranked_ids = [cid for cid, _ in fused]
    # 'a' and 'b' appear in both lists near the top -> should rank above 'c'/'d'.
    assert ranked_ids[0] in {"a", "b"}
    assert ranked_ids.index("a") < ranked_ids.index("c")


def test_factory_keyword_baseline(library, chunks):
    retriever = build_retriever("keyword", chunks, library=library)
    results = retriever.search("dormitorio", top_k=5)
    assert isinstance(results, list)


def test_factory_bm25_beats_empty(chunks):
    retriever = build_retriever("bm25", chunks)
    results = retriever.search("seguro médico póliza", top_k=5)
    assert results
