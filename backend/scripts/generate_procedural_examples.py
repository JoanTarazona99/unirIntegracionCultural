"""Generate deterministic, corpus-grounded procedural examples offline."""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from atomic_json import atomic_write_json
from enhanced_rag import EnhancedRAGModule
from procedural import ProcedureEvaluator, ProcedureGenerator
from retrieval.chunks import build_chunks_from_library


EXAMPLE_SPECS = (
    {
        "filename": "migration_registration.json",
        "procedure_type": "registration",
        "query": "¿Cómo hago el registro migratorio después de llegar a Rusia?",
        "chunk_ids": ("МВД РФ::0", "МФЦ::0"),
        "profile": {
            "country": "Vietnam",
            "visa_type": "student",
            "russian_level": "A1",
        },
    },
    {
        "filename": "university_enrollment.json",
        "procedure_type": "enrollment",
        "query": "¿Cómo completo la matrícula como estudiante extranjero en KubGU?",
        "chunk_ids": ("КубГУ::0", "КубГУ::4", "Документы::0"),
        "profile": {
            "country": "Vietnam",
            "visa_type": "student",
            "russian_level": "A1",
            "academic_level": "bachelor",
        },
    },
    {
        "filename": "student_visa.json",
        "procedure_type": "visa",
        "query": "¿Qué necesito para solicitar y prorrogar una visa de estudiante?",
        "chunk_ids": ("Госуслуги::2", "МВД РФ::1", "ГУВМ МВД::1"),
        "profile": {
            "country": "Vietnam",
            "visa_type": "student",
            "russian_level": "A1",
        },
    },
)


def _sha256_payload(payload: dict) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def generate(output_dir: Path) -> dict:
    rag = EnhancedRAGModule(use_llm=False, project_root=PROJECT_ROOT)
    chunks = {
        chunk.id: chunk
        for chunk in build_chunks_from_library(rag.document_library)
    }
    generator = ProcedureGenerator()
    evaluator = ProcedureEvaluator()
    manifest_files = []

    for spec in EXAMPLE_SPECS:
        selected = []
        for chunk_id in spec["chunk_ids"]:
            if chunk_id not in chunks:
                raise RuntimeError(f"Required chunk not found: {chunk_id}")
            selected.append(chunks[chunk_id])
        correlation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, spec["query"]))
        recommendation = generator.generate_steps(
            spec["procedure_type"],
            selected,
            spec["profile"],
            retrieval_mode="curated_active_corpus",
            correlation_id=correlation_id,
        )
        evaluation = evaluator.evaluate(recommendation)
        if not evaluation.sufficient:
            raise RuntimeError(
                f"Example {spec['filename']} is insufficient: {evaluation.reasons}"
            )
        payload = {
            "query": spec["query"],
            "selection_mode": "curated_active_corpus",
            "source_chunk_ids": list(spec["chunk_ids"]),
            "recommendation": recommendation.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "limitations": [
                "Corpus-grounded example; not legal advice or live-source validation.",
                "Usefulness has not been evaluated by human participants.",
            ],
        }
        target = output_dir / spec["filename"]
        atomic_write_json(target, payload)
        manifest_files.append(
            {
                "path": spec["filename"],
                "sha256": _sha256_payload(payload),
                "correlation_id": correlation_id,
                "source_chunk_ids": list(spec["chunk_ids"]),
            }
        )

    manifest = {
        "schema_version": "procedural-examples-v1",
        "generation_mode": "offline_deterministic",
        "llm_used": False,
        "network_used": False,
        "examples": manifest_files,
    }
    atomic_write_json(output_dir / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    generated = generate(PROJECT_ROOT / "data" / "procedural" / "examples")
    print(json.dumps(generated, ensure_ascii=True, indent=2))