"""Reusable offline availability probe for the neural evaluation models."""

from __future__ import annotations

import os


REQUIRED_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "TOKENIZERS_PARALLELISM": "false",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
}


def set_offline_environment(env=None) -> dict[str, str]:
    """Force the environment used by the parent and every probe child."""
    target = os.environ if env is None else env
    target.update(REQUIRED_OFFLINE_ENV)
    return {name: target[name] for name in REQUIRED_OFFLINE_ENV}


set_offline_environment()

import argparse
import contextlib
import importlib.metadata
import io
import json
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


PROBE_VERSION = "1.0"
EXPECTED_INTERPRETER = Path(
    r"C:\venvs\unirIntegracionCultural\venv-rag-eval-probe\Scripts\python.exe"
)
COMPONENTS: dict[str, dict[str, Any]] = {
    "dense": {
        "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "cache_name": "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2",
        "commit": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
        "output_shape": [1, 384],
    },
    "rerank_multilingual": {
        "model_id": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        "cache_name": "models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1",
        "commit": "1427fd652930e4ba29e8149678df786c240d8825",
        "output_shape": [1],
    },
    "rerank_english": {
        "model_id": "cross-encoder/ms-marco-MiniLM-L-12-v2",
        "cache_name": "models--cross-encoder--ms-marco-MiniLM-L-12-v2",
        "commit": "7b0235231ca2674cb8ca8f022859a6eba2b1c968",
        "output_shape": [1],
    },
}
VERSION_PACKAGES = (
    "torch",
    "sentence-transformers",
    "transformers",
    "huggingface-hub",
    "rank-bm25",
)


def _hub_cache(env: Optional[Mapping[str, str]] = None) -> Path:
    values = os.environ if env is None else env
    if values.get("HF_HUB_CACHE"):
        return Path(values["HF_HUB_CACHE"])
    if values.get("HF_HOME"):
        return Path(values["HF_HOME"]) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def locate_snapshots(cache_dir: Optional[Path] = None) -> dict[str, dict[str, Any]]:
    """Resolve required snapshots without consulting the Hugging Face Hub."""
    cache = cache_dir or _hub_cache()
    snapshots = {}
    for component, configuration in COMPONENTS.items():
        path = (
            cache
            / configuration["cache_name"]
            / "snapshots"
            / configuration["commit"]
        )
        snapshots[component] = {
            "model_id": configuration["model_id"],
            "commit": configuration["commit"],
            "path": str(path),
            "exists": path.is_dir(),
        }
    return snapshots


def runtime_versions() -> dict[str, str]:
    versions = {"python": sys.version.split()[0]}
    for package in VERSION_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "missing"
    return versions


def interpreter_error(executable: Path) -> Optional[str]:
    normalized = os.path.normcase(os.path.abspath(str(executable)))
    expected = os.path.normcase(os.path.abspath(str(EXPECTED_INTERPRETER)))
    if "venv311" in normalized:
        return "venv311 is not authorized for the offline neural probe"
    if normalized != expected:
        return f"unauthorized probe interpreter: {executable}"
    return None


def _install_network_barriers(attempts: list[str]) -> None:
    def blocked(*args, **kwargs):
        attempts.append(repr(args[:2]))
        raise RuntimeError("network attempt blocked by offline neural probe")

    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    urllib.request.urlopen = blocked


