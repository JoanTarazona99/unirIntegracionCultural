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
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


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


def load_benchmark(path: str | Path) -> List[BenchmarkItem]:
    """Load and validate a JSONL benchmark file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    items: List[BenchmarkItem] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - data guard
                raise ValueError(
                    f"Invalid JSON on line {line_no} of {path}: {exc}"
                ) from exc

            relevant = obj.get("relevant_chunk_ids") or []
            if not relevant:
                raise ValueError(
                    f"Benchmark item '{obj.get('id', line_no)}' has no relevant_chunk_ids"
                )
            items.append(
                BenchmarkItem(
                    id=str(obj.get("id", line_no)),
                    question=obj["question"],
                    lang=obj.get("lang", "es"),
                    category=obj.get("category", "general"),
                    relevant_chunk_ids=list(relevant),
                    notes=obj.get("notes", ""),
                    metadata=obj.get("metadata", {}),
                )
            )
    return items
