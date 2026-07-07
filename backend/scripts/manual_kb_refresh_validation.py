#!/usr/bin/env python3
"""Manual end-to-end validation for KB refresh scheduler with force=True."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from enhanced_rag import EnhancedRAGModule
from kb_refresh import KnowledgeBaseRefresher
from kb_scheduler import KnowledgeRefreshScheduler
from retrieval.chunks import build_chunks_from_library


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _count_versions(base: Path):
    if not base.exists():
        return 0
    return sum(1 for _ in base.rglob("*.json"))


def _wait_for_api(base_url: str, timeout_seconds: int = 20) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            r = requests.get(f"{base_url}/api/status", timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def _measure_api_latency(base_url: str, samples: int, gap_seconds: float) -> dict:
    latencies_ms = []
    success = 0
    errors = 0
    for _ in range(samples):
        start = time.perf_counter()
        try:
            r = requests.get(f"{base_url}/api/status", timeout=1.5)
            elapsed = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(elapsed)
            if r.status_code == 200:
                success += 1
            else:
                errors += 1
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(elapsed)
            errors += 1
        time.sleep(gap_seconds)

    return {
        "samples": samples,
        "success": success,
        "errors": errors,
        "avg_ms": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else None,
        "max_ms": round(max(latencies_ms), 2) if latencies_ms else None,
        "min_ms": round(min(latencies_ms), 2) if latencies_ms else None,
    }


def _measure_api_latency_during_refresh(project_root: Path, base_url: str) -> dict:
    refresher = KnowledgeBaseRefresher(project_root=project_root, rag_module=EnhancedRAGModule())
    refresh_output = {}

    def _run_refresh():
        refresh_output["summary"] = refresher.run_refresh(force=True)

    t = threading.Thread(target=_run_refresh, daemon=True)
    t.start()

    during = _measure_api_latency(base_url, samples=14, gap_seconds=0.2)

    t.join(timeout=90)
    return {
        **during,
        "refresh_completed": "summary" in refresh_output,
    }


def main():
    backend_dir = Path(__file__).resolve().parent.parent
    project_root = backend_dir.parent
    data_dir = project_root / "data"
    base_url = "http://127.0.0.1:8000"

    if not _wait_for_api(base_url):
        print(json.dumps({"error": "API not reachable on http://127.0.0.1:8000"}, ensure_ascii=False, indent=2))
        return

    probe_file = project_root / "frontend" / "refresh_probe.html"
    probe_file.write_text("<html><body>refresh probe v1</body></html>", encoding="utf-8")

    rag = EnhancedRAGModule()
    refresher = KnowledgeBaseRefresher(project_root=project_root, rag_module=rag)

    # Add two controlled sources to the current registry for deterministic end-to-end checks.
    registry_seed = _read_json(data_dir / "source_registry.json", [])
    ids = {r.get("source_id") for r in registry_seed}
    if "local_static_index" not in ids:
        registry_seed.append(
            {
                "source_id": "local_static_index",
                "url": f"{base_url}/frontend/index.html",
                "domain": "127.0.0.1",
                "type": "service_page",
                "category": "stable",
                "confidence": 1.0,
                "status": "active",
                "hash_current": "",
                "last_checked": None,
                "last_updated": None,
                "fail_count": 0,
                "active_version": None,
                "check_interval_hours": 1,
                "target_source": "LOCAL_STATIC",
                "target_section_title": "Local static refresh",
            }
        )
    if "local_refresh_probe" not in ids:
        registry_seed.append(
            {
                "source_id": "local_refresh_probe",
                "url": f"{base_url}/frontend/refresh_probe.html",
                "domain": "127.0.0.1",
                "type": "service_page",
                "category": "stable",
                "confidence": 1.0,
                "status": "active",
                "hash_current": "",
                "last_checked": None,
                "last_updated": None,
                "fail_count": 0,
                "active_version": None,
                "check_interval_hours": 1,
                "target_source": "LOCAL_REFRESH_PROBE",
                "target_section_title": "Local probe refresh",
            }
        )
    with (data_dir / "source_registry.json").open("w", encoding="utf-8") as f:
        json.dump(registry_seed, f, ensure_ascii=False, indent=2)

    registry_before = _read_json(data_dir / "source_registry.json", [])
    versions_before = _count_versions(data_dir / "kb_versions")

    baseline_api = _measure_api_latency(base_url, samples=8, gap_seconds=0.2)

    # Run #1 force=True on current registry.
    run1 = refresher.run_refresh(force=True)

    # Run #2 force=True should mostly be unchanged for stable content.
    run2 = refresher.run_refresh(force=True)

    # Explicit before/after updated case: modify a controlled source content.
    probe_file.write_text("<html><body>refresh probe v2 changed</body></html>", encoding="utf-8")
    run3 = refresher.run_refresh(category="stable", force=True)

    versions_after = _count_versions(data_dir / "kb_versions")
    registry_after = _read_json(data_dir / "source_registry.json", [])

    # Validate inactive sections are excluded from chunking/retrieval path.
    chunks = build_chunks_from_library(rag.document_library)
    inactive_count = 0
    active_count = 0
    chunks_for_target = 0
    if "LOCAL_REFRESH_PROBE" in rag.document_library.documents:
        sections = rag.document_library.documents["LOCAL_REFRESH_PROBE"].get("sections", [])
        inactive_count = sum(1 for s in sections if s.get("is_active") is False)
        active_count = sum(1 for s in sections if s.get("is_active") is not False)
        chunks_for_target = sum(1 for c in chunks if c.source == "LOCAL_REFRESH_PROBE")

    # Concurrency safety check: two concurrent force refresh calls should not corrupt JSON.
    concurrent_results = []

    def _worker():
        concurrent_results.append(refresher.run_refresh(force=True))

    t1 = threading.Thread(target=_worker, daemon=True)
    t2 = threading.Thread(target=_worker, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=120)
    t2.join(timeout=120)

    # Parse sanity after concurrent runs.
    concurrent_parse_ok = True
    for p in (
        data_dir / "source_registry.json",
        data_dir / "candidate_sources.json",
        data_dir / "refresh_log.json",
    ):
        try:
            _ = _read_json(p, None)
            if _ is None:
                concurrent_parse_ok = False
        except Exception:
            concurrent_parse_ok = False

    # Duplicate-job mitigation check.
    scheduler_a = KnowledgeRefreshScheduler(refresher, critical_hours=6, faq_admission_hours=24, stable_hours=168)
    scheduler_b = KnowledgeRefreshScheduler(refresher, critical_hours=6, faq_admission_hours=24, stable_hours=168)
    scheduler_a.start()
    time.sleep(0.15)
    scheduler_b.start()
    time.sleep(0.15)
    leader_a = scheduler_a.is_leader
    leader_b = scheduler_b.is_leader
    scheduler_a.stop()
    scheduler_b.stop()

    api_latency = _measure_api_latency_during_refresh(project_root, base_url)

    report = {
        "run1": run1,
        "run2": run2,
        "run3_forced_update": run3,
        "controlled_update_source_id": "local_refresh_probe",
        "baseline_api_latency": baseline_api,
        "versions_before": versions_before,
        "versions_after": versions_after,
        "new_versions_created": max(0, versions_after - versions_before),
        "inactive_sections_count": inactive_count,
        "active_sections_count": active_count,
        "chunks_for_target_source": chunks_for_target,
        "inactive_excluded_from_chunks": (chunks_for_target == active_count),
        "registry_source_count_before": len(registry_before),
        "registry_source_count_after": len(registry_after),
        "concurrent_runs": {
            "runs": len(concurrent_results),
            "json_parse_ok_after": concurrent_parse_ok,
        },
        "scheduler_leader_lock": {
            "scheduler_a_leader": leader_a,
            "scheduler_b_leader": leader_b,
            "single_leader": (leader_a != leader_b),
        },
        "api_latency_during_refresh": api_latency,
        "timestamp": time.time(),
    }

    output_path = data_dir / "refresh_validation_report.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
