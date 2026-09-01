import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from atomic_json import atomic_write_json
from kb_refresh import FetchResult, KnowledgeBaseRefresher
from kb_scheduler import KnowledgeRefreshScheduler


class FakeRAG:
    def __init__(self):
        self.applied = []
        self.reindex_calls = []

    def apply_refreshed_source(self, source, content, version_id):
        self.applied.append(
            {
                "source_id": source.get("source_id"),
                "target_source": source.get("target_source"),
                "version_id": version_id,
                "content": content,
            }
        )

    def reindex_sources_incremental(self, changed_sources):
        self.reindex_calls.append(list(changed_sources))


class FetcherStub:
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, url: str) -> FetchResult:
        return self.mapping.get(
            url,
            FetchResult(url=url, status_code=404, content="", ok=False, error="not_found"),
        )


def _source(url: str, domain: str = "kubsu.ru", source_id: str = "src1"):
    return {
        "source_id": source_id,
        "url": url,
        "domain": domain,
        "type": "faq",
        "category": "faq_admission",
        "confidence": 0.95,
        "status": "active",
        "hash_current": "",
        "last_checked": None,
        "last_updated": None,
        "fail_count": 0,
        "active_version": None,
        "check_interval_hours": 1,
        "target_source": "FAQ",
        "target_section_title": "Refresh section",
    }


def _mk_refresher(tmp_path: Path, fetch_map, rag=None):
    return KnowledgeBaseRefresher(
        project_root=tmp_path,
        rag_module=rag,
        fetcher=FetcherStub(fetch_map),
        controlled_fixture=True,
        max_failures=3,
        min_candidate_confidence=0.75,
        min_content_chars=10,
    )


def test_scheduler_runtime_lock_is_created_and_stale_lock_is_replaced(tmp_path):
    data_dir = tmp_path / "runtime-data"
    refresher = SimpleNamespace(data_dir=data_dir)
    scheduler = KnowledgeRefreshScheduler(refresher)
    lock_path = data_dir / "kb_scheduler.leader.lock"

    assert not lock_path.exists()
    assert scheduler._acquire_leader_lock() is True
    assert scheduler.is_leader is True
    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())

    scheduler._release_leader_lock()
    assert scheduler.is_leader is False
    assert not lock_path.exists()

    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("inactive-pid", encoding="utf-8")
    stale_timestamp = time.time() - 181
    os.utime(lock_path, (stale_timestamp, stale_timestamp))

    assert scheduler._acquire_leader_lock() is True
    assert scheduler.is_leader is True
    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())
    scheduler._release_leader_lock()
    assert not lock_path.exists()


@pytest.mark.parametrize("failure_point", ["write", "flush", "file_fsync", "replace"])
def test_atomic_write_json_preserves_valid_target_and_removes_temporary(
    tmp_path,
    failure_point,
):
    target = tmp_path / "state.json"
    target.write_text('{"before": true}\n', encoding="utf-8")

    if failure_point in {"write", "flush"}:
        real_named_temporary = __import__("tempfile").NamedTemporaryFile

        class FailingTemporary:
            def __init__(self, *args, **kwargs):
                self.handle = real_named_temporary(*args, **kwargs)
                self.name = self.handle.name

            def __enter__(self):
                self.handle.__enter__()
                return self

            def __exit__(self, *args):
                return self.handle.__exit__(*args)

            def write(self, value):
                if failure_point == "write":
                    raise OSError("controlled temporary write failure")
                return self.handle.write(value)

            def flush(self):
                if failure_point == "flush":
                    raise OSError("controlled flush failure")
                return self.handle.flush()

            def fileno(self):
                return self.handle.fileno()

        context = patch("atomic_json.tempfile.NamedTemporaryFile", FailingTemporary)
    elif failure_point == "file_fsync":
        context = patch("atomic_json.os.fsync", side_effect=OSError("controlled fsync failure"))
    else:
        context = patch("atomic_json.os.replace", side_effect=OSError("controlled replace failure"))

    with context, pytest.raises(OSError):
        atomic_write_json(target, {"after": True})

    assert target.read_text(encoding="utf-8") == '{"before": true}\n'
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob(".*.tmp")) == []


def test_atomic_write_json_serialization_failure_creates_nothing(tmp_path):
    target = tmp_path / "unexpected" / "state.json"

    with pytest.raises(TypeError):
        atomic_write_json(target, {"invalid": object()})

    assert not target.exists()
    assert not target.parent.exists()


