"""
Benchmark loader for the KubGU-RAG domain evaluation set.

The benchmark is a JSONL file where each line is one query with its gold
relevant chunk IDs. Chunk IDs use the stable ``source::index`` scheme produced
by ``retrieval.build_chunks_from_library``.

Schema (one JSON object per line):
    {
      "id": "q001",
      "question": "¿Cuánto tiempo tengo para registrarme al llegar a Rusia?",
      "lang": "es",
      "category": "migration",
      "relevant_chunk_ids": ["МВД РФ::0"],
      "notes": "optional free text / gold answer reference"
    }
"""

from __future__ import annotations

import json
import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class BenchmarkItem:
    """A single evaluation query with its gold relevant chunks."""

    id: str
    question: str
    lang: str
    category: str
    relevant_chunk_ids: List[str]
    notes: str = ""
    metadata: dict = field(default_factory=dict)


class BenchmarkValidationError(ValueError):
    """Raised when a benchmark does not satisfy the evaluation schema."""


REQUIRED_FIELDS = (
    "id",
    "question",
    "lang",
    "category",
    "relevant_chunk_ids",
)


def benchmark_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest of a benchmark file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_benchmark(
    path: str | Path,
    *,
    allow_unlabeled: bool = False,
) -> List[BenchmarkItem]:
    """Load and validate a JSONL benchmark file.

    Empty relevance lists are accepted only when ``allow_unlabeled`` is true;
    the evaluator records and excludes those queries from metric aggregates.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    items: List[BenchmarkItem] = []
    seen_ids = set()
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - data guard
                raise BenchmarkValidationError(
                    f"Invalid JSON on line {line_no} of {path}: {exc}"
                ) from exc

            if not isinstance(obj, dict):
                raise BenchmarkValidationError(
                    f"Line {line_no} of {path} must contain a JSON object"
                )
            missing = [field for field in REQUIRED_FIELDS if field not in obj]
            if missing:
                raise BenchmarkValidationError(
                    f"Line {line_no} of {path} is missing fields: {', '.join(missing)}"
                )

            item_id = obj["id"]
            if not isinstance(item_id, str) or not item_id.strip():
                raise BenchmarkValidationError(
                    f"Line {line_no} of {path} has an invalid id"
                )
            if item_id in seen_ids:
                raise BenchmarkValidationError(
                    f"Duplicate benchmark id '{item_id}' on line {line_no}"
                )
            seen_ids.add(item_id)

            for field_name in ("question", "lang", "category"):
                value = obj[field_name]
                if not isinstance(value, str) or not value.strip():
                    raise BenchmarkValidationError(
                        f"Benchmark item '{item_id}' has an invalid {field_name}"
                    )

            relevant = obj["relevant_chunk_ids"]
            if not isinstance(relevant, list) or not all(
                isinstance(chunk_id, str) and chunk_id.strip()
                for chunk_id in relevant
            ):
                raise BenchmarkValidationError(
                    f"Benchmark item '{item_id}' has invalid relevant_chunk_ids"
                )
            if len(relevant) != len(set(relevant)):
                raise BenchmarkValidationError(
                    f"Benchmark item '{item_id}' has duplicate relevant_chunk_ids"
                )
            if not relevant and not allow_unlabeled:
                raise BenchmarkValidationError(
                    f"Benchmark item '{obj.get('id', line_no)}' has no relevant_chunk_ids"
                )
            items.append(
                BenchmarkItem(
                    id=item_id,
                    question=obj["question"],
                    lang=obj["lang"],
                    category=obj["category"],
                    relevant_chunk_ids=list(relevant),
                    notes=obj.get("notes", ""),
                    metadata=obj.get("metadata", {}),
                )
            )
    return items


def filter_benchmark(
    items: Iterable[BenchmarkItem],
    *,
    language: Optional[str] = None,
    category: Optional[str] = None,
) -> List[BenchmarkItem]:
    """Filter benchmark items by exact language and category labels."""
    return [
        item
        for item in items
        if (language is None or item.lang == language)
        and (category is None or item.category == category)
    ]


def summarize_benchmark(items: Iterable[BenchmarkItem]) -> dict:
    """Return machine-readable benchmark counts."""
    item_list = list(items)
    return {
        "total_queries": len(item_list),
        "labeled_queries": sum(bool(item.relevant_chunk_ids) for item in item_list),
        "unlabeled_queries": sum(not item.relevant_chunk_ids for item in item_list),
        "languages": dict(sorted(Counter(item.lang for item in item_list).items())),
        "categories": dict(
            sorted(Counter(item.category for item in item_list).items())
        ),
        "relevance_labels": sum(
            len(item.relevant_chunk_ids) for item in item_list
        ),
    }