def run_component(component: str, snapshot_path: Path) -> tuple[dict, int]:
    """Load and infer with one model in an isolated child process."""
    configuration = COMPONENTS[component]
    attempts: list[str] = []
    _install_network_barriers(attempts)
    library_stdout = io.StringIO()
    library_stderr = io.StringIO()
    payload = {
        "component": component,
        "status": "error",
        "snapshot_commit": configuration["commit"],
        "output_shape": [],
        "finite": False,
        "network_attempts": 0,
        "stderr": "",
        "error": None,
    }

    try:
        if not snapshot_path.is_dir():
            raise FileNotFoundError(f"snapshot absent: {snapshot_path}")
        with contextlib.redirect_stdout(library_stdout), contextlib.redirect_stderr(
            library_stderr
        ):
            import numpy as np
            from sentence_transformers import CrossEncoder, SentenceTransformer

            if component == "dense":
                model = SentenceTransformer(
                    str(snapshot_path), local_files_only=True, device="cpu"
                )
                output = np.asarray(
                    model.encode(
                        ["offline neural availability probe"],
                        convert_to_numpy=True,
                        show_progress_bar=False,
                    )
                )
            else:
                model = CrossEncoder(
                    str(snapshot_path), local_files_only=True, device="cpu"
                )
                pair = (
                    ("registro migratorio", "documentos para registro")
                    if component == "rerank_multilingual"
                    else ("student visa", "visa requirements")
                )
                output = np.asarray(
                    model.predict([pair], show_progress_bar=False)
                )

        payload["output_shape"] = list(output.shape)
        payload["finite"] = bool(np.isfinite(output).all())
        if payload["output_shape"] != configuration["output_shape"]:
            raise ValueError(
                f"invalid output shape: {payload['output_shape']}"
            )
        if not payload["finite"]:
            raise ValueError("model output contains non-finite values")
        payload["status"] = "ok"
    except BaseException as exc:  # noqa: BLE001 - child must report model failures
        payload["error"] = f"{type(exc).__name__}: {exc}"

    payload["network_attempts"] = len(attempts)
    captured_stderr = library_stderr.getvalue().strip()
    captured_stdout = library_stdout.getvalue().strip()
    payload["stderr"] = captured_stderr
    if captured_stdout:
        payload["library_stdout"] = captured_stdout
    if attempts:
        payload["status"] = "error"
        payload["error"] = payload["error"] or "network attempt detected"
    ok = payload["status"] == "ok" and not attempts
    return payload, 0 if ok else 1


def _process_failure(returncode: int, stdout: str, stderr: str) -> str:
    details = f"{stdout}\n{stderr}".lower()
    if "segmentation fault" in details or returncode in {139, -11}:
        return "Segmentation fault"
    if "winerror 1114" in details:
        return "WinError 1114"
    return f"subprocess exited with return code {returncode}"


def _parse_child_result(
    component: str,
    snapshot: Mapping[str, Any],
    process: subprocess.CompletedProcess,
) -> dict:
    stdout = process.stdout or ""
    stderr = process.stderr or ""
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        return {
            "component": component,
            "status": "error",
            "snapshot_commit": snapshot["commit"],
            "output_shape": [],
            "finite": False,
            "network_attempts": None,
            "returncode": process.returncode,
            "stderr": stderr.strip(),
            "error": (
                _process_failure(process.returncode, stdout, stderr)
                if process.returncode
                else "invalid child JSON: expected exactly one stdout line"
            ),
        }
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        return {
            "component": component,
            "status": "error",
            "snapshot_commit": snapshot["commit"],
            "output_shape": [],
            "finite": False,
            "network_attempts": None,
            "returncode": process.returncode,
            "stderr": stderr.strip(),
            "error": f"invalid child JSON: {exc}",
        }

    payload["returncode"] = process.returncode
    payload["stderr"] = "\n".join(
        value for value in (str(payload.get("stderr", "")).strip(), stderr.strip()) if value
    )
    expected_shape = COMPONENTS[component]["output_shape"]
    network_attempts = payload.get("network_attempts")
    valid = (
        payload.get("component") == component
        and payload.get("status") == "ok"
        and payload.get("snapshot_commit") == snapshot["commit"]
        and payload.get("output_shape") == expected_shape
        and payload.get("finite") is True
        and isinstance(network_attempts, int)
        and not isinstance(network_attempts, bool)
        and network_attempts == 0
        and process.returncode == 0
    )
    if not valid:
        payload["status"] = "error"
        payload["error"] = payload.get("error") or (
            _process_failure(process.returncode, stdout, stderr)
            if process.returncode
            else "child result failed validation"
        )
    return payload


