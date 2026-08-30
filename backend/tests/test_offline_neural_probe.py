"""Pure tests for the subprocess-based offline neural probe."""

import json
import subprocess
from pathlib import Path

from eval import offline_neural_probe as probe


def _snapshots(tmp_path):
    for configuration in probe.COMPONENTS.values():
        (
            tmp_path
            / configuration["cache_name"]
            / "snapshots"
            / configuration["commit"]
        ).mkdir(parents=True)
    return probe.locate_snapshots(tmp_path)


def _success_process(component):
    configuration = probe.COMPONENTS[component]
    payload = {
        "component": component,
        "status": "ok",
        "snapshot_commit": configuration["commit"],
        "output_shape": configuration["output_shape"],
        "finite": True,
        "network_attempts": 0,
        "stderr": "",
        "error": None,
    }
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(payload) + "\n", stderr=""
    )


def _component_from_command(command):
    return command[command.index("--component") + 1]


def _run(tmp_path, runner, **kwargs):
    _snapshots(tmp_path)
    return probe.run_probe(
        5,
        runner=runner,
        cache_dir=tmp_path,
        executable=probe.EXPECTED_INTERPRETER,
        versions={"python": "3.11.5", "torch": "test"},
        timestamp="2026-08-30T00:00:00+00:00",
        **kwargs,
    )


def test_required_offline_variables_are_forced():
    env = {}

    values = probe.set_offline_environment(env)

    assert values == probe.REQUIRED_OFFLINE_ENV
    assert env == probe.REQUIRED_OFFLINE_ENV


def test_probe_declares_exactly_three_components():
    assert tuple(probe.COMPONENTS) == (
        "dense",
        "rerank_multilingual",
        "rerank_english",
    )


def test_parent_succeeds_only_with_three_valid_zero_network_results(tmp_path):
    summary = _run(
        tmp_path,
        lambda command, **kwargs: _success_process(
            _component_from_command(command)
        ),
    )

    assert summary["offline_probe_ok"] is True
    assert summary["total_network_attempts"] == 0
    assert len(summary["results"]) == 3
    assert summary["failures"] == []


def test_nonzero_returncode_blocks_success(tmp_path):
    def runner(command, **kwargs):
        component = _component_from_command(command)
        process = _success_process(component)
        process.returncode = 1
        return process

    summary = _run(tmp_path, runner)

    assert summary["offline_probe_ok"] is False
    assert all(result["status"] == "error" for result in summary["results"])


def test_network_attempt_blocks_success(tmp_path):
    def runner(command, **kwargs):
        component = _component_from_command(command)
        process = _success_process(component)
        payload = json.loads(process.stdout)
        payload["network_attempts"] = 1
        process.stdout = json.dumps(payload) + "\n"
        return process

    summary = _run(tmp_path, runner)

    assert summary["offline_probe_ok"] is False
    assert summary["total_network_attempts"] == 3


def test_invalid_child_json_blocks_success(tmp_path):
    summary = _run(
        tmp_path,
        lambda command, **kwargs: subprocess.CompletedProcess(
            args=command, returncode=0, stdout="not-json\n", stderr=""
        ),
    )

    assert summary["offline_probe_ok"] is False
    assert summary["total_network_attempts"] is None
    assert "invalid child JSON" in summary["failures"][0]["error"]


def test_missing_snapshot_blocks_success_without_launching_it(tmp_path):
    _snapshots(tmp_path)
    missing = probe.COMPONENTS["rerank_english"]
    path = tmp_path / missing["cache_name"] / "snapshots" / missing["commit"]
    path.rmdir()
    launched = []

    def runner(command, **kwargs):
        component = _component_from_command(command)
        launched.append(component)
        return _success_process(component)

    summary = probe.run_probe(
        5,
        runner=runner,
        cache_dir=tmp_path,
        executable=probe.EXPECTED_INTERPRETER,
        versions={},
    )

    assert summary["offline_probe_ok"] is False
    assert "rerank_english" not in launched
    assert "snapshot absent" in summary["failures"][0]["error"]


def test_timeout_blocks_success(tmp_path):
    def runner(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    summary = _run(tmp_path, runner)

    assert summary["offline_probe_ok"] is False
    assert summary["total_network_attempts"] is None
    assert "timeout" in summary["failures"][0]["error"]


def test_segmentation_fault_is_reported(tmp_path):
    summary = _run(
        tmp_path,
        lambda command, **kwargs: subprocess.CompletedProcess(
            args=command,
            returncode=139,
            stdout="",
            stderr="Segmentation fault",
        ),
    )

    assert summary["offline_probe_ok"] is False
    assert summary["failures"][0]["error"] == "Segmentation fault"


def test_winerror_1114_is_reported(tmp_path):
    summary = _run(
        tmp_path,
        lambda command, **kwargs: subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout="",
            stderr="OSError: [WinError 1114] DLL initialization failed",
        ),
    )

    assert summary["offline_probe_ok"] is False
    assert summary["failures"][0]["error"] == "WinError 1114"


def test_summary_preserves_versions_commits_and_errors(tmp_path):
    summary = _run(
        tmp_path,
        lambda command, **kwargs: subprocess.CompletedProcess(
            args=command, returncode=1, stdout="", stderr="failed"
        ),
    )

    assert summary["versions"] == {"python": "3.11.5", "torch": "test"}
    assert {
        value["commit"] for value in summary["snapshots"].values()
    } == {configuration["commit"] for configuration in probe.COMPONENTS.values()}
    assert len(summary["failures"]) == 3


def test_probe_source_does_not_import_benchmark_or_corpus():
    source = Path(probe.__file__).read_text(encoding="utf-8")

    assert "eval.benchmark" not in source
    assert "enhanced_rag" not in source
    assert "build_chunks" not in source


def test_venv311_is_rejected():
    assert probe.interpreter_error(Path(r"C:\project\venv311\Scripts\python.exe"))
    assert probe.interpreter_error(probe.EXPECTED_INTERPRETER) is None