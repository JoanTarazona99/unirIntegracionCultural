"""
Chunk model and helpers for the retrieval stack.

A ``Chunk`` is the atomic retrievable unit. Chunks are built from the existing
``OfficialDocumentLibrary`` (see backend/enhanced_rag.py) so retrieval operates
over exactly the same corpus as the production keyword search, enabling a fair
baseline-vs-hybrid comparison.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Matches word characters across scripts (Latin + Cyrillic), so tokenization
# works for both Spanish/English and Russian content.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    """Lowercase, Unicode-aware word tokenizer (Latin + Cyrillic friendly)."""
    if not text:
        return []
    return _TOKEN_RE.findall(text.lower())


@dataclass
class Chunk:
    """A single retrievable document chunk with a stable identifier."""

    id: str
    source: str
    title: str
    content: str
    source_url: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Concatenated title + content used for indexing and embeddings."""
        return f"{self.title}\n{self.content}".strip()

    def to_result_dict(self, relevance: float, search_mode: str) -> Dict:
        """Render as the dict shape expected by the rest of the RAG pipeline."""
        return {
            "id": self.id,
            "source": self.source,
            "source_url": self.source_url,
            "title": self.title,
            "content": self.content.strip(),
            "relevance": float(relevance),
            "search_mode": search_mode,
        }


def build_chunks_from_flat(flat_documents: List[Dict]) -> List[Chunk]:
    """Build chunks from ``OfficialDocumentLibrary._flatten_documents`` output."""
    chunks: List[Chunk] = []
    per_source_index: Dict[str, int] = {}
    for doc in flat_documents:
        source = doc.get("source", "unknown")
        idx = per_source_index.get(source, 0)
        per_source_index[source] = idx + 1
        chunks.append(
            Chunk(
                id=f"{source}::{idx}",
                source=source,
                title=doc.get("title", "") or "",
                content=(doc.get("content", "") or "").strip(),
                source_url=doc.get("source_url"),
            )
        )
    return chunks


def build_chunks_from_library(library) -> List[Chunk]:
    """
    Build chunks from an ``OfficialDocumentLibrary`` instance.

    Uses the library's flattening when available, otherwise walks the nested
    ``documents`` structure directly. Chunk IDs are stable (``source::index``)
    so a benchmark can reference gold chunks reliably.
    """
    # Prefer the library's own flattening for a single source of truth.
    flatten = getattr(library, "_flatten_documents", None)
    flat = getattr(library, "flat_documents", None)
    if callable(flatten):
        try:
            flatten()
            flat = getattr(library, "flat_documents", None)
        except Exception:
            flat = None
    if flat:
        return build_chunks_from_flat(flat)

    # Fallback: walk the nested documents dict.
    chunks: List[Chunk] = []
    documents = getattr(library, "documents", {}) or {}
    for source, doc in documents.items():
        url = doc.get("url")
        for idx, section in enumerate(doc.get("sections", [])):
            if section.get("is_active") is False:
                continue
            chunks.append(
                Chunk(
                    id=f"{source}::{idx}",
                    source=source,
                    title=section.get("title", "") or "",
                    content=(section.get("content", "") or "").strip(),
                    source_url=url,
                )
            )
    return chunks
