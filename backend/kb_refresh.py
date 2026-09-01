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
import ipaddress
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse

import requests

from app.config.settings import settings
from atomic_json import atomic_write_bytes, atomic_write_json


DEFAULT_ALLOWED_HOSTS = frozenset({
    "kubsu.ru",
    "www.kubsu.ru",
    "inter.kubsu.ru",
    "mvd.ru",
    "www.mvd.ru",
    "gu-krasnodar.mvd.ru",
    "guvm.mvd.ru",
    "xn--b1aew.xn--p1ai",
    "mfc.gov.ru",
    "www.mfc.gov.ru",
    "gosuslugi.ru",
    "www.gosuslugi.ru",
})
REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
DEFAULT_PROMPT_INJECTION_PATTERNS = (
    ("ignore_previous_instructions", r"\bignore\s+(?:all\s+)?previous\s+instructions?\b"),
    ("disregard_previous_instructions", r"\bdisregard\s+(?:all\s+)?(?:prior|previous)\s+instructions?\b"),
    ("reveal_system_prompt", r"\b(?:reveal|show|print|expose)\b.{0,60}\bsystem\s+prompts?\b"),
    ("override_system_instructions", r"\boverride\b.{0,60}\bsystem\s+instructions?\b"),
)


@dataclass(frozen=True)
class URLValidationResult:
    decision: str
    normalized_url: Optional[str] = None
    hostname: Optional[str] = None

    @property
    def accepted(self) -> bool:
        return self.decision == "accepted"


class AcquisitionPolicyError(Exception):
    def __init__(
        self,
        reason: str,
        *,
        category: Optional[str] = None,
        content_length: Optional[int] = None,
        content_hash: Optional[str] = None,
        rejected: bool = True,
        redirect_chain: Optional[List[str]] = None,
    ):
        super().__init__(reason)
        self.reason = reason
        self.category = category
        self.content_length = content_length
        self.content_hash = content_hash
        self.rejected = rejected
        self.redirect_chain = list(redirect_chain or [])


def normalize_and_validate_url(
    url: str,
    *,
    allowed_hostnames: Iterable[str],
    allow_subdomains_for: Iterable[str] = (),
    allowed_ports: Iterable[int] = (443,),
) -> URLValidationResult:
    """Normalize one HTTPS URL and apply an exact-host allowlist policy."""
    raw_url = str(url or "").strip()
    if not raw_url:
        return URLValidationResult("invalid_url")
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return URLValidationResult("invalid_url")
    if not parsed.scheme:
        return URLValidationResult("invalid_url")
    if parsed.scheme.lower() != "https":
        return URLValidationResult("https_required")
    if not parsed.netloc:
        return URLValidationResult("invalid_url")
    if parsed.username is not None or parsed.password is not None:
        return URLValidationResult("userinfo_not_allowed")
    try:
        hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        port = parsed.port
    except (UnicodeError, ValueError):
        return URLValidationResult("invalid_url")
    if not hostname or any(char.isspace() for char in hostname):
        return URLValidationResult("invalid_url")
    if port is not None and port not in {int(value) for value in allowed_ports}:
        return URLValidationResult("port_not_allowed")

    exact_hosts = {
        str(value).encode("idna").decode("ascii").lower().rstrip(".")
        for value in allowed_hostnames
        if value
    }
    subdomain_roots = {
        str(value).encode("idna").decode("ascii").lower().rstrip(".")
        for value in allow_subdomains_for
        if value
    }
    host_allowed = hostname in exact_hosts or any(
        hostname.endswith(f".{root}") for root in subdomain_roots
    )
    if not host_allowed:
        return URLValidationResult("domain_not_allowed", hostname=hostname)

    normalized_netloc = hostname
    if port is not None:
        normalized_netloc = f"{hostname}:{port}"
    normalized = parsed._replace(
        scheme="https",
        netloc=normalized_netloc,
        fragment="",
    ).geturl()
    return URLValidationResult("accepted", normalized, hostname)


class _UsefulHTMLTextExtractor(HTMLParser):
    _IGNORED_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.useful_parts: List[str] = []
        self.ignored_text_chars = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._IGNORED_TAGS:
            self._ignored_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data):
        text = str(data or "").strip()
        if not text:
            return
        if self._ignored_depth:
            self.ignored_text_chars += len(text)
        else:
            self.useful_parts.append(text)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.useful_parts)).strip()


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
    content: object = ""
    ok: bool = False
    error: Optional[str] = None
    requested_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    location: Optional[str] = None
    final_url: Optional[str] = None
    body_chunks: Optional[Iterable[bytes]] = None
    content_type: Optional[str] = "text/html"
    exception_type: Optional[str] = None

    def __post_init__(self):
        self.requested_url = self.requested_url or self.url
        self.final_url = self.final_url or self.url
        self.headers = dict(self.headers or {})
        if self.location is None:
            self.location = next(
                (
                    value for key, value in self.headers.items()
                    if str(key).lower() == "location"
                ),
                None,
            )


@dataclass
class AcquisitionRefreshResult:
    """Outcome of one candidate acquisition transaction."""

    success: bool
    status: str
    source_id: Optional[str] = None
    version_id: Optional[str] = None
    fingerprint: Optional[str] = None
    affected_chunk_ids: Optional[List[str]] = None
    error: Optional[str] = None
    correlation_id: str = ""
    reindexed: bool = False
    redirect_chain: Optional[List[str]] = None
    run_id: str = ""
    public_acquisition_enabled: bool = False
    public_manifest_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "status": self.status,
            "source_id": self.source_id,
            "version_id": self.version_id,
            "fingerprint": self.fingerprint,
            "affected_chunk_ids": list(self.affected_chunk_ids or []),
            "error": self.error,
            "correlation_id": self.correlation_id,
            "reindexed": self.reindexed,
            "redirect_chain": list(self.redirect_chain or []),
            "run_id": self.run_id,
            "public_acquisition_enabled": self.public_acquisition_enabled,
            "public_manifest_path": self.public_manifest_path,
        }


