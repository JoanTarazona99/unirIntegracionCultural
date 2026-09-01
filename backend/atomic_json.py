"""Crash-safe JSON persistence helpers."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def _created_parent_directories(parent: Path) -> list[Path]:
    missing = []
    current = parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    parent.mkdir(parents=True, exist_ok=True)
    return missing


def _cleanup_empty_directories(directories: list[Path]) -> None:
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(str(directory), flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cleanup_stale_temporaries(target: Path, minimum_age_seconds: float = 120.0) -> None:
    cutoff = time.time() - minimum_age_seconds
    for temporary in target.parent.glob(f".{target.name}.*.tmp"):
        try:
            if temporary.stat().st_mtime <= cutoff:
                temporary.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_write_json(path: Path, payload: dict | list) -> None:
    """Durably replace a JSON file without exposing partial contents."""
    target = Path(path)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    created_directories = _created_parent_directories(target.parent)
    _cleanup_stale_temporaries(target)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
        _fsync_directory(target.parent)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        _cleanup_empty_directories(created_directories)
        raise

def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Durably replace a file while preserving an exact byte snapshot."""
    target = Path(path)
    created_directories = _created_parent_directories(target.parent)
    _cleanup_stale_temporaries(target)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
        _fsync_directory(target.parent)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        _cleanup_empty_directories(created_directories)
        raise