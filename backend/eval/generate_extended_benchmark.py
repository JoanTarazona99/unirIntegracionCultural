"""Generate a deterministic, corpus-grounded synthetic benchmark offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Sequence

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPOSITORY_DIR = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from eval.benchmark_generation_config import (  # noqa: E402
    ANNOTATION_STATUS,
    CATEGORY_TARGETS,
    DEFAULT_SEED,
    GENERATOR_VERSION,
    LANGUAGES,
    LANGUAGE_TARGETS,
    LEGACY_STATUS,
    QUESTION_TEMPLATES,
    TOPICS,
    TopicSpec,
)

DEFAULT_OUTPUT = _REPOSITORY_DIR / "data" / "eval" / "benchmark_extended.jsonl"
DEFAULT_MANIFEST = (
    _REPOSITORY_DIR / "data" / "eval" / "benchmark_extended.manifest.json"
)
DEFAULT_DIAGNOSTICS = (
    _REPOSITORY_DIR / "data" / "eval" / "benchmark_extended_diagnostics.json"
)
SCHEMA_VERSION = "kubgu-synthetic-retrieval-jsonl-v2"
ALLOWED_LANGUAGES = set(LANGUAGES)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _topic_text(topic: TopicSpec, language: str) -> str:
    return str(getattr(topic, language))


def _has_expected_language_shape(text: str, language: str) -> bool:
    if language == "es":
        return text.startswith("¿") and text.endswith("?")
    if language == "en":
        return text.startswith("What ") and text.endswith("?")
    if language == "ru":
        letters = [character for character in text if character.isalpha()]
        cyrillic = [character for character in letters if "а" <= character.lower() <= "я"]
        return text.endswith("?") and bool(letters) and len(cyrillic) / len(letters) >= 0.7
    return False


def generate_records(
    fragment_ids: Iterable[str],
    *,
    seed: int = DEFAULT_SEED,
    topics: Sequence[TopicSpec] = TOPICS,
    languages: Sequence[str] = LANGUAGES,
) -> list[dict]:
    """Create one grounded synthetic question per topic and language."""
    available_ids = set(fragment_ids)
    configured_ids = {topic.fragment_id for topic in topics}
    if len(configured_ids) != len(topics):
        raise ValueError("Topic configuration contains duplicate fragment IDs")
    missing = sorted(configured_ids - available_ids)
    unexpected = sorted(available_ids - configured_ids)
    if missing or unexpected:
        raise ValueError(
            f"Corpus/config mismatch: missing={missing}, unexpected={unexpected}"
        )
    if not languages or any(language not in ALLOWED_LANGUAGES for language in languages):
        raise ValueError(f"Languages must be selected from {sorted(ALLOWED_LANGUAGES)}")

    generator = random.Random(seed)
    records = []
    for language in languages:
        for topic in topics:
            templates = QUESTION_TEMPLATES[language]
            template_index = generator.randrange(len(templates))
            question = templates[template_index].format(
                topic=_topic_text(topic, language)
            )
            query_id = f"q{len(records) + 1:03d}"
            notes = (
                "Synthetic template-derived query grounded in the referenced "
                "active fragment; requires human review before inferential use."
            )
            generation_metadata = {
                "generator_version": GENERATOR_VERSION,
                "method": "deterministic_multilingual_templates",
                "seed": seed,
                "template_index": template_index,
                "source_fragment": topic.fragment_id,
            }
            records.append(
                {
                    "query_id": query_id,
                    "query_text": question,
                    "language": language,
                    "category": topic.category,
                    "relevant_fragments": [topic.fragment_id],
                    "annotation_notes": notes,
                    "annotation_type": "synthetic_binary",
                    "annotation_status": ANNOTATION_STATUS,
                    "used_for_official_metrics": False,
                    "status": LEGACY_STATUS,
                    "generation_metadata": generation_metadata,
                    # Backward-compatible aliases for the existing evaluator.
                    "id": query_id,
                    "question": question,
                    "lang": language,
                    "relevant_chunk_ids": [topic.fragment_id],
                    "notes": notes,
                    "metadata": {
                        "annotation_type": "synthetic_binary",
                        "status": LEGACY_STATUS,
                        "generation": generation_metadata,
                    },
                }
            )
    return records


def validate_records(records: Sequence[Mapping], valid_fragment_ids: Iterable[str]) -> dict:
    """Validate schema, uniqueness, language, relevance and corpus references."""
    valid_ids = set(valid_fragment_ids)
    errors = []
    seen_ids = set()
    seen_questions = set()
    for index, record in enumerate(records, start=1):
        query_id = record.get("query_id")
        query_text = record.get("query_text")
        language = record.get("language")
        category = record.get("category")
        relevant = record.get("relevant_fragments")

        if not isinstance(query_id, str) or not query_id.strip():
            errors.append(f"Record {index}: invalid query_id")
        elif query_id in seen_ids:
            errors.append(f"Record {index}: duplicate query_id {query_id}")
        else:
            seen_ids.add(query_id)
        if not isinstance(query_text, str) or len(query_text.strip()) < 20:
            errors.append(f"Record {index}: query_text is empty or too short")
        elif query_text in seen_questions:
            errors.append(f"Record {index}: duplicate query_text")
        else:
            seen_questions.add(query_text)
        if language not in ALLOWED_LANGUAGES:
            errors.append(f"Record {index}: invalid language {language!r}")
        elif isinstance(query_text, str) and not _has_expected_language_shape(
            query_text, language
        ):
            errors.append(f"Record {index}: query_text does not match language shape")
        if not isinstance(category, str) or not category.strip():
            errors.append(f"Record {index}: invalid category")
        if not isinstance(relevant, list) or not relevant:
            errors.append(f"Record {index}: relevant_fragments must be non-empty")
        elif any(fragment_id not in valid_ids for fragment_id in relevant):
            errors.append(f"Record {index}: unknown relevant fragment")
        if record.get("annotation_status") != ANNOTATION_STATUS:
            errors.append(
                f"Record {index}: annotation_status must be {ANNOTATION_STATUS!r}"
            )
        if record.get("used_for_official_metrics") is not False:
            errors.append(
                f"Record {index}: used_for_official_metrics must be false"
            )
        if record.get("status") != LEGACY_STATUS:
            errors.append(f"Record {index}: legacy status alias is not explicit")
        if record.get("annotation_type") != "synthetic_binary":
            errors.append(f"Record {index}: annotation type is not synthetic_binary")
        generation = record.get("generation_metadata")
        if not isinstance(generation, dict) or not {
            "generator_version",
            "method",
            "seed",
            "template_index",
            "source_fragment",
        }.issubset(generation):
            errors.append(f"Record {index}: incomplete generation metadata")
        if record.get("id") != query_id or record.get("question") != query_text:
            errors.append(f"Record {index}: evaluator aliases do not match")
        if record.get("lang") != language or record.get("relevant_chunk_ids") != relevant:
            errors.append(f"Record {index}: evaluator aliases do not match")

    languages = dict(
        sorted(
            Counter(
                value if isinstance(value, str) else "<invalid>"
                for value in (record.get("language") for record in records)
            ).items()
        )
    )
    categories = dict(
        sorted(
            Counter(
                value if isinstance(value, str) else "<invalid>"
                for value in (record.get("category") for record in records)
            ).items()
        )
    )
    return {
        "valid": not errors,
        "errors": errors,
        "total_queries": len(records),
        "languages": languages,
        "categories": categories,
        "unique_query_ids": len(seen_ids),
        "unique_query_texts": len(seen_questions),
        "referenced_fragments": len(
            {
                fragment_id
                for record in records
                for fragment_id in record.get("relevant_fragments", [])
                if fragment_id in valid_ids
            }
        ),
    }


def build_manifest(
    benchmark_path: Path,
    records: Sequence[Mapping],
    diagnostics: Mapping,
    *,
    source_count: int,
    fragment_count: int,
    seed: int,
) -> dict:
    """Build a machine-readable manifest from generated and validated data."""
    return {
        "benchmark_version": "kubgu-retrieval-synthetic-v2",
        "benchmark_file": benchmark_path.name,
        "sha256": _sha256(benchmark_path),
        "schema": SCHEMA_VERSION,
        "total_queries": len(records),
        "languages": diagnostics["languages"],
        "categories": diagnostics["categories"],
        "source_count": source_count,
        "active_fragment_count": fragment_count,
        "relevance": "synthetic binary fragment identifiers",
        "annotation_provenance": "deterministic templates grounded in active corpus fragments",
        "annotation_status": ANNOTATION_STATUS,
        "used_for_official_metrics": False,
        "official_evaluation_eligible": False,
        "generation": {
            "seed": seed,
            "generator_version": GENERATOR_VERSION,
            "method": "deterministic_multilingual_templates",
            "language_targets": LANGUAGE_TARGETS,
            "category_targets": CATEGORY_TARGETS,
        },
    }


def write_outputs(
    records: Sequence[Mapping],
    diagnostics: Mapping,
    *,
    benchmark_path: Path,
    manifest_path: Path,
    diagnostics_path: Path,
    source_count: int,
    fragment_count: int,
    seed: int,
) -> dict:
    """Write JSONL, manifest and diagnostics after successful validation."""
    if not diagnostics.get("valid"):
        raise ValueError("Refusing to write an invalid generated benchmark")
    benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    with benchmark_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = build_manifest(
        benchmark_path,
        records,
        diagnostics,
        source_count=source_count,
        fragment_count=fragment_count,
        seed=seed,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    diagnostic_payload = {
        **diagnostics,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "source_count": source_count,
        "active_fragment_count": fragment_count,
        "language_targets_match": diagnostics["languages"] == LANGUAGE_TARGETS,
        "category_targets_match": diagnostics["categories"] == CATEGORY_TARGETS,
        "human_review_required": True,
        "annotation_status": ANNOTATION_STATUS,
        "used_for_official_metrics": False,
        "official_evaluation_eligible": False,
    }
    diagnostics_path.write_text(
        json.dumps(diagnostic_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"manifest": manifest, "diagnostics": diagnostic_payload}


def _load_active_corpus():
    os.environ["ENABLE_SEMANTIC_SEARCH"] = "0"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from enhanced_rag import OfficialDocumentLibrary
    from retrieval import build_chunks_from_library

    library = OfficialDocumentLibrary()
    chunks = build_chunks_from_library(library)
    return library, chunks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the extended synthetic benchmark")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--diagnostics", default=str(DEFAULT_DIAGNOSTICS))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    library, chunks = _load_active_corpus()
    fragment_ids = [chunk.id for chunk in chunks]
    records = generate_records(fragment_ids, seed=args.seed)
    diagnostics = validate_records(records, fragment_ids)
    if diagnostics["languages"] != LANGUAGE_TARGETS:
        diagnostics["errors"].append("Generated language counts do not match targets")
    if diagnostics["categories"] != CATEGORY_TARGETS:
        diagnostics["errors"].append("Generated category counts do not match targets")
    diagnostics["valid"] = not diagnostics["errors"]
    if not diagnostics["valid"]:
        print(json.dumps(diagnostics, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    outputs = write_outputs(
        records,
        diagnostics,
        benchmark_path=Path(args.output),
        manifest_path=Path(args.manifest),
        diagnostics_path=Path(args.diagnostics),
        source_count=len({chunk.source for chunk in chunks}),
        fragment_count=len(chunks),
        seed=args.seed,
    )
    print(json.dumps(outputs["diagnostics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
