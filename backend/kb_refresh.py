"""
Incremental Knowledge Base refresh engine for official RAG sources.

This module complements reactive integration with a periodic pipeline that:
- refreshes known official sources from a whitelist,
- detects content changes using fingerprints,
- versions updated content,
- avoids duplicate ingestion,
- marks stale/unreachable sources safely,
- triggers incremental reindex only when needed,
- records structured traceability logs and run metrics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import requests


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: str
    ok: bool
    error: Optional[str] = None


class KnowledgeBaseRefresher:
    """Incremental refresh manager for KB sources and candidate discovery."""

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        rag_module=None,
        fetcher: Optional[Callable[[str], FetchResult]] = None,
        max_failures: int = 3,
        min_candidate_confidence: float = 0.75,
        min_content_chars: int = 200,
    ):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.data_dir = self.project_root / "data"
        self.kb_versions_dir = self.data_dir / "kb_versions"

        self.source_registry_path = self.data_dir / "source_registry.json"
        self.candidate_sources_path = self.data_dir / "candidate_sources.json"
        self.refresh_log_path = self.data_dir / "refresh_log.json"
        self.integration_log_path = self.data_dir / "integration_log.json"

        self.rag_module = rag_module
        self.fetcher = fetcher or self._default_fetcher
        self.max_failures = max_failures
        self.min_candidate_confidence = min_candidate_confidence
        self.min_content_chars = min_content_chars

        self.category_default_interval_hours = {
            "critical": 6,
            "faq_admission": 24,
            "stable": 24 * 7,
        }
        self._local_lock = threading.RLock()
        self._state_lock_path = self.data_dir / "kb_refresh.state.lock"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.kb_versions_dir.mkdir(parents=True, exist_ok=True)
        self._bootstrap_files()

    @contextmanager
    def _file_lock(self, lock_path: Path, timeout_seconds: float = 8.0):
        """Cross-process lock via lock-file creation (atomic O_EXCL)."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.time()
        while True:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("utf-8"))
                os.close(fd)
                break
            except FileExistsError:
                # Best-effort stale lock cleanup.
                try:
                    if time.time() - lock_path.stat().st_mtime > 120:
                        lock_path.unlink(missing_ok=True)
                        continue
                except Exception:
                    pass
                if time.time() - start > timeout_seconds:
                    raise TimeoutError(f"Could not acquire lock: {lock_path.name}")
                time.sleep(0.05)

        try:
            yield
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass

    @contextmanager
    def _state_lock(self):
        with self._local_lock:
            with self._file_lock(self._state_lock_path):
                yield

    def _bootstrap_files(self) -> None:
        if not self.source_registry_path.exists():
            self._write_json(self.source_registry_path, self._default_source_registry())
        if not self.candidate_sources_path.exists():
            self._write_json(self.candidate_sources_path, [])
        if not self.refresh_log_path.exists():
            self._write_json(self.refresh_log_path, [])
        if not self.integration_log_path.exists():
            self._write_json(self.integration_log_path, [])

    def _default_source_registry(self) -> List[Dict]:
        return [
            {
                "source_id": "mvd_foreigners",
                "url": "https://xn--b1aew.xn--p1ai",
                "domain": "gu-krasnodar.mvd.ru",
                "type": "migration",
                "category": "critical",
                "confidence": 0.98,
                "fallback_urls": ["https://guvm.mvd.ru"],
                "status": "active",
                "hash_current": "",
                "last_checked": None,
                "last_updated": None,
                "fail_count": 0,
                "active_version": None,
                "check_interval_hours": 6,
                "target_source": "МВД РФ",
                "target_section_title": "Actualizacion oficial: migracion",
            },
            {
                "source_id": "mfc_services",
                "url": "https://mfc.gov.ru",
                "domain": "mfc.gov.ru",
                "type": "public_services",
                "category": "stable",
                "confidence": 0.95,
                "fallback_urls": ["https://www.gosuslugi.ru"],
                "status": "active",
                "hash_current": "",
                "last_checked": None,
                "last_updated": None,
                "fail_count": 0,
                "active_version": None,
                "check_interval_hours": 24 * 7,
                "target_source": "МФЦ",
                "target_section_title": "Actualizacion oficial: MFC servicios",
            },
            {
                "source_id": "kubgu_faq",
                "url": "https://kubsu.ru",
                "domain": "kubsu.ru",
                "type": "faq",
                "category": "faq_admission",
                "confidence": 0.95,
                "fallback_urls": ["https://kubsu.ru/ru"],
                "status": "active",
                "hash_current": "",
                "last_checked": None,
                "last_updated": None,
                "fail_count": 0,
                "active_version": None,
                "check_interval_hours": 24,
                "target_source": "FAQ",
                "target_section_title": "Actualizacion oficial: FAQ KubGU",
            },
            {
                "source_id": "kubgu_admission",
                "url": "https://kubsu.ru",
                "domain": "kubsu.ru",
                "type": "admission",
                "category": "faq_admission",
                "confidence": 0.97,
                "fallback_urls": ["https://kubsu.ru/ru"],
                "status": "active",
                "hash_current": "",
                "last_checked": None,
                "last_updated": None,
                "fail_count": 0,
                "active_version": None,
                "check_interval_hours": 24,
                "target_source": "КубГУ",
                "target_section_title": "Actualizacion oficial: admision",
            },
        ]

    def _read_json(self, path: Path, default):
        lock = path.with_suffix(path.suffix + ".lock")
        with self._local_lock:
            with self._file_lock(lock):
                if not path.exists():
                    return deepcopy(default)
                try:
                    with path.open("r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return deepcopy(default)

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.with_suffix(path.suffix + ".lock")
        with self._local_lock:
            with self._file_lock(lock):
                with path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def _append_json_entry(self, path: Path, entry: Dict) -> None:
        lock = path.with_suffix(path.suffix + ".lock")
        with self._local_lock:
            with self._file_lock(lock):
                rows = []
                if path.exists():
                    try:
                        with path.open("r", encoding="utf-8") as f:
                            rows = json.load(f)
                    except Exception:
                        rows = []
                rows.append(entry)
                with path.open("w", encoding="utf-8") as f:
                    json.dump(rows, f, ensure_ascii=False, indent=2)

    def _default_fetcher(self, url: str) -> FetchResult:
        try:
            response = requests.get(url, timeout=8)
            return FetchResult(
                url=url,
                status_code=response.status_code,
                content=response.text or "",
                ok=200 <= response.status_code < 300,
                error=None,
            )
        except Exception as e:
            return FetchResult(url=url, status_code=0, content="", ok=False, error=str(e))

    def _fetch_with_fallback(self, source: Dict) -> Tuple[FetchResult, str]:
        urls = [source.get("url", "")]
        urls.extend(source.get("fallback_urls", []) or [])

        last_result = FetchResult(url=source.get("url", ""), status_code=0, content="", ok=False, error="no_url")
        for candidate in [u for u in urls if u]:
            result = self.fetcher(candidate)
            if result.ok:
                return result, candidate
            last_result = result
        return last_result, source.get("url", "")

    def _clean_content(self, raw: str) -> str:
        text = raw or ""
        text = re.sub(r"<script[\\s\\S]*?</script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _fingerprint(self, text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def _allowed_domains(self, registry: List[Dict]) -> set:
        return {r.get("domain", "") for r in registry if r.get("domain")}

    def _classify_topic(self, text: str) -> Optional[str]:
        t = (text or "").lower()
        if any(k in t for k in ("visa", "visado", "migr", "регистра", "mvd")):
            return "critical"
        if any(k in t for k in ("faq", "admission", "admis", "matricula", "enroll")):
            return "faq_admission"
        if any(k in t for k in ("service", "mfc", "gosuslugi", "portal")):
            return "stable"
        return None

    def _is_due(self, source: Dict, now: datetime, force: bool) -> bool:
        if force:
            return True
        if source.get("status") in {"retired"}:
            return False

        interval = int(
            source.get("check_interval_hours")
            or self.category_default_interval_hours.get(source.get("category", "stable"), 24)
        )
        last_checked = _parse_iso(source.get("last_checked"))
        if last_checked is None:
            return True
        return now - last_checked >= timedelta(hours=interval)

    def _persist_version(self, source: Dict, cleaned_content: str, fingerprint: str, checked_at: str) -> str:
        source_id = source.get("source_id", "unknown")
        version_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{fingerprint[:10]}"
        source_dir = self.kb_versions_dir / source_id
        source_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "source_id": source_id,
            "url": source.get("url"),
            "domain": source.get("domain"),
            "type": source.get("type"),
            "category": source.get("category"),
            "version_id": version_id,
            "fingerprint": fingerprint,
            "checked_at": checked_at,
            "content": cleaned_content,
        }
        self._write_json(source_dir / f"{version_id}.json", payload)
        return version_id

    def _log_refresh_event(self, event: str, source: Dict, **extra) -> None:
        entry = {
            "timestamp": _utc_now_iso(),
            "event": event,
            "source_id": source.get("source_id"),
            "url": source.get("url"),
            "domain": source.get("domain"),
            "category": source.get("category"),
            "status": source.get("status"),
            **extra,
        }
        self._append_json_entry(self.refresh_log_path, entry)

    def _log_integration_event(self, event: str, source: Dict, **extra) -> None:
        entry = {
            "timestamp": _utc_now_iso(),
            "event": event,
            "kind": "scheduled_refresh",
            "source_id": source.get("source_id"),
            "url": source.get("url"),
            **extra,
        }
        self._append_json_entry(self.integration_log_path, entry)

    def _kb_upsert(self, source: Dict, cleaned_content: str, version_id: str) -> None:
        if self.rag_module is None:
            return
        if hasattr(self.rag_module, "apply_refreshed_source"):
            self.rag_module.apply_refreshed_source(
                source=source,
                content=cleaned_content,
                version_id=version_id,
            )

    def _refresh_single_source(self, source: Dict) -> Tuple[str, Optional[str], Optional[str]]:
        checked_at = _utc_now_iso()
        fetch_result, checked_url = self._fetch_with_fallback(source)
        source["last_checked"] = checked_at
        source["last_success_url"] = checked_url if fetch_result.ok else source.get("last_success_url")

        if not fetch_result.ok:
            source["fail_count"] = int(source.get("fail_count", 0)) + 1
            if source["fail_count"] >= int(source.get("max_failures", self.max_failures)):
                source["status"] = "stale"
            else:
                source["status"] = "unreachable"
            self._log_refresh_event(
                "source_checked",
                source,
                result="failed",
                http_status=fetch_result.status_code,
                checked_url=checked_url,
                error=fetch_result.error,
                fail_count=source["fail_count"],
            )
            return "failed", fetch_result.error, None

        source["fail_count"] = 0
        cleaned = self._clean_content(fetch_result.content)
        if len(cleaned) < self.min_content_chars:
            source["status"] = "unreachable"
            source["fail_count"] = int(source.get("fail_count", 0)) + 1
            self._log_refresh_event(
                "source_checked",
                source,
                result="failed",
                http_status=fetch_result.status_code,
                checked_url=checked_url,
                error="insufficient_content",
                content_chars=len(cleaned),
            )
            return "failed", "insufficient_content", None

        fingerprint = self._fingerprint(cleaned)
        if fingerprint == source.get("hash_current"):
            source["status"] = "active"
            self._log_refresh_event(
                "source_checked",
                source,
                result="unchanged",
                checked_url=checked_url,
                fingerprint=fingerprint,
            )
            return "unchanged", None, None

        old_version = source.get("active_version")
        version_id = self._persist_version(source, cleaned, fingerprint, checked_at)

        source["status"] = "active"
        source["hash_current"] = fingerprint
        source["last_updated"] = checked_at
        source["active_version"] = version_id
        source["archived_version"] = old_version

        self._kb_upsert(source, cleaned, version_id)

        self._log_refresh_event(
            "source_checked",
            source,
            result="updated",
            checked_url=checked_url,
            fingerprint=fingerprint,
            previous_version=old_version,
            active_version=version_id,
        )
        self._log_integration_event(
            "source_updated",
            source,
            previous_version=old_version,
            active_version=version_id,
        )
        return "updated", None, version_id

    def enqueue_candidate_source(
        self,
        *,
        url: str,
        domain: str,
        source_type: str,
        confidence: float,
        discovered_from: str,
        snippet: str = "",
    ) -> Dict:
        candidates = self._read_json(self.candidate_sources_path, [])
        existing = next((c for c in candidates if c.get("url") == url), None)
        if existing:
            return existing

        candidate = {
            "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:12],
            "url": url,
            "domain": domain,
            "type": source_type,
            "confidence": float(confidence),
            "discovered_from": discovered_from,
            "snippet": snippet,
            "status": "pending",
            "created_at": _utc_now_iso(),
            "validated_at": None,
            "validation_reason": None,
        }
        candidates.append(candidate)
        self._write_json(self.candidate_sources_path, candidates)
        return candidate

    def _validate_candidate(self, candidate: Dict, registry: List[Dict]) -> Tuple[bool, str]:
        allowed_domains = self._allowed_domains(registry)
        if candidate.get("domain") not in allowed_domains:
            return False, "domain_not_allowed"
        if float(candidate.get("confidence", 0.0)) < self.min_candidate_confidence:
            return False, "low_confidence"
        if any(r.get("url") == candidate.get("url") for r in registry):
            return False, "duplicate_url"
        topic = self._classify_topic(f"{candidate.get('type', '')} {candidate.get('snippet', '')}")
        if topic is None:
            return False, "invalid_topic"

        fetch_result = self.fetcher(candidate["url"])
        if not fetch_result.ok:
            return False, "source_unreachable"
        cleaned = self._clean_content(fetch_result.content)
        if len(cleaned) < self.min_content_chars:
            return False, "insufficient_content"

        fp = self._fingerprint(cleaned)
        if any(r.get("hash_current") == fp and fp for r in registry):
            return False, "duplicate_content"
        return True, topic

    def process_candidate_sources(self) -> Dict:
        with self._state_lock():
            registry = self._read_json(self.source_registry_path, [])
            candidates = self._read_json(self.candidate_sources_path, [])

            accepted = 0
            rejected = 0

            for candidate in candidates:
                if candidate.get("status") != "pending":
                    continue

                is_valid, reason_or_topic = self._validate_candidate(candidate, registry)
                candidate["validated_at"] = _utc_now_iso()
                if not is_valid:
                    candidate["status"] = "rejected"
                    candidate["validation_reason"] = reason_or_topic
                    rejected += 1
                    self._append_json_entry(
                        self.refresh_log_path,
                        {
                            "timestamp": _utc_now_iso(),
                            "event": "candidate_rejected",
                            "url": candidate.get("url"),
                            "reason": reason_or_topic,
                        },
                    )
                    continue

                category = reason_or_topic
                new_source = {
                    "source_id": f"candidate_{candidate['id']}",
                    "url": candidate["url"],
                    "domain": candidate["domain"],
                    "type": candidate.get("type") or "candidate",
                    "category": category,
                    "confidence": candidate.get("confidence", 0.0),
                    "status": "active",
                    "hash_current": "",
                    "last_checked": None,
                    "last_updated": None,
                    "fail_count": 0,
                    "active_version": None,
                    "check_interval_hours": self.category_default_interval_hours.get(category, 24),
                    "target_source": "FAQ" if category == "faq_admission" else "КубГУ",
                    "target_section_title": "Actualizacion oficial: fuente candidata validada",
                }
                registry.append(new_source)
                candidate["status"] = "accepted"
                candidate["validation_reason"] = "accepted_auto"
                accepted += 1

                self._append_json_entry(
                    self.refresh_log_path,
                    {
                        "timestamp": _utc_now_iso(),
                        "event": "candidate_accepted",
                        "url": candidate.get("url"),
                        "category": category,
                    },
                )

            self._write_json(self.source_registry_path, registry)
            self._write_json(self.candidate_sources_path, candidates)
            return {
                "accepted_candidates": accepted,
                "rejected_candidates": rejected,
            }

    def run_refresh(self, *, category: Optional[str] = None, force: bool = False) -> Dict:
        started = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)

        checked = 0
        updated = 0
        unchanged = 0
        failed = 0
        stale = 0

        changed_sources: List[str] = []
        versions_created: List[Dict] = []

        with self._state_lock():
            registry = self._read_json(self.source_registry_path, [])

            for source in registry:
                if category and source.get("category") != category:
                    continue
                if not self._is_due(source, now, force):
                    continue

                checked += 1
                result, _, version_id = self._refresh_single_source(source)
                if result == "updated":
                    updated += 1
                    changed_sources.append(source.get("target_source") or source.get("source_id"))
                    versions_created.append(
                        {
                            "source_id": source.get("source_id"),
                            "active_version": version_id,
                        }
                    )
                elif result == "unchanged":
                    unchanged += 1
                elif result == "failed":
                    failed += 1
                    if source.get("status") == "stale":
                        stale += 1

            self._write_json(self.source_registry_path, registry)

        # Trigger incremental reindex only if there were changes.
        if changed_sources and self.rag_module is not None and hasattr(self.rag_module, "reindex_sources_incremental"):
            self.rag_module.reindex_sources_incremental(changed_sources)

        candidate_stats = self.process_candidate_sources()

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        run_summary = {
            "timestamp": _utc_now_iso(),
            "event": "reindex_complete",
            "category": category or "all",
            "total_checked": checked,
            "updated": updated,
            "unchanged": unchanged,
            "failed": failed,
            "stale": stale,
            "accepted_candidates": candidate_stats["accepted_candidates"],
            "rejected_candidates": candidate_stats["rejected_candidates"],
            "reindexed_sources": sorted(set(changed_sources)),
            "versions_created": versions_created,
            "duration_seconds": round(duration, 3),
        }
        self._append_json_entry(self.refresh_log_path, run_summary)
        return run_summary