def _failed_result(component: str, snapshot: Mapping[str, Any], error: str) -> dict:
    return {
        "component": component,
        "status": "error",
        "snapshot_commit": snapshot["commit"],
        "output_shape": [],
        "finite": False,
        "network_attempts": 0,
        "returncode": None,
        "stderr": "",
        "error": error,
    }


def _probe_ok(results: Sequence[Mapping[str, Any]]) -> bool:
    if {result.get("component") for result in results} != set(COMPONENTS):
        return False
    return all(
        result.get("status") == "ok"
        and result.get("returncode") == 0
        and result.get("finite") is True
        and result.get("output_shape") == COMPONENTS[result["component"]]["output_shape"]
        and result.get("network_attempts") == 0
        for result in results
    )


def build_summary(
    results: Sequence[Mapping[str, Any]],
    snapshots: Mapping[str, Mapping[str, Any]],
    *,
    executable: Path,
    versions: Optional[Mapping[str, str]] = None,
    timestamp: Optional[str] = None,
) -> dict:
    attempts = [result.get("network_attempts") for result in results]
    attempts_complete = all(
        isinstance(value, int) and not isinstance(value, bool) for value in attempts
    )
    total_attempts = sum(attempts) if attempts_complete else None
    failures = [
        {
            "component": result.get("component"),
            "error": result.get("error") or "probe component failed",
        }
        for result in results
        if result.get("status") != "ok"
    ]
    interpreter_failure = interpreter_error(executable)
    if interpreter_failure:
        failures.insert(0, {"component": "parent", "error": interpreter_failure})
    offline_probe_ok = (
        interpreter_failure is None
        and attempts_complete
        and total_attempts == 0
        and _probe_ok(results)
    )
    return {
        "probe_version": PROBE_VERSION,
        "timestamp_utc": timestamp
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": {
            "python_executable": str(executable),
            "expected_python_executable": str(EXPECTED_INTERPRETER),
            "offline_variables": {
                name: os.environ.get(name) for name in REQUIRED_OFFLINE_ENV
            },
        },
        "versions": dict(versions or runtime_versions()),
        "snapshots": dict(snapshots),
        "results": list(results),
        "total_network_attempts": total_attempts,
        "network_attempts_complete": attempts_complete,
        "offline_probe_ok": offline_probe_ok,
        "failures": failures,
    }


def run_probe(
    timeout: float,
    *,
    runner=subprocess.run,
    cache_dir: Optional[Path] = None,
    executable: Optional[Path] = None,
    versions: Optional[Mapping[str, str]] = None,
    timestamp: Optional[str] = None,
) -> dict:
    """Run one clean subprocess per model and return an evidence summary."""
    set_offline_environment()
    python = Path(executable or sys.executable)
    snapshots = locate_snapshots(cache_dir)
    parent_error = interpreter_error(python)
    results = []

    for component, snapshot in snapshots.items():
        if parent_error:
            results.append(_failed_result(component, snapshot, parent_error))
            continue
        if not snapshot["exists"]:
            results.append(
                _failed_result(
                    component, snapshot, f"snapshot absent: {snapshot['path']}"
                )
            )
            continue
        command = [
            str(python),
            str(Path(__file__).resolve()),
            "--component",
            component,
            "--snapshot",
            snapshot["path"],
        ]
        try:
            process = runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired:
            timed_out = _failed_result(
                component, snapshot, f"subprocess timeout after {timeout} seconds"
            )
            timed_out["network_attempts"] = None
            results.append(timed_out)
            continue
        results.append(_parse_child_result(component, snapshot, process))

    return build_summary(
        results,
        snapshots,
        executable=python,
        versions=versions,
        timestamp=timestamp,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--component", choices=tuple(COMPONENTS), help=argparse.SUPPRESS)
    parser.add_argument("--snapshot", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.component:
        if args.snapshot is None:
            payload = _failed_result(
                args.component,
                {"commit": COMPONENTS[args.component]["commit"]},
                "component mode requires --snapshot",
            )
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return 1
        payload, returncode = run_component(args.component, args.snapshot)
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return returncode

    summary = run_probe(args.timeout)
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0 if summary["offline_probe_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())