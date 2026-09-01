"""Contract tests for the reviewed exploratory benchmark B3 adapter."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from eval.adapt_reviewed_benchmark_for_b3 import (
    ADAPTER_VERSION,
    DATASET_TYPE,
    EVALUATION_DATASET_TYPE,
    EXPECTED_LANGUAGE_COUNTS,
    EXPECTED_RECORD_COUNT,
    FIELD_MAPPING,
    TRACEABILITY_FIELDS,
    adapt_records,
    load_active_inventory,
    load_jsonl,
    serialize_jsonl,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114.jsonl"
SOURCE_MANIFEST_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114.manifest.json"
SOURCE_DIAGNOSTICS_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114_diagnostics.json"
INVENTORY_PATH = ROOT / "data/eval/benchmark_extended.jsonl"
OUTPUT_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114_b3.jsonl"
MANIFEST_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114_b3.manifest.json"
DIAGNOSTICS_PATH = ROOT / "data/eval/benchmark_extended_reviewed_114_b3_diagnostics.json"


@pytest.fixture(scope="module")
def source_records() -> list[dict]:
    return load_jsonl(SOURCE_PATH)


@pytest.fixture(scope="module")
def inventory() -> tuple[set[str], set[str]]:
    return load_active_inventory(load_jsonl(INVENTORY_PATH))


@pytest.fixture(scope="module")
def excluded_ids() -> tuple[str, ...]:
    diagnostics = json.loads(SOURCE_DIAGNOSTICS_PATH.read_text(encoding="utf-8"))
    return tuple(diagnostics["excluded_query_ids"])


def _adapt(
    records: list[dict],
    inventory: tuple[set[str], set[str]],
    excluded_ids: tuple[str, ...],
) -> list[dict]:
    categories, fragments = inventory
    return adapt_records(
        records,
        allowed_categories=categories,
        active_fragments=fragments,
        excluded_ids=excluded_ids,
    )


@pytest.fixture(scope="module")
def adapted_records(source_records, inventory, excluded_ids) -> list[dict]:
    return _adapt(source_records, inventory, excluded_ids)


def test_adapter_produces_exactly_114_records(adapted_records) -> None:
    assert len(adapted_records) == EXPECTED_RECORD_COUNT == 114


def test_all_ids_are_unique(adapted_records) -> None:
    ids = [record["id"] for record in adapted_records]
    assert len(ids) == len(set(ids))


def test_all_five_b3_fields_exist(adapted_records) -> None:
    assert all(set(FIELD_MAPPING).issubset(record) for record in adapted_records)


def test_b3_fields_map_exactly_to_reviewed_source(source_records, adapted_records) -> None:
    for source, adapted in zip(source_records, adapted_records):
        for b3_field, source_field in FIELD_MAPPING.items():
            assert adapted[b3_field] == source[source_field]


def test_all_source_fields_and_traceability_are_preserved(
    source_records, adapted_records
) -> None:
    for source, adapted in zip(source_records, adapted_records):
        assert set(TRACEABILITY_FIELDS).issubset(adapted)
        assert all(adapted[field] == value for field, value in source.items())


def test_no_pending_id_appears(adapted_records, excluded_ids) -> None:
    assert len(excluded_ids) == 18
    assert set(excluded_ids).isdisjoint(record["id"] for record in adapted_records)


def test_language_distribution_is_38_each(adapted_records) -> None:
    assert Counter(record["lang"] for record in adapted_records) == EXPECTED_LANGUAGE_COUNTS


def test_all_fragments_exist_in_active_inventory(adapted_records, inventory) -> None:
    _, active_fragments = inventory
    assert all(
        fragment in active_fragments
        for record in adapted_records
        for fragment in record["relevant_chunk_ids"]
    )


def test_all_eligibility_flags_are_false(adapted_records) -> None:
    for record in adapted_records:
        assert record["official_evaluation_eligible"] is False
        assert record["used_for_official_metrics"] is False
        assert record["human_review_completed"] is False
        assert record["evaluation_dataset_type"] == EVALUATION_DATASET_TYPE
        assert record["b3_adapter_version"] == ADAPTER_VERSION


def test_empty_reviewed_text_is_rejected(source_records, inventory, excluded_ids) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[0]["reviewed_query_text"] = "  "
    with pytest.raises(ValueError, match="reviewed_query_text must be non-empty"):
        _adapt(invalid, inventory, excluded_ids)


def test_empty_reviewed_fragments_are_rejected(
    source_records, inventory, excluded_ids
) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[0]["reviewed_relevant_fragments"] = []
    with pytest.raises(ValueError, match="reviewed_relevant_fragments must be a non-empty list"):
        _adapt(invalid, inventory, excluded_ids)


def test_duplicate_id_is_rejected(source_records, inventory, excluded_ids) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[1]["query_id"] = invalid[0]["query_id"]
    with pytest.raises(ValueError, match="duplicate query_id"):
        _adapt(invalid, inventory, excluded_ids)


def test_invalid_language_is_rejected(source_records, inventory, excluded_ids) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[0]["language"] = "fr"
    with pytest.raises(ValueError, match="language must be one of es, en, ru"):
        _adapt(invalid, inventory, excluded_ids)


def test_invalid_category_is_rejected(source_records, inventory, excluded_ids) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[0]["reviewed_category"] = "not-a-category"
    with pytest.raises(ValueError, match="17-category vocabulary"):
        _adapt(invalid, inventory, excluded_ids)


def test_unknown_fragment_is_rejected(source_records, inventory, excluded_ids) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[0]["reviewed_relevant_fragments"] = ["Unknown::999"]
    with pytest.raises(ValueError, match="reviewed fragments are not active"):
        _adapt(invalid, inventory, excluded_ids)


def test_official_metrics_true_is_rejected(
    source_records, inventory, excluded_ids
) -> None:
    invalid = copy.deepcopy(source_records)
    invalid[0]["used_for_official_metrics"] = True
    with pytest.raises(ValueError, match="used_for_official_metrics must be false"):
        _adapt(invalid, inventory, excluded_ids)


def test_manifest_and_diagnostics_match_jsonl(adapted_records, excluded_ids) -> None:
    output = load_jsonl(OUTPUT_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    diagnostics = json.loads(DIAGNOSTICS_PATH.read_text(encoding="utf-8"))
    languages = dict(sorted(Counter(record["lang"] for record in output).items()))
    categories = dict(sorted(Counter(record["category"] for record in output).items()))
    multi_fragment = sum(len(record["relevant_chunk_ids"]) > 1 for record in output)

    assert output == adapted_records
    assert manifest["dataset_type"] == DATASET_TYPE
    assert manifest["total_records"] == diagnostics["total_records"] == len(output)
    assert manifest["accepted_records"] == 15
    assert manifest["revised_records"] == 99
    assert manifest["pending_excluded"] == len(excluded_ids) == 18
    assert manifest["rejected_excluded"] == 0
    assert manifest["languages"] == diagnostics["languages"] == languages
    assert manifest["categories"] == diagnostics["categories"] == categories
    assert manifest["multi_fragment_records"] == diagnostics["multi_fragment_records"] == multi_fragment
    assert manifest["adapter_version"] == diagnostics["adapter_version"] == "v1"
    assert manifest["field_mapping"] == FIELD_MAPPING
    assert set(manifest["source_inputs"]) == {
        "reviewed_jsonl",
        "reviewed_manifest",
        "reviewed_diagnostics",
        "active_inventory",
    }
    assert all(
        manifest[field] is diagnostics["eligibility_flags"][field] is False
        for field in (
            "official_evaluation_eligible",
            "used_for_official_metrics",
            "human_review_completed",
        )
    )
    assert diagnostics["valid"] is True
    assert diagnostics["errors"] == []
    assert diagnostics["unique_ids"] == len(output)
    assert diagnostics["expected_excluded_ids"] == list(excluded_ids)
    assert diagnostics["excluded_ids_present"] == []
    assert all(diagnostics["invariants"].values())


def test_output_hash_matches_manifest_and_diagnostics() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    diagnostics = json.loads(DIAGNOSTICS_PATH.read_text(encoding="utf-8"))
    actual_hash = sha256_file(OUTPUT_PATH)
    assert manifest["sha256"] == diagnostics["output_sha256"] == actual_hash


def test_regeneration_is_deterministic(source_records, inventory, excluded_ids) -> None:
    first = serialize_jsonl(_adapt(source_records, inventory, excluded_ids))
    second = serialize_jsonl(_adapt(source_records, inventory, excluded_ids))
    assert first == second == OUTPUT_PATH.read_bytes()