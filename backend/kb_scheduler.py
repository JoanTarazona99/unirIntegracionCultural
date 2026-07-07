"""Periodic scheduler for KnowledgeBaseRefresher using background threads."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class _JobSpec:
    name: str
    interval_seconds: int
    category: Optional[str] = None


class _PeriodicWorker:
    def __init__(self, spec: _JobSpec, callback):
        self.spec = spec
        self.callback = callback
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"kb-refresh-{spec.name}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.callback(self.spec)
            self._stop.wait(self.spec.interval_seconds)


class KnowledgeRefreshScheduler:
    """Simple maintainable scheduler for periodic incremental KB refresh."""

    def __init__(
        self,
        refresher,
        *,
        critical_hours: int = 6,
        faq_admission_hours: int = 24,
        stable_hours: int = 24 * 7,
        candidate_hours: int = 4,
        use_distributed_lock: bool = False,
        redis_url: str = "redis://localhost:6379",
        distributed_lock_key: str = "kubgu:kb_scheduler:leader",
        distributed_lock_ttl_seconds: int = 180,
    ):
        self.refresher = refresher
        self._running = False
        self._workers: Dict[str, _PeriodicWorker] = {}
        self._leader_lock_path = Path(refresher.data_dir) / "kb_scheduler.leader.lock"
        self._is_leader = False
        self._use_distributed_lock = use_distributed_lock
        self._redis_url = redis_url
        self._distributed_lock_key = distributed_lock_key
        self._distributed_lock_ttl_seconds = distributed_lock_ttl_seconds
        self._redis_client = None
        self._distributed_lock_token = None
        self._specs = [
            _JobSpec(name="critical", interval_seconds=max(1, critical_hours) * 3600, category="critical"),
            _JobSpec(name="faq_admission", interval_seconds=max(1, faq_admission_hours) * 3600, category="faq_admission"),
            _JobSpec(name="stable", interval_seconds=max(1, stable_hours) * 3600, category="stable"),
            _JobSpec(name="candidates", interval_seconds=max(1, candidate_hours) * 3600, category=None),
        ]

    @property
    def is_leader(self) -> bool:
        return self._is_leader

    def _acquire_leader_lock(self) -> bool:
        self._leader_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self._leader_lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            os.close(fd)
            self._is_leader = True
            return True
        except FileExistsError:
            # Best effort stale lock cleanup.
            try:
                if time.time() - self._leader_lock_path.stat().st_mtime > 180:
                    self._leader_lock_path.unlink(missing_ok=True)
                    return self._acquire_leader_lock()
            except Exception:
                pass
            self._is_leader = False
            return False

    def _release_leader_lock(self) -> None:
        if not self._is_leader:
            return
        try:
            self._leader_lock_path.unlink(missing_ok=True)
        except Exception:
            pass
        self._is_leader = False

    def _acquire_distributed_lock(self) -> bool:
        if not self._use_distributed_lock:
            return True
        try:
            import redis

            self._redis_client = redis.Redis.from_url(self._redis_url, decode_responses=True)
            token = f"{os.getpid()}:{time.time()}"
            acquired = self._redis_client.set(
                self._distributed_lock_key,
                token,
                nx=True,
                ex=max(30, int(self._distributed_lock_ttl_seconds)),
            )
            if acquired:
                self._distributed_lock_token = token
                return True
            return False
        except Exception:
            # Safe behavior for multi-host mode: if distributed lock is required
            # and unavailable, do not start scheduler workers.
            return False

    def _release_distributed_lock(self) -> None:
        if not self._use_distributed_lock or not self._redis_client or not self._distributed_lock_token:
            return
        try:
            current = self._redis_client.get(self._distributed_lock_key)
            if current == self._distributed_lock_token:
                self._redis_client.delete(self._distributed_lock_key)
        except Exception:
            pass
        finally:
            self._distributed_lock_token = None

    def _execute_job(self, spec: _JobSpec) -> None:
        if spec.name == "candidates":
            self.refresher.process_candidate_sources()
            return
        self.refresher.run_refresh(category=spec.category)

    def start(self) -> None:
        if self._running:
            return
        if not self._acquire_distributed_lock():
            return
        if not self._acquire_leader_lock():
            # Another process is scheduler leader; skip workers in this process.
            self._release_distributed_lock()
            return
        self._running = True
        for spec in self._specs:
            worker = _PeriodicWorker(spec, self._execute_job)
            self._workers[spec.name] = worker
            worker.start()

    def stop(self) -> None:
        if not self._running:
            self._release_leader_lock()
            self._release_distributed_lock()
            return
        self._running = False
        for worker in self._workers.values():
            worker.stop()
        self._workers = {}
        self._release_leader_lock()
        self._release_distributed_lock()

    def run_once(self, *, force: bool = False) -> Dict:
        """Convenience method for manual runs in dev/tests."""
        return self.refresher.run_refresh(force=force)