def test_atomic_write_json_propagates_supported_directory_fsync_failure(
    tmp_path,
    monkeypatch,
):
    target = tmp_path / "state.json"
    target.write_text('{"before": true}\n', encoding="utf-8")
    monkeypatch.setattr(
        "atomic_json._fsync_directory",
        lambda _directory: (_ for _ in ()).throw(OSError("controlled directory fsync failure")),
    )

    with pytest.raises(OSError, match="directory fsync"):
        atomic_write_json(target, {"after": True})

    assert target.read_text(encoding="utf-8").startswith('{\n  "after": true')
    assert list(tmp_path.glob(".*.tmp")) == []


def test_atomic_write_json_removes_stale_interrupted_temporary(tmp_path):
    target = tmp_path / "state.json"
    stale = tmp_path / ".state.json.interrupted.tmp"
    stale.write_text("partial", encoding="utf-8")
    old_timestamp = time.time() - 121
    os.utime(stale, (old_timestamp, old_timestamp))

    atomic_write_json(target, {"consistent": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"consistent": True}
    assert not stale.exists()


class CrashSafeRAG:
    def __init__(self):
        self.document_library = SimpleNamespace(
            documents={"Base": {"content": "stable"}},
            flat_documents=[{"source": "Base", "content": "stable"}],
            semantic_engine=None,
            _use_semantic=False,
        )
        self._retriever = object()
        self.apply_calls = []
        self.reindex_calls = []

    def apply_refreshed_source(self, source, content, version_id):
        self.apply_calls.append((source["source_id"], version_id))
        self.document_library.documents["Dynamic"] = {"content": content}
        self.document_library.flat_documents.append({"content": content})
        self._retriever = object()
        return [f"refresh:{source['source_id']}:{version_id}"]

    def reindex_sources_incremental(self, source_ids):
        self.reindex_calls.append(list(source_ids))


def _transaction_candidate():
    return {
        "url": "https://kubsu.ru/crash-safe-admission",
        "domain": "kubsu.ru",
        "type": "admission",
        "confidence": 0.95,
        "snippet": "official admission and enrollment guidance",
        "title": "Crash-safe admission fixture",
    }


def _transaction_refresher(tmp_path):
    candidate = _transaction_candidate()
    rag = CrashSafeRAG()
    refresher = _mk_refresher(
        tmp_path,
        {
            candidate["url"]: FetchResult(
                url=candidate["url"],
                status_code=200,
                content="Official admission guidance for international students.",
                ok=True,
            )
        },
        rag=rag,
    )
    return refresher, rag, candidate


def _transaction_snapshot(refresher, rag):
    return {
        "registry": refresher.source_registry_path.read_bytes(),
        "candidates": refresher.candidate_sources_path.read_bytes(),
        "documents": json.dumps(rag.document_library.documents, sort_keys=True),
        "flat_documents": json.dumps(rag.document_library.flat_documents, sort_keys=True),
        "retriever": rag._retriever,
    }


def _assert_transaction_rolled_back(refresher, rag, before, reason):
    assert refresher.source_registry_path.read_bytes() == before["registry"]
    assert refresher.candidate_sources_path.read_bytes() == before["candidates"]
    assert json.dumps(rag.document_library.documents, sort_keys=True) == before["documents"]
    assert json.dumps(rag.document_library.flat_documents, sort_keys=True) == before["flat_documents"]
    assert rag._retriever is before["retriever"]
    assert not list(refresher.kb_versions_dir.rglob("*.json"))
    assert not list(refresher.data_dir.rglob("*.tmp"))
    assert not list(refresher.data_dir.rglob("*.lock"))
    refresh_events = json.loads(refresher.refresh_log_path.read_text(encoding="utf-8"))
    assert not any(event.get("event") == "candidate_acquisition_indexed" for event in refresh_events)
    assert refresh_events[-1]["event"] == "candidate_acquisition_failed"
    assert refresh_events[-1]["reason"] == reason


def test_transaction_rolls_back_failure_after_version_before_registry(tmp_path):
    refresher, rag, candidate = _transaction_refresher(tmp_path)
    before = _transaction_snapshot(refresher, rag)
    persist_version = refresher._persist_version

    def persist_then_fail(*args, **kwargs):
        persist_version(*args, **kwargs)
        assert list(refresher.kb_versions_dir.rglob("*.json"))
        raise OSError("controlled failure after version persistence")

    refresher._persist_version = persist_then_fail
    result = refresher.acquire_refresh_and_index_candidate(
        candidate,
        correlation_id="corr-after-version",
    )

    assert result.success is False
    assert result.error == "persistence_error"
    _assert_transaction_rolled_back(refresher, rag, before, "persistence_error")


def test_transaction_rolls_back_pending_registry_before_index(tmp_path):
    refresher, rag, candidate = _transaction_refresher(tmp_path)
    before = _transaction_snapshot(refresher, rag)

    def fail_after_registry(_source_ids):
        registry = json.loads(refresher.source_registry_path.read_text(encoding="utf-8"))
        pending = next(row for row in registry if row.get("url") == candidate["url"])
        assert pending["status"] == "pending_update"
        assert pending["active_version"] is None
        raise RuntimeError("controlled failure before indexing")

    rag.reindex_sources_incremental = fail_after_registry
    result = refresher.acquire_refresh_and_index_candidate(
        candidate,
        correlation_id="corr-after-registry",
    )

    assert result.success is False
    assert result.error == "indexing_error"
    _assert_transaction_rolled_back(refresher, rag, before, "indexing_error")


def test_success_log_failure_rolls_back_success_and_all_transaction_state(tmp_path):
    refresher, rag, candidate = _transaction_refresher(tmp_path)
    before = _transaction_snapshot(refresher, rag)
    append_entry = refresher._append_json_entry

    def write_success_then_fail(path, entry):
        append_entry(path, entry)
        if entry.get("event") == "candidate_acquisition_indexed":
            raise OSError("controlled success log failure")

    refresher._append_json_entry = write_success_then_fail
    result = refresher.acquire_refresh_and_index_candidate(
        candidate,
        correlation_id="corr-success-log-failure",
    )

    assert result.success is False
    assert result.error == "observability_error"
    _assert_transaction_rolled_back(refresher, rag, before, "observability_error")
    integration_events = json.loads(
        refresher.integration_log_path.read_text(encoding="utf-8")
    )
    assert not any(event.get("event") == "candidate_source_indexed" for event in integration_events)


def test_scheduled_success_logs_observe_committed_registry_and_completed_index(tmp_path):
    url = "https://kubsu.ru/scheduled-order"
    rag = CrashSafeRAG()
    refresher = _mk_refresher(
        tmp_path,
        {
            url: FetchResult(
                url=url,
                status_code=200,
                content="Updated scheduled admission content.",
                ok=True,
            )
        },
        rag=rag,
    )
    source = _source(url)
    source["hash_current"] = "old-hash"
    source["last_checked"] = "2020-01-01T00:00:00+00:00"
    refresher._write_json(refresher.source_registry_path, [source])
    refresh_log = refresher._log_refresh_event
    integration_log = refresher._log_integration_event

    def assert_committed(log_method, event, logged_source, **extra):
        registry = json.loads(refresher.source_registry_path.read_text(encoding="utf-8"))
        committed = registry[0]
        assert committed["status"] == "active"
        assert committed["active_version"] == logged_source["active_version"]
        assert len(rag.reindex_calls) == 1
        return log_method(event, logged_source, **extra)

    refresher._log_refresh_event = lambda event, logged_source, **extra: assert_committed(
        refresh_log, event, logged_source, **extra
    )
    refresher._log_integration_event = lambda event, logged_source, **extra: assert_committed(
        integration_log, event, logged_source, **extra
    )

    summary = refresher.run_refresh(category="faq_admission")

    assert summary["updated"] == 1
    assert summary["observability_failures"] == 0


def test_scheduled_reindex_failure_rolls_back_registry_version_and_rag(tmp_path):
    url = "https://kubsu.ru/scheduled-rollback"
    rag = CrashSafeRAG()
    refresher = _mk_refresher(
        tmp_path,
        {
            url: FetchResult(
                url=url,
                status_code=200,
                content="Updated scheduled rollback content.",
                ok=True,
            )
        },
        rag=rag,
    )
    source = _source(url)
    source["hash_current"] = "old-hash"
    source["last_checked"] = "2020-01-01T00:00:00+00:00"
    refresher._write_json(refresher.source_registry_path, [source])
    before = _transaction_snapshot(refresher, rag)
    rag.reindex_sources_incremental = lambda _sources: (_ for _ in ()).throw(
        RuntimeError("controlled scheduled index failure")
    )

    with pytest.raises(RuntimeError, match="scheduled index failure"):
        refresher.run_refresh(category="faq_admission")

    assert refresher.source_registry_path.read_bytes() == before["registry"]
    assert json.dumps(rag.document_library.documents, sort_keys=True) == before["documents"]
    assert json.dumps(rag.document_library.flat_documents, sort_keys=True) == before["flat_documents"]
    assert rag._retriever is before["retriever"]
    assert not list(refresher.kb_versions_dir.rglob("*.json"))
    refresh_events = json.loads(refresher.refresh_log_path.read_text(encoding="utf-8"))
    assert not any(event.get("result") == "updated" for event in refresh_events)
    integration_events = json.loads(
        refresher.integration_log_path.read_text(encoding="utf-8")
    )
    assert not any(event.get("event") == "source_updated" for event in integration_events)


def test_source_unchanged(tmp_path):
    content = "<html>unchanged content</html>"
    url = "https://kubsu.ru/faq-1"
    fetch = {url: FetchResult(url=url, status_code=200, content=content, ok=True)}
    rag = FakeRAG()
    refresher = _mk_refresher(tmp_path, fetch, rag=rag)

    source = _source(url=url)
    source["hash_current"] = refresher._fingerprint(refresher._clean_content(content))
    source["last_checked"] = "2020-01-01T00:00:00+00:00"
    refresher._write_json(refresher.source_registry_path, [source])

    stats = refresher.run_refresh(category="faq_admission")

    assert stats["unchanged"] == 1
    assert stats["updated"] == 0
    assert rag.reindex_calls == []


def test_source_updated(tmp_path):
    content = "<html>new content changed</html>"
    url = "https://kubsu.ru/faq-2"
    fetch = {url: FetchResult(url=url, status_code=200, content=content, ok=True)}
    rag = FakeRAG()
    refresher = _mk_refresher(tmp_path, fetch, rag=rag)

    source = _source(url=url)
    source["hash_current"] = "old_hash"
    source["last_checked"] = "2020-01-01T00:00:00+00:00"
    refresher._write_json(refresher.source_registry_path, [source])

    stats = refresher.run_refresh(category="faq_admission")

    assert stats["updated"] == 1
    assert len(rag.applied) == 1
    assert len(rag.reindex_calls) == 1
    assert "FAQ" in rag.reindex_calls[0]


def test_new_candidate_valid(tmp_path):
    candidate_url = "https://kubsu.ru/new-admission"
    fetch = {
        candidate_url: FetchResult(
            url=candidate_url,
            status_code=200,
            content="admission requirements and enrollment details for students",
            ok=True,
        )
    }
    rag = FakeRAG()
    refresher = _mk_refresher(tmp_path, fetch, rag=rag)
    refresher._write_json(refresher.source_registry_path, [_source("https://kubsu.ru/base")])

    refresher.enqueue_candidate_source(
        url=candidate_url,
        domain="kubsu.ru",
        source_type="admission",
        confidence=0.9,
        discovered_from="web_search",
        snippet="admission and enrollment FAQ",
    )
    result = refresher.process_candidate_sources()
    registry = refresher._read_json(refresher.source_registry_path, [])
    candidates = refresher._read_json(refresher.candidate_sources_path, [])

    assert result["accepted_candidates"] == 1
    assert any(r.get("url") == candidate_url for r in registry)
    assert candidates[0]["status"] == "indexed"
    assert candidates[0]["transaction_success"] is True
    assert candidates[0]["source_id"]
    assert candidates[0]["version_id"]
    assert rag.reindex_calls


def test_new_candidate_invalid(tmp_path):
    candidate_url = "https://unknown.example/whatever"
    fetch = {
        candidate_url: FetchResult(url=candidate_url, status_code=200, content="valid enough", ok=True)
    }
    refresher = _mk_refresher(tmp_path, fetch, rag=FakeRAG())
    refresher._write_json(refresher.source_registry_path, [_source("https://kubsu.ru/base")])

    refresher.enqueue_candidate_source(
        url=candidate_url,
        domain="unknown.example",
        source_type="admission",
        confidence=0.9,
        discovered_from="web_search",
        snippet="admission",
    )
    result = refresher.process_candidate_sources()
    candidates = refresher._read_json(refresher.candidate_sources_path, [])

    assert result["rejected_candidates"] == 1
    assert candidates[0]["status"] == "rejected"


def test_discovered_unvalidated_candidate_is_ignored(tmp_path):
    candidate_url = "https://kubsu.ru/discovered-only"
    rag = FakeRAG()
    refresher = _mk_refresher(tmp_path, {}, rag=rag)
    candidate = {
        "id": "discovered-only",
        "url": candidate_url,
        "domain": "kubsu.ru",
        "status": "discovered_unvalidated",
        "origin": "reactive_query",
        "query_sha256": "0" * 64,
        "query_length": 20,
        "correlation_id": "corr-discovered-only",
        "validation_reason": "awaiting_transaction",
    }
    refresher._write_json(refresher.candidate_sources_path, [candidate])
    registry_before = refresher.source_registry_path.read_bytes()

    result = refresher.process_candidate_sources()

    assert result == {"accepted_candidates": 0, "rejected_candidates": 0}
    assert refresher._read_json(refresher.candidate_sources_path, []) == [candidate]
    assert refresher.source_registry_path.read_bytes() == registry_before
    assert not list(refresher.kb_versions_dir.rglob("*.json"))
    assert rag.applied == []
    assert rag.reindex_calls == []


def test_source_temporarily_down(tmp_path):
    url = "https://kubsu.ru/unreachable"
    fetch = {url: FetchResult(url=url, status_code=503, content="", ok=False, error="service_unavailable")}
    refresher = _mk_refresher(tmp_path, fetch)
    source = _source(url=url)
    source["last_checked"] = "2020-01-01T00:00:00+00:00"
    refresher._write_json(refresher.source_registry_path, [source])

    stats = refresher.run_refresh(category="faq_admission")
    registry = refresher._read_json(refresher.source_registry_path, [])

    assert stats["failed"] == 1
    assert registry[0]["status"] == "unreachable"
    assert registry[0]["fail_count"] == 1


def test_duplicate_document_candidate_rejected(tmp_path):
    base_url = "https://kubsu.ru/base"
    duplicate_url = "https://kubsu.ru/dup"
    duplicate_content = "same content for duplicate detection"

    fetch = {
        duplicate_url: FetchResult(url=duplicate_url, status_code=200, content=duplicate_content, ok=True)
    }
    refresher = _mk_refresher(tmp_path, fetch, rag=FakeRAG())

    source = _source(base_url)
    source["hash_current"] = refresher._fingerprint(refresher._clean_content(duplicate_content))
    refresher._write_json(refresher.source_registry_path, [source])

    refresher.enqueue_candidate_source(
        url=duplicate_url,
        domain="kubsu.ru",
        source_type="faq",
        confidence=0.95,
        discovered_from="web_search",
        snippet="faq",
    )

    result = refresher.process_candidate_sources()
    candidates = refresher._read_json(refresher.candidate_sources_path, [])

    assert result["rejected_candidates"] == 1
    assert candidates[0]["validation_reason"] == "duplicate_content"


def test_incremental_update_without_full_reindex(tmp_path):
    url_unchanged = "https://kubsu.ru/source-a"
    url_changed = "https://kubsu.ru/source-b"

    content_unchanged = "stable text"
    content_changed = "new changed text"

    fetch = {
        url_unchanged: FetchResult(url=url_unchanged, status_code=200, content=content_unchanged, ok=True),
        url_changed: FetchResult(url=url_changed, status_code=200, content=content_changed, ok=True),
    }

    rag = FakeRAG()
    refresher = _mk_refresher(tmp_path, fetch, rag=rag)

    s1 = _source(url_unchanged, source_id="src_a")
    s1["hash_current"] = refresher._fingerprint(refresher._clean_content(content_unchanged))
    s1["last_checked"] = "2020-01-01T00:00:00+00:00"

    s2 = _source(url_changed, source_id="src_b")
    s2["hash_current"] = "old_hash"
    s2["last_checked"] = "2020-01-01T00:00:00+00:00"

    refresher._write_json(refresher.source_registry_path, [s1, s2])

    stats = refresher.run_refresh(category="faq_admission")

    assert stats["updated"] == 1
    assert stats["unchanged"] == 1
    assert len(rag.reindex_calls) == 1
    assert rag.reindex_calls[0] == ["FAQ"]
