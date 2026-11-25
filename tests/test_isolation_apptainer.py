"""Unit tests for the opt-in Apptainer candidate isolation backend.

Verifies exact Apptainer command construction, fail-closed SHA-256 and
``SANDBOX_SPEC_LABEL`` enforcement, ``0700`` per-candidate temp-dir hygiene,
allowlisted host environment, symlink rejection, fault classification,
safe shared-UID ``RLIMIT_NPROC`` handling, and zero regression on the default
Docker backend.
"""

from __future__ import annotations

import errno
import hashlib
import os
import resource
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from rl.common import isolation
from rl.common.evaluator import EvaluationStatus, PixCellEvaluator
from rl.common.isolation import (
    APPTAINER_PROCESS_LIMIT,
    BACKEND_ENV,
    IMAGE_ENV,
    MEMORY_LIMIT_BYTES,
    SIF_ENV,
    SIF_SHA256_ENV,
    WORKSPACE_ROOT_ENV,
    ExecutionBoundary,
    IsolationError,
)
from rl.common.sandbox_spec import SANDBOX_SPEC_LABEL


def _make_sif(tmp_path: Path, payload: bytes = b"fake-sif-image-bytes") -> tuple[Path, str]:
    sif = tmp_path / "evaluator.sif"
    sif.write_bytes(payload)
    sif.chmod(0o644)
    digest = hashlib.sha256(payload).hexdigest()
    return sif, digest


def _apptainer_boundary(tmp_path: Path, runtime: Path | None = None) -> ExecutionBoundary:
    sif, digest = _make_sif(tmp_path)
    return ExecutionBoundary(
        runtime_path=runtime or (tmp_path / "apptainer"),
        daemon_endpoint="",
        image_ref=str(sif.resolve()),
        image_id=f"sha256:{digest}",
        workspace_root=tmp_path,
        pids_limit=APPTAINER_PROCESS_LIMIT,
        backend="apptainer",
    )


