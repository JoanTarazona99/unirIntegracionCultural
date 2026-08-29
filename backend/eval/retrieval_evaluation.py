"""Offline command-line evaluation of the repository's retrieval methods."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, Tuple

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPOSITORY_DIR = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from eval.benchmark import (  # noqa: E402
    benchmark_sha256,
    filter_benchmark,
    load_benchmark,
    summarize_benchmark,
)
from eval.evaluator import (  # noqa: E402
    evaluate_retriever,
    unavailable_method,
    write_results,
)
from eval.statistics import compare_bm25_with_best_hybrid  # noqa: E402

DEFAULT_BENCHMARK = _REPOSITORY_DIR / "data" / "eval" / "benchmark.jsonl"
DEFAULT_MANIFEST = _REPOSITORY_DIR / "data" / "eval" / "benchmark.manifest.json"
DEFAULT_OUTPUT_DIR = _REPOSITORY_DIR / "data" / "eval" / "results"
DEFAULT_METHODS = ["keyword", "bm25", "dense", "hybrid", "hybrid_rerank"]
ALLOWED_METHODS = set(DEFAULT_METHODS)
NEURAL_METHODS = {"dense", "hybrid", "hybrid_rerank"}


def _enable_offline_mode() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def _validate_semantic_configuration(methods: Sequence[str]) -> None:
    requested_neural = sorted(set(methods) & NEURAL_METHODS)
    if requested_neural and os.environ.get("ENABLE_SEMANTIC_SEARCH") != "1":
        joined = ", ".join(requested_neural)
        raise RuntimeError(
            "ENABLE_SEMANTIC_SEARCH must be exactly '1' for neural retrieval "
            f"methods: {joined}"
        )


def _git_commit() -> Optional[str]:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPOSITORY_DIR,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _load_manifest(path: Path, benchmark: Path) -> dict:
    if not path.exists():
        return {
            "benchmark_version": "unversioned",
            "manifest": None,
            "checksum_verified": False,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = payload.get("sha256")
    actual = benchmark_sha256(benchmark)
    if expected != actual:
        raise ValueError(
            f"Benchmark checksum mismatch: expected {expected}, obtained {actual}"
        )
    payload["manifest"] = str(path)
    payload["checksum_verified"] = True
    return payload


def _activation_metadata(method: str, retriever, *, completed: bool = False) -> dict:
    if method == "dense":
        dense = retriever
        dense_active = getattr(dense, "_embeddings", None) is not None
    elif method in {"hybrid", "hybrid_rerank"}:
        dense = getattr(retriever, "dense", None)
        dense_active = bool(getattr(retriever, "_dense_active", False))
    else:
        dense = None
        dense_active = False

    reranker = getattr(retriever, "reranker", None)
    reranker_active = bool(
        reranker is not None and getattr(reranker, "_prediction_count", 0) > 0
    )
    if completed:
        effective_method = method
    elif method in {"hybrid", "hybrid_rerank"} and not dense_active:
        effective_method = "bm25_fallback_blocked"
    elif method == "hybrid_rerank" and not reranker_active:
        effective_method = "hybrid_without_reranking_blocked"
    else:
        effective_method = "none"

    return {
        "requested_method": method,
        "effective_method": effective_method,
        "dense_active": dense_active,
        "reranker_active": reranker_active,
        "models": {
            "dense": getattr(dense, "model_name", None),
            "reranker_configured": getattr(reranker, "model_name", None),
            "reranker_loaded": sorted(
                getattr(reranker, "_loaded_models", set())
            ),
            "reranker_used": sorted(getattr(reranker, "_models_used", set())),
        },
        "reranker_prediction_count": getattr(
            reranker, "_prediction_count", 0
        ),
        "activation_error": getattr(reranker, "_last_error", None),
    }


def _unavailable_reason(method: str, retriever, items) -> Optional[str]:
    if method == "dense" and getattr(retriever, "_embeddings", None) is None:
        return "dense embeddings were not built in offline mode"
    if method in {"hybrid", "hybrid_rerank"} and not getattr(
        retriever, "_dense_active", False
    ):
        return "dense stage was not active; reporting a BM25 fallback as hybrid is disabled"
    if method == "hybrid_rerank":
        reranker = getattr(retriever, "reranker", None)
        required_models = {
            reranker.MODEL_VARIANTS.get(item.lang, reranker.DEFAULT_MODEL)
            for item in items
        }
        for model_name in sorted(required_models):
            try:
                if not reranker._ensure_model(model_name):
                    return f"cross-encoder model unavailable offline: {model_name}"
            except RuntimeError as exc:
                return str(exc)
    return None


def _build_verified_retriever(method: str, library, chunks, items) -> Tuple[object, Optional[str]]:
    from retrieval import build_retriever

    retriever = build_retriever(
        method,
        chunks,
        library=library,
        strict_reranker=(method == "hybrid_rerank"),
    )
    return retriever, _unavailable_reason(method, retriever, items)


def _finalize_method_result(method: str, retriever, result: dict, query_count: int) -> dict:
    activation = _activation_metadata(method, retriever)
    errors = sorted(
        {
            query["error"]
            for query in result["queries"]
            if query.get("error")
        }
    )
    reason = None
    if result["retrieval_error_count"]:
        reason = "strict retrieval failed for one or more queries"
    elif method == "hybrid_rerank" and not activation["reranker_active"]:
        reason = "strict reranker completed no predictions"

    if reason:
        return unavailable_method(
            method,
            reason,
            query_count,
            activation=activation,
            errors=errors or [reason],
        )

    result.update(_activation_metadata(method, retriever, completed=True))
    result["errors"] = []
    return result


def _validate_gold_ids(items, chunks) -> None:
    valid_ids = {chunk.id for chunk in chunks}
    unknown = {
        item.id: sorted(set(item.relevant_chunk_ids) - valid_ids)
        for item in items
        if set(item.relevant_chunk_ids) - valid_ids
    }
    if unknown:
        raise ValueError(f"Benchmark references unknown active chunk IDs: {unknown}")


def run(args: argparse.Namespace) -> Tuple[dict, Optional[dict]]:
    """Run the configured evaluation and optionally serialize its artifacts."""
    _enable_offline_mode()
    _validate_semantic_configuration(args.methods)
    # Imports are deliberately delayed until offline flags are set.
    from enhanced_rag import OfficialDocumentLibrary
    from retrieval import build_chunks_from_library

    benchmark_path = Path(args.benchmark).resolve()
    manifest = _load_manifest(Path(args.manifest).resolve(), benchmark_path)
    all_items = load_benchmark(benchmark_path, allow_unlabeled=True)
    items = filter_benchmark(
        all_items, language=args.language, category=args.category
    )
    if not items:
        raise ValueError("No benchmark queries match the requested filters")

    library = OfficialDocumentLibrary()
    chunks = build_chunks_from_library(library)
    _validate_gold_ids(items, chunks)

    results = []
    for method in args.methods:
        try:
            retriever, reason = _build_verified_retriever(
                method, library, chunks, items
            )
            if reason:
                results.append(
                    unavailable_method(
                        method,
                        reason,
                        len(items),
                        activation=_activation_metadata(method, retriever),
                    )
                )
            else:
                result = evaluate_retriever(method, retriever, items, args.k)
                results.append(
                    _finalize_method_result(
                        method,
                        retriever,
                        result,
                        len(items),
                    )
                )
        except Exception as exc:  # noqa: BLE001 - preserve method failure in output
            results.append(
                unavailable_method(
                    method, f"{type(exc).__name__}: {exc}", len(items)
                )
            )

    timestamp = datetime.now(timezone.utc)
    run_id = args.run_id or timestamp.strftime("retrieval_eval_%Y%m%dT%H%M%SZ")
    report = {
        "run": {
            "run_id": run_id,
            "timestamp_utc": timestamp.isoformat(),
            "git_commit": _git_commit(),
            "seed": args.seed,
            "offline": True,
            "requested_methods": args.methods,
            "k": sorted(set(args.k)),
            "filters": {
                "language": args.language,
                "category": args.category,
            },
        },
        "benchmark": {
            "path": str(benchmark_path),
            "version": manifest.get("benchmark_version", "unversioned"),
            "sha256": benchmark_sha256(benchmark_path),
            "manifest": manifest.get("manifest"),
            "checksum_verified": manifest.get("checksum_verified", False),
            "all_queries": summarize_benchmark(all_items),
            "selected_queries": summarize_benchmark(items),
            "annotation_provenance": manifest.get(
                "annotation_provenance", "not documented"
            ),
            "relevance": manifest.get("relevance", "not documented"),
        },
        "corpus": {
            "source_count": len({chunk.source for chunk in chunks}),
            "chunk_count": len(chunks),
            "source": "OfficialDocumentLibrary active in-memory corpus",
        },
        "retrieval_configuration": {
            "keyword": {"implementation": "OfficialDocumentLibrary._keyword_search"},
            "bm25": {"implementation": "BM25Okapi", "query_expansion": True},
            "dense": {
                "model": "paraphrase-multilingual-MiniLM-L12-v2"
            },
            "hybrid": {
                "fusion": "reciprocal_rank_fusion",
                "rrf_k": 60,
                "candidate_multiplier": 4,
            },
            "hybrid_rerank": {
                "reranker": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
                "automatic_language_model_selection": True,
            },
        },
        "results": results,
    }
    report["statistical_comparison"] = (
        {"status": "not_computed", "reason": "bootstrap disabled"}
        if args.skip_bootstrap
        else compare_bm25_with_best_hybrid(
            results, samples=args.bootstrap_samples, seed=args.seed
        )
    )

    artifacts = None
    if not args.no_save:
        artifacts = write_results(report, args.output_dir)
    return report, artifacts


def _print_summary(report: dict, artifacts: Optional[dict]) -> None:
    selected = report["benchmark"]["selected_queries"]["total_queries"]
    print(
        f"Benchmark {report['benchmark']['version']}: {selected} queries | "
        f"{report['corpus']['source_count']} sources | "
        f"{report['corpus']['chunk_count']} chunks"
    )
    for result in report["results"]:
        if result["status"] != "completed":
            print(f"{result['method']}: NOT EXECUTED - {result['reason']}")
            continue
        metrics = " | ".join(
            f"{name}={value:.6f}" for name, value in result["aggregate"].items()
        )
        print(f"{result['method']}: {metrics}")
    comparison = report["statistical_comparison"]
    if comparison["status"] != "computed":
        print(f"Bootstrap: NOT COMPUTED - {comparison['reason']}")
    if artifacts:
        for kind, path in artifacts.items():
            print(f"{kind}: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline, reproducible retrieval evaluation"
    )
    parser.add_argument("--benchmark", default=str(DEFAULT_BENCHMARK))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument(
        "--method",
        "--methods",
        "--modes",
        dest="methods",
        nargs="+",
        choices=sorted(ALLOWED_METHODS),
        default=DEFAULT_METHODS,
    )
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5])
    parser.add_argument("--language")
    parser.add_argument("--category")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-id")
    parser.add_argument("--no-save", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report, artifacts = run(args)
    _print_summary(report, artifacts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
