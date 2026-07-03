"""
Evaluation routes for the academic (master's) dashboard.

Runs the information-retrieval benchmark (data/eval/benchmark.jsonl) against the
live knowledge base and reports standard IR metrics: Hit@k, Recall@k,
Precision@k, MRR and nDCG@k, broken down by language and category.

By default only lightweight modes (keyword, bm25) run so the endpoint stays
responsive. Neural modes (dense/hybrid/hybrid_rerank) can be requested but are
CPU/GPU heavy and degrade gracefully to bm25 if models are unavailable.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import get_rag_module
from app.config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parents[3]
_BENCHMARK = _BACKEND_DIR.parent / "data" / "eval" / "benchmark.jsonl"
_RESULTS_DIR = _BACKEND_DIR.parent / "data" / "eval" / "results"
_API_RESULT_FILE = _RESULTS_DIR / "api_latest.json"

_ALLOWED_MODES = {"keyword", "bm25", "dense", "hybrid", "hybrid_rerank"}


def _run_evaluation(modes: List[str], k: int) -> dict:
    """Execute the benchmark for the requested retrieval modes."""
    from eval.benchmark import load_benchmark
    from eval.run_eval import evaluate_mode
    from retrieval import build_chunks_from_library

    if not _BENCHMARK.exists():
        raise FileNotFoundError(f"Benchmark file not found: {_BENCHMARK}")

    rag_module = get_rag_module()
    library = rag_module.document_library
    chunks = build_chunks_from_library(library)
    items = load_benchmark(_BENCHMARK)

    results = []
    for mode in modes:
        t0 = time.perf_counter()
        try:
            res = evaluate_mode(mode, library, chunks, items, k)
        except Exception as e:  # degrade gracefully, report the failure
            logger.warning("eval_mode_failed", mode=mode, error=str(e))
            continue
        res["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
        # Drop verbose per-item detail from the API payload; keep aggregates.
        res.pop("per_item", None)
        results.append(res)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "k": k,
        "num_queries": len(items),
        "modes": [r["mode"] for r in results],
        "results": results,
    }

    # Persist as the latest API evaluation snapshot.
    try:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        _API_RESULT_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.warning("eval_result_persist_failed", error=str(e))

    return payload


@router.post("/api/eval/run")
async def run_evaluation(
    modes: Optional[str] = Query(
        default="keyword,bm25",
        description="Comma-separated retrieval modes: keyword,bm25,dense,hybrid,hybrid_rerank",
    ),
    k: int = Query(default=5, ge=1, le=20, description="Cutoff k for @k metrics"),
):
    """Run the IR benchmark and return aggregate metrics per retrieval mode."""
    requested = [m.strip().lower() for m in (modes or "").split(",") if m.strip()]
    invalid = [m for m in requested if m not in _ALLOWED_MODES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid modes: {invalid}. Allowed: {sorted(_ALLOWED_MODES)}",
        )
    if not requested:
        requested = ["keyword", "bm25"]

    try:
        return _run_evaluation(requested, k)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("eval_run_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/api/eval/results")
async def get_last_results():
    """Return the last cached evaluation snapshot (fast, no computation)."""
    if _API_RESULT_FILE.exists():
        try:
            return json.loads(_API_RESULT_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Corrupt results file: {str(e)}")
    return {
        "timestamp": None,
        "results": [],
        "message": "No evaluation has been run yet. POST /api/eval/run to generate metrics.",
    }
