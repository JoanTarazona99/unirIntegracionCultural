"""Pure tests for the separate synthetic benchmark review workflow."""

import copy
import json
from pathlib import Path

import pytest

from eval.validate_benchmark_review import (
    ANNOTATION_STATUS,
    create_review_template,
    validate_review_records,
)


REPOSITORY_DIR = Path(__file__).resolve().parents[2]
SOURCE_PATH = REPOSITORY_DIR / "data" / "eval" / "benchmark_extended.jsonl"


@pytest.fixture(scope="module")
def source_records():
    return [
        json.loads(line)
        for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture
def pending_records(source_records):
    return create_review_template(source_records)


def complete_record(record, status="accepted"):
    updated = copy.deepcopy(record)
    updated.update(
        {
            "reviewed_query_text": updated["synthetic_query_text"],
            "reviewed_category": updated["synthetic_category"],
            "reviewed_relevant_fragments": updated["synthetic_relevant_fragments"],
            "review_status": status,
            "semantic_validity": "valid",
            "relevance_validity": "valid",
            "language_quality": "fluent",
            "ambiguity": "low",
            "notes": None,
            "reviewer_id": "reviewer-01",
            "reviewed_at": "2026-08-29T12:00:00Z",
        }
    )
    return updated


def error_messages(report):
    return [entry["message"] for entry in report["errors"]]


def test_fully_pending_template_is_valid(source_records, pending_records):
    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is True
    assert report["errors"] == []
    assert report["total_records"] == 132
    assert report["review_status_counts"] == {"pending": 132}
    assert report["pending_count"] == 132
    assert report["future_export_eligible_records"] == 0
    assert report["official_evaluation_eligible"] is False
    assert all(record["annotation_status"] == ANNOTATION_STATUS for record in pending_records)
    assert all(record["used_for_official_metrics"] is False for record in pending_records)


def test_complete_accepted_record_is_valid(source_records, pending_records):
    pending_records[0] = complete_record(pending_records[0])

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is True
    assert report["accepted_count"] == 1
    assert report["future_export_eligible_records"] == 1
    assert pending_records[0]["used_for_official_metrics"] is False


def test_complete_revised_record_is_valid(source_records, pending_records):
    pending_records[0] = complete_record(pending_records[0], status="revised")
    pending_records[0]["reviewed_query_text"] = "Consulta revisada por una persona"
    pending_records[0]["language_quality"] = "acceptable"
    pending_records[0]["ambiguity"] = "medium"

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is True
    assert report["revised_count"] == 1
    assert report["future_export_eligible_records"] == 1


def test_rejected_record_with_reason_is_valid(source_records, pending_records):
    pending_records[0]["review_status"] = "rejected"
    pending_records[0]["notes"] = "The query does not express a coherent information need."

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is True
    assert report["rejected_count"] == 1
    assert report["future_export_eligible_records"] == 0


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    (
        ("reviewed_query_text", None, "requires non-empty reviewed_query_text"),
        ("reviewed_relevant_fragments", None, "requires reviewed_relevant_fragments"),
        ("reviewed_category", None, "requires a valid reviewed_category"),
        ("reviewer_id", None, "requires non-empty reviewer_id"),
        ("reviewed_at", None, "requires non-empty reviewed_at"),
    ),
)
def test_accepted_record_requires_complete_review(
    source_records, pending_records, field, value, expected_message
):
    pending_records[0] = complete_record(pending_records[0])
    pending_records[0][field] = value

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any(expected_message in message for message in error_messages(report))
    assert report["future_export_eligible_records"] == 0


def test_duplicate_query_id_fails(source_records, pending_records):
    pending_records[0] = complete_record(pending_records[0])
    pending_records[1]["query_id"] = pending_records[0]["query_id"]

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("duplicate query_id" in message for message in report["integrity_errors"])
    assert report["future_export_eligible_records"] == 0


def test_missing_synthetic_query_id_fails(source_records, pending_records):
    pending_records.pop()

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("missing synthetic query_id" in message for message in report["integrity_errors"])


def test_extra_unknown_query_id_fails(source_records, pending_records):
    unknown = copy.deepcopy(pending_records[0])
    unknown["query_id"] = "q999"
    pending_records.append(unknown)

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("unknown query_id: q999" in message for message in report["integrity_errors"])


def test_non_existing_reviewed_fragment_fails(source_records, pending_records):
    pending_records[0] = complete_record(pending_records[0])
    pending_records[0]["reviewed_relevant_fragments"] = ["Unknown source::999"]

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("reviewed fragment is not active" in message for message in report["integrity_errors"])


def test_invalid_reviewed_category_fails(source_records, pending_records):
    pending_records[0] = complete_record(pending_records[0])
    pending_records[0]["reviewed_category"] = "unsupported_category"

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("source category vocabulary" in message for message in report["schema_errors"])


def test_invalid_controlled_vocabulary_value_fails(source_records, pending_records):
    pending_records[0] = complete_record(pending_records[0])
    pending_records[0]["semantic_validity"] = "probably"

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("invalid semantic_validity" in message for message in report["schema_errors"])


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("synthetic_query_text", "Altered synthetic text"),
        ("language", "en"),
        ("synthetic_category", "housing"),
        ("synthetic_relevant_fragments", ["КубГУ::1"]),
        ("annotation_status", "human_validated"),
    ),
)
def test_altered_synthetic_field_fails(source_records, pending_records, field, value):
    pending_records[0][field] = value

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any(f"synthetic field {field} differs" in message for message in report["integrity_errors"])


def test_official_metrics_true_fails(source_records, pending_records):
    pending_records[0]["used_for_official_metrics"] = True

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("used_for_official_metrics must be false" in message for message in report["eligibility_errors"])
    assert report["official_evaluation_eligible"] is False


def test_pending_record_with_human_field_fails(source_records, pending_records):
    pending_records[0]["notes"] = "Premature annotation"

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("pending record has non-null human fields" in message for message in report["integrity_errors"])


def test_rejected_record_without_notes_fails(source_records, pending_records):
    pending_records[0]["review_status"] = "rejected"

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("rejected record requires non-empty notes" in message for message in report["integrity_errors"])


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-08-29",
        "2026-08-29T12:00:00",
        "2026-08-29T12:00:00+03:00",
        "not-a-timestamp",
    ),
)
def test_non_iso_utc_timestamp_fails(source_records, pending_records, timestamp):
    pending_records[0] = complete_record(pending_records[0])
    pending_records[0]["reviewed_at"] = timestamp

    report = validate_review_records(source_records, pending_records)

    assert report["valid"] is False
    assert any("ISO-8601 UTC timestamp" in message for message in report["schema_errors"])


def test_manifest_must_preserve_official_exclusion(source_records, pending_records):
    manifest = {
        "total_records": 132,
        "annotation_status": ANNOTATION_STATUS,
        "used_for_official_metrics": True,
        "official_evaluation_eligible": True,
    }

    report = validate_review_records(source_records, pending_records, manifest)

    assert report["valid"] is False
    assert len(report["eligibility_errors"]) == 2