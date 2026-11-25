"""Shared deterministic Python -> GDS -> absolute-scale IoU evaluation.

The evaluator measures; it does not search, repair, or provide textual
feedback. Candidate execution happens in a sacrificial subprocess. Reference
and evaluator failures are typed separately so they cannot become negative
policy examples by accident.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from homi.conductor.source_policy import strict_purity_violations
from michaelangelo.core.compare_absolute import (
    compute_metrics,
    extract_polygons,
    render_gds_absolute,
)
from michaelangelo.core.rc01 import evaluate_rc01_calibrated

from .contracts import VerifierReference
from .geometry import boundary_mask, chamfer_sym_um
from .isolation import (
    ExecutionBoundary,
    candidate_identity,
    require_execution_boundary,
)
from .output import extract_code


class EvaluationStatus(str, Enum):
    OK = "ok"
    SYNTAX_ERROR = "syntax_error"
    SOURCE_REJECTED = "source_rejected"
    RUNTIME_TIMEOUT = "runtime_timeout"
    RUNTIME_ERROR = "runtime_error"
    NO_GDS = "no_gds"
    BAD_GDS = "bad_gds"
    REFERENCE_ERROR = "reference_error"
    MEASUREMENT_ERROR = "measurement_error"
    WORKER_ERROR = "worker_error"


class Attribution(str, Enum):
    MODEL = "model"
    REFERENCE = "reference"
    EVALUATOR = "evaluator"


@dataclass(frozen=True)
class EvaluationResult:
    status: EvaluationStatus
    attribution: Attribution
    iou: float | None = None
    dice: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    violations: tuple[str, ...] = ()
    error: str | None = None
    latency_seconds: float = 0.0
    retryable: bool = False

    @property
    def mask_from_training(self) -> bool:
        return self.attribution is not Attribution.MODEL


class ReferenceFailure(ValueError):
    pass


@dataclass(frozen=True)
class _PreparedReference:
    target: Image.Image
    calibration: dict[str, Any]
    cache_key: str


_APPTAINER_FATAL_RE = re.compile(r"(?m)^FATAL:")
_EXECUTE_SET_LIMIT_RE = re.compile(
    r'(?m)^  File "[^"]*execute\.py", line \d+, in _set_limit$'
)
_EXECUTE_APPLY_LIMITS_RE = re.compile(
    r'(?m)^  File "[^"]*execute\.py", line \d+, in _apply_limits$'
)
_EXECUTE_RLIMIT_ERROR_RE = re.compile(
    r"(?m)^RuntimeError: failed to install required rlimit \d+\s*$"
)


def _is_apptainer_infrastructure_failure(
    *,
    return_code: int,
    stdout_size: int,
    stderr_size: int,
    stderr_text: str,
) -> bool:
    """Distinguish sandbox/rlimit startup faults from model-authored runtime errors.

    Requires empty stdout so candidate print() output can never spoof a worker fault,
    and requires execute.py's exact pre-execution traceback (with no device.py frame)
    for rlimit installation failures.
    """

    if stdout_size > 0:
        return False
    if return_code in {126, 127}:
        return True
    if return_code == 255 and _APPTAINER_FATAL_RE.search(stderr_text):
        return True
    if (
        return_code == 1
        and stderr_size <= 16_384
        and "device.py" not in stderr_text
        and _EXECUTE_SET_LIMIT_RE.search(stderr_text)
        and _EXECUTE_APPLY_LIMITS_RE.search(stderr_text)
        and _EXECUTE_RLIMIT_ERROR_RE.search(stderr_text)
    ):
        return True
    return False


def _restore_writable_dirs(root: Path) -> None:
    """Restore 0700 on non-symlink directories so temp cleanup cannot fail on chmod."""

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                continue
            os.chmod(current, 0o700)
            with os.scandir(current) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
        except OSError:
            continue


def _error_text(value: BaseException | str, limit: int = 1200) -> str:
    text = str(value).replace("\x00", "")
    return text[-limit:]


def _json_diagnostic(value: Any) -> Any:
    """Convert measurement diagnostics to strict, finite JSON primitives."""

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("measurement diagnostic is not finite")
        return result
    if isinstance(value, np.generic):
        return _json_diagnostic(value.item())
    if isinstance(value, np.ndarray):
        return _json_diagnostic(value.tolist())
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("measurement diagnostic keys must be strings")
        return {
            key: _json_diagnostic(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_diagnostic(item) for item in value]
    raise TypeError(
        f"measurement diagnostic contains {type(value).__name__}"
    )


def _render_sha256(image: Image.Image) -> str:
    """Hash a calibrated candidate raster without depending on image encoders."""

    grayscale = image.convert("L")
    header = f"L:{grayscale.width}x{grayscale.height}\0".encode()
    return hashlib.sha256(header + grayscale.tobytes()).hexdigest()


def _calibration_from_target(
    target: Image.Image,
    footprint_um: tuple[float, float],
) -> dict[str, Any]:
    array = np.asarray(target.convert("L"))
    mask = array < 245
    if not mask.any():
        raise ReferenceFailure("target_image contains no layer-(1,0) material")
    ys, xs = np.where(mask)
    bbox = [
        int(xs.min()),
        int(ys.min()),
        int(xs.max()) + 1,
        int(ys.max()) + 1,
    ]
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]
    length_um, width_um = footprint_um
    return {
        "bbox": bbox,
        "bbox_size_px": [bbox_width, bbox_height],
        "offset": bbox[:2],
        "scale_px_per_um": [bbox_width / length_um, bbox_height / width_um],
        "footprint_um": [length_um, width_um],
        "image_size_px": list(target.size),
        "white_threshold": 245,
    }


def _prepare_reference(reference: VerifierReference) -> _PreparedReference:
    if len(reference.footprint_um) != 2 or any(
        not math.isfinite(value) or value <= 0 for value in reference.footprint_um
    ):
        raise ReferenceFailure("invalid physical footprint")
    digest = hashlib.sha256(reference.target_image_bytes).hexdigest()
    if digest != reference.target_image_sha256:
        raise ReferenceFailure("target_image SHA-256 mismatch")
    try:
        target = Image.open(io.BytesIO(reference.target_image_bytes)).convert("L")
        target.load()
    except Exception as exc:
        raise ReferenceFailure(f"target_image is not a readable image: {_error_text(exc)}") from exc
    if target.width < 2 or target.height < 2:
        raise ReferenceFailure("target_image is too small to score")
    calibration = _calibration_from_target(target, reference.footprint_um)
    cache_key = f"{digest}:{reference.footprint_um[0]:.12g}:{reference.footprint_um[1]:.12g}"
    return _PreparedReference(target, calibration, cache_key)


class PixCellEvaluator:
    """Bounded, ordered evaluator for one or more rollout groups."""

    def __init__(
        self,
        *,
        max_workers: int = 8,
        execution_timeout_seconds: float = 20.0,
        evaluator_retries: int = 1,
        require_isolation: bool = False,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        if execution_timeout_seconds <= 0:
            raise ValueError("execution_timeout_seconds must be positive")
        if evaluator_retries < 0:
            raise ValueError("evaluator_retries must be non-negative")
        self.max_workers = max_workers
        self.execution_timeout_seconds = execution_timeout_seconds
        self.evaluator_retries = evaluator_retries
        self.execution_boundary: ExecutionBoundary | None = (
            require_execution_boundary() if require_isolation else None
        )
        self._reference_cache: dict[str, _PreparedReference] = {}
        self._reference_lock = threading.Lock()
        self._closed = False

    def __enter__(self) -> "PixCellEvaluator":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._closed = True

    def validate_reference(self, reference: VerifierReference) -> dict[str, Any]:
        """Fail-fast validation intended for the zero-spend launch preflight."""

        prepared = _prepare_reference(reference)
        return {
            "target_image_sha256": reference.target_image_sha256,
            "image_size_px": list(prepared.target.size),
            "bbox": list(prepared.calibration["bbox"]),
            "scale_px_per_um": list(prepared.calibration["scale_px_per_um"]),
        }

    def _prepared(self, reference: VerifierReference) -> _PreparedReference:
        provisional_key = (
            f"{reference.target_image_sha256}:"
            f"{reference.footprint_um[0]:.12g}:{reference.footprint_um[1]:.12g}"
        )
        with self._reference_lock:
            cached = self._reference_cache.get(provisional_key)
        if cached is not None:
            return cached
        prepared = _prepare_reference(reference)
        with self._reference_lock:
            return self._reference_cache.setdefault(prepared.cache_key, prepared)

    def _child_environment(self, workdir: Path) -> dict[str, str]:
        environment = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")
            if key in os.environ
        }
        memory_limit = (
            self.execution_boundary.memory_limit_bytes
            if self.execution_boundary is not None
            else 4 * 1024 * 1024 * 1024
        )
        process_limit = (
            self.execution_boundary.pids_limit
            if self.execution_boundary is not None
            else 32
        )
        environment.update(
            {
                "HOME": str(workdir),
                "MPLBACKEND": "Agg",
                "MKL_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "PYTHONHASHSEED": "0",
                "VECLIB_MAXIMUM_THREADS": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "TMPDIR": str(workdir),
                "XDG_CACHE_HOME": str(workdir / ".cache"),
                "XDG_CONFIG_HOME": str(workdir / ".config"),
                "PIXCELL_EVAL_CPU_SECONDS": "18",
                "PIXCELL_EVAL_FILE_BYTES": str(16 * 1024 * 1024),
                "PIXCELL_EVAL_OPEN_FILES": "128",
                "PIXCELL_EVAL_ADDRESS_BYTES": str(memory_limit),
                "PIXCELL_EVAL_PROCESS_COUNT": str(process_limit),
                "PIXCELL_EVAL_REQUIRE_LIMITS": (
                    "1" if self.execution_boundary is not None else "0"
                ),
            }
        )
        return environment

    @staticmethod
    def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # On macOS XNU, signaling a process group whose leader has already
            # exited/been reaped while children are tearing down can raise EPERM.
            if process.poll() is None:
                raise

    def _run_local_candidate(
        self,
        source: str,
        workdir: Path,
    ) -> tuple[EvaluationStatus, str | None]:
        script = workdir / "device.py"
        script.write_text(source, encoding="utf-8")
        log_path = workdir / "execution.log"
        command = [
            sys.executable,
            str(Path(__file__).with_name("execute.py")),
            str(script),
        ]
        try:
            with log_path.open("wb") as log:
                process = subprocess.Popen(
                    command,
                    cwd=workdir,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    env=self._child_environment(workdir),
                    start_new_session=True,
                )
                timeout_handled = False
                try:
                    return_code = process.wait(timeout=self.execution_timeout_seconds)
                except subprocess.TimeoutExpired:
                    timeout_handled = True
                    self._kill_process_group(process)
                    process.wait()
                    return EvaluationStatus.RUNTIME_TIMEOUT, "candidate execution timed out"
                finally:
                    # A candidate may leave background descendants after its
                    # main process exits successfully. Always reap its process
                    # group; the external container's init handles anything
                    # that deliberately created a new session.
                    if not timeout_handled:
                        self._kill_process_group(process)
        except OSError as exc:
            return EvaluationStatus.WORKER_ERROR, _error_text(exc)

        tail = ""
        try:
            tail = log_path.read_bytes()[-4096:].decode("utf-8", errors="replace")
        except OSError:
            pass
        if return_code != 0:
            return (
                EvaluationStatus.RUNTIME_ERROR,
                _error_text(tail or f"candidate exited with status {return_code}"),
            )
        gds = workdir / "device.gds"
        if not gds.is_file() or gds.stat().st_size == 0:
            return EvaluationStatus.NO_GDS, "program did not write a non-empty device.gds"
        return EvaluationStatus.OK, None

    def _container_control(
        self,
        arguments: list[str],
        *,
        timeout: float = 30.0,
    ) -> subprocess.CompletedProcess[bytes]:
        assert self.execution_boundary is not None
        return subprocess.run(
            [
                str(self.execution_boundary.runtime_path),
                "--host",
                self.execution_boundary.daemon_endpoint,
                *arguments,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )

    def _cleanup_candidate_containers(
        self,
        *,
        candidate_id: str,
        known_id: str | None,
    ) -> bool:
        identifiers: set[str] = set()
        if known_id is not None:
            identifiers.add(known_id)
        cleanup_ok = True
        try:
            listed = self._container_control(
                [
                    "ps",
                    "--all",
                    "--quiet",
                    "--filter",
                    f"label=org.qpg-mit.pixcell.candidate={candidate_id}",
                ],
                timeout=10.0,
            )
        except (OSError, subprocess.TimeoutExpired):
            cleanup_ok = False
        else:
            if listed.returncode != 0:
                cleanup_ok = False
            else:
                identifiers.update(
                    value
                    for value in listed.stdout.decode(
                        "ascii", errors="ignore"
                    ).splitlines()
                    if re.fullmatch(r"[0-9a-f]{12,64}", value)
                )
        for identifier in identifiers:
            try:
                removed = self._container_control(
                    ["rm", "--force", identifier],
                    timeout=15.0,
                )
            except (OSError, subprocess.TimeoutExpired):
                cleanup_ok = False
            else:
                cleanup_ok = cleanup_ok and removed.returncode == 0
        return cleanup_ok

    def _container_state(self, container_id: str) -> dict[str, Any] | None:
        try:
            inspected = self._container_control(
                ["inspect", container_id],
                timeout=10.0,
            )
            document = json.loads(inspected.stdout)
            state = document[0]["State"]
        except (
            OSError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            IndexError,
            KeyError,
            TypeError,
        ):
            return None
        return state if inspected.returncode == 0 and isinstance(state, dict) else None

    def _apptainer_host_environment(self, apptainer_tmp: Path) -> dict[str, str]:
        """Minimal allowlisted host env for invoking the apptainer CLI itself."""

        environment = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")
            if key in os.environ
        }
        tmp = str(apptainer_tmp)
        environment["APPTAINER_TMPDIR"] = tmp
        environment["APPTAINER_LOCALCACHEDIR"] = tmp
        environment["TMPDIR"] = tmp
        return environment

    def _run_apptainer_candidate(
        self,
        source: str,
        workdir: Path,
    ) -> tuple[EvaluationStatus, str | None]:
        assert self.execution_boundary is not None
        workdir.chmod(0o700)
        input_dir = workdir / "input"
        run_work_dir = workdir / "work"
        apptainer_tmp = workdir / "apptainer-tmp"
        input_dir.mkdir(mode=0o700, exist_ok=False)
        run_work_dir.mkdir(mode=0o700, exist_ok=False)
        apptainer_tmp.mkdir(mode=0o700, exist_ok=False)
        input_dir.chmod(0o700)
        run_work_dir.chmod(0o700)
        apptainer_tmp.chmod(0o700)

        script = input_dir / "device.py"
        runner = input_dir / "execute.py"
        script.write_text(source, encoding="utf-8")
        shutil.copyfile(Path(__file__).with_name("execute.py"), runner)
        script.chmod(0o400)
        runner.chmod(0o400)

        stdout_path = workdir / "stdout.log"
        stderr_path = workdir / "stderr.log"
        command = self.execution_boundary.exec_command(input_dir, run_work_dir)
        try:
            try:
                with (
                    stdout_path.open("wb") as stdout_log,
                    stderr_path.open("wb") as stderr_log,
                ):
                    process = subprocess.Popen(
                        command,
                        cwd=workdir,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout_log,
                        stderr=stderr_log,
                        env=self._apptainer_host_environment(apptainer_tmp),
                        start_new_session=True,
                    )
                    timeout_handled = False
                    try:
                        return_code = process.wait(
                            timeout=self.execution_timeout_seconds
                        )
                    except subprocess.TimeoutExpired:
                        timeout_handled = True
                        self._kill_process_group(process)
                        process.wait()
                        return (
                            EvaluationStatus.RUNTIME_TIMEOUT,
                            "candidate execution timed out",
                        )
                    finally:
                        # Killing the process group kills the Apptainer PID-1
                        # process in the --pid namespace, causing the kernel to
                        # reap all container descendants atomically.
                        if not timeout_handled:
                            self._kill_process_group(process)
            except OSError as exc:
                return EvaluationStatus.WORKER_ERROR, _error_text(exc)

            stdout_size = 0
            stderr_size = 0
            stderr_tail = ""
            stdout_tail = ""
            try:
                stdout_size = stdout_path.stat().st_size
                if stdout_size:
                    stdout_tail = stdout_path.read_bytes()[-4096:].decode(
                        "utf-8", errors="replace"
                    )
            except OSError:
                pass
            try:
                stderr_size = stderr_path.stat().st_size
                if stderr_size:
                    stderr_tail = stderr_path.read_bytes()[-16_384:].decode(
                        "utf-8", errors="replace"
                    )
            except OSError:
                pass
            if return_code != 0:
                if _is_apptainer_infrastructure_failure(
                    return_code=return_code,
                    stdout_size=stdout_size,
                    stderr_size=stderr_size,
                    stderr_text=stderr_tail,
                ):
                    return (
                        EvaluationStatus.WORKER_ERROR,
                        _error_text(
                            stderr_tail
                            or f"apptainer sandbox failed with status {return_code}"
                        ),
                    )
                combined_tail = stderr_tail or stdout_tail
                return (
                    EvaluationStatus.RUNTIME_ERROR,
                    _error_text(
                        combined_tail or f"candidate exited with status {return_code}"
                    ),
                )

            candidate_gds = run_work_dir / "device.gds"
            try:
                gds_stat = os.lstat(candidate_gds)
            except FileNotFoundError:
                return EvaluationStatus.NO_GDS, "program did not write device.gds"
            except OSError:
                return (
                    EvaluationStatus.NO_GDS,
                    "program did not leave a readable regular device.gds",
                )
            if (
                not stat.S_ISREG(gds_stat.st_mode)
                or not 0 < gds_stat.st_size <= 16 * 1024 * 1024
            ):
                return (
                    EvaluationStatus.NO_GDS,
                    "program did not write a non-empty regular device.gds",
                )

            open_flags = (
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0)
            )
            try:
                fd = os.open(candidate_gds, open_flags)
                with os.fdopen(fd, "rb") as handle:
                    opened_stat = os.fstat(handle.fileno())
                    if not stat.S_ISREG(opened_stat.st_mode):
                        return (
                            EvaluationStatus.NO_GDS,
                            "program did not write a non-empty regular device.gds",
                        )
                    payload = handle.read(16 * 1024 * 1024 + 1)
            except OSError:
                return (
                    EvaluationStatus.NO_GDS,
                    "program did not leave a readable regular device.gds",
                )
            if not payload:
                return EvaluationStatus.NO_GDS, "program wrote an empty device.gds"
            if len(payload) > 16 * 1024 * 1024:
                return (
                    EvaluationStatus.NO_GDS,
                    "program did not write a non-empty regular device.gds",
                )
            try:
                (workdir / "device.gds").write_bytes(payload)
            except OSError as exc:
                return EvaluationStatus.WORKER_ERROR, _error_text(exc)
            return EvaluationStatus.OK, None
        finally:
            _restore_writable_dirs(run_work_dir)
            _restore_writable_dirs(apptainer_tmp)

    def _run_isolated_candidate(
        self,
        source: str,
        workdir: Path,
    ) -> tuple[EvaluationStatus, str | None]:
        assert self.execution_boundary is not None
        if self.execution_boundary.backend == "apptainer":
            return self._run_apptainer_candidate(source, workdir)
        return self._run_docker_candidate(source, workdir)

    def _run_docker_candidate(
        self,
        source: str,
        workdir: Path,
    ) -> tuple[EvaluationStatus, str | None]:
        assert self.execution_boundary is not None
        script = workdir / "device.py"
        script.write_text(source, encoding="utf-8")
        shutil.copyfile(Path(__file__).with_name("execute.py"), workdir / "execute.py")
        candidate_id = uuid.uuid4().hex
        candidate_uid, candidate_gid = candidate_identity(candidate_id)
        # The parent workspace is private (0700). The bind root itself only
        # contains this candidate's admitted source and trusted runner, so it
        # may be traversable by the unique container UID.
        script.chmod(0o444)
        (workdir / "execute.py").chmod(0o444)
        workdir.chmod(0o755)
        cid_path = workdir / ".container-id"
        container_id: str | None = None
        try:
            created = subprocess.run(
                self.execution_boundary.create_command(
                    workdir,
                    candidate_id=candidate_id,
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            create_error = _error_text(exc)
            created = None
        else:
            create_error = None
        candidate_ids = []
        if created is not None:
            candidate_ids.append(
                created.stdout.decode("ascii", errors="ignore").strip()
            )
        try:
            candidate_ids.append(cid_path.read_text(encoding="ascii").strip())
        except OSError:
            pass
        container_id = next(
            (
                value
                for value in candidate_ids
                if re.fullmatch(r"[0-9a-f]{12,64}", value)
            ),
            None,
        )
        if created is None or created.returncode != 0 or container_id is None:
            cleanup_ok = self._cleanup_candidate_containers(
                candidate_id=candidate_id,
                known_id=container_id,
            )
            detail = create_error
            if created is not None and created.returncode != 0:
                detail = _error_text(
                    created.stderr.decode("utf-8", errors="replace")
                    or "candidate container creation failed"
                )
            if container_id is None and detail is None:
                detail = "container runtime returned an invalid ID"
            if not cleanup_ok:
                detail = f"{detail}; candidate container cleanup failed"
            return EvaluationStatus.WORKER_ERROR, detail

        status = EvaluationStatus.WORKER_ERROR
        error: str | None = "candidate container did not run"
        cleanup_ok = False
        try:
            try:
                started = self._container_control(
                    ["start", container_id],
                    timeout=10.0,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                status = EvaluationStatus.WORKER_ERROR
                error = _error_text(exc)
            else:
                if started.returncode != 0:
                    status = EvaluationStatus.WORKER_ERROR
                    error = "candidate container failed to start"
                else:
                    # Only this trusted reader runs as container root: the
                    # supervisor's real wait status is deliberately stored in
                    # a root-only tmpfs that candidate code cannot forge.
                    marker_command = [
                        "exec",
                        "--user",
                        "0:0",
                        container_id,
                        "/usr/local/bin/python",
                        "-c",
                        (
                            "import pathlib,time\n"
                            "p=pathlib.Path('/status/exit-code')\n"
                            "while True:\n"
                            " try:\n"
                            "  t=p.read_text(encoding='ascii').strip() if p.is_file() else ''\n"
                            " except OSError:\n"
                            "  t=''\n"
                            " if t:\n"
                            "  print(t,end='')\n"
                            "  break\n"
                            " time.sleep(0.05)\n"
                        ),
                    ]
                    try:
                        marker = self._container_control(
                            marker_command,
                            timeout=self.execution_timeout_seconds,
                        )
                    except subprocess.TimeoutExpired:
                        state = self._container_state(container_id)
                        if state is not None and state.get("OOMKilled"):
                            status = EvaluationStatus.RUNTIME_ERROR
                            error = "candidate exceeded the memory limit"
                        elif state is not None and state.get("Running"):
                            status = EvaluationStatus.RUNTIME_TIMEOUT
                            error = "candidate execution timed out"
                        else:
                            status = EvaluationStatus.WORKER_ERROR
                            error = (
                                "candidate sandbox stopped before reporting "
                                "an exit status"
                            )
                    except OSError as exc:
                        status = EvaluationStatus.WORKER_ERROR
                        error = _error_text(exc)
                    else:
                        state = self._container_state(container_id)
                        marker_text = marker.stdout.decode(
                            "ascii", errors="ignore"
                        ).strip()
                        if state is not None and state.get("OOMKilled"):
                            status = EvaluationStatus.RUNTIME_ERROR
                            error = "candidate exceeded the memory limit"
                        elif state is None:
                            status = EvaluationStatus.WORKER_ERROR
                            error = "candidate sandbox state is unavailable"
                        elif not state.get("Running"):
                            exit_code = state.get("ExitCode")
                            if isinstance(exit_code, int) and exit_code != 0:
                                status = EvaluationStatus.RUNTIME_ERROR
                                error = (
                                    "candidate sandbox exited with status "
                                    f"{exit_code}"
                                )
                            else:
                                status = EvaluationStatus.WORKER_ERROR
                                error = (
                                    "candidate sandbox stopped before reporting "
                                    "an exit status"
                                )
                        elif marker.returncode != 0:
                            status = EvaluationStatus.WORKER_ERROR
                            error = "candidate status collection failed"
                        elif marker_text != "0":
                            if re.fullmatch(r"[1-9][0-9]*", marker_text):
                                status = EvaluationStatus.RUNTIME_ERROR
                                error = (
                                    "candidate exited with status "
                                    f"{marker_text}"
                                )
                            else:
                                status = EvaluationStatus.WORKER_ERROR
                                error = "candidate returned an invalid exit status"
                        else:
                            # Docker's archive copy path does not expose
                            # tmpfs-backed files consistently. Read the one
                            # admitted artifact through a fixed trusted
                            # interpreter while the candidate process is held
                            # asleep and the container is still alive.
                            output_reader = (
                                "import os,stat,sys\n"
                                "p='/work/device.gds'\n"
                                "try:\n"
                                " s=os.lstat(p)\n"
                                "except FileNotFoundError:\n"
                                " raise SystemExit(66)\n"
                                "if not stat.S_ISREG(s.st_mode) or "
                                "not 0 < s.st_size <= 16777216:\n"
                                " raise SystemExit(65)\n"
                                "with open(p,'rb',buffering=0) as f:\n"
                                " sys.stdout.buffer.write(f.read())\n"
                            )
                            try:
                                copied = self._container_control(
                                    [
                                        "exec",
                                        "--user",
                                        f"{candidate_uid}:{candidate_gid}",
                                        container_id,
                                        "/usr/local/bin/python",
                                        "-c",
                                        output_reader,
                                    ],
                                    timeout=15.0,
                                )
                            except (OSError, subprocess.TimeoutExpired) as exc:
                                status = EvaluationStatus.WORKER_ERROR
                                error = _error_text(exc)
                            else:
                                if copied.returncode == 66:
                                    status = EvaluationStatus.NO_GDS
                                    error = "program did not write device.gds"
                                elif copied.returncode == 65:
                                    status = EvaluationStatus.NO_GDS
                                    error = (
                                        "program did not write a non-empty "
                                        "regular device.gds"
                                    )
                                elif copied.returncode in {1, 65, 66}:
                                    status = EvaluationStatus.NO_GDS
                                    error = (
                                        "program did not leave a readable "
                                        "regular device.gds"
                                    )
                                elif copied.returncode != 0:
                                    status = EvaluationStatus.WORKER_ERROR
                                    error = "candidate output collection failed"
                                elif not copied.stdout:
                                    status = EvaluationStatus.NO_GDS
                                    error = "program wrote an empty device.gds"
                                elif len(copied.stdout) > 16 * 1024 * 1024:
                                    status = EvaluationStatus.WORKER_ERROR
                                    error = "candidate output exceeded the collection bound"
                                else:
                                    try:
                                        (workdir / "device.gds").write_bytes(
                                            copied.stdout
                                        )
                                    except OSError as exc:
                                        status = EvaluationStatus.WORKER_ERROR
                                        error = _error_text(exc)
                                    else:
                                        status = EvaluationStatus.OK
                                        error = None
        except (OSError, subprocess.TimeoutExpired) as exc:
            status = EvaluationStatus.WORKER_ERROR
            error = _error_text(exc)
        finally:
            cleanup_ok = self._cleanup_candidate_containers(
                candidate_id=candidate_id,
                known_id=container_id,
            )
        if not cleanup_ok:
            return (
                EvaluationStatus.WORKER_ERROR,
                "candidate container cleanup failed",
            )
        return status, error

    def _run_candidate(
        self,
        source: str,
        workdir: Path,
    ) -> tuple[EvaluationStatus, str | None]:
        if self.execution_boundary is not None:
            return self._run_isolated_candidate(source, workdir)
        return self._run_local_candidate(source, workdir)

    def evaluate(
        self,
        reference: VerifierReference,
        completion: str,
    ) -> EvaluationResult:
        if self._closed:
            raise RuntimeError("evaluator is closed")
        started = time.monotonic()
        source = extract_code(completion)
        if not source:
            return EvaluationResult(
                EvaluationStatus.SYNTAX_ERROR,
                Attribution.MODEL,
                error="empty program",
                latency_seconds=time.monotonic() - started,
            )

        try:
            compile(source, "device.py", "exec")
        except SyntaxError as exc:
            return EvaluationResult(
                EvaluationStatus.SYNTAX_ERROR,
                Attribution.MODEL,
                error=_error_text(exc),
                latency_seconds=time.monotonic() - started,
            )

        violations = tuple(strict_purity_violations(source))
        if violations:
            return EvaluationResult(
                EvaluationStatus.SOURCE_REJECTED,
                Attribution.MODEL,
                violations=violations,
                error=violations[0],
                latency_seconds=time.monotonic() - started,
            )

        try:
            prepared = self._prepared(reference)
        except ReferenceFailure as exc:
            return EvaluationResult(
                EvaluationStatus.REFERENCE_ERROR,
                Attribution.REFERENCE,
                error=_error_text(exc),
                latency_seconds=time.monotonic() - started,
            )
        except Exception as exc:
            return EvaluationResult(
                EvaluationStatus.WORKER_ERROR,
                Attribution.EVALUATOR,
                error=_error_text(exc),
                latency_seconds=time.monotonic() - started,
                retryable=True,
            )

        temporary_root = (
            self.execution_boundary.workspace_root
            if self.execution_boundary is not None
            else None
        )
        with tempfile.TemporaryDirectory(
            prefix="pixcell-eval-",
            dir=temporary_root,
        ) as temporary:
            workdir = Path(temporary)
            execution_status, execution_error = self._run_candidate(source, workdir)
            if execution_status is not EvaluationStatus.OK:
                attribution = (
                    Attribution.EVALUATOR
                    if execution_status is EvaluationStatus.WORKER_ERROR
                    else Attribution.MODEL
                )
                return EvaluationResult(
                    execution_status,
                    attribution,
                    error=execution_error,
                    latency_seconds=time.monotonic() - started,
                    retryable=attribution is Attribution.EVALUATOR,
                )

            gds_path = workdir / "device.gds"
            try:
                polygons = extract_polygons(gds_path)
                if not polygons:
                    raise ValueError("device.gds has no layer-(1,0) polygons")
            except Exception as exc:
                return EvaluationResult(
                    EvaluationStatus.BAD_GDS,
                    Attribution.MODEL,
                    error=_error_text(exc),
                    latency_seconds=time.monotonic() - started,
                )

            try:
                raster, render_info = render_gds_absolute(
                    polygons,
                    prepared.calibration,
                )
                metrics = compute_metrics(raster, prepared.target.copy())
                raster_mask = np.asarray(raster.convert("L")) < 245
                target_mask = np.asarray(prepared.target) < 245
                scale_x, scale_y = prepared.calibration["scale_px_per_um"]
                chamfer_b, _, _ = chamfer_sym_um(
                    boundary_mask(raster_mask),
                    boundary_mask(target_mask),
                    2.0 / (scale_x + scale_y),
                )
                _full, full_a_to_b, full_b_to_a = chamfer_sym_um(
                    raster_mask, target_mask, 2.0 / (scale_x + scale_y)
                )
                gds_size_um = (
                    float(render_info["gds_size_um"][0]),
                    float(render_info["gds_size_um"][1]),
                )
                rc01_breakdown = evaluate_rc01_calibrated(
                    raster,
                    prepared.target,
                    prepared.calibration,
                    gds_size_um=gds_size_um,
                )
                rc01_dict = rc01_breakdown.to_dict()
                if not math.isfinite(rc01_dict["mean_bnd_dist_px"]):
                    rc01_dict["mean_bnd_dist_px"] = None
                metrics = {
                    **metrics,
                    "chamfer_boundary_um": (
                        None if chamfer_b == float("inf") else float(chamfer_b)
                    ),
                    "chamfer_pred_to_target_um": (
                        None if full_a_to_b == float("inf") else float(full_a_to_b)
                    ),
                    "chamfer_target_to_pred_um": (
                        None if full_b_to_a == float("inf") else float(full_b_to_a)
                    ),
                    "rc01": rc01_dict,
                    "rc01_score": float(rc01_breakdown.score),
                    "rc01_overflow_factor": float(rc01_breakdown.overflow_factor),
                    "rc01_empty": not bool(raster_mask.any()),
                }
                diagnostics = _json_diagnostic(
                    {
                        **metrics,
                        "render_info": render_info,
                        "render_sha256": _render_sha256(raster),
                        "reference_sha256": reference.target_image_sha256,
                    }
                )
            except Exception as exc:
                return EvaluationResult(
                    EvaluationStatus.MEASUREMENT_ERROR,
                    Attribution.EVALUATOR,
                    error=_error_text(exc),
                    latency_seconds=time.monotonic() - started,
                    retryable=True,
                )

        if not isinstance(diagnostics, dict):
            raise RuntimeError("measurement diagnostics are not an object")
        iou = float(diagnostics["IoU"])
        dice = float(diagnostics["Dice"])
        return EvaluationResult(
            EvaluationStatus.OK,
            Attribution.MODEL,
            iou=iou,
            dice=dice,
            metrics=diagnostics,
            latency_seconds=time.monotonic() - started,
        )

    def evaluate_many(
        self,
        reference: VerifierReference,
        completions: list[str],
    ) -> list[EvaluationResult]:
        """Score one rollout group in one bounded, ordered batch."""

        return self.evaluate_batch([(reference, item) for item in completions])

    def evaluate_batch(
        self,
        requests: list[tuple[VerifierReference, str]],
    ) -> list[EvaluationResult]:
        """Score mixed tasks while preserving request order."""

        if self._closed:
            raise RuntimeError("evaluator is closed")
        if not requests:
            return []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(requests))) as pool:
            results = list(pool.map(lambda item: self.evaluate(*item), requests))

        for _ in range(self.evaluator_retries):
            retry_indexes = [
                index
                for index, result in enumerate(results)
                if result.retryable and result.attribution is Attribution.EVALUATOR
            ]
            if not retry_indexes:
                break
            with ThreadPoolExecutor(
                max_workers=min(self.max_workers, len(retry_indexes))
            ) as pool:
                replacements = list(
                    pool.map(
                        lambda index: self.evaluate(*requests[index]),
                        retry_indexes,
                    )
                )
            for index, replacement in zip(retry_indexes, replacements, strict=True):
                results[index] = replacement
        return results
