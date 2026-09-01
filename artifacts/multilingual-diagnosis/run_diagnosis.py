import json
import importlib.metadata
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from enhanced_rag import EnhancedRAGModule
from retrieval.chunks import tokenize
from retrieval.sparse import expand_query_tokens


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = (
    PROJECT_ROOT / "artifacts" / "real-source-tests" / "spbu-20260901" / "state"
)
DENSE_SNAPSHOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
    / "snapshots"
    / "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
)
QUERIES = [
    ("es", "¿Qué programas ofrece SPbU?"),
    ("en", "What programs does SPbU offer?"),
    ("ru", "Какие программы предлагает СПБГУ?"),
    ("ru_technical", "программы дополнительное образование онлайн курсы"),
]
MODES = ("keyword", "bm25", "dense")


def compact_result(result):
    return {
        "source": result.get("source"),
        "source_url": result.get("source_url"),
        "title": result.get("title"),
        "relevance": result.get("relevance"),
        "search_mode": result.get("search_mode"),
        "id": result.get("id") or result.get("chunk_id"),
    }


def main():
    package_versions = {}
    for package in (
        "torch",
        "torchvision",
        "transformers",
        "sentence-transformers",
        "numpy",
        "rank-bm25",
    ):
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = None

    try:
        import sentence_transformers  # noqa: F401
    except Exception as error:
        sentence_transformers_import = {
            "success": False,
            "error_type": type(error).__name__,
            "error": str(error),
        }
    else:
        sentence_transformers_import = {"success": True, "error": None}

    output = {
        "state_root": str(STATE_ROOT),
        "dense_snapshot": str(DENSE_SNAPSHOT),
        "dense_snapshot_exists": DENSE_SNAPSHOT.is_dir(),
        "offline_model_loading": True,
        "environment": {
            "package_versions": package_versions,
            "sentence_transformers_import": sentence_transformers_import,
        },
        "queries": [],
        "runs": [],
    }

    for language, query in QUERIES:
        tokens = tokenize(query)
        output["queries"].append(
            {
                "language": language,
                "query": query,
                "legacy_keyword_tokens": query.lower().split(),
                "unicode_tokens": tokens,
                "bm25_expanded_tokens": expand_query_tokens(tokens),
            }
        )

    for mode in MODES:
        rag = EnhancedRAGModule(use_llm=False, project_root=STATE_ROOT)
        rag._retrieval_config["mode"] = mode
        if mode == "dense":
            rag._retrieval_config["dense_model"] = str(DENSE_SNAPSHOT)

        mode_run = {
            "requested_mode": mode,
            "rehydrated_chunks": len(rag.document_library.flat_documents),
            "results": [],
        }
        for language, query in QUERIES:
            results, effective_mode = rag._retrieve(query)
            top_results = [compact_result(item) for item in results[:5]]
            mode_run["results"].append(
                {
                    "language": language,
                    "query": query,
                    "effective_mode": effective_mode,
                    "spbu_rank": next(
                        (
                            rank
                            for rank, item in enumerate(top_results, start=1)
                            if item.get("source_url") == "https://spbu.ru"
                        ),
                        None,
                    ),
                    "top_results": top_results,
                }
            )

        retriever = rag._retriever
        mode_run["retriever_class"] = (
            type(retriever).__name__ if retriever is not None else None
        )
        mode_run["retriever_available"] = (
            retriever.is_available() if retriever is not None else None
        )
        mode_run["dense_model_loaded"] = bool(
            getattr(retriever, "_loaded", False)
        )
        output["runs"].append(mode_run)

    serialized = json.dumps(output, ensure_ascii=False, indent=2)
    Path(__file__).with_name("results.json").write_text(
        serialized + "\n", encoding="utf-8"
    )
    print(serialized)


if __name__ == "__main__":
    main()