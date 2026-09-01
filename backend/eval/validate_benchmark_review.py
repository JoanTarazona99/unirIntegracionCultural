"""Validate and create the human-review layer for the synthetic benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


ANNOTATION_STATUS = "synthetic_needs_human_review"
EXPECTED_RECORD_COUNT = 132
OFFICIAL_METRICS_NOTICE = (
    "This review template is not eligible for official evaluation metrics."
)

REVIEW_STATUSES = {"pending", "accepted", "revised", "rejected"}
SEMANTIC_VALIDITIES = {"valid", "invalid", "unclear"}
RELEVANCE_VALIDITIES = {"valid", "invalid", "multi_fragment", "unclear"}
LANGUAGE_QUALITIES = {"fluent", "acceptable", "needs_edit", "invalid"}
AMBIGUITIES = {"low", "medium", "high"}

RECORD_FIELDS = (
    "query_id",
    "synthetic_query_text",
    "reviewed_query_text",
    "language",
    "synthetic_category",
    "reviewed_category",
    "synthetic_relevant_fragments",
    "reviewed_relevant_fragments",
    "annotation_status",
    "used_for_official_metrics",
    "review_status",
    "semantic_validity",
    "relevance_validity",
    "language_quality",
    "ambiguity",
    "notes",
    "reviewer_id",
    "reviewed_at",
)

HUMAN_DECISION_FIELDS = (
    "reviewed_query_text",
    "reviewed_category",
    "reviewed_relevant_fragments",
    "semantic_validity",
    "relevance_validity",
    "language_quality",
    "ambiguity",
    "notes",
    "reviewer_id",
    "reviewed_at",
)

CONTROLLED_FIELDS = {
    "review_status": REVIEW_STATUSES,
    "semantic_validity": SEMANTIC_VALIDITIES,
    "relevance_validity": RELEVANCE_VALIDITIES,
    "language_quality": LANGUAGE_QUALITIES,
    "ambiguity": AMBIGUITIES,
}

FRAGMENT_ID_PATTERN = re.compile(r"^[^:\r\n]+::(?:0|[1-9]\d*)$")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSONL lines as objects."""
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: JSONL value must be an object")
        records.append(value)
    return records


