"""Offline integration tests for the evaluator using simulated retrievers."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from eval.benchmark import BenchmarkItem, load_benchmark
from eval.evaluator import evaluate_retriever, write_results

_FIXTURE = Path(__file__).parent / "fixtures" / "evaluation_synthetic.jsonl"


@dataclass
class FakeChunk:
    id: str


@dataclass
class FakeResult:
    chunk: FakeChunk
    score: float


class SimulatedRetriever:
    def search(self, query, top_k=5):
        if query == "registration deadline":
            return [FakeResult(FakeChunk("doc-a::0"), 1.0)]
        if query == "dormitory price":
            return [
                FakeResult(FakeChunk("doc-x::0"), 0.7),
                FakeResult(FakeChunk("doc-b::1"), 0.7),
                FakeResult(FakeChunk("doc-b::0"), 0.4),
            ]
        return []


class FailingRetriever:
    def search(self, query, top_k=5):
        raise RuntimeError("simulated failure")


def test_evaluator_records_rankings_groups_and_unlabeled_queries():
    items = load_benchmark(_FIXTURE, allow_unlabeled=True)
    result = evaluate_retriever("simulated", SimulatedRetriever(), items, [1, 3, 5])
    assert result["query_count"] == 3
    assert result["evaluated_query_count"] == 2
    assert result["excluded_unlabeled_count"] == 1
    assert result["queries"][0]["first_relevant_rank"] == 1
    assert result["queries"][1]["first_relevant_rank"] == 2
    assert result["queries"][2]["status"] == "excluded_unlabeled"
    assert result["by_language"]["en"]["query_count"] == 2
    assert result["by_category"]["housing"]["query_count"] == 1


def test_equal_scores_preserve_retriever_order():
    item = BenchmarkItem("q", "dormitory price", "en", "housing", ["doc-b::1"])
    result = evaluate_retriever("simulated", SimulatedRetriever(), [item], [3])
    ranking = result["queries"][0]["ranking"]
    assert [entry["chunk_id"] for entry in ranking[:2]] == ["doc-x::0", "doc-b::1"]


def test_empty_results_and_retrieval_errors_are_explicit():
    unlabeled_query = BenchmarkItem("empty", "unknown", "en", "other", ["doc-z::0"])
    empty = evaluate_retriever("simulated", SimulatedRetriever(), [unlabeled_query], [5])
    failed = evaluate_retriever("failing", FailingRetriever(), [unlabeled_query], [5])
    assert empty["queries"][0]["status"] == "empty_results"
    assert empty["aggregate"]["MRR@5"] == 0.0
    assert failed["queries"][0]["status"] == "retrieval_error"
    assert failed["retrieval_error_count"] == 1
    assert "simulated failure" in failed["queries"][0]["error"]


def test_json_and_csv_serialization(tmp_path):
    items = load_benchmark(_FIXTURE, allow_unlabeled=True)
    result = evaluate_retriever("simulated", SimulatedRetriever(), items, [1, 5])
    report = {
        "run": {"run_id": "synthetic_run"},
        "results": [result],
        "statistical_comparison": {"status": "not_computed"},
    }
    paths = write_results(report, tmp_path)
    payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert payload["results"][0]["method"] == "simulated"
    with Path(paths["summary_csv"]).open(encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    with Path(paths["queries_csv"]).open(encoding="utf-8", newline="") as handle:
        query_rows = list(csv.DictReader(handle))
    assert summary_rows[0]["selected_query_count"] == "3"
    assert summary_rows[0]["evaluated_query_count"] == "2"
    assert summary_rows[0]["requested_method"] == "simulated"
    assert len(query_rows) == 3
    assert query_rows[0]["retrieved_chunk_ids"] == '["doc-a::0"]'
    with Path(paths["language_csv"]).open(encoding="utf-8", newline="") as handle:
        language_rows = list(csv.DictReader(handle))
    with Path(paths["category_csv"]).open(encoding="utf-8", newline="") as handle:
        category_rows = list(csv.DictReader(handle))
    bootstrap = json.loads(Path(paths["bootstrap_json"]).read_text(encoding="utf-8"))
    assert {row["language"] for row in language_rows} == {"en"}
    assert {row["category"] for row in category_rows} == {"housing", "migration"}
    assert bootstrap == {"status": "not_computed"}
