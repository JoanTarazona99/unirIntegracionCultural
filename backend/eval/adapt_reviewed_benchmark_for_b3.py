"""Adapt the reviewed exploratory benchmark to the B3 JSONL contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ADAPTER_VERSION = "v1"
DATASET_TYPE = "synthetic_ai_reviewed_exploratory_b3_input"
EVALUATION_DATASET_TYPE = "synthetic_ai_reviewed_exploratory"
EXPECTED_RECORD_COUNT = 114
EXPECTED_STATUS_COUNTS = {"accepted": 15, "revised": 99}
EXPECTED_LANGUAGE_COUNTS = {"es": 38, "en": 38, "ru": 38}
EXPECTED_PENDING_EXCLUDED = 18
EXPECTED_REJECTED_EXCLUDED = 0
ALLOWED_LANGUAGES = set(EXPECTED_LANGUAGE_COUNTS)
ALLOWED_REVIEW_STATUSES = {"accepted", "revised"}
ALLOWED_RELEVANCE_VALIDITIES = {"valid", "multi_fragment"}
ALLOWED_LANGUAGE_QUALITIES = {"fluent", "acceptable"}
ALLOWED_AMBIGUITIES = {"low", "medium"}

FIELD_MAPPING = {
    "id": "query_id",
    "question": "reviewed_query_text",
    "lang": "language",
    "category": "reviewed_category",
    "relevant_chunk_ids": "reviewed_relevant_fragments",
}

TRACEABILITY_FIELDS = (
    "query_id",
    "synthetic_query_text",
    "synthetic_category",
    "synthetic_relevant_fragments",
    "reviewed_query_text",
    "reviewed_category",
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
    "export_status",
    "official_evaluation_eligible",
    "source_review_statuses_included",
    "pending_excluded",
    "rejected_excluded",
    "human_review_completed",
    "export_protocol_version",
)

WARNING = (
    "Los registros y qrels conservan origen sintético y fueron revisados con "
    "asistencia de IA; este adaptador no los convierte en anotaciones humanas "
    "ni en un benchmark oficial."
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSONL lines and require every value to be an object."""
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: JSONL value must be an object")
        records.append(value)
    return records


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def serialize_jsonl(records: Iterable[Mapping[str, Any]]) -> bytes:
    text = "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    )
    return text.encode("utf-8")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_active_inventory(
    benchmark_records: Sequence[Mapping[str, Any]],
) -> tuple[set[str], set[str]]:
    """Return the category vocabulary and active fragment IDs from the benchmark."""
    categories = {
        record["category"]
        for record in benchmark_records
        if _is_non_empty_string(record.get("category"))
    }
    fragments = {
        fragment
        for record in benchmark_records
        for fragment in record.get("relevant_fragments", [])
        if _is_non_empty_string(fragment)
    }
    if len(categories) != 17:
        raise ValueError(
            f"active category vocabulary must contain 17 values; found {len(categories)}"
        )
    if not fragments:
        raise ValueError("active fragment inventory must not be empty")
    return categories, fragments


def validate_source_artifacts(
    source_path: Path,
    source_manifest: Mapping[str, Any],
    source_diagnostics: Mapping[str, Any],
) -> tuple[str, ...]:
    """Validate provenance metadata and return the expected excluded IDs."""
    errors: list[str] = []
    source_hash = sha256_file(source_path)
    if source_manifest.get("sha256") != source_hash:
        errors.append("source manifest SHA-256 does not match the reviewed JSONL")
    if source_diagnostics.get("export_sha256") != source_hash:
        errors.append("source diagnostics SHA-256 does not match the reviewed JSONL")
    if source_manifest.get("total_records") != EXPECTED_RECORD_COUNT:
        errors.append("source manifest total_records must be 114")
    if source_diagnostics.get("valid") is not True:
        errors.append("source diagnostics must be valid")
    for field in (
        "used_for_official_metrics",
        "official_evaluation_eligible",
        "human_review_completed",
    ):
        if source_manifest.get(field) is not False:
            errors.append(f"source manifest {field} must be false")
        if source_diagnostics.get(field) is not False:
            errors.append(f"source diagnostics {field} must be false")

    excluded_ids = source_diagnostics.get("excluded_query_ids")
    if not isinstance(excluded_ids, list) or not all(
        _is_non_empty_string(query_id) for query_id in excluded_ids
    ):
        errors.append("source diagnostics excluded_query_ids must be a string list")
        excluded_ids = []
    if len(excluded_ids) != EXPECTED_PENDING_EXCLUDED:
        errors.append("source diagnostics must identify exactly 18 excluded IDs")
    if len(excluded_ids) != len(set(excluded_ids)):
        errors.append("source diagnostics excluded_query_ids must be unique")
    if errors:
        raise ValueError("; ".join(errors))
    return tuple(excluded_ids)