def _env_pairs(command: list[str]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for index, token in enumerate(command):
        if token == "--env" and index + 1 < len(command):
            key, value = command[index + 1].split("=", 1)
            pairs[key] = value
    return pairs


def test_default_backend_remains_docker_when_unset_or_docker(monkeypatch, tmp_path: Path) -> None:
    runtime = tmp_path / "docker"
    image = "sha256:" + "a" * 64
    monkeypatch.delenv(BACKEND_ENV, raising=False)
    monkeypatch.setattr(isolation.os, "getuid", lambda: 1000)
    monkeypatch.setenv(IMAGE_ENV, image)
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

    for value in (None, "", "docker"):
        if value is None:
            monkeypatch.delenv(BACKEND_ENV, raising=False)
        else:
            monkeypatch.setenv(BACKEND_ENV, value)
        boundary = isolation.require_execution_boundary()
        assert boundary.backend == "docker"
        assert boundary.runtime_path == runtime
        assert boundary.image_id == image


def test_unsupported_backend_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(isolation.os, "getuid", lambda: 1000)
    monkeypatch.setenv(BACKEND_ENV, "podman")
    with pytest.raises(IsolationError, match="unsupported PIXCELL_EVALUATOR_BACKEND"):
        isolation.require_execution_boundary()


def test_apptainer_exec_command_construction_and_limits(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TINKER_API_KEY", "secret-must-not-appear")
    monkeypatch.setenv("WANDB_API_KEY", "secret-must-not-appear")
    boundary = _apptainer_boundary(tmp_path)
    input_dir = (tmp_path / "input").resolve()
    work_dir = (tmp_path / "work").resolve()

    command = boundary.exec_command(input_dir, work_dir)

    assert command[0] == str(boundary.runtime_path)
    assert command[1:10] == [
        "exec",
        "--containall",
        "--cleanenv",
        "--no-home",
        "--net",
        "--network=none",
        "--pid",
        "--writable-tmpfs",
        "--bind",
    ]
    assert f"{input_dir}:/input:ro" in command
    assert f"{work_dir}:/work:rw" in command
    pwd_idx = command.index("--pwd")
    assert command[pwd_idx + 1] == "/work"
    assert command[-4:] == [
        boundary.image_ref,
        "/usr/local/bin/python",
        "/input/execute.py",
        "/input/device.py",
    ]

    envs = _env_pairs(command)
    assert envs["HOME"] == "/work"
    assert envs["MPLBACKEND"] == "Agg"
    assert envs["OMP_NUM_THREADS"] == "1"
    assert envs["OPENBLAS_NUM_THREADS"] == "1"
    assert envs["MKL_NUM_THREADS"] == "1"
    assert envs["NUMEXPR_NUM_THREADS"] == "1"
    assert envs["VECLIB_MAXIMUM_THREADS"] == "1"
    assert envs["PYTHONHASHSEED"] == "0"
    assert envs["PYTHONDONTWRITEBYTECODE"] == "1"
    assert envs["PYTHONNOUSERSITE"] == "1"
    assert envs["PIXCELL_EVAL_CPU_SECONDS"] == "18"
    assert envs["PIXCELL_EVAL_FILE_BYTES"] == str(16 * 1024 * 1024)
    assert envs["PIXCELL_EVAL_OPEN_FILES"] == "128"
    assert envs["PIXCELL_EVAL_ADDRESS_BYTES"] == str(MEMORY_LIMIT_BYTES)
    assert envs["PIXCELL_EVAL_REQUIRE_LIMITS"] == "1"
    # Shared HPC host UID safe NPROC ceiling (clamped to host hard limit in execute.py)
    assert int(envs["PIXCELL_EVAL_PROCESS_COUNT"]) == APPTAINER_PROCESS_LIMIT
    assert int(envs["PIXCELL_EVAL_PROCESS_COUNT"]) >= 4096

    assert not any("TINKER" in token or "WANDB" in token for token in command)


def test_backend_command_method_guards_and_path_validation(tmp_path: Path) -> None:
    apptainer = _apptainer_boundary(tmp_path)
    docker = ExecutionBoundary(
        runtime_path=tmp_path / "docker",
        daemon_endpoint="unix:///var/run/docker.sock",
        image_ref="sha256:" + "a" * 64,
        image_id="sha256:" + "a" * 64,
        workspace_root=tmp_path,
    )

    with pytest.raises(IsolationError, match="only valid for the docker backend"):
        apptainer.create_command(tmp_path.resolve(), candidate_id="c" * 32)
    with pytest.raises(IsolationError, match="only valid for the apptainer backend"):
        docker.exec_command((tmp_path / "in").resolve(), (tmp_path / "wk").resolve())

    with pytest.raises(IsolationError, match="must be absolute"):
        apptainer.exec_command(Path("relative/in"), (tmp_path / "wk").resolve())
    with pytest.raises(IsolationError, match="must be absolute"):
        apptainer.exec_command((tmp_path / "in").resolve(), Path("relative/wk"))
    with pytest.raises(IsolationError, match="must be distinct"):
        apptainer.exec_command(tmp_path.resolve(), tmp_path.resolve())
    with pytest.raises(IsolationError, match="forbidden bind character"):
        apptainer.exec_command(Path("/tmp/bad:dir"), (tmp_path / "wk").resolve())
    with pytest.raises(IsolationError, match="forbidden bind character"):
        apptainer.exec_command((tmp_path / "in").resolve(), Path("/tmp/bad,dir"))


def test_apptainer_boundary_requires_sif_sha256_and_spec_label(
    monkeypatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "apptainer"
    sif, digest = _make_sif(tmp_path)
    expected_spec = "e" * 64
    inspected_commands: list[list[str]] = []

    monkeypatch.setattr(isolation.os, "getuid", lambda: 1000)
    monkeypatch.setenv(BACKEND_ENV, "apptainer")
    monkeypatch.setattr(isolation, "_trusted_apptainer_runtime", lambda: runtime)
    monkeypatch.setattr(isolation, "sandbox_spec_sha256", lambda: expected_spec)
    monkeypatch.setattr(isolation, "_workspace_root", lambda: tmp_path)

    # Missing SIF env fails closed
    monkeypatch.delenv(SIF_ENV, raising=False)
    monkeypatch.delenv(SIF_SHA256_ENV, raising=False)
    with pytest.raises(IsolationError, match=SIF_ENV):
        isolation.require_execution_boundary()

    # Missing SHA-256 env fails closed
    monkeypatch.setenv(SIF_ENV, str(sif))
    with pytest.raises(IsolationError, match=SIF_SHA256_ENV):
        isolation.require_execution_boundary()

    # Invalid SHA-256 format fails closed
    monkeypatch.setenv(SIF_SHA256_ENV, "not-a-sha256")
    with pytest.raises(IsolationError, match="64-character lowercase hexadecimal"):
        isolation.require_execution_boundary()

    # Wrong SHA-256 fails closed BEFORE invoking apptainer inspect
    def fake_checked_json(cmd: list[str]):
        inspected_commands.append(cmd)
        return {"type": "container", "data": {"attributes": {"labels": {SANDBOX_SPEC_LABEL: expected_spec}}}}

    monkeypatch.setattr(isolation, "_checked_json", fake_checked_json)
    monkeypatch.setenv(SIF_SHA256_ENV, "0" * 64)
    with pytest.raises(IsolationError, match="SHA-256 mismatch"):
        isolation.require_execution_boundary()
    assert inspected_commands == []

    # Missing / mismatched SANDBOX_SPEC_LABEL fails closed
    monkeypatch.setenv(SIF_SHA256_ENV, digest)
    monkeypatch.setattr(
        isolation,
        "_checked_json",
        lambda _cmd: {"type": "container", "data": {"attributes": {"labels": {}}}},
    )
    with pytest.raises(IsolationError, match="committed sandbox specification"):
        isolation.require_execution_boundary()

    monkeypatch.setattr(
        isolation,
        "_checked_json",
        lambda _cmd: {
            "type": "container",
            "data": {"attributes": {"labels": {SANDBOX_SPEC_LABEL: "f" * 64}}},
        },
    )
    with pytest.raises(IsolationError, match="committed sandbox specification"):
        isolation.require_execution_boundary()

    # World-writable SIF fails closed
    sif.chmod(0o666)
    try:
        with pytest.raises(IsolationError, match="world-writable"):
            isolation.require_execution_boundary()
    finally:
        sif.chmod(0o644)

    # Valid raw hex and sha256:-prefixed digest both succeed and verify apptainer inspect --json
    monkeypatch.setattr(isolation, "_checked_json", fake_checked_json)
    for pin in (digest, f"sha256:{digest}"):
        inspected_commands.clear()
        monkeypatch.setenv(SIF_SHA256_ENV, pin)
        boundary = isolation.require_execution_boundary()
        assert boundary.backend == "apptainer"
        assert boundary.runtime_path == runtime
        assert boundary.image_ref == str(sif.resolve())
        assert boundary.image_id == f"sha256:{digest}"
        assert boundary.pids_limit == APPTAINER_PROCESS_LIMIT
        assert inspected_commands == [[str(runtime), "inspect", "--json", str(sif.resolve())]]


def test_workspace_root_override_enforces_0700_permissions(monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "hpc-scratch-eval"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(custom))
    resolved = isolation._workspace_root()
    assert resolved == custom.resolve()
    assert stat.S_IMODE(resolved.stat().st_mode) == 0o700

    custom.chmod(0o755)
    with pytest.raises(IsolationError, match="mode 0700"):
        isolation._workspace_root()

    regular_file = tmp_path / "not-a-dir"
    regular_file.write_text("file", encoding="utf-8")
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(regular_file))
    with pytest.raises(IsolationError, match="workspace root"):
        isolation._workspace_root()

    # Forbidden bind char in workspace root fails fast during Apptainer preflight
    bad_root = tmp_path / "bad:workspace"
    bad_root.mkdir(mode=0o700)
    sif, digest = _make_sif(tmp_path)
    runtime = tmp_path / "apptainer"
    expected_spec = "e" * 64
    monkeypatch.setenv(BACKEND_ENV, "apptainer")
    monkeypatch.setenv(SIF_ENV, str(sif))
    monkeypatch.setenv(SIF_SHA256_ENV, digest)
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(bad_root))
    monkeypatch.setattr(isolation, "_trusted_apptainer_runtime", lambda: runtime)
    monkeypatch.setattr(isolation, "sandbox_spec_sha256", lambda: expected_spec)
    monkeypatch.setattr(
        isolation,
        "_checked_json",
        lambda _cmd: {
            "type": "container",
            "data": {"attributes": {"labels": {SANDBOX_SPEC_LABEL: expected_spec}}},
        },
    )
    with pytest.raises(IsolationError, match="forbidden bind character"):
        isolation.require_execution_boundary()


def test_apptainer_evaluator_runner_tempdirs_env_isolation_timeouts_and_symlinks(
    monkeypatch, tmp_path: Path
) -> None:
    """Exercise PixCellEvaluator._run_isolated_candidate with an executable stub runtime."""
    from homi.conductor.source_policy import strict_purity_violations

    # Write a tiny executable Python stub masquerading as `apptainer` so we test real Popen,
    # 0700 temp-dir permissions, dedicated apptainer-tmp, 0400 read-only input scripts, clean
    # host env, timeout killpg, symlink refusal, anti-spoofing, chmod-000 cleanup, and real
    # execute.py rlimit failure vs candidate crash attribution.
    stub = tmp_path / "fake-apptainer"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, stat, subprocess, sys\n"
        "argv = sys.argv[1:]\n"
        "assert argv[0] == 'exec'\n"
        "assert 'TINKER_API_KEY' not in os.environ\n"
        "assert 'SSH_AUTH_SOCK' not in os.environ\n"
        "binds = [argv[i+1] for i, t in enumerate(argv) if t == '--bind']\n"
        "in_dir = pathlib.Path(next(b.split(':')[0] for b in binds if b.endswith(':/input:ro')))\n"
        "wk_dir = pathlib.Path(next(b.split(':')[0] for b in binds if b.endswith(':/work:rw')))\n"
        "atmp = pathlib.Path(os.environ['APPTAINER_TMPDIR'])\n"
        "assert atmp.name == 'apptainer-tmp' and atmp != in_dir and atmp != wk_dir\n"
        "assert os.environ['TMPDIR'] == str(atmp)\n"
        "assert os.environ['APPTAINER_LOCALCACHEDIR'] == str(atmp)\n"
        "assert stat.S_IMODE(atmp.stat().st_mode) == 0o700\n"
        "assert stat.S_IMODE(in_dir.stat().st_mode) == 0o700\n"
        "assert stat.S_IMODE(wk_dir.stat().st_mode) == 0o700\n"
        "assert stat.S_IMODE((in_dir / 'device.py').stat().st_mode) == 0o400\n"
        "assert stat.S_IMODE((in_dir / 'execute.py').stat().st_mode) == 0o400\n"
        "src = (in_dir / 'device.py').read_text(encoding='utf-8')\n"
        "if 'SIMULATE_APPTAINER_FATAL' in src:\n"
        "    print('WARNING: skipping mount', file=sys.stderr)\n"
        "    print('FATAL:   container creation failed: namespace error', file=sys.stderr)\n"
        "    raise SystemExit(255)\n"
        "if 'SIMULATE_MISSING_PYTHON' in src:\n"
        "    print('/usr/local/bin/python: not found', file=sys.stderr)\n"
        "    raise SystemExit(127)\n"
        "if 'SIMULATE_SYMLINK_ATTACK' in src:\n"
        "    (wk_dir / 'device.gds').symlink_to('/etc/hosts')\n"
        "    raise SystemExit(0)\n"
        "env = dict(os.environ)\n"
        "for i, t in enumerate(argv):\n"
        "    if t == '--env':\n"
        "        k, v = argv[i+1].split('=', 1)\n"
        "        env[k] = v\n"
        "assert env['PIXCELL_EVAL_REQUIRE_LIMITS'] == '1'\n"
        f"assert env['PIXCELL_EVAL_ADDRESS_BYTES'] == '{MEMORY_LIMIT_BYTES}'\n"
        f"assert env['PIXCELL_EVAL_PROCESS_COUNT'] == '{APPTAINER_PROCESS_LIMIT}'\n"
        "if 'SIMULATE_REAL_RLIMIT_FAIL' in src:\n"
        "    print('WARNING: host warning before python', file=sys.stderr)\n"
        "    env['PIXCELL_EVAL_CPU_SECONDS'] = '-5'\n"
        "if sys.platform == 'darwin':\n"
        "    import resource\n"
        "    env['PIXCELL_EVAL_ADDRESS_BYTES'] = str(resource.getrlimit(resource.RLIMIT_AS)[1])\n"
        "proc = subprocess.run([sys.executable, str(in_dir / 'execute.py'), str(in_dir / 'device.py')], cwd=wk_dir, env=env)\n"
        "raise SystemExit(proc.returncode)\n",
        encoding="utf-8",
    )
    stub.chmod(0o700)

    boundary = _apptainer_boundary(tmp_path, runtime=stub)
    monkeypatch.setenv("TINKER_API_KEY", "must-not-leak")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/private/ssh.sock")
    monkeypatch.setattr(
        "rl.common.evaluator.require_execution_boundary",
        lambda: boundary,
    )

    with PixCellEvaluator(
        max_workers=1,
        execution_timeout_seconds=5.0,
        evaluator_retries=0,
        require_isolation=True,
    ) as evaluator:
        # 1. Valid candidate executes through real execute.py with required rlimits + writes device.gds
        w_ok = tmp_path / "run_ok"
        w_ok.mkdir()
        status, err = evaluator._run_isolated_candidate(
            "from pathlib import Path\nPath('device.gds').write_bytes(b'gds-payload')\n",
            w_ok,
        )
        assert status is EvaluationStatus.OK, err
        assert (w_ok / "device.gds").read_bytes() == b"gds-payload"
        assert stat.S_IMODE(w_ok.stat().st_mode) == 0o700

        # 2. Candidate Python exception -> RUNTIME_ERROR (model fault, not worker error)
        w_crash = tmp_path / "run_crash"
        w_crash.mkdir()
        status, err = evaluator._run_isolated_candidate("raise RuntimeError('boom')\n", w_crash)
        assert status is EvaluationStatus.RUNTIME_ERROR
        assert err is not None and "boom" in err

        # 2b. Purity-passing candidate attempts to spoof WORKER_ERROR via stdout/exception/SystemExit
        spoof_programs = [
            'print("failed to install required rlimit")\nraise RuntimeError("model bug")\n',
            'raise RuntimeError("failed to install required rlimit 9")\n',
            (
                'raise RuntimeError(\n'
                '    "\\n  File \\"/input/execute.py\\", line 55, in _apply_limits\\n"\n'
                '    "  File \\"/input/execute.py\\", line 31, in _set_limit\\n"\n'
                '    "RuntimeError: failed to install required rlimit 0"\n'
                ')\n'
            ),
            'print("FATAL: fake container error")\nraise SystemExit(255)\n',
        ]
        for idx, spoof in enumerate(spoof_programs):
            assert strict_purity_violations(spoof) == []
            w_sp = tmp_path / f"run_spoof_{idx}"
            w_sp.mkdir()
            status, _ = evaluator._run_isolated_candidate(spoof, w_sp)
            assert status is EvaluationStatus.RUNTIME_ERROR, f"spoof {idx} misclassified as {status}"

        # 3. Missing device.gds -> NO_GDS
        w_nogds = tmp_path / "run_nogds"
        w_nogds.mkdir()
        status, _ = evaluator._run_isolated_candidate("x = 1\n", w_nogds)
        assert status is EvaluationStatus.NO_GDS

        # 4. Symlink device.gds -> refused as NO_GDS (never reads host file)
        w_sym = tmp_path / "run_sym"
        w_sym.mkdir()
        status, _ = evaluator._run_isolated_candidate("# SIMULATE_SYMLINK_ATTACK\n", w_sym)
        assert status is EvaluationStatus.NO_GDS
        assert not (w_sym / "device.gds").exists()

        # 4b. Candidate creating a chmod-000 subdirectory inside /work is still cleanly removable
        w_ro = tmp_path / "run_chmod"
        w_ro.mkdir()
        status, _ = evaluator._run_isolated_candidate(
            "from pathlib import Path\nd = Path('locked')\nd.mkdir()\n"
            "(d / 'x').write_text('a')\nd.chmod(0o000)\n",
            w_ro,
        )
        assert status is EvaluationStatus.NO_GDS
        assert stat.S_IMODE((w_ro / "work" / "locked").stat().st_mode) == 0o700

        # 5. Apptainer FATAL startup failure -> WORKER_ERROR (infrastructure fault, never model zero)
        w_fatal = tmp_path / "run_fatal"
        w_fatal.mkdir()
        status, err = evaluator._run_isolated_candidate("# SIMULATE_APPTAINER_FATAL\n", w_fatal)
        assert status is EvaluationStatus.WORKER_ERROR
        assert err is not None and "FATAL:" in err

        # 5b. Broken SIF missing Python (exit 127, empty stdout) -> WORKER_ERROR
        w_127 = tmp_path / "run_127"
        w_127.mkdir()
        status, _ = evaluator._run_isolated_candidate("# SIMULATE_MISSING_PYTHON\n", w_127)
        assert status is EvaluationStatus.WORKER_ERROR

        # 5c. Real execute.py required-rlimit installation failure -> WORKER_ERROR
        w_rlimit = tmp_path / "run_rlimit"
        w_rlimit.mkdir()
        status, err = evaluator._run_isolated_candidate("# SIMULATE_REAL_RLIMIT_FAIL\n", w_rlimit)
        assert status is EvaluationStatus.WORKER_ERROR
        assert err is not None and "failed to install required rlimit" in err

        # 6. Wall-clock timeout -> RUNTIME_TIMEOUT and process group cleanly reaped
        evaluator.execution_timeout_seconds = 0.5
        w_to = tmp_path / "run_timeout"
        w_to.mkdir()
        status, _ = evaluator._run_isolated_candidate(
            "import time\ntime.sleep(30)\n",
            w_to,
        )
        assert status is EvaluationStatus.RUNTIME_TIMEOUT


