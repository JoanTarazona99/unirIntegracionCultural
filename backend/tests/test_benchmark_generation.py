"""Offline tests for deterministic extended benchmark generation."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from eval.benchmark_generation_config import (
    ANNOTATION_STATUS,
    CATEGORY_TARGETS,
    DEFAULT_SEED,
    LANGUAGE_TARGETS,
    LEGACY_STATUS,
    TOPICS,
    TopicSpec,
)
from eval.generate_extended_benchmark import (
    SCHEMA_VERSION,
    generate_records,
    validate_records,
    write_outputs,
)
from eval.benchmark import load_benchmark


def test_generation_is_deterministic_and_meets_targets():
    fragment_ids = [topic.fragment_id for topic in TOPICS]
    first = generate_records(fragment_ids, seed=DEFAULT_SEED)
    second = generate_records(fragment_ids, seed=DEFAULT_SEED)

    assert first == second
    assert len(first) == 132
    assert Counter(record["language"] for record in first) == LANGUAGE_TARGETS
    assert Counter(record["category"] for record in first) == CATEGORY_TARGETS
    assert len({record["query_id"] for record in first}) == 132
    assert len({record["query_text"] for record in first}) == 132


def test_generated_records_follow_schema_and_use_binary_relevance():
    fragment_ids = [topic.fragment_id for topic in TOPICS]
    records = generate_records(fragment_ids, seed=DEFAULT_SEED)
    diagnostics = validate_records(records, fragment_ids)

    assert diagnostics["valid"] is True
    assert diagnostics["errors"] == []
    assert diagnostics["referenced_fragments"] == 44
    for record in records:
        assert record["language"] in {"es", "en", "ru"}
        assert record["query_text"].endswith("?")
        assert len(record["relevant_fragments"]) == 1
        assert record["annotation_type"] == "synthetic_binary"
        assert record["annotation_status"] == ANNOTATION_STATUS
        assert record["used_for_official_metrics"] is False
        assert record["status"] == LEGACY_STATUS
        assert record["id"] == record["query_id"]
        assert record["question"] == record["query_text"]
        assert record["relevant_chunk_ids"] == record["relevant_fragments"]


def test_generation_rejects_corpus_configuration_drift():
    fragment_ids = [topic.fragment_id for topic in TOPICS]
    with pytest.raises(ValueError, match="Corpus/config mismatch"):
        generate_records(fragment_ids[:-1], seed=DEFAULT_SEED)
    with pytest.raises(ValueError, match="Corpus/config mismatch"):
        generate_records(fragment_ids + ["unexpected::0"], seed=DEFAULT_SEED)


def test_validation_reports_invalid_records():
    record = {
        "query_id": "q001",
        "query_text": "short",
        "language": "de",
        "category": "",
        "relevant_fragments": [],
        "annotation_type": "expert",
        "status": "approved",
    }
    diagnostics = validate_records([record, record], {"doc::0"})

    assert diagnostics["valid"] is False
    assert any("duplicate query_id" in error for error in diagnostics["errors"])
    assert any("invalid language" in error for error in diagnostics["errors"])
    assert any("relevant_fragments must be non-empty" in error for error in diagnostics["errors"])

    missing_fields = validate_records([{}], {"doc::0"})
    assert missing_fields["valid"] is False
    assert missing_fields["languages"] == {"<invalid>": 1}
    assert missing_fields["categories"] == {"<invalid>": 1}


@pytest.mark.parametrize(
    ("field", "invalid_value", "expected_error"),
    (
        ("annotation_status", None, "annotation_status must be"),
        ("annotation_status", "approved", "annotation_status must be"),
        ("used_for_official_metrics", None, "used_for_official_metrics must be false"),
        ("used_for_official_metrics", True, "used_for_official_metrics must be false"),
    ),
)
def test_validation_requires_synthetic_review_and_official_exclusion(
    field, invalid_value, expected_error
):
    fragment_ids = [topic.fragment_id for topic in TOPICS]
    record = generate_records(fragment_ids, seed=DEFAULT_SEED)[0]
    if invalid_value is None:
        record.pop(field)
    else:
        record[field] = invalid_value

    diagnostics = validate_records([record], fragment_ids)

    assert diagnostics["valid"] is False
    assert any(expected_error in error for error in diagnostics["errors"])


def test_write_outputs_builds_consistent_manifest_and_diagnostics(tmp_path):
    topics = (
        TopicSpec("source::0", "education", "la admisión", "admission", "поступление"),
        TopicSpec("source::1", "housing", "el alojamiento", "housing", "жильё"),
    )
    fragment_ids = [topic.fragment_id for topic in topics]
    records = generate_records(
        fragment_ids,
        seed=7,
        topics=topics,
        languages=("es", "en", "ru"),
    )
    diagnostics = validate_records(records, fragment_ids)
    benchmark = tmp_path / "benchmark_extended.jsonl"
    manifest_path = tmp_path / "benchmark_extended.manifest.json"
    diagnostics_path = tmp_path / "benchmark_extended_diagnostics.json"

    outputs = write_outputs(
        records,
        diagnostics,
        benchmark_path=benchmark,
        manifest_path=manifest_path,
        diagnostics_path=diagnostics_path,
        source_count=1,
        fragment_count=2,
        seed=7,
    )

    parsed_records = [json.loads(line) for line in benchmark.read_text(encoding="utf-8").splitlines()]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    saved_diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    assert parsed_records == records
    assert manifest == outputs["manifest"]
    assert manifest["total_queries"] == 6
    assert manifest["languages"] == {"en": 2, "es": 2, "ru": 2}
    assert manifest["categories"] == {"education": 3, "housing": 3}
    assert manifest["source_count"] == 1
    assert manifest["active_fragment_count"] == 2
    assert manifest["annotation_status"] == ANNOTATION_STATUS
    assert manifest["used_for_official_metrics"] is False
    assert manifest["official_evaluation_eligible"] is False
    assert saved_diagnostics["valid"] is True
    assert saved_diagnostics["annotation_status"] == ANNOTATION_STATUS
    assert saved_diagnostics["used_for_official_metrics"] is False
    assert saved_diagnostics["official_evaluation_eligible"] is False
    loaded = load_benchmark(benchmark)
    assert [item.id for item in loaded] == [record["query_id"] for record in records]


def test_checked_in_outputs_match_generator_and_manifest_hash():
    repository_dir = Path(__file__).resolve().parents[2]
    benchmark_path = repository_dir / "data" / "eval" / "benchmark_extended.jsonl"
    manifest_path = repository_dir / "data" / "eval" / "benchmark_extended.manifest.json"
    diagnostics_path = repository_dir / "data" / "eval" / "benchmark_extended_diagnostics.json"

    records = [
        json.loads(line)
        for line in benchmark_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_records = generate_records(
        [topic.fragment_id for topic in TOPICS], seed=DEFAULT_SEED
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    benchmark_hash = hashlib.sha256(benchmark_path.read_bytes()).hexdigest()

    assert records == expected_records
    assert manifest["benchmark_version"] == "kubgu-retrieval-synthetic-v2"
    assert manifest["schema"] == SCHEMA_VERSION
    assert manifest["sha256"] == benchmark_hash
    assert manifest["total_queries"] == len(records) == 132
    assert manifest["languages"] == diagnostics["languages"] == LANGUAGE_TARGETS
    assert manifest["categories"] == diagnostics["categories"] == CATEGORY_TARGETS
    for payload in (manifest, diagnostics):
        assert payload["annotation_status"] == ANNOTATION_STATUS
        assert payload["used_for_official_metrics"] is False
        assert payload["official_evaluation_eligible"] is False


def test_writer_refuses_invalid_benchmark(tmp_path):
    with pytest.raises(ValueError, match="Refusing to write"):
        write_outputs(
            [],
            {"valid": False},
            benchmark_path=tmp_path / "benchmark.jsonl",
            manifest_path=tmp_path / "manifest.json",
            diagnostics_path=tmp_path / "diagnostics.json",
            source_count=0,
            fragment_count=0,
            seed=1,
        )
