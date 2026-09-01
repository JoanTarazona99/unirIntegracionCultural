import importlib.metadata
import json
import os
from dataclasses import replace
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from enhanced_rag import EnhancedRAGModule
from retrieval.chunks import build_chunks_from_library, tokenize
from retrieval.dense import DenseRetriever
from retrieval.sparse import BM25Retriever


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = (
    PROJECT_ROOT / "artifacts" / "real-source-tests" / "spbu-20260901" / "state"
)
SPBU_URL = "https://spbu.ru"

ALIAS_QUERIES = [
    "¿Qué programas ofrece SpbU?",
    "¿Qué programas ofrece СПБГУ?",
    "What programs does SpbU offer?",
    "SpbU programs admission",
]

EXPANDED_QUERIES = [
    "программы образование СПБГУ курсы",
    "programas educación SpbU cursos",
    "programs education SpbU courses",
]

MANUAL_EXPANSION = {
    "programas": ["программы", "образование", "курсы"],
    "programs": ["программы", "образование", "курсы"],
    "ofrece": ["предлагает"],
    "offer": ["предлагает"],
    "educación": ["образование"],
    "education": ["образование"],
    "cursos": ["курсы"],
    "courses": ["курсы"],
    "spbu": ["спбгу", "санкт", "петербургский", "университет"],
}


def compact_result(result):
    grounding = result.get("grounding") or {}
    sources = result.get("sources") or []
    return {
        "query": result.get("query"),
        "sources_found": result.get("sources_found"),
        "top_sources": [item.get("source_url") for item in sources[:3]],
        "relevance": [item.get("relevance") for item in sources[:3]],
        "search_mode": result.get("search_mode"),
        "response_mode": result.get("response_mode"),
        "grounding_level": grounding.get("level"),
        "grounding_score": grounding.get("score"),
        "spbu_retrieved": any(
            item.get("source_url") == SPBU_URL for item in sources
        ),
    }


def compact_hits(hits):
    return [
        {
            "rank": rank,
            "source": hit.chunk.source,
            "source_url": hit.chunk.source_url,
            "score": hit.score,
            "chunk_id": hit.chunk.id,
        }
        for rank, hit in enumerate(hits, start=1)
    ]


def expand_to_russian(query):
    source_tokens = tokenize(query)
    expanded_tokens = list(source_tokens)
    for token in source_tokens:
        expanded_tokens.extend(MANUAL_EXPANSION.get(token, []))
    return " ".join(expanded_tokens)


def run_end_to_end(rag, queries, language):
    return [
        compact_result(
            rag.search_and_generate(
                query=query,
                context_type="chat",
                language=language,
                allow_external=False,
            )
        )
        for query in queries
    ]


def main():
    rag = EnhancedRAGModule(use_llm=False, project_root=STATE_ROOT)
    chunks = build_chunks_from_library(rag.document_library)
    spbu_chunks = [chunk for chunk in chunks if chunk.source_url == SPBU_URL]
    if len(spbu_chunks) != 1:
        raise RuntimeError(f"Expected one SPbU chunk, found {len(spbu_chunks)}")

    baseline_bm25 = BM25Retriever(use_query_expansion=True)
    baseline_bm25.index(chunks)

    alias_chunks = [
        replace(
            chunk,
            title=(
                f"{chunk.title} | SpbU | СПбГУ | "
                "Санкт-Петербургский государственный университет"
            ),
        )
        if chunk.source_url == SPBU_URL
        else chunk
        for chunk in chunks
    ]
    alias_bm25 = BM25Retriever(use_query_expansion=True)
    alias_bm25.index(alias_chunks)

    original_query = "¿Qué programas ofrece SpbU?"
    normalized_query = " ".join(tokenize(original_query))
    expanded_query = expand_to_russian(original_query)

    output = {
        "protocol": {
            "state_root": str(STATE_ROOT),
            "rehydrated_chunks": len(chunks),
            "spbu_chunks": len(spbu_chunks),
            "network_allowed": False,
            "benchmarks_executed": False,
        },
        "existing_alias_configuration": "none for SPbU/UNAM/UBA",
        "experiment_1_explicit_alias_queries_keyword": run_end_to_end(
            rag, ALIAS_QUERIES, "es"
        ),
        "experiment_2_manual_expanded_queries_keyword": run_end_to_end(
            rag, EXPANDED_QUERIES, "ru"
        ),
        "controlled_components": {
            "original_query": original_query,
            "legacy_tokens": original_query.lower().split(),
            "unicode_tokens": tokenize(original_query),
            "normalized_query": normalized_query,
            "expanded_query": expanded_query,
            "baseline_bm25": compact_hits(
                baseline_bm25.search(original_query, top_k=5)
            ),
            "alias_metadata_bm25": compact_hits(
                alias_bm25.search(original_query, top_k=5)
            ),
            "query_expansion_bm25": compact_hits(
                baseline_bm25.search(expanded_query, top_k=5)
            ),
            "alias_and_query_expansion_bm25": compact_hits(
                alias_bm25.search(expanded_query, top_k=5)
            ),
            "normalized_keyword": [
                {
                    "source": row.get("source"),
                    "source_url": row.get("source_url"),
                    "relevance": row.get("relevance"),
                    "search_mode": row.get("search_mode"),
                }
                for row in rag.document_library.search(normalized_query)[:5]
            ],
        },
        "dense": {
            "available": DenseRetriever().is_available(),
            "torch": importlib.metadata.version("torch"),
            "sentence_transformers": importlib.metadata.version(
                "sentence-transformers"
            ),
            "transformers": importlib.metadata.version("transformers"),
        },
    }

    serialized = json.dumps(output, ensure_ascii=False, indent=2)
    Path(__file__).with_name("results.json").write_text(
        serialized + "\n", encoding="utf-8"
    )
    print(serialized)


if __name__ == "__main__":
    main()