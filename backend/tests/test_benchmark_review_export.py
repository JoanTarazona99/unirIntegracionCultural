"""Contract tests for the synthetic AI-reviewed exploratory export."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "data/eval/benchmark_extended.jsonl"
TEMPLATE_PATH = ROOT / "data/eval/benchmark_extended_review_template.jsonl"
EXPORT_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114.jsonl"
MANIFEST_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114.manifest.json"
DIAGNOSTICS_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114_diagnostics.json"

INCLUDED_STATUSES = {"accepted", "revised"}
EXPECTED_TEMPLATE_SHA256 = (
    "1061405d4c3c016c74c0990e7e7b4bd92274102c6962a328621e3b33415e1aa4"
)
WARNING = (
    "Los qrels conservan origen sintético y fueron auditados con asistencia de "
    "IA; no constituyen anotaciones humanas ni un benchmark oficial."
)
EXPORT_METADATA = {
    "export_status": "synthetic_ai_reviewed_exploratory",
    "official_evaluation_eligible": False,
    "used_for_official_metrics": False,
    "source_review_statuses_included": ["accepted", "revised"],
    "pending_excluded": True,
    "rejected_excluded": True,
    "human_review_completed": False,
    "export_protocol_version": "v1",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_exportable(record: dict[str, Any], active_fragments: set[str]) -> bool:
    reviewed_text = record.get("reviewed_query_text")
    reviewed_category = record.get("reviewed_category")
    reviewed_fragments = record.get("reviewed_relevant_fragments")
    reviewer_id = record.get("reviewer_id")
    reviewed_at = record.get("reviewed_at")
    return (
        record.get("review_status") in INCLUDED_STATUSES
        and isinstance(reviewed_text, str)
        and bool(reviewed_text.strip())
        and isinstance(reviewed_category, str)
        and bool(reviewed_category.strip())
        and isinstance(reviewed_fragments, list)
        and bool(reviewed_fragments)
        and all(fragment in active_fragments for fragment in reviewed_fragments)
        and record.get("semantic_validity") == "valid"
        and record.get("relevance_validity") in {"valid", "multi_fragment"}
        and record.get("language_quality") in {"fluent", "acceptable"}
        and record.get("ambiguity") in {"low", "medium"}
        and isinstance(reviewer_id, str)
        and bool(reviewer_id.strip())
        and isinstance(reviewed_at, str)
        and bool(reviewed_at.strip())
    )


def _expected_export(
    template: list[dict[str, Any]], active_fragments: set[str]
) -> list[dict[str, Any]]:
    expected = []
    for record in template:
        if _is_exportable(record, active_fragments):
            exported_record = dict(record)
            exported_record.update(EXPORT_METADATA)
            expected.append(exported_record)
    return expected


def test_export_contains_exactly_the_114_eligible_reviewed_records() -> None:
    source = _load_jsonl(SOURCE_PATH)
    template = _load_jsonl(TEMPLATE_PATH)
    exported = _load_jsonl(EXPORT_PATH)
    active_fragments = {
        fragment for record in source for fragment in record["relevant_fragments"]
    }
    expected = _expected_export(template, active_fragments)

    assert len(template) == 132
    assert len(expected) == 114
    assert len(exported) == 114
    assert exported == expected


def test_export_ids_statuses_flags_and_exclusions() -> None:
    template = _load_jsonl(TEMPLATE_PATH)
    exported = _load_jsonl(EXPORT_PATH)
    exported_ids = [record["query_id"] for record in exported]
    pending_ids = {
        record["query_id"] for record in template if record["review_status"] == "pending"
    }
    rejected_ids = {
        record["query_id"] for record in template if record["review_status"] == "rejected"
    }

    assert len(exported_ids) == len(set(exported_ids))
    assert pending_ids.isdisjoint(exported_ids)
    assert rejected_ids.isdisjoint(exported_ids)
    assert all(record["review_status"] in INCLUDED_STATUSES for record in exported)
    assert all(record["used_for_official_metrics"] is False for record in exported)
    assert all(record["official_evaluation_eligible"] is False for record in exported)
    assert all(record["human_review_completed"] is False for record in exported)


def test_synthetic_fields_and_reviewed_fragments_match_sources() -> None:
    source = _load_jsonl(SOURCE_PATH)
    exported = _load_jsonl(EXPORT_PATH)
    source_by_id = {record["query_id"]: record for record in source}
    active_fragments = {
        fragment for record in source for fragment in record["relevant_fragments"]
    }

    for record in exported:
        synthetic = source_by_id[record["query_id"]]
        assert record["synthetic_query_text"] == synthetic["query_text"]
        assert record["language"] == synthetic["language"]
        assert record["synthetic_category"] == synthetic["category"]
        assert record["synthetic_relevant_fragments"] == synthetic["relevant_fragments"]
        assert record["annotation_status"] == synthetic["annotation_status"]
        assert all(
            fragment in active_fragments
            for fragment in record["reviewed_relevant_fragments"]
        )


def test_manifest_and_diagnostics_match_export() -> None:
    source = _load_jsonl(SOURCE_PATH)
    exported = _load_jsonl(EXPORT_PATH)
    template = _load_jsonl(TEMPLATE_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    diagnostics = json.loads(DIAGNOSTICS_PATH.read_text(encoding="utf-8"))
    status_counts = Counter(record["review_status"] for record in exported)
    languages = dict(sorted(Counter(record["language"] for record in exported).items()))
    categories = dict(
        sorted(Counter(record["reviewed_category"] for record in exported).items())
    )
    multi_fragment = sum(
        record["relevance_validity"] == "multi_fragment" for record in exported
    )
    pending_ids = [
        record["query_id"] for record in template if record["review_status"] == "pending"
    ]

    generated_at = manifest.pop("generated_at")
    assert manifest == {
        "dataset_type": "synthetic_ai_reviewed_exploratory",
        "total_records": len(exported),
        "accepted_records": status_counts["accepted"],
        "revised_records": status_counts["revised"],
        "pending_excluded": len(pending_ids),
        "rejected_excluded": 0,
        "official_evaluation_eligible": False,
        "used_for_official_metrics": False,
        "human_review_completed": False,
        "source_template": "data/eval/benchmark_extended_review_template.jsonl",
        "source_template_sha256": EXPECTED_TEMPLATE_SHA256,
        "source_benchmark": "data/eval/benchmark_extended.jsonl",
        "source_benchmark_sha256": _sha256(SOURCE_PATH),
        "source_statuses_included": ["accepted", "revised"],
        "languages": languages,
        "reviewed_categories": categories,
        "multi_fragment_records": multi_fragment,
        "sha256": _sha256(EXPORT_PATH),
        "protocol_version": "v1",
        "warning": WARNING,
    }
    assert len(source) == len(template) == 132
    assert status_counts == {"accepted": 15, "revised": 99}
    assert len(pending_ids) == 18
    assert _sha256(TEMPLATE_PATH) == EXPECTED_TEMPLATE_SHA256
    datetime.fromisoformat(generated_at.replace("Z", "+00:00"))

    assert diagnostics["valid"] is True
    assert diagnostics["errors"] == []
    assert diagnostics["total_records"] == len(exported)
    assert diagnostics["languages"] == languages
    assert diagnostics["reviewed_categories"] == categories
    assert diagnostics["multi_fragment_records"] == multi_fragment
    assert diagnostics["excluded_query_ids"] == pending_ids
    assert diagnostics["excluded_by_rule"] == {
        "pending_status": 18,
        "rejected_status": 0,
        "review_status_not_included": 0,
        "reviewed_query_text_missing": 0,
        "reviewed_category_missing_or_invalid": 0,
        "reviewed_relevant_fragments_missing": 0,
        "semantic_validity_not_valid": 0,
        "relevance_validity_not_eligible": 0,
        "language_quality_not_eligible": 0,
        "ambiguity_high_or_invalid": 0,
        "reviewer_id_missing": 0,
        "reviewed_at_missing_or_invalid": 0,
        "reviewed_fragment_not_active": 0,
        "synthetic_field_altered": 0,
        "used_for_official_metrics_not_false": 0,
    }
    assert diagnostics["ineligible_accepted_or_revised_query_ids"] == []
    assert diagnostics["official_evaluation_eligible"] is False
    assert diagnostics["used_for_official_metrics"] is False
    assert diagnostics["human_review_completed"] is False


def test_export_is_deterministic_and_is_not_the_132_record_template() -> None:
    source = _load_jsonl(SOURCE_PATH)
    template = _load_jsonl(TEMPLATE_PATH)
    exported = _load_jsonl(EXPORT_PATH)
    active_fragments = {
        fragment for record in source for fragment in record["relevant_fragments"]
    }

    first_generation = _expected_export(template, active_fragments)
    second_generation = _expected_export(template, active_fragments)
    assert first_generation == second_generation == exported
    assert len(exported) == 114
    assert len(exported) != len(template) == 132