def test_execute_py_accepts_apptainer_required_rlimits_under_shared_uid(tmp_path: Path) -> None:
    """Running real rl/common/execute.py with PIXCELL_EVAL_REQUIRE_LIMITS=1 and
    APPTAINER_PROCESS_LIMIT succeeds without colliding on host UID NPROC."""
    script = tmp_path / "ok.py"
    script.write_text(
        "import resource\n"
        "assert resource.getrlimit(resource.RLIMIT_CPU)[0] <= 18\n"
        "assert resource.getrlimit(resource.RLIMIT_FSIZE)[0] <= 16 * 1024 * 1024\n"
        "assert resource.getrlimit(resource.RLIMIT_NOFILE)[0] <= 128\n"
        "assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)\n",
        encoding="utf-8",
    )
    execute_py = Path(__file__).resolve().parents[1] / "rl" / "common" / "execute.py"
    # On Linux containers RLIMIT_AS=4GB is enforced directly; macOS host kernels reject
    # lowering RLIMIT_AS below the host dyld virtual map, so use host hard limit on darwin.
    address_bytes = (
        resource.getrlimit(resource.RLIMIT_AS)[1]
        if sys.platform == "darwin"
        else MEMORY_LIMIT_BYTES
    )
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PIXCELL_EVAL_CPU_SECONDS": "18",
        "PIXCELL_EVAL_FILE_BYTES": str(16 * 1024 * 1024),
        "PIXCELL_EVAL_OPEN_FILES": "128",
        "PIXCELL_EVAL_ADDRESS_BYTES": str(address_bytes),
        "PIXCELL_EVAL_PROCESS_COUNT": str(APPTAINER_PROCESS_LIMIT),
        "PIXCELL_EVAL_REQUIRE_LIMITS": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(execute_py), str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    assert proc.returncode == 0, proc.stderr


