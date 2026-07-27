from __future__ import annotations

from pathlib import Path

import pytest

from rl.common import evaluator as evaluator_module
from rl.common import isolation
from rl.common.evaluator import PixCellEvaluator
from rl.common.isolation import ExecutionBoundary, IsolationError


def _boundary(tmp_path: Path) -> ExecutionBoundary:
    return ExecutionBoundary(
        runtime_path=tmp_path / "docker",
        daemon_endpoint="unix:///var/run/docker.sock",
        image_ref="sha256:" + "a" * 64,
        image_id="sha256:" + "a" * 64,
        workspace_root=tmp_path,
    )


def test_candidate_container_command_enforces_per_program_boundary(tmp_path):
    boundary = _boundary(tmp_path)
    command = boundary.create_command(
        tmp_path.resolve(),
        candidate_id="c" * 32,
    )
    rendered = " ".join(command)
    assert "create" in command
    assert "--network none" in rendered
    assert "--read-only" in command
    assert "--cap-drop ALL" in rendered
    assert "--cap-add KILL" in rendered
    assert "--cap-add SETGID" in rendered
    assert "--cap-add SETUID" in rendered
    assert "--security-opt no-new-privileges:true" in rendered
    assert "--memory-swap" in command
    assert "--pids-limit" in command
    assert "--log-driver none" in rendered
    assert "dst=/input,readonly" in rendered
    assert "/work:rw,nosuid,nodev,noexec" in rendered
    assert "/status:rw,nosuid,nodev,noexec" in rendered
    assert "--entrypoint /usr/local/bin/python" in rendered
    assert "/usr/local/lib/pixcell/supervise.py" in command
    assert "PIXCELL_EVAL_HOLD=1" not in command
    assert not any("TINKER" in value for value in command)


def test_execution_boundary_requires_immutable_image(monkeypatch, tmp_path):
    runtime = tmp_path / "docker"
    monkeypatch.setattr(isolation.os, "getuid", lambda: 1000)
    monkeypatch.setenv(isolation.IMAGE_ENV, "pixcell-evaluator:latest")
    monkeypatch.setattr(isolation, "_trusted_runtime", lambda: runtime)
    monkeypatch.setattr(
        isolation,
        "_require_local_daemon",
        lambda _runtime: "unix:///var/run/docker.sock",
    )
    with pytest.raises(IsolationError, match="immutable image"):
        isolation.require_execution_boundary()


def test_execution_boundary_binds_resolved_image(monkeypatch, tmp_path):
    runtime = tmp_path / "docker"
    image = "sha256:" + "b" * 64
    monkeypatch.setattr(isolation.os, "getuid", lambda: 1000)
    monkeypatch.setenv(isolation.IMAGE_ENV, image)
    monkeypatch.setattr(isolation, "_trusted_runtime", lambda: runtime)
    monkeypatch.setattr(
        isolation,
        "_require_local_daemon",
        lambda _runtime: "unix:///var/run/docker.sock",
    )
    monkeypatch.setattr(
        isolation,
        "_resolve_image",
        lambda _runtime, _endpoint, _image: image,
    )
    monkeypatch.setattr(isolation, "_workspace_root", lambda: tmp_path)
    boundary = isolation.require_execution_boundary()
    assert boundary.runtime_path == runtime
    assert boundary.daemon_endpoint == "unix:///var/run/docker.sock"
    assert boundary.image_ref == image
    assert boundary.image_id == image


def test_image_must_carry_current_sandbox_spec_label(monkeypatch, tmp_path):
    runtime = tmp_path / "docker"
    image = "sha256:" + "c" * 64
    monkeypatch.setattr(isolation, "sandbox_spec_sha256", lambda: "d" * 64)
    monkeypatch.setattr(
        isolation,
        "_checked_json",
        lambda _command: [
            {
                "Id": image,
                "RepoDigests": [],
                "Config": {"Labels": {}},
            }
        ],
    )
    with pytest.raises(IsolationError, match="committed sandbox specification"):
        isolation._resolve_image(
            runtime,
            "unix:///var/run/docker.sock",
            image,
        )


def test_evaluator_fails_closed_when_isolation_is_required(monkeypatch):
    def reject():
        raise IsolationError("missing boundary")

    monkeypatch.setattr(evaluator_module, "require_execution_boundary", reject)
    with pytest.raises(IsolationError, match="missing boundary"):
        PixCellEvaluator(require_isolation=True)


def test_child_environment_is_allowlisted(monkeypatch, tmp_path):
    monkeypatch.setenv("TINKER_API_KEY", "must-not-leak")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/private/agent.sock")
    evaluator = PixCellEvaluator()
    environment = evaluator._child_environment(tmp_path)
    assert "TINKER_API_KEY" not in environment
    assert "SSH_AUTH_SOCK" not in environment
    assert environment["HOME"] == str(tmp_path)
    assert environment["TMPDIR"] == str(tmp_path)
    assert environment["PYTHONNOUSERSITE"] == "1"
