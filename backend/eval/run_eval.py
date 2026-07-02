"""
Evaluation harness: compare retrieval strategies on the domain benchmark.

Runs each configured retrieval mode against data/eval/benchmark.jsonl and reports
IR metrics (Recall@k, MRR, nDCG@k, Precision@k), overall and broken down by
language and category. Results are printed as a table and saved to
data/eval/results/.

Usage (from the backend/ directory):
    python -m eval.run_eval
    python -m eval.run_eval --modes keyword bm25 hybrid --k 5
    python -m eval.run_eval --modes keyword bm25 dense hybrid hybrid_rerank

This is CPU-first: dense/hybrid_rerank modes degrade gracefully to BM25 if the
sentence-transformers models are unavailable.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Allow running both as `python -m eval.run_eval` and `python eval/run_eval.py`.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from eval.benchmark import BenchmarkItem, load_benchmark  # noqa: E402
from eval.metrics import (  # noqa: E402
    hit_at_k,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from retrieval import build_chunks_from_library, build_retriever  # noqa: E402

DEFAULT_BENCHMARK = _BACKEND_DIR.parent / "data" / "eval" / "benchmark.jsonl"
RESULTS_DIR = _BACKEND_DIR.parent / "data" / "eval" / "results"
DEFAULT_MODES = ["keyword", "bm25", "hybrid"]


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_mode(
    mode: str, library, chunks, items: List[BenchmarkItem], k: int
) -> Dict:
    """Run one retrieval mode over the benchmark and aggregate metrics."""
    retriever = build_retriever(mode, chunks, library=library)

    per_item = []
    by_lang: Dict[str, List[float]] = defaultdict(list)
    by_cat: Dict[str, List[float]] = defaultdict(list)

    for item in items:
        results = retriever.search(item.question, top_k=k)
        retrieved_ids = [r.chunk.id for r in results]
        rel = item.relevant_chunk_ids

        metrics = {
            "hit": hit_at_k(retrieved_ids, rel, k),
            "recall": recall_at_k(retrieved_ids, rel, k),
            "precision": precision_at_k(retrieved_ids, rel, k),
            "mrr": mrr(retrieved_ids, rel),
            "ndcg": ndcg_at_k(retrieved_ids, rel, k),
        }
        per_item.append({"id": item.id, "retrieved": retrieved_ids, **metrics})
        by_lang[item.lang].append(metrics["ndcg"])
        by_cat[item.category].append(metrics["ndcg"])

    aggregate = {
        f"Hit@{k}": _avg([p["hit"] for p in per_item]),
        f"Recall@{k}": _avg([p["recall"] for p in per_item]),
        f"Precision@{k}": _avg([p["precision"] for p in per_item]),
        "MRR": _avg([p["mrr"] for p in per_item]),
        f"nDCG@{k}": _avg([p["ndcg"] for p in per_item]),
    }
    return {
        "mode": mode,
        "aggregate": aggregate,
        "by_lang_ndcg": {lang: _avg(v) for lang, v in sorted(by_lang.items())},
        "by_category_ndcg": {cat: _avg(v) for cat, v in sorted(by_cat.items())},
        "per_item": per_item,
    }


def print_table(all_results: List[Dict], k: int) -> None:
    metric_keys = [f"Hit@{k}", f"Recall@{k}", f"Precision@{k}", "MRR", f"nDCG@{k}"]
    col_w = 14
    header = "Mode".ljust(16) + "".join(m.ljust(col_w) for m in metric_keys)
    print("\n" + "=" * len(header))
    print("RETRIEVAL COMPARISON  (higher is better)")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for res in all_results:
        row = res["mode"].ljust(16)
        row += "".join(f"{res['aggregate'][m]:.3f}".ljust(col_w) for m in metric_keys)
        print(row)
    print("-" * len(header))

    # Fairness view: nDCG by language.
    langs = sorted({l for r in all_results for l in r["by_lang_ndcg"]})
    if langs:
        print("\nnDCG@%d by language (fairness view):" % k)
        head = "Mode".ljust(16) + "".join(l.upper().ljust(10) for l in langs)
        print(head)
        for res in all_results:
            row = res["mode"].ljust(16)
            row += "".join(
                f"{res['by_lang_ndcg'].get(l, 0.0):.3f}".ljust(10) for l in langs
            )
            print(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate KubGU-RAG retrieval modes")
    parser.add_argument("--modes", nargs="+", default=DEFAULT_MODES)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--benchmark", type=str, default=str(DEFAULT_BENCHMARK))
    parser.add_argument("--save", action="store_true", default=True)
    args = parser.parse_args()

    from enhanced_rag import OfficialDocumentLibrary

    library = OfficialDocumentLibrary()
    chunks = build_chunks_from_library(library)
    items = load_benchmark(args.benchmark)
    print(f"[eval] {len(chunks)} chunks | {len(items)} benchmark queries | k={args.k}")

    all_results = []
    for mode in args.modes:
        try:
            print(f"[eval] Running mode: {mode} ...")
            all_results.append(evaluate_mode(mode, library, chunks, items, args.k))
        except Exception as exc:  # noqa: BLE001
            print(f"[eval] Mode '{mode}' failed: {exc}")

    print_table(all_results, args.k)

    if args.save and all_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"eval_{stamp}.json"
        with out.open("w", encoding="utf-8") as fh:
            json.dump(
                {"k": args.k, "benchmark": args.benchmark, "results": all_results},
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n[eval] Saved detailed results to {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
