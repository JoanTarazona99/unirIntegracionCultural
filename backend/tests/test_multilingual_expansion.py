"""Focused tests for multilingual query expansion and source aliases."""

import pytest

from retrieval import Chunk
from retrieval.chunks import build_chunks_from_flat
from retrieval.expansion import DEFAULT_EXPANSION_VERSION, expand_query
from retrieval.sparse import BM25Retriever


def test_source_aliases_are_stored_and_indexed_in_chunk_metadata():
    aliases = ["SPbU", "СПбГУ", "Saint Petersburg State University"]
    chunks = build_chunks_from_flat(
        [
            {
                "source": "Saint Petersburg State University",
                "source_url": "https://spbu.ru",
                "aliases": aliases,
                "title": "Образовательные программы",
                "content": "Информация для поступающих.",
            }
        ]
    )

    assert chunks[0].metadata["aliases"] == aliases
    assert all(alias in chunks[0].text for alias in aliases)


def test_source_aliases_include_configured_and_hostname_variants():
    from enhanced_rag import OfficialDocumentLibrary

    aliases = OfficialDocumentLibrary._source_aliases(
        {
            "source_id": "candidate_spbu",
            "target_source": "Saint Petersburg State University",
            "url": "https://spbu.ru",
            "aliases": ["SPbU", "СПбГУ"],
        }
    )

    assert {"SPbU", "СПбГУ", "Saint Petersburg State University"}.issubset(aliases)
    assert "spbu" in {alias.casefold() for alias in aliases}


@pytest.mark.parametrize(
    ("query", "language", "expected"),
    [
        ("programas educación cursos", "es", ["программы", "образование", "курсы"]),
        ("admisión licenciatura posgrado", "es", ["поступление", "бакалавриат", "магистратура", "аспирантура"]),
        ("programs education courses admission", "en", ["программы", "образование", "курсы", "поступление"]),
    ],
)
def test_expand_query_es_en_to_ru(query, language, expected):
    expanded = expand_query(query, language, "ru")

    assert all(term in expanded for term in expected)
    assert DEFAULT_EXPANSION_VERSION == "academic-es-en-ru-v1"


def test_bm25_fuses_original_and_expanded_rankings_with_traceability():
    chunks = [
        Chunk(
            id="spbu::0",
            source="Saint Petersburg State University",
            title="Образовательные программы",
            content="Бакалавриат, магистратура и аспирантура.",
            metadata={"aliases": ["SPbU", "СПбГУ"]},
        ),
        Chunk(
            id="other::0",
            source="Other",
            title="Programs",
            content="General programs directory.",
        ),
        Chunk(
            id="unrelated::0",
            source="Unrelated",
            title="Housing",
            content="Dormitory contact details.",
        ),
    ]
    retriever = BM25Retriever(rrf_k=60)
    retriever.index(chunks)

    results = retriever.search("¿Qué programas ofrece SPbU?", top_k=2)

    spbu_result = next(result for result in results if result.chunk.id == "spbu::0")
    variants = {hit["variant"] for hit in spbu_result.trace["query_hits"]}
    assert variants == {"original", "expanded"}
    assert spbu_result.trace["rrf_k"] == 60
    assert spbu_result.score == pytest.approx(2 / 61)