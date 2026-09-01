"""Tests for atomic evaluation-result persistence without real result data."""

from __future__ import annotations

import csv
import errno
import json
import os
from pathlib import Path

import pytest

from eval.transactional_result_persistence import (
    ArtifactValidationError,
    atomic_write_csv,
    atomic_write_json,
    publish_staging,
    validate_artifact_windows_safe,
    validate_csv,
    validate_json,
)


ARTIFACT_NAMES = (
    "full.json",
    "summary.csv",
    "queries.csv",
    "languages.csv",
    "categories.csv",
    "bootstrap.json",
)


def _create_valid_staging(root: Path) -> Path:
    staging = root / ".results.staging"
    staging.mkdir()
    for name in ARTIFACT_NAMES:
        path = staging / name
        if path.suffix == ".json":
            path.write_text('{"valid": true}\n', encoding="utf-8")
        else:
            path.write_text("method,score\nkeyword,1.0\n", encoding="utf-8")
    return staging


def _assert_unpublished(staging: Path, final: Path) -> None:
    assert staging.is_dir()
    assert {path.name for path in staging.iterdir()} == set(ARTIFACT_NAMES)
    assert not final.exists()


def test_atomic_write_json(tmp_path: Path) -> None:
    target = tmp_path / "result.json"

    atomic_write_json(target, {"language": "ru", "score": 1.0})

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "language": "ru",
        "score": 1.0,
    }
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_csv(tmp_path: Path) -> None:
    target = tmp_path / "summary.csv"

    atomic_write_csv(
        target,
        [{"method": "dense", "score": 0.75}],
        fieldnames=("method", "score"),
    )

    with target.open("r", encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle)) == [{"method": "dense", "score": "0.75"}]
    assert list(tmp_path.iterdir()) == [target]


def test_validate_json_does_not_fsync_read_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "result.json"
    artifact.write_text('{"ok": true}', encoding="utf-8")
    calls = []
    monkeypatch.setattr(os, "fsync", lambda descriptor: calls.append(descriptor))

    validate_json(artifact)

    assert calls == []


def test_validate_csv_does_not_fsync_read_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "summary.csv"
    artifact.write_text("method,score\nbm25,1.0\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(os, "fsync", lambda descriptor: calls.append(descriptor))

    validate_csv(artifact)

    assert calls == []


def test_publish_staging_atomically_with_six_files(tmp_path: Path) -> None:
    staging = _create_valid_staging(tmp_path)
    final = tmp_path / "results"

    publish_staging(staging, final, ARTIFACT_NAMES)

    assert not staging.exists()
    assert final.is_dir()
    assert {path.name for path in final.iterdir()} == set(ARTIFACT_NAMES)


def test_publish_rejects_missing_artifact_and_preserves_staging(tmp_path: Path) -> None:
    staging = _create_valid_staging(tmp_path)
    (staging / ARTIFACT_NAMES[-1]).unlink()
    final = tmp_path / "results"

    with pytest.raises(ArtifactValidationError, match="missing=.*bootstrap.json"):
        publish_staging(staging, final, ARTIFACT_NAMES)

    assert staging.is_dir()
    assert not final.exists()


def test_publish_rejects_existing_final(tmp_path: Path) -> None:
    staging = _create_valid_staging(tmp_path)
    final = tmp_path / "results"
    final.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        publish_staging(staging, final, ARTIFACT_NAMES)

    assert staging.is_dir()
    assert final.is_dir()


def test_publish_rejects_staging_subdirectory(tmp_path: Path) -> None:
    staging = _create_valid_staging(tmp_path)
    (staging / ARTIFACT_NAMES[-1]).unlink()
    (staging / ARTIFACT_NAMES[-1]).mkdir()
    final = tmp_path / "results"

    with pytest.raises(ArtifactValidationError, match="non-file entries"):
        publish_staging(staging, final, ARTIFACT_NAMES)

    assert staging.is_dir()
    assert not final.exists()


def test_publish_rejects_invalid_json(tmp_path: Path) -> None:
    staging = _create_valid_staging(tmp_path)
    (staging / "full.json").write_text("{invalid", encoding="utf-8")
    final = tmp_path / "results"

    with pytest.raises(ArtifactValidationError, match="Invalid JSON"):
        publish_staging(staging, final, ARTIFACT_NAMES)

    _assert_unpublished(staging, final)


def test_publish_rejects_invalid_csv(tmp_path: Path) -> None:
    staging = _create_valid_staging(tmp_path)
    (staging / "summary.csv").write_text('method,score\n"unterminated', encoding="utf-8")
    final = tmp_path / "results"

    with pytest.raises(ArtifactValidationError, match="Invalid CSV"):
        publish_staging(staging, final, ARTIFACT_NAMES)

    _assert_unpublished(staging, final)


def test_fsync_write_error_leaves_no_target_or_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "result.json"

    def fail_fsync(_descriptor: int) -> None:
        raise OSError(errno.EBADF, "Bad file descriptor")

    monkeypatch.setattr(os, "fsync", fail_fsync)

    with pytest.raises(OSError, match="Bad file descriptor"):
        atomic_write_json(target, {"ok": True})

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_validation_error_does_not_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staging = _create_valid_staging(tmp_path)
    final = tmp_path / "results"

    def fail_validation(_path: Path) -> None:
        raise ArtifactValidationError("simulated validation failure")

    monkeypatch.setattr(
        "eval.transactional_result_persistence.validate_artifact_windows_safe",
        fail_validation,
    )

    with pytest.raises(ArtifactValidationError, match="simulated validation failure"):
        publish_staging(staging, final, ARTIFACT_NAMES)

    _assert_unpublished(staging, final)


def test_windows_safe_read_validation_cannot_raise_bad_file_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "result.json"
    artifact.write_text('{"ok": true}', encoding="utf-8")

    def bad_descriptor_if_called(_descriptor: int) -> None:
        raise OSError(errno.EBADF, "Bad file descriptor")

    monkeypatch.setattr(os, "fsync", bad_descriptor_if_called)

    validate_artifact_windows_safe(artifact)


@pytest.mark.parametrize("failure", ["invalid_json", "invalid_csv"])
def test_failed_publication_keeps_staging_intact_and_final_absent(
    tmp_path: Path, failure: str
) -> None:
    staging = _create_valid_staging(tmp_path)
    final = tmp_path / "results"
    if failure == "invalid_json":
        (staging / "bootstrap.json").write_text("not-json", encoding="utf-8")
    else:
        (staging / "queries.csv").write_text('query,score\n"broken', encoding="utf-8")

    with pytest.raises(ArtifactValidationError):
        publish_staging(staging, final, ARTIFACT_NAMES)

    _assert_unpublished(staging, final)