class KnowledgeBaseRefresher:
    """Incremental refresh manager for KB sources and candidate discovery."""

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        rag_module=None,
        fetcher: Optional[Callable[[str], FetchResult]] = None,
        http_session: Optional[requests.Session] = None,
        fetch_timeout_seconds: float = 8.0,
        tls_ca_bundle: Optional[str] = None,
        enable_public_source_acquisition: Optional[bool] = None,
        public_source_allowed_urls: Optional[Iterable[str]] = None,
        public_source_allowed_hosts: Optional[Iterable[str]] = None,
        public_source_max_requests_per_run: Optional[int] = None,
        public_source_max_redirects: Optional[int] = None,
        controlled_fixture: bool = False,
        max_failures: int = 3,
        min_candidate_confidence: float = 0.75,
        min_content_chars: int = 200,
        allowed_hostnames: Optional[Iterable[str]] = None,
        allow_subdomains_for: Iterable[str] = (),
        allowed_ports: Iterable[int] = (443,),
        allowed_mime_types: Iterable[str] = ("text/html", "text/plain"),
        max_content_bytes: int = 1_000_000,
        min_extracted_text_chars: Optional[int] = None,
        max_redirect_hops: int = 3,
        max_fetch_retries: int = 2,
        prompt_injection_patterns: Optional[Sequence[Tuple[str, str]]] = None,
        clock: Optional[Callable[[], datetime]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
    ):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.data_dir = self.project_root / "data"
        self.kb_versions_dir = self.data_dir / "kb_versions"

        self.source_registry_path = self.data_dir / "source_registry.json"
        self.candidate_sources_path = self.data_dir / "candidate_sources.json"
        self.refresh_log_path = self.data_dir / "refresh_log.json"
        self.integration_log_path = self.data_dir / "integration_log.json"
        self.public_manifest_dir = self.data_dir / "public_acquisition_manifests"

        self.rag_module = rag_module
        self.http_session = http_session or requests.Session()
        self.http_session.trust_env = False
        self.fetch_timeout_seconds = float(fetch_timeout_seconds)
        self.tls_ca_bundle = str(tls_ca_bundle) if tls_ca_bundle else None
        self.enable_public_source_acquisition = bool(
            settings.enable_public_source_acquisition
            if enable_public_source_acquisition is None
            else enable_public_source_acquisition
        )
        configured_urls = (
            settings.public_source_allowed_urls
            if public_source_allowed_urls is None
            else public_source_allowed_urls
        )
        configured_hosts = (
            settings.public_source_allowed_hosts
            if public_source_allowed_hosts is None
            else public_source_allowed_hosts
        )
        self.public_source_allowed_urls = {
            str(value).strip() for value in configured_urls if str(value).strip()
        }
        self.public_source_allowed_hosts = {
            str(value).encode("idna").decode("ascii").lower().rstrip(".")
            for value in configured_hosts
            if value
        }
        self.public_source_max_requests_per_run = int(
            settings.public_source_max_requests_per_run
            if public_source_max_requests_per_run is None
            else public_source_max_requests_per_run
        )
        self.public_source_max_redirects = int(
            settings.public_source_max_redirects
            if public_source_max_redirects is None
            else public_source_max_redirects
        )
        self.controlled_fixture = bool(controlled_fixture)
        self._public_request_counts: Dict[str, int] = {}
        self.fetcher = fetcher or self._default_fetcher
        self.max_failures = max_failures
        self.min_candidate_confidence = min_candidate_confidence
        self.min_content_chars = min_content_chars
        self.allowed_hostnames = {
            str(host).lower().rstrip(".")
            for host in (allowed_hostnames or DEFAULT_ALLOWED_HOSTS)
        }
        self.allow_subdomains_for = {
            str(host).lower().rstrip(".") for host in allow_subdomains_for
        }
        self.allowed_ports = {int(port) for port in allowed_ports}
        self.allowed_mime_types = {
            str(mime).lower().split(";", 1)[0].strip()
            for mime in allowed_mime_types
        }
        self.max_content_bytes = int(max_content_bytes)
        self.min_extracted_text_chars = int(
            min_extracted_text_chars
            if min_extracted_text_chars is not None
            else min_content_chars
        )
        self.max_redirect_hops = int(max_redirect_hops)
        self.max_fetch_retries = int(max_fetch_retries)
        patterns = (
            DEFAULT_PROMPT_INJECTION_PATTERNS
            if prompt_injection_patterns is None
            else prompt_injection_patterns
        )
        self.prompt_injection_patterns = tuple(
            (category, re.compile(pattern, re.IGNORECASE | re.DOTALL))
            for category, pattern in patterns
        )
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sleeper = sleeper or time.sleep

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
        lock = path.with_suffix(path.suffix + ".lock")
        try:
            with self._local_lock:
                with self._file_lock(lock):
                    atomic_write_json(path, data)
        except BaseException:
            try:
                path.parent.rmdir()
            except OSError:
                pass
            raise

    def _append_json_entry(self, path: Path, entry: Dict) -> None:
        lock = path.with_suffix(path.suffix + ".lock")
        try:
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
                    atomic_write_json(path, rows)
        except BaseException:
            try:
                path.parent.rmdir()
            except OSError:
                pass
            raise

    def _default_fetcher(self, url: str) -> FetchResult:
        response = None
        try:
            response = self.http_session.get(
                url,
                timeout=self.fetch_timeout_seconds,
                allow_redirects=False,
                stream=True,
                verify=self.tls_ca_bundle or True,
            )
            headers = dict(response.headers)
            chunks = []
            declared_length = response.headers.get("Content-Length")
            declared_oversize = False
            if declared_length is not None:
                try:
                    declared_oversize = int(declared_length) > self.max_content_bytes
                except ValueError:
                    declared_oversize = True
            if not declared_oversize:
                bytes_read = 0
                for chunk in response.iter_content(chunk_size=16_384):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    bytes_read += len(chunk)
                    if bytes_read > self.max_content_bytes:
                        break
            return FetchResult(
                url=url,
                status_code=response.status_code,
                content="",
                ok=200 <= response.status_code < 300,
                error=None,
                requested_url=url,
                headers=headers,
                location=response.headers.get("Location"),
                final_url=url,
                body_chunks=chunks,
                content_type=response.headers.get("Content-Type"),
            )
        except requests.Timeout as exc:
            raise TimeoutError("fetch_timeout") from exc
        except requests.exceptions.SSLError as exc:
            message = str(exc).lower()
            if "hostname mismatch" in message or "not valid for" in message:
                reason = "tls_hostname_mismatch"
            elif (
                "certificate verify failed" in message
                or "self-signed certificate" in message
                or "unable to get local issuer" in message
            ):
                reason = "tls_certificate_untrusted"
            else:
                reason = "tls_connection_error"
            return FetchResult(
                url=url,
                status_code=0,
                content="",
                ok=False,
                error=reason,
                exception_type=type(exc).__name__,
            )
        except requests.ConnectionError as exc:
            return FetchResult(
                url=url,
                status_code=0,
                content="",
                ok=False,
                error="fetch_connection_error",
                exception_type=type(exc).__name__,
            )
        except Exception as exc:
            return FetchResult(
                url=url,
                status_code=0,
                content="",
                ok=False,
                error="fetch_error",
                exception_type=type(exc).__name__,
            )
        finally:
            if response is not None:
                response.close()

    def _validate_url(self, url: str, registry: List[Dict]) -> URLValidationResult:
        return normalize_and_validate_url(
            url,
            allowed_hostnames=self._allowed_domains(registry),
            allow_subdomains_for=self.allow_subdomains_for,
            allowed_ports=self.allowed_ports,
        )

    def _fetch_with_retries(
        self,
        url: str,
        before_attempt: Optional[Callable[[], None]] = None,
    ) -> FetchResult:
        for attempt in range(self.max_fetch_retries + 1):
            if before_attempt is not None:
                before_attempt()
            try:
                result = self.fetcher(url)
            except (TimeoutError, requests.Timeout) as exc:
                if attempt < self.max_fetch_retries:
                    self.sleeper(0)
                    continue
                raise AcquisitionPolicyError("fetch_timeout", rejected=False) from exc
            except Exception as exc:
                raise AcquisitionPolicyError("fetch_error", rejected=False) from exc

            if 500 <= int(result.status_code or 0) <= 599 and attempt < self.max_fetch_retries:
                self.sleeper(0)
                continue
            return result
        raise AcquisitionPolicyError("fetch_error", rejected=False)

    def _response_content_type(self, result: FetchResult) -> str:
        header_content_type = next(
            (
                value for key, value in (result.headers or {}).items()
                if str(key).lower() == "content-type"
            ),
            None,
        )
        return str(header_content_type or result.content_type or "text/html").lower().split(";", 1)[0].strip()

    def _read_response_bytes(self, result: FetchResult) -> bytes:
        declared_length = next(
            (
                value for key, value in (result.headers or {}).items()
                if str(key).lower() == "content-length"
            ),
            None,
        )
        if declared_length is not None:
            try:
                if int(declared_length) > self.max_content_bytes:
                    raise AcquisitionPolicyError("content_too_large")
            except ValueError as exc:
                raise AcquisitionPolicyError("content_decode_error") from exc

        if result.body_chunks is not None:
            chunks = result.body_chunks
        elif isinstance(result.content, bytes):
            chunks = (result.content,)
        else:
            chunks = (str(result.content or "").encode("utf-8"),)

        collected = bytearray()
        try:
            for chunk in chunks:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise AcquisitionPolicyError("content_decode_error")
                collected.extend(chunk)
                if len(collected) > self.max_content_bytes:
                    raise AcquisitionPolicyError("content_too_large")
        except AcquisitionPolicyError:
            raise
        except Exception as exc:
            raise AcquisitionPolicyError("content_decode_error") from exc
        return bytes(collected)

    def _extract_validated_text(self, payload: bytes, mime_type: str) -> str:
        try:
            decoded = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise AcquisitionPolicyError("content_decode_error") from exc

        if mime_type == "text/html":
            parser = _UsefulHTMLTextExtractor()
            try:
                parser.feed(decoded)
                parser.close()
            except Exception as exc:
                raise AcquisitionPolicyError("content_decode_error") from exc
            cleaned = parser.get_text()
            if not cleaned and parser.ignored_text_chars:
                raise AcquisitionPolicyError("no_useful_text")
        else:
            cleaned = re.sub(r"\s+", " ", decoded).strip()

        if len(cleaned) < self.min_extracted_text_chars:
            raise AcquisitionPolicyError("insufficient_content")
        return cleaned

    def _detect_prompt_injection(self, text: str) -> Optional[str]:
        for category, pattern in self.prompt_injection_patterns:
            if pattern.search(text):
                return category
        return None

    def _fetch_validated_content(
        self,
        url: str,
        registry: List[Dict],
        public_context: Optional[Dict] = None,
    ) -> Tuple[str, str, List[str]]:
        initial_validation = self._validate_url(url, registry)
        if not initial_validation.accepted:
            raise AcquisitionPolicyError(initial_validation.decision)

        current_url = initial_validation.normalized_url or url
        redirect_chain = [current_url]
        redirect_hops = 0
        while True:
            result = self._fetch_with_retries(
                current_url,
                before_attempt=(
                    lambda: self._reserve_public_request(public_context)
                    if public_context is not None
                    else None
                ),
            )
            status_code = int(result.status_code or 0)
            if public_context is not None:
                public_context["transport_exception_type"] = result.exception_type
            if status_code == 0 or (
                200 <= status_code < 300 and not result.ok and result.error
            ):
                raise AcquisitionPolicyError(
                    result.error or "fetch_error",
                    category=result.exception_type,
                    rejected=False,
                )
            if status_code in REDIRECT_STATUS_CODES:
                if redirect_hops >= self.max_redirect_hops:
                    raise AcquisitionPolicyError("redirect_hop_limit")
                if not result.location:
                    raise AcquisitionPolicyError("invalid_url")
                redirect_target = urljoin(current_url, str(result.location))
                if public_context is not None:
                    public_context["redirect_chain"] = redirect_chain + [redirect_target]
                    self._validate_public_url(
                        redirect_target,
                        public_context,
                        redirect_hops=redirect_hops + 1,
                    )
                redirect_validation = self._validate_url(redirect_target, registry)
                if not redirect_validation.accepted:
                    raise AcquisitionPolicyError(
                        "redirect_domain_not_allowed",
                        category=redirect_validation.decision,
                        redirect_chain=redirect_chain + [redirect_target],
                    )
                current_url = redirect_validation.normalized_url or redirect_target
                redirect_chain.append(current_url)
                redirect_hops += 1
                continue

            if status_code == 404:
                raise AcquisitionPolicyError("http_status_404")
            if 500 <= status_code <= 599:
                raise AcquisitionPolicyError("http_status_5xx", rejected=False)
            if not 200 <= status_code < 300:
                raise AcquisitionPolicyError(f"http_status_{status_code}")

            mime_type = self._response_content_type(result)
            if public_context is not None:
                public_context["content_type"] = mime_type
                declared_length = next(
                    (
                        value
                        for key, value in (result.headers or {}).items()
                        if str(key).lower() == "content-length"
                    ),
                    None,
                )
                try:
                    public_context["content_length"] = (
                        int(declared_length) if declared_length is not None else None
                    )
                except ValueError:
                    public_context["content_length"] = None
            if mime_type not in self.allowed_mime_types:
                raise AcquisitionPolicyError(
                    "mime_type_not_allowed",
                    category=mime_type or "missing",
                )
            payload = self._read_response_bytes(result)
            if public_context is not None:
                public_context["content_length"] = len(payload)
                public_context["content_hash"] = hashlib.sha256(payload).hexdigest()
            cleaned = self._extract_validated_text(payload, mime_type)
            prompt_rule = self._detect_prompt_injection(cleaned)
            if prompt_rule:
                raise AcquisitionPolicyError(
                    "prompt_injection_detected",
                    category=prompt_rule,
                    content_length=len(payload),
                    content_hash=hashlib.sha256(payload).hexdigest(),
                )
            return current_url, cleaned, redirect_chain

    def _verified_fingerprint(self, text: str) -> str:
        try:
            fingerprint = self._fingerprint(text)
            verification = self._fingerprint(text)
        except Exception as exc:
            raise AcquisitionPolicyError("fingerprint_error", rejected=False) from exc
        if (
            fingerprint != verification
            or re.fullmatch(r"[0-9a-f]{64}", str(fingerprint or "")) is None
        ):
            raise AcquisitionPolicyError("fingerprint_mismatch", rejected=False)
        return fingerprint

    def _fetch_with_fallback(
        self,
        source: Dict,
        registry: Optional[List[Dict]] = None,
    ) -> Tuple[FetchResult, str]:
        urls = [source.get("url", "")]
        urls.extend(source.get("fallback_urls", []) or [])

        last_result = FetchResult(url=source.get("url", ""), status_code=0, content="", ok=False, error="no_url")
        for candidate in [u for u in urls if u]:
            try:
                final_url, cleaned, _ = self._fetch_validated_content(
                    candidate,
                    registry or [source],
                )
                return FetchResult(
                    url=candidate,
                    requested_url=candidate,
                    final_url=final_url,
                    status_code=200,
                    content=cleaned,
                    content_type="text/plain",
                    ok=True,
                ), candidate
            except AcquisitionPolicyError as exc:
                last_result = FetchResult(
                    url=candidate,
                    status_code=0,
                    content="",
                    ok=False,
                    error=exc.reason,
                )
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
        return set(self.allowed_hostnames) | set(self.public_source_allowed_hosts)

    def _is_loopback_url(self, url: str) -> bool:
        try:
            hostname = (urlparse(url).hostname or "").lower().rstrip(".")
            if hostname == "localhost":
                return True
            return ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            return False

    def _new_public_context(
        self,
        url: str,
        *,
        correlation_id: str,
        run_id: str,
    ) -> Optional[Dict]:
        if self.controlled_fixture or self._is_loopback_url(url):
            return None
        return {
            "run_id": run_id,
            "correlation_id": correlation_id,
            "timestamp_utc": _utc_now_iso(),
            "public_acquisition_enabled": self.enable_public_source_acquisition,
            "requested_url": str(url or "").strip(),
            "normalized_url": None,
            "allowed_url_match": False,
            "allowed_host_match": False,
            "request_limit": self.public_source_max_requests_per_run,
            "requests_attempted": self._public_request_counts.get(run_id, 0),
            "redirect_chain": [],
            "tls_verification": (
                "required_custom_ca" if self.tls_ca_bundle else "required_system_ca"
            ),
            "content_type": None,
            "content_length": None,
            "content_hash": None,
            "transport_exception_type": None,
        }

    def _validate_public_url(
        self,
        url: str,
        context: Dict,
        *,
        redirect_hops: int = 0,
    ) -> None:
        raw_url = str(url or "").strip()
        try:
            parsed = urlparse(raw_url)
            hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        except (UnicodeError, ValueError):
            raise AcquisitionPolicyError("invalid_url")
        validation = normalize_and_validate_url(
            raw_url,
            allowed_hostnames={hostname} if hostname else set(),
            allowed_ports=self.allowed_ports,
        )
        context["normalized_url"] = validation.normalized_url
        context["allowed_url_match"] = raw_url in self.public_source_allowed_urls
        context["allowed_host_match"] = hostname in self.public_source_allowed_hosts
        if not validation.accepted:
            raise AcquisitionPolicyError(validation.decision)
        if not self.enable_public_source_acquisition:
            raise AcquisitionPolicyError("public_acquisition_disabled")
        if redirect_hops > self.public_source_max_redirects:
            raise AcquisitionPolicyError(
                "public_redirect_not_allowed",
                redirect_chain=list(context.get("redirect_chain") or []),
            )
        if not context["allowed_url_match"] or not context["allowed_host_match"]:
            raise AcquisitionPolicyError("public_url_not_allowlisted")

    def _reserve_public_request(self, context: Dict) -> None:
        run_id = str(context["run_id"])
        attempted = self._public_request_counts.get(run_id, 0)
        if attempted >= self.public_source_max_requests_per_run:
            context["requests_attempted"] = attempted
            raise AcquisitionPolicyError("public_request_limit_exceeded")
        attempted += 1
        self._public_request_counts[run_id] = attempted
        context["requests_attempted"] = attempted

    def _finalize_public_result(
        self,
        result: AcquisitionRefreshResult,
        context: Optional[Dict],
        *,
        run_id: str,
    ) -> AcquisitionRefreshResult:
        result.run_id = run_id
        result.public_acquisition_enabled = self.enable_public_source_acquisition
        if context is None:
            return result
        context.update({
            "result_status": result.status,
            "result_reason": result.error,
            "source_id": result.source_id,
            "version_id": result.version_id,
            "redirect_chain": list(result.redirect_chain or context["redirect_chain"]),
        })
        manifest_key = hashlib.sha256(
            f"{run_id}|{context['timestamp_utc']}|{context['requested_url']}".encode("utf-8")
        ).hexdigest()[:20]
        manifest_path = self.public_manifest_dir / f"{manifest_key}.json"
        self._write_json(manifest_path, context)
        result.public_manifest_path = str(manifest_path)
        return result

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
        version_id = f"{self.clock().strftime('%Y%m%d%H%M%S')}-{fingerprint[:10]}"
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
            "public_acquisition_enabled": self.enable_public_source_acquisition,
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
            "public_acquisition_enabled": self.enable_public_source_acquisition,
            "source_id": source.get("source_id"),
            "url": source.get("url"),
            **extra,
        }
        self._append_json_entry(self.integration_log_path, entry)

    def _snapshot_rag_state(self):
        if self.rag_module is None or not hasattr(self.rag_module, "document_library"):
            return None
        library = self.rag_module.document_library
        return {
            "documents": deepcopy(library.documents),
            "flat_documents": deepcopy(library.flat_documents),
            "retriever": getattr(self.rag_module, "_retriever", None),
        }

    def _restore_rag_state(self, snapshot) -> None:
        if snapshot is None or self.rag_module is None:
            return
        library = self.rag_module.document_library
        library.documents = snapshot["documents"]
        library.flat_documents = snapshot["flat_documents"]
        self.rag_module._retriever = snapshot["retriever"]
        if getattr(library, "semantic_engine", None) and library._use_semantic:
            library.semantic_engine.build_index(library.flat_documents)

    def _restore_file(self, path: Path, previous: Optional[bytes]) -> None:
        if previous is None:
            path.unlink(missing_ok=True)
            return
        atomic_write_bytes(path, previous)

    def acquire_refresh_and_index_candidate(
        self,
        candidate: Dict,
        *,
        correlation_id: str,
        run_id: Optional[str] = None,
    ) -> AcquisitionRefreshResult:
        """Validate, fetch, version, apply, and index a candidate in one transaction.

        Scheduled refresh keeps its two-phase workflow. This adapter is for chat,
        where accepted evidence must become retrievable before the final response.
        """
        source = None
        version_path = None
        registry_before = None
        candidates_before = None
        refresh_log_before = None
        integration_log_before = None
        rag_snapshot = None
        version_files_before = None
        manifest_files_before = set()
        success_observability_started = False
        redirect_chain: List[str] = []
        stage = "validation"
        effective_run_id = str(run_id or correlation_id)
        public_context = None
        query_trace = {
            key: candidate[key]
            for key in ("query_sha256", "query_length", "query_language")
            if key in candidate
        }

        with self._state_lock():
            try:
                registry_before = (
                    self.source_registry_path.read_bytes()
                    if self.source_registry_path.exists()
                    else None
                )
                candidates_before = (
                    self.candidate_sources_path.read_bytes()
                    if self.candidate_sources_path.exists()
                    else None
                )
                refresh_log_before = (
                    self.refresh_log_path.read_bytes()
                    if self.refresh_log_path.exists()
                    else None
                )
                integration_log_before = (
                    self.integration_log_path.read_bytes()
                    if self.integration_log_path.exists()
                    else None
                )
                if self.public_manifest_dir.exists():
                    manifest_files_before = set(self.public_manifest_dir.glob("*.json"))
                registry = self._read_json(self.source_registry_path, [])
                candidates = self._read_json(self.candidate_sources_path, [])
                if self.rag_module is None:
                    raise ValueError("rag_module_required")

                url = str(candidate.get("url") or "").strip()
                public_context = self._new_public_context(
                    url,
                    correlation_id=correlation_id,
                    run_id=effective_run_id,
                )
                if public_context is not None:
                    public_context["redirect_chain"] = [url]
                    self._validate_public_url(url, public_context)
                url_validation = self._validate_url(url, registry)
                if not url_validation.accepted:
                    raise AcquisitionPolicyError(url_validation.decision)
                url = url_validation.normalized_url or url
                domain = url_validation.hostname or ""
                candidate_domain = str(candidate.get("domain") or domain).lower().rstrip(".")
                if candidate_domain != domain:
                    raise AcquisitionPolicyError("domain_not_allowed")
                if float(candidate.get("confidence", 0.0)) < self.min_candidate_confidence:
                    raise AcquisitionPolicyError("low_confidence")

                topic = self._classify_topic(
                    f"{candidate.get('type', '')} {candidate.get('snippet', '')}"
                )
                if topic is None:
                    raise AcquisitionPolicyError("invalid_topic")

                stage = "fetch"
                _, cleaned, redirect_chain = self._fetch_validated_content(
                    url,
                    registry,
                    public_context,
                )
                stage = "fingerprint"
                fingerprint = self._verified_fingerprint(cleaned)

                source = next((row for row in registry if row.get("url") == url), None)
                if source and source.get("hash_current") == fingerprint and source.get("active_version"):
                    stored_candidate = next(
                        (row for row in candidates if row.get("url") == url),
                        None,
                    )
                    if stored_candidate is not None:
                        stored_candidate.update({
                            "status": "indexed",
                            "validated_at": self.clock().isoformat(),
                            "validation_reason": "already_indexed",
                            "source_id": source["source_id"],
                            "version_id": source["active_version"],
                            "fingerprint": fingerprint,
                            "transaction_success": True,
                        })
                        self._write_json(self.candidate_sources_path, candidates)
                    success_observability_started = True
                    stage = "audit_log"
                    self._log_refresh_event(
                        "candidate_acquisition_unchanged",
                        source,
                        correlation_id=correlation_id,
                        fingerprint=fingerprint,
                        **query_trace,
                    )
                    result = AcquisitionRefreshResult(
                        success=True,
                        status="unchanged",
                        source_id=source.get("source_id"),
                        version_id=source.get("active_version"),
                        fingerprint=fingerprint,
                        affected_chunk_ids=[],
                        correlation_id=correlation_id,
                        reindexed=False,
                        redirect_chain=redirect_chain,
                    )
                    return self._finalize_public_result(
                        result,
                        public_context,
                        run_id=effective_run_id,
                    )

                duplicate = next(
                    (
                        row for row in registry
                        if row is not source and row.get("hash_current") == fingerprint
                    ),
                    None,
                )
                if duplicate:
                    success_observability_started = True
                    stage = "audit_log"
                    self._log_refresh_event(
                        "candidate_acquisition_duplicate_content",
                        duplicate,
                        correlation_id=correlation_id,
                        reason="duplicate_content",
                        fingerprint=fingerprint,
                        **query_trace,
                    )
                    duplicate_version = duplicate.get("active_version")
                    stored_candidate = next(
                        (row for row in candidates if row.get("url") == url),
                        None,
                    )
                    if duplicate_version and stored_candidate is not None:
                        stored_candidate.update({
                            "status": "indexed",
                            "validated_at": self.clock().isoformat(),
                            "validation_reason": "duplicate_content_indexed",
                            "source_id": duplicate["source_id"],
                            "version_id": duplicate_version,
                            "fingerprint": fingerprint,
                            "transaction_success": True,
                        })
                        self._write_json(self.candidate_sources_path, candidates)
                    result = AcquisitionRefreshResult(
                        success=bool(duplicate_version),
                        status="duplicate_content" if duplicate_version else "rejected",
                        source_id=duplicate.get("source_id"),
                        version_id=duplicate_version,
                        fingerprint=fingerprint,
                        affected_chunk_ids=[],
                        correlation_id=correlation_id,
                        reindexed=False,
                        error=None if duplicate_version else "duplicate_content",
                        redirect_chain=redirect_chain,
                    )
                    return self._finalize_public_result(
                        result,
                        public_context,
                        run_id=effective_run_id,
                    )

                candidate_id = candidate.get("id") or hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
                if source is None:
                    source = {
                        "source_id": f"candidate_{candidate_id}",
                        "url": url,
                        "domain": domain,
                        "type": candidate.get("type") or "candidate",
                        "category": topic,
                        "confidence": float(candidate.get("confidence", 0.0)),
                        "status": "pending_update",
                        "hash_current": "",
                        "last_checked": None,
                        "last_updated": None,
                        "fail_count": 0,
                        "active_version": None,
                        "check_interval_hours": self.category_default_interval_hours.get(topic, 24),
                        "target_source": candidate.get("title") or f"candidate_{candidate_id}",
                        "target_section_title": candidate.get("title") or "Fuente candidata validada",
                    }
                    registry.append(source)

                checked_at = self.clock().isoformat()
                previous_version = source.get("active_version")
                source_versions_dir = self.kb_versions_dir / source["source_id"]
                version_files_before = set(source_versions_dir.glob("*.json"))
                stage = "persist"
                version_id = self._persist_version(source, cleaned, fingerprint, checked_at)
                version_path = self.kb_versions_dir / source["source_id"] / f"{version_id}.json"
                rag_snapshot = self._snapshot_rag_state()

                affected = None
                if self.rag_module is not None:
                    stage = "apply"
                    affected = self.rag_module.apply_refreshed_source(
                        source=source,
                        content=cleaned,
                        version_id=version_id,
                    )
                    stage = "registry_pending"
                    self._write_json(self.source_registry_path, registry)
                    stage = "index"
                    self.rag_module.reindex_sources_incremental([source["source_id"]])
                affected_chunk_ids = list(affected or [f"refresh:{source['source_id']}:{version_id}"])

                source.update({
                    "status": "active",
                    "hash_current": fingerprint,
                    "last_checked": checked_at,
                    "last_updated": checked_at,
                    "active_version": version_id,
                    "archived_version": previous_version,
                })
                stored_candidate = next(
                    (row for row in candidates if row.get("url") == url),
                    None,
                )
                if stored_candidate is None:
                    stored_candidate = dict(candidate)
                    stored_candidate["id"] = candidate_id
                    candidates.append(stored_candidate)
                stored_candidate.update({
                    "status": "indexed",
                    "validated_at": checked_at,
                    "validation_reason": "accepted_and_indexed",
                    "source_id": source["source_id"],
                    "version_id": version_id,
                    "fingerprint": fingerprint,
                    "transaction_success": True,
                })

                stage = "registry_commit"
                self._write_json(self.source_registry_path, registry)
                stage = "candidate_commit"
                self._write_json(self.candidate_sources_path, candidates)
                success_observability_started = True
                stage = "audit_log"
                self._log_refresh_event(
                    "candidate_acquisition_indexed",
                    source,
                    correlation_id=correlation_id,
                    fingerprint=fingerprint,
                    previous_version=previous_version,
                    active_version=version_id,
                    affected_chunk_ids=affected_chunk_ids,
                    **query_trace,
                )
                self._log_integration_event(
                    "candidate_source_indexed",
                    source,
                    kind="chat_acquisition",
                    correlation_id=correlation_id,
                    active_version=version_id,
                    affected_chunk_ids=affected_chunk_ids,
                )
                result = AcquisitionRefreshResult(
                    success=True,
                    status="indexed",
                    source_id=source["source_id"],
                    version_id=version_id,
                    fingerprint=fingerprint,
                    affected_chunk_ids=affected_chunk_ids,
                    correlation_id=correlation_id,
                    reindexed=self.rag_module is not None,
                    redirect_chain=redirect_chain,
                )
                stage = "manifest"
                return self._finalize_public_result(
                    result,
                    public_context,
                    run_id=effective_run_id,
                )
            except Exception as exc:
                self._restore_rag_state(rag_snapshot)
                if version_path is not None:
                    version_path.unlink(missing_ok=True)
                if source is not None and version_files_before is not None:
                    source_versions_dir = self.kb_versions_dir / source["source_id"]
                    for created_version in (
                        set(source_versions_dir.glob("*.json")) - version_files_before
                    ):
                        created_version.unlink(missing_ok=True)
                    if source_versions_dir.exists() and not any(source_versions_dir.iterdir()):
                        source_versions_dir.rmdir()
                if registry_before is not None or self.source_registry_path.exists():
                    self._restore_file(self.source_registry_path, registry_before)
                if candidates_before is not None or self.candidate_sources_path.exists():
                    self._restore_file(self.candidate_sources_path, candidates_before)
                if success_observability_started:
                    self._restore_file(self.refresh_log_path, refresh_log_before)
                    self._restore_file(self.integration_log_path, integration_log_before)
                if self.public_manifest_dir.exists():
                    for created_manifest in (
                        set(self.public_manifest_dir.glob("*.json")) - manifest_files_before
                    ):
                        created_manifest.unlink(missing_ok=True)
                    if not any(self.public_manifest_dir.iterdir()):
                        self.public_manifest_dir.rmdir()
                if isinstance(exc, AcquisitionPolicyError):
                    reason = exc.reason
                    rejected = exc.rejected
                    category = exc.category
                    content_length = exc.content_length
                    content_hash = exc.content_hash
                    redirect_chain = exc.redirect_chain or redirect_chain
                else:
                    reason = {
                        "fingerprint": "fingerprint_error",
                        "persist": "persistence_error",
                        "apply": "application_error",
                        "index": "indexing_error",
                        "registry_pending": "registry_persistence_error",
                        "registry_commit": "registry_persistence_error",
                        "candidate_commit": "candidate_persistence_error",
                        "audit_log": "observability_error",
                        "manifest": "observability_error",
                    }.get(stage, "acquisition_error")
                    rejected = False
                    category = None
                    content_length = None
                    content_hash = None
                failed_source = dict(source or candidate)
                if not rejected:
                    failed_source["status"] = "rolled_back"
                try:
                    if reason == "prompt_injection_detected":
                        self._append_json_entry(
                            self.refresh_log_path,
                            {
                                "url": url if "url" in locals() else candidate.get("url"),
                                "reason": reason,
                                "category": category,
                                "length": content_length,
                                "content_hash": content_hash,
                                "correlation_id": correlation_id,
                                "public_acquisition_enabled": self.enable_public_source_acquisition,
                                **query_trace,
                            },
                        )
                    else:
                        self._log_refresh_event(
                            "candidate_acquisition_failed",
                            failed_source,
                            correlation_id=correlation_id,
                            reason=reason,
                            category=category,
                            **query_trace,
                        )
                except Exception:
                    pass
                result = AcquisitionRefreshResult(
                    success=False,
                    status="rejected" if rejected else "failed",
                    source_id=source.get("source_id") if source else None,
                    error=reason,
                    correlation_id=correlation_id,
                    redirect_chain=redirect_chain,
                )
                try:
                    return self._finalize_public_result(
                        result,
                        public_context,
                        run_id=effective_run_id,
                    )
                except Exception:
                    return result

    def _kb_upsert(self, source: Dict, cleaned_content: str, version_id: str) -> None:
        if self.rag_module is None:
            return
        if hasattr(self.rag_module, "apply_refreshed_source"):
            self.rag_module.apply_refreshed_source(
                source=source,
                content=cleaned_content,
                version_id=version_id,
            )

    def _refresh_single_source(
        self,
        source: Dict,
        registry: Optional[List[Dict]] = None,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        checked_at = _utc_now_iso()
        fetch_result, checked_url = self._fetch_with_fallback(source, registry)
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
        origin: str = "manual_review",
    ) -> Dict:
        if origin != "manual_review":
            raise ValueError("candidate_origin_not_scheduler_eligible")
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
            "origin": "manual_review",
            "created_at": _utc_now_iso(),
            "validated_at": None,
            "validation_reason": None,
            "transaction_success": False,
        }
        candidates.append(candidate)
        self._write_json(self.candidate_sources_path, candidates)
        return candidate

    def _validate_candidate(self, candidate: Dict, registry: List[Dict]) -> Tuple[bool, str]:
        url_validation = self._validate_url(str(candidate.get("url") or ""), registry)
        if not url_validation.accepted:
            return False, url_validation.decision
        candidate_domain = str(candidate.get("domain") or "").lower().rstrip(".")
        if candidate_domain != url_validation.hostname:
            return False, "domain_not_allowed"
        if float(candidate.get("confidence", 0.0)) < self.min_candidate_confidence:
            return False, "low_confidence"
        if any(r.get("url") == candidate.get("url") for r in registry):
            return False, "duplicate_url"
        topic = self._classify_topic(f"{candidate.get('type', '')} {candidate.get('snippet', '')}")
        if topic is None:
            return False, "invalid_topic"

        try:
            _, cleaned, _ = self._fetch_validated_content(candidate["url"], registry)
            fp = self._verified_fingerprint(cleaned)
        except AcquisitionPolicyError as exc:
            return False, exc.reason
        if any(r.get("hash_current") == fp and fp for r in registry):
            return False, "duplicate_content"
        return True, topic

    def process_candidate_sources(self) -> Dict:
        candidates = self._read_json(self.candidate_sources_path, [])
        eligible = [
            dict(candidate)
            for candidate in candidates
            if candidate.get("status") == "pending"
            and candidate.get("origin") == "manual_review"
        ]
        accepted = 0
        rejected = 0

        for candidate in eligible:
            candidate_id = str(
                candidate.get("id")
                or hashlib.sha1(str(candidate.get("url") or "").encode("utf-8")).hexdigest()[:12]
            )
            correlation_id = str(
                candidate.get("correlation_id")
                or f"manual-{candidate_id}"
            )
            result = self.acquire_refresh_and_index_candidate(
                candidate,
                correlation_id=correlation_id,
            )
            if result.success:
                accepted += 1
                continue

            rejected += 1
            with self._state_lock():
                current_candidates = self._read_json(self.candidate_sources_path, [])
                stored_candidate = next(
                    (row for row in current_candidates if row.get("id") == candidate.get("id")),
                    None,
                )
                if stored_candidate is not None:
                    stored_candidate.update({
                        "status": "rejected",
                        "validated_at": _utc_now_iso(),
                        "validation_reason": result.error or "acquisition_error",
                        "transaction_success": False,
                    })
                    self._write_json(self.candidate_sources_path, current_candidates)
            self._append_json_entry(
                self.refresh_log_path,
                {
                    "timestamp": _utc_now_iso(),
                    "event": "candidate_rejected",
                    "url": candidate.get("url"),
                    "reason": result.error or "acquisition_error",
                    "correlation_id": correlation_id,
                },
            )

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
        updated_events: List[Dict] = []
        observability_failures = 0

        with self._state_lock():
            registry_before = self.source_registry_path.read_bytes()
            rag_before = self._snapshot_rag_state()
            version_files_before = set(self.kb_versions_dir.rglob("*.json"))
            try:
                registry = self._read_json(self.source_registry_path, [])

                for source in registry:
                    if category and source.get("category") != category:
                        continue
                    if not self._is_due(source, now, force):
                        continue

                    checked += 1
                    result, _, version_id = self._refresh_single_source(source, registry)
                    if result == "updated":
                        updated += 1
                        changed_sources.append(source.get("target_source") or source.get("source_id"))
                        versions_created.append(
                            {
                                "source_id": source.get("source_id"),
                                "active_version": version_id,
                            }
                        )
                        updated_events.append(deepcopy(source))
                    elif result == "unchanged":
                        unchanged += 1
                    elif result == "failed":
                        failed += 1
                        if source.get("status") == "stale":
                            stale += 1

                self._write_json(self.source_registry_path, registry)

                if (
                    changed_sources
                    and self.rag_module is not None
                    and hasattr(self.rag_module, "reindex_sources_incremental")
                ):
                    self.rag_module.reindex_sources_incremental(changed_sources)
            except Exception:
                self._restore_rag_state(rag_before)
                for created_version in (
                    set(self.kb_versions_dir.rglob("*.json")) - version_files_before
                ):
                    created_version.unlink(missing_ok=True)
                for source_directory in self.kb_versions_dir.iterdir():
                    if source_directory.is_dir() and not any(source_directory.iterdir()):
                        source_directory.rmdir()
                self._restore_file(self.source_registry_path, registry_before)
                raise

        for source in updated_events:
            try:
                self._log_refresh_event(
                    "source_checked",
                    source,
                    result="updated",
                    fingerprint=source.get("hash_current"),
                    previous_version=source.get("archived_version"),
                    active_version=source.get("active_version"),
                )
                self._log_integration_event(
                    "source_updated",
                    source,
                    previous_version=source.get("archived_version"),
                    active_version=source.get("active_version"),
                )
            except Exception as exc:
                observability_failures += 1
                try:
                    self._append_json_entry(
                        self.refresh_log_path,
                        {
                            "timestamp": _utc_now_iso(),
                            "event": "source_update_observability_failed",
                            "source_id": source.get("source_id"),
                            "active_version": source.get("active_version"),
                            "error": type(exc).__name__,
                        },
                    )
                except Exception:
                    pass

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
            "observability_failures": observability_failures,
            "duration_seconds": round(duration, 3),
        }
        try:
            self._append_json_entry(self.refresh_log_path, run_summary)
        except Exception:
            run_summary["observability_failures"] += 1
        return run_summary