def adapt_records(
    source_records: Sequence[Mapping[str, Any]],
    *,
    allowed_categories: set[str],
    active_fragments: set[str],
    excluded_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Validate and adapt records without filtering, reordering, or mutating input."""
    errors: list[str] = []
    excluded_id_set = set(excluded_ids)
    source_ids = [record.get("query_id") for record in source_records]
    id_counts = Counter(query_id for query_id in source_ids if isinstance(query_id, str))

    if len(source_records) != EXPECTED_RECORD_COUNT:
        errors.append(
            f"source must contain exactly {EXPECTED_RECORD_COUNT} records; "
            f"found {len(source_records)}"
        )
    duplicates = sorted(query_id for query_id, count in id_counts.items() if count > 1)
    if duplicates:
        errors.append(f"duplicate query_id values: {', '.join(duplicates)}")

    adapted: list[dict[str, Any]] = []
    for index, source in enumerate(source_records):
        query_id = source.get("query_id")
        label = query_id if _is_non_empty_string(query_id) else f"record[{index}]"
        missing_traceability = [field for field in TRACEABILITY_FIELDS if field not in source]
        if missing_traceability:
            errors.append(
                f"{label}: missing traceability fields: {', '.join(missing_traceability)}"
            )
        if not _is_non_empty_string(query_id):
            errors.append(f"{label}: query_id must be a non-empty string")
        elif query_id in excluded_id_set:
            errors.append(f"{label}: excluded pending ID must not appear")
        if source.get("review_status") not in ALLOWED_REVIEW_STATUSES:
            errors.append(f"{label}: review_status must be accepted or revised")
        if source.get("semantic_validity") != "valid":
            errors.append(f"{label}: semantic_validity must be valid")
        if source.get("relevance_validity") not in ALLOWED_RELEVANCE_VALIDITIES:
            errors.append(f"{label}: relevance_validity is not eligible")
        if source.get("language_quality") not in ALLOWED_LANGUAGE_QUALITIES:
            errors.append(f"{label}: language_quality is not eligible")
        if source.get("ambiguity") not in ALLOWED_AMBIGUITIES:
            errors.append(f"{label}: ambiguity must be low or medium")
        if not _is_non_empty_string(source.get("reviewed_query_text")):
            errors.append(f"{label}: reviewed_query_text must be non-empty")
        if source.get("reviewed_category") not in allowed_categories:
            errors.append(f"{label}: reviewed_category is not in the 17-category vocabulary")
        if source.get("language") not in ALLOWED_LANGUAGES:
            errors.append(f"{label}: language must be one of es, en, ru")

        reviewed_fragments = source.get("reviewed_relevant_fragments")
        if not isinstance(reviewed_fragments, list) or not reviewed_fragments:
            errors.append(f"{label}: reviewed_relevant_fragments must be a non-empty list")
        else:
            invalid_fragments = [
                fragment
                for fragment in reviewed_fragments
                if not _is_non_empty_string(fragment) or fragment not in active_fragments
            ]
            if invalid_fragments:
                errors.append(
                    f"{label}: reviewed fragments are not active: {invalid_fragments!r}"
                )
        for field in ("reviewer_id", "reviewed_at"):
            if not _is_non_empty_string(source.get(field)):
                errors.append(f"{label}: {field} must be present and non-empty")
        for field in (
            "used_for_official_metrics",
            "official_evaluation_eligible",
            "human_review_completed",
        ):
            if source.get(field) is not False:
                errors.append(f"{label}: {field} must be false")

        output = copy.deepcopy(dict(source))
        output.update(
            {
                canonical: copy.deepcopy(source.get(reviewed))
                for canonical, reviewed in FIELD_MAPPING.items()
            }
        )
        output.update(
            {
                "evaluation_dataset_type": EVALUATION_DATASET_TYPE,
                "used_for_official_metrics": False,
                "official_evaluation_eligible": False,
                "human_review_completed": False,
                "b3_adapter_version": ADAPTER_VERSION,
            }
        )
        adapted.append(output)

    language_counts = Counter(record.get("lang") for record in adapted)
    status_counts = Counter(record.get("review_status") for record in adapted)
    if dict(language_counts) != EXPECTED_LANGUAGE_COUNTS:
        errors.append(
            f"language distribution must be {EXPECTED_LANGUAGE_COUNTS}; "
            f"found {dict(language_counts)}"
        )
    if dict(status_counts) != EXPECTED_STATUS_COUNTS:
        errors.append(
            f"review status distribution must be {EXPECTED_STATUS_COUNTS}; "
            f"found {dict(status_counts)}"
        )

    for index, (source, output) in enumerate(zip(source_records, adapted)):
        label = source.get("query_id", f"record[{index}]")
        if any(output.get(field) != value for field, value in source.items()):
            errors.append(f"{label}: a source field changed during adaptation")
        for canonical, reviewed in FIELD_MAPPING.items():
            if output.get(canonical) != source.get(reviewed):
                errors.append(f"{label}: canonical field {canonical} changed content")

    if errors:
        raise ValueError("\n".join(errors))
    return adapted


def build_metadata(
    source_records: Sequence[Mapping[str, Any]],
    adapted_records: Sequence[Mapping[str, Any]],
    *,
    output_hash: str,
    deterministic_regeneration: bool,
    source_references: Mapping[str, Mapping[str, str]],
    excluded_ids: Sequence[str],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build coherent manifest and diagnostics for validated adapted records."""
    languages = dict(sorted(Counter(record["lang"] for record in adapted_records).items()))
    categories = dict(
        sorted(Counter(record["category"] for record in adapted_records).items())
    )
    statuses = Counter(record["review_status"] for record in adapted_records)
    multi_fragment = sum(
        len(record["relevant_chunk_ids"]) > 1 for record in adapted_records
    )
    source_ids = [record["query_id"] for record in source_records]
    output_ids = [record["id"] for record in adapted_records]
    source_fields_preserved = all(
        all(output.get(field) == value for field, value in source.items())
        for source, output in zip(source_records, adapted_records)
    )
    canonical_content_unchanged = all(
        all(output[canonical] == source[reviewed] for canonical, reviewed in FIELD_MAPPING.items())
        for source, output in zip(source_records, adapted_records)
    )
    eligibility_flags = {
        "official_evaluation_eligible": False,
        "used_for_official_metrics": False,
        "human_review_completed": False,
    }
    invariants = {
        "record_count_is_114": len(adapted_records) == EXPECTED_RECORD_COUNT,
        "one_output_per_source": len(adapted_records) == len(source_records),
        "source_order_preserved": output_ids == source_ids,
        "ids_are_unique": len(output_ids) == len(set(output_ids)),
        "five_b3_fields_present": all(
            set(FIELD_MAPPING).issubset(record) for record in adapted_records
        ),
        "canonical_content_unchanged": canonical_content_unchanged,
        "source_fields_preserved": source_fields_preserved,
        "pending_ids_absent": set(excluded_ids).isdisjoint(output_ids),
        "language_distribution_is_38_each": languages == EXPECTED_LANGUAGE_COUNTS,
        "all_eligibility_flags_false": all(
            all(record[field] is False for field in eligibility_flags)
            for record in adapted_records
        ),
        "output_hash_matches_serialization": (
            sha256_bytes(serialize_jsonl(adapted_records)) == output_hash
        ),
        "deterministic_regeneration": deterministic_regeneration,
    }
    manifest = {
        "dataset_type": DATASET_TYPE,
        "total_records": len(adapted_records),
        "accepted_records": statuses["accepted"],
        "revised_records": statuses["revised"],
        "pending_excluded": EXPECTED_PENDING_EXCLUDED,
        "rejected_excluded": EXPECTED_REJECTED_EXCLUDED,
        "languages": languages,
        "categories": categories,
        "multi_fragment_records": multi_fragment,
        **eligibility_flags,
        "adapter_version": ADAPTER_VERSION,
        "sha256": output_hash,
        "source_inputs": dict(source_references),
        "created_at": generated_at,
        "warning": WARNING,
        "field_mapping": FIELD_MAPPING,
    }
    diagnostics = {
        "valid": all(invariants.values()),
        "errors": [] if all(invariants.values()) else [
            name for name, passed in invariants.items() if not passed
        ],
        "total_records": len(adapted_records),
        "unique_ids": len(set(output_ids)),
        "ids_are_unique": invariants["ids_are_unique"],
        "languages": languages,
        "categories": categories,
        "multi_fragment_records": multi_fragment,
        "source_comparison": {
            "source_records": len(source_records),
            "output_records": len(adapted_records),
            "one_output_per_source": invariants["one_output_per_source"],
            "source_order_preserved": invariants["source_order_preserved"],
            "source_fields_preserved": source_fields_preserved,
            "canonical_content_unchanged": canonical_content_unchanged,
        },
        "expected_excluded_ids": list(excluded_ids),
        "expected_excluded_count": len(excluded_ids),
        "excluded_ids_present": sorted(set(excluded_ids) & set(output_ids)),
        "eligibility_flags": eligibility_flags,
        "output_sha256": output_hash,
        "invariants": invariants,
        "adapter_version": ADAPTER_VERSION,
        "generated_at": generated_at,
        "warning": WARNING,
    }
    return manifest, diagnostics


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _portable_reference(path: Path) -> str:
    repository = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(repository).as_posix()
    except ValueError:
        return path.name


def adapt_files(
    source_path: Path,
    source_manifest_path: Path,
    source_diagnostics_path: Path,
    inventory_path: Path,
    output_path: Path,
    output_manifest_path: Path,
    output_diagnostics_path: Path,
) -> dict[str, Any]:
    """Validate all inputs and write the three B3 adapter artifacts."""
    source_records = load_jsonl(source_path)
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_diagnostics = json.loads(source_diagnostics_path.read_text(encoding="utf-8"))
    if not isinstance(source_manifest, dict) or not isinstance(source_diagnostics, dict):
        raise ValueError("source manifest and diagnostics must be JSON objects")
    excluded_ids = validate_source_artifacts(
        source_path, source_manifest, source_diagnostics
    )
    allowed_categories, active_fragments = load_active_inventory(
        load_jsonl(inventory_path)
    )
    adapted_records = adapt_records(
        source_records,
        allowed_categories=allowed_categories,
        active_fragments=active_fragments,
        excluded_ids=excluded_ids,
    )
    output_content = serialize_jsonl(adapted_records)
    regenerated_content = serialize_jsonl(
        adapt_records(
            source_records,
            allowed_categories=allowed_categories,
            active_fragments=active_fragments,
            excluded_ids=excluded_ids,
        )
    )
    deterministic_regeneration = regenerated_content == output_content
    if not deterministic_regeneration:
        raise ValueError("B3 JSONL regeneration is not deterministic")
    output_hash = sha256_bytes(output_content)
    source_references = {
        "reviewed_jsonl": {
            "path": _portable_reference(source_path),
            "sha256": sha256_file(source_path),
        },
        "reviewed_manifest": {
            "path": _portable_reference(source_manifest_path),
            "sha256": sha256_file(source_manifest_path),
        },
        "reviewed_diagnostics": {
            "path": _portable_reference(source_diagnostics_path),
            "sha256": sha256_file(source_diagnostics_path),
        },
        "active_inventory": {
            "path": _portable_reference(inventory_path),
            "sha256": sha256_file(inventory_path),
        },
    }
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    manifest, diagnostics = build_metadata(
        source_records,
        adapted_records,
        output_hash=output_hash,
        deterministic_regeneration=deterministic_regeneration,
        source_references=source_references,
        excluded_ids=excluded_ids,
        generated_at=generated_at,
    )
    if not diagnostics["valid"]:
        raise ValueError(f"refusing to write invalid B3 artifacts: {diagnostics['errors']}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_content)
    _write_json(output_manifest_path, manifest)
    _write_json(output_diagnostics_path, diagnostics)
    return diagnostics


def default_paths() -> tuple[Path, ...]:
    repository = Path(__file__).resolve().parents[2]
    eval_data = repository / "data" / "eval"
    return (
        eval_data / "benchmark_extended_reviewed_114.jsonl",
        eval_data / "benchmark_extended_reviewed_114.manifest.json",
        eval_data / "benchmark_extended_reviewed_114_diagnostics.json",
        eval_data / "benchmark_extended.jsonl",
        eval_data / "benchmark_extended_reviewed_114_b3.jsonl",
        eval_data / "benchmark_extended_reviewed_114_b3.manifest.json",
        eval_data / "benchmark_extended_reviewed_114_b3_diagnostics.json",
    )


def main() -> int:
    defaults = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=defaults[0])
    parser.add_argument("--source-manifest", type=Path, default=defaults[1])
    parser.add_argument("--source-diagnostics", type=Path, default=defaults[2])
    parser.add_argument("--inventory", type=Path, default=defaults[3])
    parser.add_argument("--output", type=Path, default=defaults[4])
    parser.add_argument("--manifest", type=Path, default=defaults[5])
    parser.add_argument("--diagnostics", type=Path, default=defaults[6])
    arguments = parser.parse_args()
    try:
        diagnostics = adapt_files(
            arguments.source,
            arguments.source_manifest,
            arguments.source_diagnostics,
            arguments.inventory,
            arguments.output,
            arguments.manifest,
            arguments.diagnostics,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())