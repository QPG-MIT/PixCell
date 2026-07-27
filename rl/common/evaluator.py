"""Shared deterministic Python -> GDS -> absolute-scale IoU evaluation.

The evaluator measures; it does not search, repair, or provide textual
feedback. Candidate execution happens in a sacrificial subprocess. Reference
and evaluator failures are typed separately so they cannot become negative
policy examples by accident.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from homi.conductor.source_policy import purity_violations
from michaelangelo.core.compare_absolute import (
    compute_metrics,
    extract_polygons,
    render_gds_absolute,
)

from .contracts import VerifierReference
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


def _error_text(value: BaseException | str, limit: int = 1200) -> str:
    text = str(value).replace("\x00", "")
    return text[-limit:]


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
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.max_workers = max_workers
        self.execution_timeout_seconds = execution_timeout_seconds
        self.evaluator_retries = evaluator_retries
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

    @staticmethod
    def _child_environment() -> dict[str, str]:
        environment = dict(os.environ)
        for key in tuple(environment):
            upper = key.upper()
            if any(
                token in upper
                for token in (
                    "_API_KEY",
                    "_TOKEN",
                    "_SECRET",
                    "PASSWORD",
                    "CREDENTIAL",
                )
            ):
                environment.pop(key, None)
        environment.update(
            {
                "MPLBACKEND": "Agg",
                "PYTHONHASHSEED": "0",
                "PIXCELL_EVAL_CPU_SECONDS": "18",
                "PIXCELL_EVAL_FILE_BYTES": str(16 * 1024 * 1024),
                "PIXCELL_EVAL_OPEN_FILES": "128",
            }
        )
        return environment

    def _run_candidate(self, source: str, workdir: Path) -> tuple[EvaluationStatus, str | None]:
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
                    env=self._child_environment(),
                    start_new_session=True,
                )
                try:
                    return_code = process.wait(timeout=self.execution_timeout_seconds)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    return EvaluationStatus.RUNTIME_TIMEOUT, "candidate execution timed out"
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

        violations = tuple(purity_violations(source))
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

        with tempfile.TemporaryDirectory(prefix="pixcell-eval-") as temporary:
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
            except Exception as exc:
                return EvaluationResult(
                    EvaluationStatus.MEASUREMENT_ERROR,
                    Attribution.EVALUATOR,
                    error=_error_text(exc),
                    latency_seconds=time.monotonic() - started,
                    retryable=True,
                )

        iou = float(metrics["IoU"])
        dice = float(metrics["Dice"])
        diagnostics = dict(metrics)
        diagnostics["render_info"] = render_info
        diagnostics["render_sha256"] = _render_sha256(raster)
        diagnostics["reference_sha256"] = reference.target_image_sha256
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