def test_docker_exit_code_reader_waits_past_zero_byte_file(monkeypatch, tmp_path: Path) -> None:
    """Docker /status/exit-code reader must wait until the file is non-empty."""
    boundary = ExecutionBoundary(
        runtime_path=tmp_path / "docker",
        daemon_endpoint="unix:///var/run/docker.sock",
        image_ref="sha256:" + "a" * 64,
        image_id="sha256:" + "a" * 64,
        workspace_root=tmp_path,
        backend="docker",
    )
    monkeypatch.setattr(
        "rl.common.evaluator.require_execution_boundary",
        lambda: boundary,
    )

    status_file = tmp_path / "status_exit_code"
    status_file.write_bytes(b"")
    captured_scripts: list[str] = []

    def fake_subprocess_run(cmd, **_kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=b"0123456789abcdef\n",
            stderr=b"",
        )

    monkeypatch.setattr("rl.common.evaluator.subprocess.run", fake_subprocess_run)

    with PixCellEvaluator(
        max_workers=1,
        execution_timeout_seconds=5.0,
        evaluator_retries=0,
        require_isolation=True,
    ) as evaluator:
        monkeypatch.setattr(
            evaluator,
            "_cleanup_candidate_containers",
            lambda **_kwargs: True,
        )
        monkeypatch.setattr(
            evaluator,
            "_container_state",
            lambda _cid: {"Running": True, "OOMKilled": False, "ExitCode": 0},
        )

        def fake_container_control(args, timeout=None):  # noqa: ARG001
            if args[0] == "start":
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"", stderr=b"")
            if args[0] == "exec" and "/status/exit-code" in args[-1]:
                reader_script = args[-1]
                captured_scripts.append(reader_script)
                adapted = reader_script.replace("'/status/exit-code'", repr(str(status_file)))
                proc = subprocess.Popen(
                    [sys.executable, "-c", adapted],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    time.sleep(0.15)
                    assert proc.poll() is None, "exit-code reader exited early on 0-byte file"
                    status_file.write_text("0\n", encoding="ascii")
                    stdout, stderr = proc.communicate(timeout=5.0)
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=5.0)
                assert proc.returncode == 0, stderr
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=stdout.encode("ascii"),
                    stderr=stderr.encode("utf-8"),
                )
            if args[0] == "exec" and "/work/device.gds" in args[-1]:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=b"gds-payload",
                    stderr=b"",
                )
            raise AssertionError(f"unexpected container_control args: {args}")

        monkeypatch.setattr(evaluator, "_container_control", fake_container_control)

        workdir = tmp_path / "docker_run"
        workdir.mkdir()
        status, err = evaluator._run_docker_candidate("x = 1\n", workdir)
        assert status is EvaluationStatus.OK, err
        assert err is None
        assert (workdir / "device.gds").read_bytes() == b"gds-payload"

    assert len(captured_scripts) == 1
    # Also verify missing -> 0-byte -> whitespace-only -> nonzero exit code transition.
    missing_file = tmp_path / "missing_exit_code"
    adapted2 = captured_scripts[0].replace("'/status/exit-code'", repr(str(missing_file)))
    proc2 = subprocess.Popen(
        [sys.executable, "-c", adapted2],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(0.10)
        assert proc2.poll() is None
        missing_file.write_bytes(b"")
        time.sleep(0.10)
        assert proc2.poll() is None
        missing_file.write_text("   \n", encoding="ascii")
        time.sleep(0.10)
        assert proc2.poll() is None
        missing_file.write_text("42", encoding="ascii")
        stdout2, stderr2 = proc2.communicate(timeout=5.0)
    finally:
        if proc2.poll() is None:
            proc2.kill()
            proc2.wait(timeout=5.0)
    assert proc2.returncode == 0, stderr2
    assert stdout2 == "42"


@pytest.mark.parametrize("backend", ["local", "apptainer"])
def test_post_wait_killpg_eperm_does_not_clobber_timeout_or_normal_exit(
    monkeypatch, tmp_path: Path, backend: str
) -> None:
    """Post-process.wait() EPERM (macOS XNU zombie teardown race) must never turn
    RUNTIME_TIMEOUT or normal completion into WORKER_ERROR, and timeout must not
    redundantly call os.killpg after process.wait() already reaped the leader.
    """
    if backend == "apptainer":
        stub = tmp_path / "fake-apptainer"
        stub.write_text(
            f"#!{sys.executable}\n"
            "import os, pathlib, subprocess, sys\n"
            "argv = sys.argv[1:]\n"
            "binds = [argv[i+1] for i, t in enumerate(argv) if t == '--bind']\n"
            "in_dir = pathlib.Path(next(b.split(':')[0] for b in binds if b.endswith(':/input:ro')))\n"
            "wk_dir = pathlib.Path(next(b.split(':')[0] for b in binds if b.endswith(':/work:rw')))\n"
            "env = dict(os.environ)\n"
            "for i, t in enumerate(argv):\n"
            "    if t == '--env':\n"
            "        k, v = argv[i+1].split('=', 1)\n"
            "        env[k] = v\n"
            "if sys.platform == 'darwin':\n"
            "    import resource\n"
            "    env['PIXCELL_EVAL_ADDRESS_BYTES'] = str(resource.getrlimit(resource.RLIMIT_AS)[1])\n"
            "proc = subprocess.run(\n"
            "    [sys.executable, str(in_dir / 'execute.py'), str(in_dir / 'device.py')],\n"
            "    cwd=wk_dir,\n"
            "    env=env,\n"
            ")\n"
            "raise SystemExit(proc.returncode)\n",
            encoding="utf-8",
        )
        stub.chmod(0o700)
        boundary = _apptainer_boundary(tmp_path, runtime=stub)
        monkeypatch.setattr(
            "rl.common.evaluator.require_execution_boundary",
            lambda: boundary,
        )

    real_popen = subprocess.Popen
    real_killpg = os.killpg
    captured_processes: list[subprocess.Popen[bytes]] = []
    killpg_calls: list[tuple[int, int, bool]] = []

    def tracking_popen(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        captured_processes.append(proc)
        return proc

    def fake_killpg(pgid: int, sig: int) -> None:
        proc = captured_processes[-1]
        reaped = proc.returncode is not None
        killpg_calls.append((pgid, sig, reaped))
        if reaped:
            raise PermissionError(errno.EPERM, "Operation not permitted")
        real_killpg(pgid, sig)

    monkeypatch.setattr("rl.common.evaluator.subprocess.Popen", tracking_popen)
    monkeypatch.setattr("rl.common.evaluator.os.killpg", fake_killpg)

    with PixCellEvaluator(
        max_workers=1,
        execution_timeout_seconds=0.3,
        evaluator_retries=0,
        require_isolation=(backend == "apptainer"),
    ) as evaluator:
        # 1. Timeout: os.killpg called exactly once BEFORE process.wait(), never after.
        w_to = tmp_path / f"{backend}_timeout"
        w_to.mkdir()
        status, err = evaluator._run_candidate(
            "import time\ntime.sleep(30)\n",
            w_to,
        )
        assert status is EvaluationStatus.RUNTIME_TIMEOUT, err
        assert err == "candidate execution timed out"
        timeout_proc = captured_processes[-1]
        assert timeout_proc.returncode is not None
        assert killpg_calls == [(timeout_proc.pid, signal.SIGKILL, False)]

        # Even if _kill_process_group is called post-wait and os.killpg raises EPERM,
        # it does not raise because process.poll() is not None.
        PixCellEvaluator._kill_process_group(timeout_proc)
        assert killpg_calls[-1] == (timeout_proc.pid, signal.SIGKILL, True)

        # 2. Normal exit: post-wait descendant cleanup absorbs EPERM and preserves OK.
        killpg_calls.clear()
        evaluator.execution_timeout_seconds = 5.0
        w_ok = tmp_path / f"{backend}_ok"
        w_ok.mkdir()
        status, err = evaluator._run_candidate(
            "from pathlib import Path\nPath('device.gds').write_bytes(b'ok')\n",
            w_ok,
        )
        assert status is EvaluationStatus.OK, err
        assert err is None
        assert (w_ok / "device.gds").read_bytes() == b"ok"
        ok_proc = captured_processes[-1]
        assert ok_proc.returncode == 0
        assert killpg_calls == [(ok_proc.pid, signal.SIGKILL, True)]


def test_kill_process_group_reraises_eperm_when_process_still_alive(
    monkeypatch,
) -> None:
    """PermissionError on a live process (poll() is None) must still fail closed."""
    real_killpg = os.killpg
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        assert proc.poll() is None

        def deny_killpg(_pgid: int, _sig: int) -> None:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr("rl.common.evaluator.os.killpg", deny_killpg)
        with pytest.raises(PermissionError):
            PixCellEvaluator._kill_process_group(proc)
    finally:
        real_killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5.0)
