"""Atomic persistence primitives for retrieval evaluation result artifacts."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ARTIFACT_COUNT = 6


class ArtifactValidationError(ValueError):
    """Raised when a staged result artifact does not satisfy its contract."""


def _temporary_path(target: Path) -> tuple[object, Path]:
    if not target.parent.is_dir():
        raise FileNotFoundError(f"Artifact directory does not exist: {target.parent}")

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    )
    return handle, Path(handle.name)


def _flush_and_sync(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def atomic_write_json(target: Path, payload: Any) -> None:
    """Write JSON durably to a temporary sibling, then replace ``target``."""
    target = Path(target)
    handle, temporary = _temporary_path(target)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            _flush_and_sync(handle)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_csv(
    target: Path,
    rows: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    """Write CSV durably to a temporary sibling, then replace ``target``."""
    target = Path(target)
    handle, temporary = _temporary_path(target)
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            _flush_and_sync(handle)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def validate_json(path: Path) -> None:
    """Parse an existing JSON artifact without syncing its read-only handle."""
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"Invalid JSON artifact {path}: {exc}") from exc


def validate_csv(path: Path) -> None:
    """Parse a non-empty CSV artifact without syncing its read-only handle."""
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if not header or any(not column.strip() for column in header):
                raise ArtifactValidationError(
                    f"Invalid CSV artifact {path}: missing or empty header"
                )
            list(reader)
    except ArtifactValidationError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ArtifactValidationError(f"Invalid CSV artifact {path}: {exc}") from exc


def validate_artifact_windows_safe(path: Path) -> None:
    """Validate JSON/CSV using read-only parsing and no ``fsync`` operation."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        validate_json(path)
    elif path.suffix.lower() == ".csv":
        validate_csv(path)
    else:
        raise ArtifactValidationError(
            f"Unsupported artifact type for {path}; expected JSON or CSV"
        )


def publish_staging(
    staging: Path,
    final: Path,
    expected_artifacts: Iterable[str],
) -> None:
    """Validate exactly six staged artifacts, then atomically publish the directory."""
    staging = Path(staging)
    final = Path(final)
    expected = tuple(expected_artifacts)
    expected_set = set(expected)

    if len(expected) != ARTIFACT_COUNT or len(expected_set) != ARTIFACT_COUNT:
        raise ArtifactValidationError(
            f"Expected artifact contract must contain exactly {ARTIFACT_COUNT} unique names"
        )
    if any(Path(name).name != name for name in expected):
        raise ArtifactValidationError("Expected artifact names must not contain paths")
    if not staging.is_dir():
        raise FileNotFoundError(f"Staging directory does not exist: {staging}")
    if final.exists():
        raise FileExistsError(f"Final result path already exists: {final}")

    entries = list(staging.iterdir())
    directories = [entry.name for entry in entries if not entry.is_file()]
    if directories:
        raise ArtifactValidationError(
            f"Staging contains non-file entries: {sorted(directories)}"
        )

    actual_set = {entry.name for entry in entries}
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        unexpected = sorted(actual_set - expected_set)
        raise ArtifactValidationError(
            f"Staging artifact set mismatch; missing={missing}, unexpected={unexpected}"
        )

    for name in sorted(expected_set):
        validate_artifact_windows_safe(staging / name)

    if final.exists():
        raise FileExistsError(f"Final result path appeared during validation: {final}")
    os.replace(staging, final)