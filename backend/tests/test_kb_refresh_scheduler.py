from pathlib import Path

from kb_refresh import FetchResult, KnowledgeBaseRefresher


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
        max_failures=3,
        min_candidate_confidence=0.75,
        min_content_chars=10,
    )


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
    refresher = _mk_refresher(tmp_path, fetch)
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

    assert result["accepted_candidates"] == 1
    assert any(r.get("url") == candidate_url for r in registry)


def test_new_candidate_invalid(tmp_path):
    candidate_url = "https://unknown.example/whatever"
    fetch = {
        candidate_url: FetchResult(url=candidate_url, status_code=200, content="valid enough", ok=True)
    }
    refresher = _mk_refresher(tmp_path, fetch)
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
    refresher = _mk_refresher(tmp_path, fetch)

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
