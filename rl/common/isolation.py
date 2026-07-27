"""Per-candidate container boundary for model-authored Python.

The Tinker launcher must retain network access, while a sampled program must
see neither that network nor the launcher's credentials.  The boundary is
therefore one disposable Docker container per candidate, not a container
around the whole training process.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .sandbox_spec import SANDBOX_SPEC_LABEL, sandbox_spec_sha256


IMAGE_ENV = "PIXCELL_EVALUATOR_IMAGE"
IMMUTABLE_IMAGE = re.compile(
    r"^(?:sha256:[0-9a-f]{64}|[^\s@]+@sha256:[0-9a-f]{64})$"
)
MEMORY_LIMIT_BYTES = 4 * 1024 * 1024 * 1024
PIDS_LIMIT = 32
CANDIDATE_PROCESS_LIMIT = 24
WORKSPACE_LIMIT_BYTES = 64 * 1024 * 1024
TMP_LIMIT_BYTES = 128 * 1024 * 1024
_CANDIDATE_UID_BASE = 100_000
_CANDIDATE_UID_SPAN = 900_000


class IsolationError(RuntimeError):
    """A usable, immutable local candidate sandbox is not available."""


@dataclass(frozen=True)
class ExecutionBoundary:
    runtime_path: Path
    daemon_endpoint: str
    image_ref: str
    image_id: str
    workspace_root: Path
    memory_limit_bytes: int = MEMORY_LIMIT_BYTES
    pids_limit: int = PIDS_LIMIT

    def create_command(self, input_dir: Path, *, candidate_id: str) -> list[str]:
        """Create, but do not start, one disposable candidate container."""

        if not input_dir.is_absolute():
            raise IsolationError("candidate input directory must be absolute")
        if os.getuid() == 0:
            raise IsolationError("candidate containers must be launched by a non-root user")
        candidate_uid, candidate_gid = candidate_identity(candidate_id)
        return [
            str(self.runtime_path),
            "--host",
            self.daemon_endpoint,
            "create",
            "--cidfile",
            str(input_dir / ".container-id"),
            "--label",
            f"org.qpg-mit.pixcell.candidate={candidate_id}",
            "--init",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "KILL",
            "--cap-add",
            "SETGID",
            "--cap-add",
            "SETUID",
            "--security-opt",
            "no-new-privileges:true",
            "--memory",
            str(self.memory_limit_bytes),
            "--memory-swap",
            str(self.memory_limit_bytes),
            "--pids-limit",
            str(self.pids_limit),
            "--cpus",
            "1.0",
            "--user",
            "0:0",
            "--workdir",
            "/work",
            "--log-driver",
            "none",
            "--mount",
            f"type=bind,src={input_dir},dst=/input,readonly",
            "--tmpfs",
            (
                "/work:rw,nosuid,nodev,noexec,"
                f"size={WORKSPACE_LIMIT_BYTES},mode=0700,"
                f"uid={candidate_uid},gid={candidate_gid}"
            ),
            "--tmpfs",
            (
                "/tmp:rw,nosuid,nodev,noexec,"
                f"size={TMP_LIMIT_BYTES},mode=0700,"
                f"uid={candidate_uid},gid={candidate_gid}"
            ),
            "--tmpfs",
            "/status:rw,nosuid,nodev,noexec,size=4096,mode=0700,uid=0,gid=0",
            "--env",
            "HOME=/work",
            "--env",
            "MPLBACKEND=Agg",
            "--env",
            "MKL_NUM_THREADS=1",
            "--env",
            "NUMEXPR_NUM_THREADS=1",
            "--env",
            "OMP_NUM_THREADS=1",
            "--env",
            "OPENBLAS_NUM_THREADS=1",
            "--env",
            "PYTHONHASHSEED=0",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "PYTHONNOUSERSITE=1",
            "--env",
            "VECLIB_MAXIMUM_THREADS=1",
            "--env",
            "TMPDIR=/tmp",
            "--env",
            "XDG_CACHE_HOME=/tmp/cache",
            "--env",
            "PIXCELL_EVAL_CPU_SECONDS=18",
            "--env",
            f"PIXCELL_EVAL_FILE_BYTES={16 * 1024 * 1024}",
            "--env",
            "PIXCELL_EVAL_OPEN_FILES=128",
            "--env",
            f"PIXCELL_EVAL_ADDRESS_BYTES={self.memory_limit_bytes}",
            "--env",
            f"PIXCELL_EVAL_PROCESS_COUNT={CANDIDATE_PROCESS_LIMIT}",
            "--env",
            "PIXCELL_EVAL_REQUIRE_LIMITS=1",
            "--env",
            f"PIXCELL_CANDIDATE_UID={candidate_uid}",
            "--env",
            f"PIXCELL_CANDIDATE_GID={candidate_gid}",
            "--entrypoint",
            "/usr/local/bin/python",
            self.image_ref,
            "/usr/local/lib/pixcell/supervise.py",
            "/input/execute.py",
            "/input/device.py",
        ]


def candidate_identity(candidate_id: str) -> tuple[int, int]:
    """Derive a container-only UID so RLIMIT_NPROC is per candidate.

    Reusing the host launch UID would make Linux count unrelated host
    processes and concurrent candidate containers against the same limit.
    """

    if not re.fullmatch(r"[0-9a-f]{32}", candidate_id):
        raise IsolationError("candidate_id must be 32 lowercase hexadecimal digits")
    uid = _CANDIDATE_UID_BASE + (
        int(candidate_id[:12], 16) % _CANDIDATE_UID_SPAN
    )
    return uid, uid


def _checked_json(command: list[str], *, timeout: float = 15.0) -> Any:
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=timeout,
            text=True,
        )
        return json.loads(result.stdout)
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ) as exc:
        raise IsolationError(f"sandbox control command failed: {command[1]}") from exc


def _trusted_runtime() -> Path:
    executable = shutil.which("docker")
    if not executable:
        raise IsolationError("docker is required for model-authored program execution")
    runtime = Path(executable).resolve(strict=True)
    metadata = runtime.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise IsolationError("docker runtime path is not a regular file")
    if metadata.st_uid not in {0, os.getuid()} or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise IsolationError(
            "docker runtime must be owned by root/the launch user and not "
            "group/world writable"
        )
    return runtime


def _require_local_daemon(runtime: Path) -> str:
    contexts = _checked_json([str(runtime), "context", "inspect"])
    try:
        endpoint = contexts[0]["Endpoints"]["docker"]["Host"]
    except (IndexError, KeyError, TypeError) as exc:
        raise IsolationError("could not resolve the active Docker endpoint") from exc
    if not isinstance(endpoint, str) or not endpoint.startswith("unix://"):
        raise IsolationError("candidate sandbox requires a local Unix-socket Docker daemon")
    return endpoint


def _resolve_image(runtime: Path, endpoint: str, image_ref: str) -> str:
    if not IMMUTABLE_IMAGE.fullmatch(image_ref):
        raise IsolationError(
            f"{IMAGE_ENV} must be an immutable image ID or repository digest"
        )
    images = _checked_json(
        [str(runtime), "--host", endpoint, "image", "inspect", image_ref]
    )
    try:
        image = images[0]
        image_id = str(image["Id"])
        repo_digests = {str(value) for value in image.get("RepoDigests") or []}
        labels = image["Config"].get("Labels") or {}
    except (IndexError, KeyError, TypeError) as exc:
        raise IsolationError("could not inspect the evaluator image") from exc
    if image_ref.startswith("sha256:"):
        if image_id != image_ref:
            raise IsolationError("evaluator image ID does not match the requested digest")
    elif image_ref not in repo_digests:
        raise IsolationError("evaluator repository digest is not present locally")
    expected_spec = sandbox_spec_sha256()
    if labels.get(SANDBOX_SPEC_LABEL) != expected_spec:
        raise IsolationError(
            "evaluator image was not built from the committed sandbox specification"
        )
    return image_id


def _workspace_root() -> Path:
    root = (Path.home() / ".cache" / "pixcell" / "evaluator").resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = root.stat()
    if metadata.st_uid != os.getuid():
        raise IsolationError("candidate workspace root is not owned by the launch user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise IsolationError("candidate workspace root must have mode 0700")
    return root


def require_execution_boundary() -> ExecutionBoundary:
    """Resolve the immutable per-candidate sandbox before any paid work."""

    if os.getuid() == 0:
        raise IsolationError("paid evaluation must run as a non-root host user")
    image_ref = os.environ.get(IMAGE_ENV, "").strip()
    if not image_ref:
        raise IsolationError(f"{IMAGE_ENV} is required before paid RL or evaluation")
    runtime = _trusted_runtime()
    endpoint = _require_local_daemon(runtime)
    image_id = _resolve_image(runtime, endpoint, image_ref)
    return ExecutionBoundary(
        runtime_path=runtime,
        daemon_endpoint=endpoint,
        image_ref=image_ref,
        image_id=image_id,
        workspace_root=_workspace_root(),
    )
