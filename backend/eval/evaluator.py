"""Deterministic, dependency-free orchestration for retrieval evaluation."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .benchmark import BenchmarkItem
from .metrics import hit_at_k, mrr, ndcg_at_k, precision_at_k, recall_at_k


def normalize_ks(ks: Iterable[int]) -> List[int]:
    """Validate, deduplicate and sort cutoff values."""
    normalized = sorted(set(ks))
    if not normalized or any(k <= 0 for k in normalized):
        raise ValueError("k values must contain at least one positive integer")
    return normalized


def compute_metrics(
    retrieved: Sequence[str], relevant: Iterable[str], ks: Iterable[int]
) -> Dict[str, float]:
    """Compute binary-relevance metrics at every requested cutoff."""
    relevant_ids = set(relevant)
    values: Dict[str, float] = {}
    for k in normalize_ks(ks):
        values[f"Hit@{k}"] = hit_at_k(retrieved, relevant_ids, k)
        values[f"Recall@{k}"] = recall_at_k(retrieved, relevant_ids, k)
        values[f"Precision@{k}"] = precision_at_k(retrieved, relevant_ids, k)
        values[f"MRR@{k}"] = mrr(retrieved[:k], relevant_ids)
        values[f"nDCG@{k}"] = ndcg_at_k(retrieved, relevant_ids, k)
    return values


def _average_metrics(records: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    metric_rows = [record["metrics"] for record in records if record["metrics"]]
    if not metric_rows:
        return {}
    return {
        key: sum(float(row[key]) for row in metric_rows) / len(metric_rows)
        for key in metric_rows[0]
    }


def _group_metrics(
    records: Sequence[Mapping[str, Any]], field: str
) -> Dict[str, dict]:
    groups: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if record["metrics"]:
            groups[str(record[field])].append(record)
    return {
        name: {"query_count": len(group), "metrics": _average_metrics(group)}
        for name, group in sorted(groups.items())
    }


def _rank_results(results: Iterable[Any], max_k: int) -> List[dict]:
    ranking = []
    seen = set()
    for result in results:
        chunk = getattr(result, "chunk", None)
        chunk_id = getattr(chunk, "id", None)
        if not isinstance(chunk_id, str) or not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        ranking.append(
            {
                "rank": len(ranking) + 1,
                "chunk_id": chunk_id,
                "score": float(getattr(result, "score", 0.0)),
            }
        )
        if len(ranking) >= max_k:
            break
    return ranking


def evaluate_retriever(
    method: str,
    retriever: Any,
    items: Sequence[BenchmarkItem],
    ks: Iterable[int],
) -> dict:
    """Evaluate an injected retriever and retain a complete per-query trace."""
    cutoffs = normalize_ks(ks)
    max_k = max(cutoffs)
    records = []

    for item in items:
        error = None
        try:
            ranking = _rank_results(
                retriever.search(item.question, top_k=max_k), max_k
            )
        except Exception as exc:  # noqa: BLE001 - errors belong in the trace
            ranking = []
            error = f"{type(exc).__name__}: {exc}"

        retrieved_ids = [entry["chunk_id"] for entry in ranking]
        relevant_ids = list(item.relevant_chunk_ids)
        first_relevant_rank = next(
            (
                entry["rank"]
                for entry in ranking
                if entry["chunk_id"] in set(relevant_ids)
            ),
            None,
        )
        if not relevant_ids:
            status = "excluded_unlabeled"
            metrics = None
        elif error:
            status = "retrieval_error"
            metrics = compute_metrics([], relevant_ids, cutoffs)
        elif not ranking:
            status = "empty_results"
            metrics = compute_metrics([], relevant_ids, cutoffs)
        else:
            status = "evaluated"
            metrics = compute_metrics(retrieved_ids, relevant_ids, cutoffs)

        records.append(
            {
                "id": item.id,
                "question": item.question,
                "language": item.lang,
                "category": item.category,
                "relevant_chunk_ids": relevant_ids,
                "ranking": ranking,
                "first_relevant_rank": first_relevant_rank,
                "status": status,
                "error": error,
                "metrics": metrics,
            }
        )

    labeled = [record for record in records if record["metrics"] is not None]
    return {
        "method": method,
        "status": "completed",
        "query_count": len(records),
        "evaluated_query_count": len(labeled),
        "excluded_unlabeled_count": sum(
            record["status"] == "excluded_unlabeled" for record in records
        ),
        "empty_result_count": sum(
            record["status"] == "empty_results" for record in records
        ),
        "retrieval_error_count": sum(
            record["status"] == "retrieval_error" for record in records
        ),
        "aggregate": _average_metrics(labeled),
        "by_language": _group_metrics(records, "language"),
        "by_category": _group_metrics(records, "category"),
        "queries": records,
    }


def unavailable_method(
    method: str,
    reason: str,
    query_count: int,
    *,
    activation: Mapping[str, Any] | None = None,
    errors: Sequence[str] | None = None,
) -> dict:
    """Represent a requested method that could not be evaluated honestly."""
    result = {
        "method": method,
        "requested_method": method,
        "effective_method": "none",
        "dense_active": False,
        "reranker_active": False,
        "models": {
            "dense": None,
            "reranker_configured": None,
            "reranker_loaded": [],
            "reranker_used": [],
        },
        "reranker_prediction_count": 0,
        "activation_error": None,
        "status": "not_executed",
        "reason": reason,
        "errors": list(errors or [reason]),
        "query_count": query_count,
        "evaluated_query_count": 0,
        "aggregate": {},
        "by_language": {},
        "by_category": {},
        "queries": [],
    }
    result.update(activation or {})
    return result


def _method_metadata(result: Mapping[str, Any]) -> dict:
    models = result.get("models", {})
    return {
        "requested_method": result.get("requested_method", result["method"]),
        "effective_method": result.get("effective_method", result["method"]),
        "dense_active": result.get("dense_active", False),
        "reranker_active": result.get("reranker_active", False),
        "dense_model": models.get("dense"),
        "reranker_configured": models.get("reranker_configured"),
        "reranker_loaded": json.dumps(
            models.get("reranker_loaded", []), ensure_ascii=False
        ),
        "reranker_used": json.dumps(
            models.get("reranker_used", []), ensure_ascii=False
        ),
        "reranker_prediction_count": result.get("reranker_prediction_count", 0),
        "retrieval_error_count": result.get("retrieval_error_count", 0),
    }


def _write_group_csv(
    path: Path,
    results: Sequence[Mapping[str, Any]],
    metric_names: Sequence[str],
    *,
    scope: str,
    group_key: str,
) -> None:
    fields = [
        "method",
        "requested_method",
        "effective_method",
        "status",
        "dense_active",
        "reranker_active",
        "dense_model",
        "reranker_configured",
        "reranker_loaded",
        "reranker_used",
        "reranker_prediction_count",
        "retrieval_error_count",
        scope,
        "query_count",
    ]
    fields.extend(metric_names)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            metadata = _method_metadata(result)
            for group_name, group in result.get(group_key, {}).items():
                row = {
                    "method": result["method"],
                    "status": result["status"],
                    scope: group_name,
                    "query_count": group["query_count"],
                    **metadata,
                    **group["metrics"],
                }
                writer.writerow(row)


def write_results(report: Mapping[str, Any], output_dir: str | Path) -> dict:
    """Serialize a report and its global, grouped, query and bootstrap views."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    run_id = str(report["run"]["run_id"])
    json_path = destination / f"{run_id}.json"
    summary_path = destination / f"{run_id}_summary.csv"
    queries_path = destination / f"{run_id}_queries.csv"
    language_path = destination / f"{run_id}_by_language.csv"
    category_path = destination / f"{run_id}_by_category.csv"
    bootstrap_path = destination / f"{run_id}_bootstrap.json"

    with json_path.open("w", encoding="utf-8", newline="") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    metric_names = sorted(
        {
            metric
            for result in report["results"]
            for metric in result.get("aggregate", {})
        }
    )
    summary_fields = [
        "method",
        "requested_method",
        "effective_method",
        "status",
        "dense_active",
        "reranker_active",
        "dense_model",
        "reranker_configured",
        "reranker_loaded",
        "reranker_used",
        "reranker_prediction_count",
        "retrieval_error_count",
        "selected_query_count",
        "evaluated_query_count",
    ]
    summary_fields.extend(metric_names)
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        for result in report["results"]:
            row = {
                "method": result["method"],
                "status": result["status"],
                "selected_query_count": result.get("query_count", 0),
                "evaluated_query_count": result.get("evaluated_query_count", 0),
                **_method_metadata(result),
                **result.get("aggregate", {}),
            }
            writer.writerow(row)

    _write_group_csv(
        language_path,
        report["results"],
        metric_names,
        scope="language",
        group_key="by_language",
    )
    _write_group_csv(
        category_path,
        report["results"],
        metric_names,
        scope="category",
        group_key="by_category",
    )

    query_fields = [
        "method",
        "id",
        "language",
        "category",
        "status",
        "first_relevant_rank",
        "relevant_chunk_ids",
        "retrieved_chunk_ids",
        "error",
    ]
    query_fields.extend(metric_names)
    with queries_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=query_fields)
        writer.writeheader()
        for result in report["results"]:
            for query in result.get("queries", []):
                row = {
                    "method": result["method"],
                    "id": query["id"],
                    "language": query["language"],
                    "category": query["category"],
                    "status": query["status"],
                    "first_relevant_rank": query["first_relevant_rank"],
                    "relevant_chunk_ids": json.dumps(
                        query["relevant_chunk_ids"], ensure_ascii=False
                    ),
                    "retrieved_chunk_ids": json.dumps(
                        [entry["chunk_id"] for entry in query["ranking"]],
                        ensure_ascii=False,
                    ),
                    "error": query["error"],
                }
                row.update(query["metrics"] or {})
                writer.writerow(row)

    with bootstrap_path.open("w", encoding="utf-8", newline="") as handle:
        json.dump(
            report.get("statistical_comparison", {}),
            handle,
            ensure_ascii=False,
            indent=2,
        )

    return {
        "json": str(json_path),
        "summary_csv": str(summary_path),
        "queries_csv": str(queries_path),
        "language_csv": str(language_path),
        "category_csv": str(category_path),
        "bootstrap_json": str(bootstrap_path),
    }