def create_review_template(
    source_records: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create pending review records without mutating synthetic source values."""
    template = []
    for source in source_records:
        template.append(
            {
                "query_id": source["query_id"],
                "synthetic_query_text": source["query_text"],
                "reviewed_query_text": None,
                "language": source["language"],
                "synthetic_category": source["category"],
                "reviewed_category": None,
                "synthetic_relevant_fragments": source["relevant_fragments"],
                "reviewed_relevant_fragments": None,
                "annotation_status": source["annotation_status"],
                "used_for_official_metrics": False,
                "review_status": "pending",
                "semantic_validity": None,
                "relevance_validity": None,
                "language_quality": None,
                "ambiguity": None,
                "notes": None,
                "reviewer_id": None,
                "reviewed_at": None,
            }
        )
    return template


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_iso_utc(value: Any) -> bool:
    if not _is_non_empty_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def _sorted_counts(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(value if isinstance(value, str) else "<invalid>" for value in values)
    return dict(sorted(counts.items()))


def _empty_report(message: str, error_type: str = "schema") -> dict[str, Any]:
    entry = {"type": error_type, "message": message}
    return {
        "valid": False,
        "errors": [entry],
        "schema_errors": [message] if error_type == "schema" else [],
        "integrity_errors": [message] if error_type == "integrity" else [],
        "eligibility_errors": [message] if error_type == "eligibility" else [],
        "total_records": 0,
        "review_status_counts": {},
        "languages": {},
        "categories": {},
        "future_export_eligible_records": 0,
        "pending_count": 0,
        "accepted_count": 0,
        "revised_count": 0,
        "rejected_count": 0,
        "annotation_status": ANNOTATION_STATUS,
        "used_for_official_metrics": False,
        "official_evaluation_eligible": False,
        "official_metrics_notice": OFFICIAL_METRICS_NOTICE,
    }


def validate_review_records(
    source_records: list[dict[str, Any]],
    review_records: list[dict[str, Any]],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a structured validation report for review records."""
    errors: list[dict[str, Any]] = []
    grouped_errors: dict[str, list[str]] = {
        "schema": [],
        "integrity": [],
        "eligibility": [],
    }
    invalid_record_indexes: set[int] = set()

    def add_error(
        error_type: str,
        message: str,
        record_index: int | None = None,
        query_id: Any = None,
    ) -> None:
        entry: dict[str, Any] = {"type": error_type, "message": message}
        if query_id is not None:
            entry["query_id"] = query_id
        errors.append(entry)
        grouped_errors[error_type].append(message)
        if record_index is not None:
            invalid_record_indexes.add(record_index)

    source_by_id: dict[str, dict[str, Any]] = {}
    for source in source_records:
        query_id = source.get("query_id")
        if isinstance(query_id, str):
            source_by_id[query_id] = source

    if len(source_records) != EXPECTED_RECORD_COUNT:
        add_error(
            "integrity",
            f"source benchmark must contain {EXPECTED_RECORD_COUNT} records; found {len(source_records)}",
        )
    if len(review_records) != EXPECTED_RECORD_COUNT:
        add_error(
            "integrity",
            f"review dataset must contain {EXPECTED_RECORD_COUNT} records; found {len(review_records)}",
        )

    review_ids = [record.get("query_id") for record in review_records]
    id_counts = Counter(query_id for query_id in review_ids if isinstance(query_id, str))
    for query_id, count in sorted(id_counts.items()):
        if count > 1:
            add_error("integrity", f"duplicate query_id: {query_id}", query_id=query_id)

    source_ids = set(source_by_id)
    review_id_set = set(id_counts)
    for query_id in sorted(source_ids - review_id_set):
        add_error("integrity", f"missing synthetic query_id: {query_id}", query_id=query_id)
    for query_id in sorted(review_id_set - source_ids):
        add_error("integrity", f"unknown query_id: {query_id}", query_id=query_id)

    allowed_categories = {
        source["category"]
        for source in source_records
        if isinstance(source.get("category"), str)
    }
    active_fragments = {
        fragment
        for source in source_records
        for fragment in source.get("relevant_fragments", [])
        if isinstance(fragment, str)
    }

    for index, record in enumerate(review_records):
        query_id = record.get("query_id")
        label = query_id if isinstance(query_id, str) else f"record[{index}]"
        missing_fields = sorted(set(RECORD_FIELDS) - set(record))
        unexpected_fields = sorted(set(record) - set(RECORD_FIELDS))
        if missing_fields:
            add_error(
                "schema",
                f"{label}: missing fields: {', '.join(missing_fields)}",
                index,
                query_id,
            )
        if unexpected_fields:
            add_error(
                "schema",
                f"{label}: unexpected fields: {', '.join(unexpected_fields)}",
                index,
                query_id,
            )

        source = source_by_id.get(query_id) if isinstance(query_id, str) else None
        if source is not None:
            expected_synthetic = {
                "synthetic_query_text": source.get("query_text"),
                "language": source.get("language"),
                "synthetic_category": source.get("category"),
                "synthetic_relevant_fragments": source.get("relevant_fragments"),
                "annotation_status": source.get("annotation_status"),
                "used_for_official_metrics": source.get("used_for_official_metrics"),
            }
            for field, expected in expected_synthetic.items():
                if record.get(field) != expected:
                    add_error(
                        "integrity",
                        f"{label}: synthetic field {field} differs from source",
                        index,
                        query_id,
                    )

        if record.get("annotation_status") != ANNOTATION_STATUS:
            add_error(
                "integrity",
                f"{label}: annotation_status must be {ANNOTATION_STATUS}",
                index,
                query_id,
            )
        if record.get("used_for_official_metrics") is not False:
            add_error(
                "eligibility",
                f"{label}: used_for_official_metrics must be false",
                index,
                query_id,
            )

        for field, vocabulary in CONTROLLED_FIELDS.items():
            value = record.get(field)
            if field == "review_status" or value is not None:
                if value not in vocabulary:
                    add_error(
                        "schema",
                        f"{label}: invalid {field}: {value!r}",
                        index,
                        query_id,
                    )

        reviewed_query_text = record.get("reviewed_query_text")
        if reviewed_query_text is not None and not isinstance(reviewed_query_text, str):
            add_error(
                "schema", f"{label}: reviewed_query_text must be a string or null", index, query_id
            )

        reviewed_category = record.get("reviewed_category")
        if reviewed_category is not None and reviewed_category not in allowed_categories:
            add_error(
                "schema",
                f"{label}: reviewed_category is not in the source category vocabulary",
                index,
                query_id,
            )

        reviewed_fragments = record.get("reviewed_relevant_fragments")
        if reviewed_fragments is not None:
            if not isinstance(reviewed_fragments, list):
                add_error(
                    "schema",
                    f"{label}: reviewed_relevant_fragments must be a list or null",
                    index,
                    query_id,
                )
            else:
                for fragment in reviewed_fragments:
                    if not isinstance(fragment, str) or not FRAGMENT_ID_PATTERN.fullmatch(fragment):
                        add_error(
                            "schema",
                            f"{label}: invalid reviewed fragment format: {fragment!r}",
                            index,
                            query_id,
                        )
                    elif fragment not in active_fragments:
                        add_error(
                            "integrity",
                            f"{label}: reviewed fragment is not active: {fragment}",
                            index,
                            query_id,
                        )

        for field in ("notes", "reviewer_id"):
            value = record.get(field)
            if value is not None and not isinstance(value, str):
                add_error(
                    "schema", f"{label}: {field} must be a string or null", index, query_id
                )

        reviewed_at = record.get("reviewed_at")
        if reviewed_at is not None and not _is_iso_utc(reviewed_at):
            add_error(
                "schema",
                f"{label}: reviewed_at must be an ISO-8601 UTC timestamp",
                index,
                query_id,
            )

        review_status = record.get("review_status")
        if review_status == "pending":
            non_null_fields = [field for field in HUMAN_DECISION_FIELDS if record.get(field) is not None]
            if non_null_fields:
                add_error(
                    "integrity",
                    f"{label}: pending record has non-null human fields: {', '.join(non_null_fields)}",
                    index,
                    query_id,
                )
        elif review_status in {"accepted", "revised"}:
            required_non_empty = {
                "reviewed_query_text": reviewed_query_text,
                "reviewer_id": record.get("reviewer_id"),
                "reviewed_at": reviewed_at,
            }
            for field, value in required_non_empty.items():
                if not _is_non_empty_string(value):
                    add_error(
                        "eligibility",
                        f"{label}: {review_status} record requires non-empty {field}",
                        index,
                        query_id,
                    )
            if reviewed_category not in allowed_categories:
                add_error(
                    "eligibility",
                    f"{label}: {review_status} record requires a valid reviewed_category",
                    index,
                    query_id,
                )
            if not isinstance(reviewed_fragments, list) or not reviewed_fragments:
                add_error(
                    "eligibility",
                    f"{label}: {review_status} record requires reviewed_relevant_fragments",
                    index,
                    query_id,
                )
            expected_values = {
                "semantic_validity": {"valid"},
                "relevance_validity": {"valid", "multi_fragment"},
                "language_quality": {"fluent", "acceptable"},
                "ambiguity": {"low", "medium"},
            }
            for field, accepted_values in expected_values.items():
                if record.get(field) not in accepted_values:
                    add_error(
                        "eligibility",
                        f"{label}: {review_status} record has ineligible {field}",
                        index,
                        query_id,
                    )
        elif review_status == "rejected" and not _is_non_empty_string(record.get("notes")):
            add_error(
                "integrity",
                f"{label}: rejected record requires non-empty notes",
                index,
                query_id,
            )

    if manifest is not None:
        required_manifest_values = {
            "annotation_status": ANNOTATION_STATUS,
            "used_for_official_metrics": False,
            "official_evaluation_eligible": False,
        }
        for field, expected in required_manifest_values.items():
            if manifest.get(field) != expected:
                add_error("eligibility", f"manifest {field} must be {expected!r}")
        if manifest.get("total_records") != len(review_records):
            add_error("integrity", "manifest total_records does not match review dataset")

    status_counts = _sorted_counts(record.get("review_status") for record in review_records)
    languages = _sorted_counts(record.get("language") for record in review_records)
    categories = _sorted_counts(
        record.get("reviewed_category") or record.get("synthetic_category")
        for record in review_records
    )
    future_export_eligible = sum(
        1
        for index, record in enumerate(review_records)
        if record.get("review_status") in {"accepted", "revised"}
        and index not in invalid_record_indexes
        and record.get("query_id") in source_by_id
        and id_counts.get(record.get("query_id")) == 1
    )

    return {
        "valid": not errors,
        "errors": errors,
        "schema_errors": grouped_errors["schema"],
        "integrity_errors": grouped_errors["integrity"],
        "eligibility_errors": grouped_errors["eligibility"],
        "total_records": len(review_records),
        "review_status_counts": status_counts,
        "languages": languages,
        "categories": categories,
        "future_export_eligible_records": future_export_eligible,
        "pending_count": status_counts.get("pending", 0),
        "accepted_count": status_counts.get("accepted", 0),
        "revised_count": status_counts.get("revised", 0),
        "rejected_count": status_counts.get("rejected", 0),
        "annotation_status": ANNOTATION_STATUS,
        "used_for_official_metrics": False,
        "official_evaluation_eligible": False,
        "official_metrics_notice": OFFICIAL_METRICS_NOTICE,
    }


def validate_review_files(
    source_path: Path,
    review_path: Path,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Load review inputs and return parse or record validation diagnostics."""
    try:
        source_records = load_jsonl(source_path)
        review_records = load_jsonl(review_path)
        manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest_path is not None
            else None
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _empty_report(f"unable to load review inputs: {exc}")
    if manifest is not None and not isinstance(manifest, dict):
        return _empty_report("review manifest must be a JSON object")
    return validate_review_records(source_records, review_records, manifest)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_review_artifacts(
    source_path: Path,
    review_path: Path,
    manifest_path: Path,
    diagnostics_path: Path,
) -> dict[str, Any]:
    """Create only the pending review template, manifest, and diagnostics."""
    source_records = load_jsonl(source_path)
    review_records = create_review_template(source_records)
    initial_report = validate_review_records(source_records, review_records)
    if not initial_report["valid"]:
        raise ValueError(f"refusing to write invalid review template: {initial_report['errors']}")

    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in review_records
        ),
        encoding="utf-8",
    )
    manifest = {
        "review_version": "kubgu-human-review-template-v1",
        "review_file": review_path.name,
        "schema": "kubgu-benchmark-human-review-jsonl-v1",
        "sha256": _sha256(review_path),
        "source_benchmark_file": source_path.name,
        "source_benchmark_sha256": _sha256(source_path),
        "total_records": len(review_records),
        "review_status_counts": initial_report["review_status_counts"],
        "languages": initial_report["languages"],
        "categories": initial_report["categories"],
        "annotation_status": ANNOTATION_STATUS,
        "used_for_official_metrics": False,
        "official_evaluation_eligible": False,
        "official_metrics_notice": OFFICIAL_METRICS_NOTICE,
    }
    diagnostics = validate_review_records(source_records, review_records, manifest)
    _write_json(manifest_path, manifest)
    _write_json(diagnostics_path, diagnostics)
    return {"manifest": manifest, "diagnostics": diagnostics}


def _default_paths() -> tuple[Path, Path, Path, Path]:
    repository = Path(__file__).resolve().parents[2]
    eval_data = repository / "data" / "eval"
    return (
        eval_data / "benchmark_extended.jsonl",
        eval_data / "benchmark_extended_review_template.jsonl",
        eval_data / "benchmark_extended_review_manifest.json",
        eval_data / "benchmark_extended_review_diagnostics.json",
    )


def main() -> int:
    source_default, review_default, manifest_default, diagnostics_default = _default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=source_default)
    parser.add_argument("--review", type=Path, default=review_default)
    parser.add_argument("--manifest", type=Path, default=manifest_default)
    parser.add_argument("--diagnostics", type=Path, default=diagnostics_default)
    parser.add_argument("--create-template", action="store_true")
    arguments = parser.parse_args()

    if arguments.create_template:
        outputs = write_review_artifacts(
            arguments.source,
            arguments.review,
            arguments.manifest,
            arguments.diagnostics,
        )
        report = outputs["diagnostics"]
    else:
        report = validate_review_files(
            arguments.source,
            arguments.review,
            arguments.manifest,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())