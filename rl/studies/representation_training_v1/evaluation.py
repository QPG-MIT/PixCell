"""Receipt-bound checkpoint evaluation for representation-training-v1.

The evaluator is deliberately narrower than the general baseline runner:

* the sampler checkpoint can only come from an immutable training-wave receipt;
* the model, renderer, effort, image limit, context, and sampling policy come
  from the committed study protocol;
* every prompt and verifier reference is checked before a Tinker client exists;
* sampled output is persisted before execution, so an infrastructure fault can
  be retried without paying for another completion; and
* candidate execution always uses the pinned isolation boundary.
"""

from __future__ import annotations

import argparse
import asyncio
import errno
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from rl.common.contracts import (
    ModelObservation,
    observation_from_row,
    reference_from_row,
    sampler_from_row,
)
from rl.common.dataset_io import parquet_paths
from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
    PixCellEvaluator,
)
from rl.common.prompt import build_prompt_text, prompt_asset_hashes
from rl.evaluation.tasks import (
    BENCHMARK_TASK_SET,
    EvaluationTask,
    canonical_json_sha256,
    load_task_manifest,
    load_task_set,
)
from rl.track_a.tinker_data import _message, _renderer

from .dataset_binding import _dataset_binding
from .protocol import (
    STUDY_ID,
    StageSpec,
    file_sha256,
    load_protocol,
    protocol_path,
    stage_spec,
    validate_source_sha,
)
from .store import StageKey, TrainingRecord, TrainingStore


EVALUATION_SCHEMA_VERSION = "pixcell-training-checkpoint-evaluation-v1"
EVALUATION_RECORD_SCHEMA_VERSION = "pixcell-training-evaluation-record-v1"
PANEL_PROGRESS = "progress"
PANEL_DEPTH_VALIDATION = "depth-validation"
PANEL_INKLING_PROMOTION = "inkling-promotion"
LEVEL_PROGRESS_PANELS = {
    "L0": "level-progress-l0",
    "L1": "level-progress-l1",
    "L2": "level-progress-l2",
    "L3": "level-progress-l3",
    "L4": "level-progress-l4",
}
PANEL_DEPTH_FINAL_SELECTION = "depth-final-selection"
LEVEL_PROGRESS_ROWS = {
    "L0": 93,
    "L1": 127,
    "L2": 98,
    "L3": 120,
    "L4": 108,
}
_MODEL_EVALUATION_STATUSES = frozenset(
    {
        EvaluationStatus.OK.value,
        EvaluationStatus.SYNTAX_ERROR.value,
        EvaluationStatus.SOURCE_REJECTED.value,
        EvaluationStatus.RUNTIME_TIMEOUT.value,
        EvaluationStatus.RUNTIME_ERROR.value,
        EvaluationStatus.NO_GDS.value,
        EvaluationStatus.BAD_GDS.value,
    }
)
PANELS = (
    PANEL_PROGRESS,
    PANEL_DEPTH_VALIDATION,
    PANEL_INKLING_PROMOTION,
)
SUPPORTED_PANELS = (
    *PANELS,
    *LEVEL_PROGRESS_PANELS.values(),
    PANEL_DEPTH_FINAL_SELECTION,
)
MAX_IMAGE_LONG_EDGE = 1920
MAX_OUTPUT_TOKENS = 60_000
TEMPERATURE = 1.0
TOP_P = 1.0
SAMPLE_CONCURRENCY = 8
EVALUATION_BATCH_SIZE = 32
EVALUATOR_WORKERS = 8
_PANEL_SELECTION_SEED = (
    "pixcell-representation-training-v1-inkling-promotion-20260728"
)
_LEVEL_PROGRESS_SELECTION = "validation-realization-slot-6"
_DEPTH_FINAL_SELECTION = "validation-realization-slot-7"
_DEPTH_COLUMNS = (
    "id",
    "level",
    "image",
    "target_image",
    "footprint_um",
    "representation_id",
    "leakage_group_id",
    "image_sha256",
    "target_image_sha256",
    "realization_slot",
    "split_role",
)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TINKER_PATH = re.compile(r"^tinker://[^\s]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_RECORD_BYTES = 32 * 1024 * 1024
_FORBIDDEN_PROMPT_FRAGMENTS = (
    "DISPLAY NOTE",
    "magnification x:y",
    "px/um",
    "target_image",
    "calibration.json",
)


class CheckpointEvaluationError(RuntimeError):
    """The requested checkpoint evaluation is not safe or reproducible."""


class CheckpointReceiptError(CheckpointEvaluationError):
    """The requested checkpoint is not bound to an exact training receipt."""


class SamplingInfrastructureFault(CheckpointEvaluationError):
    """Tinker sampling failed outside the model's generated program."""


class ReferencePanelFault(CheckpointEvaluationError):
    """A private verifier reference is invalid or changed."""


class EvaluationInfrastructureFault(CheckpointEvaluationError):
    """The isolated evaluator failed independently of model output."""


class ImmutableEvaluationRecordError(CheckpointEvaluationError):
    """A create-only evaluation record already contains different bytes."""


@dataclass(frozen=True)
class CheckpointBinding:
    key: StageKey
    stage: StageSpec
    wave: str
    checkpoint_name: str
    checkpoint: dict[str, Any]
    checkpoint_inventory_sha256: str
    sampler_path: str
    run_manifest: TrainingRecord
    wave_receipt: TrainingRecord


@dataclass(frozen=True)
class BaseModelBinding:
    """An explicit base-model sampler identity with no fictitious receipt."""

    key: StageKey
    stage: StageSpec
    wave: str
    checkpoint_name: str
    checkpoint: dict[str, Any]
    checkpoint_inventory_sha256: str
    sampler_path: str
    binding_sha256: str


EvaluationBinding = CheckpointBinding | BaseModelBinding


@dataclass(frozen=True)
class PreparedTask:
    task: EvaluationTask
    prompt_tokens: int
    prompt_text_sha256: str
    reference_evidence: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CheckpointEvaluationError(
            "evaluation record is not finite JSON"
        ) from exc


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EvaluationInfrastructureFault(
                "evaluator returned a non-finite number"
            )
        return value
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if hasattr(value, "item"):
        return _safe_json(value.item())
    return str(value)


def _record_document(
    *,
    record_type: str,
    key: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = json.loads(_canonical_bytes(payload))
    document = {
        "schema_version": EVALUATION_RECORD_SCHEMA_VERSION,
        "record_type": record_type,
        "key": dict(key),
        "payload": normalized,
        "payload_sha256": _canonical_sha256(normalized),
    }
    document["record_sha256"] = _canonical_sha256(document)
    return document


def _validate_record(
    value: Mapping[str, Any],
    *,
    record_type: str,
    key: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "record_type",
        "key",
        "payload",
        "payload_sha256",
        "record_sha256",
    }
    if set(value) != required:
        raise CheckpointEvaluationError("evaluation record schema changed")
    if value["schema_version"] != EVALUATION_RECORD_SCHEMA_VERSION:
        raise CheckpointEvaluationError("evaluation record has a foreign schema")
    if value["record_type"] != record_type or value["key"] != dict(key):
        raise CheckpointEvaluationError(
            "evaluation record key differs from its canonical path"
        )
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise CheckpointEvaluationError("evaluation record payload is not an object")
    if value["payload_sha256"] != _canonical_sha256(payload):
        raise CheckpointEvaluationError("evaluation payload digest mismatch")
    unsigned = dict(value)
    observed = str(unsigned.pop("record_sha256"))
    if observed != _canonical_sha256(unsigned) or not _SHA256.fullmatch(observed):
        raise CheckpointEvaluationError("evaluation envelope digest mismatch")
    return dict(value)


class _EvaluationLock(AbstractContextManager["_EvaluationLock"]):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "_EvaluationLock":
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.path, flags, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            if "fd" in locals():
                os.close(fd)
            raise CheckpointEvaluationError(
                "this exact checkpoint panel is already active"
            ) from exc
        self.fd = fd
        return self

    def __exit__(self, *_args: object) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


class CheckpointEvaluationStore:
    """Create-only records under one receipt-bound training stage."""

    def __init__(
        self,
        *,
        stage_path: Path,
        wave: str,
        checkpoint_name: str,
        panel: str,
    ) -> None:
        if (
            not _IDENTIFIER.fullmatch(wave)
            or not _IDENTIFIER.fullmatch(checkpoint_name)
            or panel not in SUPPORTED_PANELS
        ):
            raise ValueError("invalid checkpoint-evaluation identity")
        self.stage_path = stage_path.expanduser().resolve(strict=True)
        requested = (
            self.stage_path
            / "evaluations"
            / wave
            / checkpoint_name
            / panel
        )
        requested.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved = requested.resolve(strict=True)
        if resolved != requested or not resolved.is_relative_to(self.stage_path):
            raise CheckpointEvaluationError(
                "evaluation root must be a real directory inside its stage"
            )
        self.root = resolved

    def acquire_lock(self) -> _EvaluationLock:
        return _EvaluationLock(self.root / ".lock")

    @staticmethod
    def _task_component(task_id: str) -> str:
        if not _IDENTIFIER.fullmatch(task_id):
            raise ValueError(f"unsafe task ID: {task_id!r}")
        return task_id

    def load_manifest(self) -> dict[str, Any] | None:
        return self._load(
            PurePosixPath("manifest.json"),
            record_type="evaluation_manifest",
            key={},
        )

    def create_or_verify_manifest(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify(
            PurePosixPath("manifest.json"),
            record_type="evaluation_manifest",
            key={},
            payload=payload,
        )

    def load_sample(self, task_id: str) -> dict[str, Any] | None:
        component = self._task_component(task_id)
        return self._load(
            PurePosixPath("candidates", component, "sample.json"),
            record_type="checkpoint_sample",
            key={"task_id": task_id},
        )

    def create_or_verify_sample(
        self,
        task_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        component = self._task_component(task_id)
        return self._create_or_verify(
            PurePosixPath("candidates", component, "sample.json"),
            record_type="checkpoint_sample",
            key={"task_id": task_id},
            payload=payload,
        )

    def load_evaluation(self, task_id: str) -> dict[str, Any] | None:
        component = self._task_component(task_id)
        return self._load(
            PurePosixPath("candidates", component, "evaluation.json"),
            record_type="checkpoint_evaluation",
            key={"task_id": task_id},
        )

    def create_or_verify_evaluation(
        self,
        task_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        component = self._task_component(task_id)
        return self._create_or_verify(
            PurePosixPath("candidates", component, "evaluation.json"),
            record_type="checkpoint_evaluation",
            key={"task_id": task_id},
            payload=payload,
        )

    def load_report(self) -> dict[str, Any] | None:
        return self._load(
            PurePosixPath("report.json"),
            record_type="checkpoint_report",
            key={},
        )

    def create_or_verify_report(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify(
            PurePosixPath("report.json"),
            record_type="checkpoint_report",
            key={},
            payload=payload,
        )

    def _path(self, relative: PurePosixPath) -> Path:
        path = self.root.joinpath(*relative.parts)
        parent = path.parent.resolve(strict=False)
        if parent != self.root and not parent.is_relative_to(self.root):
            raise CheckpointEvaluationError("evaluation record escaped its root")
        return path

    def _create_or_verify(
        self,
        relative: PurePosixPath,
        *,
        record_type: str,
        key: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        expected = _record_document(
            record_type=record_type,
            key=key,
            payload=payload,
        )
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = _canonical_bytes(expected) + b"\n"
        temporary = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(temporary, flags, 0o600)
            try:
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                os.close(fd)
            try:
                os.link(temporary, path)
                directory_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except FileExistsError:
                observed = self._load(
                    relative,
                    record_type=record_type,
                    key=key,
                )
                if observed is None or _canonical_bytes(observed) != _canonical_bytes(
                    expected
                ):
                    raise ImmutableEvaluationRecordError(
                        f"{relative} already contains different data"
                    )
                return observed
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return expected

    def _load(
        self,
        relative: PurePosixPath,
        *,
        record_type: str,
        key: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        path = self._path(relative)
        if not path.exists():
            return None
        return _validate_record(
            self._read(path),
            record_type=record_type,
            key=key,
        )

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise CheckpointEvaluationError(
                    f"{path} must not be a symlink"
                ) from exc
            raise
        try:
            metadata = os.fstat(fd)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size > _MAX_RECORD_BYTES
            ):
                raise CheckpointEvaluationError(
                    f"{path} is not a bounded regular file"
                )
            chunks: list[bytes] = []
            remaining = _MAX_RECORD_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > _MAX_RECORD_BYTES:
                raise CheckpointEvaluationError(
                    f"{path} exceeds the record bound"
                )
        finally:
            os.close(fd)
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CheckpointEvaluationError(
                f"{path} is not valid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise CheckpointEvaluationError(f"{path} must contain an object")
        return value


def _depth_rows(dataset_root: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    rows: list[dict[str, Any]] = []
    for path in parquet_paths(
        dataset_root,
        configuration="depth",
        split="validation",
    ):
        schema = set(pq.read_schema(path).names)
        missing = set(_DEPTH_COLUMNS) - schema
        if missing:
            raise ReferencePanelFault(
                f"{path} is missing evaluation fields: {sorted(missing)}"
            )
        rows.extend(
            pq.read_table(path, columns=list(_DEPTH_COLUMNS)).to_pylist()
        )
    return rows


def _depth_task(row: Mapping[str, Any]) -> EvaluationTask:
    sampler = sampler_from_row(row)
    return EvaluationTask(
        task_id=sampler.opaque_id,
        level=sampler.level.upper(),
        representation_id=sampler.representation_id,
        observation=observation_from_row(row),
        reference=reference_from_row(row),
    )


def _benchmark_tasks(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[EvaluationTask]:
    manifest = (
        protocol_path(repo_root).parent
        / str(protocol["evaluation"]["task_manifest"])
    ).resolve(strict=True)
    if not manifest.is_relative_to(repo_root):
        raise ReferencePanelFault("benchmark manifest escaped the repository")
    document = load_task_manifest(manifest, repo_root=repo_root)
    if (
        document["logical_sha256"]
        != protocol["evaluation"]["task_manifest_logical_sha256"]
    ):
        raise ReferencePanelFault(
            "benchmark manifest differs from the training protocol"
        )
    tasks = load_task_set(
        repo_root=repo_root,
        manifest=document,
        task_set=BENCHMARK_TASK_SET,
    )
    if [task.task_id for task in tasks] != [f"F{index}" for index in range(1, 9)]:
        raise ReferencePanelFault("progress panel is not exact ordered F1-F8")
    return tasks


def _selection_rank(*values: str) -> str:
    payload = "\0".join((_PANEL_SELECTION_SEED, *values))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _inkling_depth_tasks(rows: Sequence[dict[str, Any]]) -> list[EvaluationTask]:
    quotas = {"L0": 6, "L1": 6, "L2": 6, "L3": 6, "L4": 36}
    by_level_representation: dict[str, dict[str, list[dict[str, Any]]]] = {
        level: {} for level in quotas
    }
    for row in rows:
        level = str(row["level"]).upper()
        if level not in by_level_representation:
            raise ReferencePanelFault(f"unexpected depth level: {level!r}")
        by_level_representation[level].setdefault(
            str(row["representation_id"]),
            [],
        ).append(row)

    selected: list[EvaluationTask] = []
    for level, count in quotas.items():
        represented = by_level_representation[level]
        representation_ids = sorted(
            represented,
            key=lambda value: _selection_rank("representation", level, value),
        )
        if len(representation_ids) < count:
            raise ReferencePanelFault(
                f"{level} has too few representations for Inkling promotion"
            )
        for representation_id in representation_ids[:count]:
            row = min(
                represented[representation_id],
                key=lambda value: _selection_rank(
                    "realization",
                    level,
                    representation_id,
                    str(value["id"]),
                ),
            )
            selected.append(_depth_task(row))
    return selected


def _one_realization_per_representation(
    rows: Sequence[dict[str, Any]],
    *,
    realization_slot: int,
    level: str | None = None,
) -> list[EvaluationTask]:
    """Select one exact held-out realization for every requested representation."""

    requested_level = level.upper() if level is not None else None
    by_representation: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row_level = str(row["level"]).upper()
        if requested_level is not None and row_level != requested_level:
            continue
        if row.get("realization_slot") == realization_slot:
            by_representation[(row_level, str(row["representation_id"]))].append(row)
    if not by_representation:
        raise ReferencePanelFault(
            f"no validation rows use realization slot {realization_slot}"
        )

    selected: list[EvaluationTask] = []
    for identity, candidates in sorted(by_representation.items()):
        if len(candidates) != 1:
            raise ReferencePanelFault(
                f"{identity[0]}/{identity[1]} has {len(candidates)} rows "
                f"for validation realization slot {realization_slot}"
            )
        selected.append(_depth_task(candidates[0]))
    return selected


def _level_for_progress_panel(panel: str) -> str | None:
    return next(
        (level for level, panel_id in LEVEL_PROGRESS_PANELS.items() if panel == panel_id),
        None,
    )


def build_panel_tasks(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    panel: str,
) -> list[EvaluationTask]:
    """Build one exact label-free evaluation panel."""

    if panel not in SUPPORTED_PANELS:
        raise ValueError(f"unsupported panel {panel!r}")
    if panel == PANEL_PROGRESS:
        tasks = _benchmark_tasks(repo_root=repo_root, protocol=protocol)
    else:
        rows = _depth_rows(repo_root / "dataset")
        if len(rows) != int(protocol["dataset"]["validation_rows"]):
            raise ReferencePanelFault(
                "depth validation row count differs from the protocol"
            )
        if panel == PANEL_DEPTH_VALIDATION:
            tasks = sorted(
                (_depth_task(row) for row in rows),
                key=lambda task: (
                    task.level,
                    task.representation_id,
                    task.task_id,
                ),
            )
        elif panel == PANEL_INKLING_PROMOTION:
            tasks = _inkling_depth_tasks(rows)
            tasks.extend(_benchmark_tasks(repo_root=repo_root, protocol=protocol))
        elif panel == PANEL_DEPTH_FINAL_SELECTION:
            tasks = _one_realization_per_representation(
                rows,
                realization_slot=7,
            )
        else:
            level = _level_for_progress_panel(panel)
            if level is None:
                raise ValueError(f"unsupported panel {panel!r}")
            tasks = _one_realization_per_representation(
                rows,
                realization_slot=6,
                level=level,
            )

    expected = {
        PANEL_PROGRESS: 8,
        PANEL_DEPTH_VALIDATION: 1092,
        PANEL_INKLING_PROMOTION: 68,
        PANEL_DEPTH_FINAL_SELECTION: 546,
        **{
            panel_id: LEVEL_PROGRESS_ROWS[level]
            for level, panel_id in LEVEL_PROGRESS_PANELS.items()
        },
    }[panel]
    if len(tasks) != expected:
        raise ReferencePanelFault(
            f"{panel} selected {len(tasks)} tasks; expected {expected}"
        )
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ReferencePanelFault(f"{panel} selected duplicate task IDs")
    if panel == PANEL_DEPTH_VALIDATION:
        representations = {task.representation_id for task in tasks}
        if len(representations) != 546:
            raise ReferencePanelFault(
                "depth validation no longer spans 546 representations"
            )
    if panel == PANEL_DEPTH_FINAL_SELECTION:
        representations = {
            (task.level, task.representation_id)
            for task in tasks
        }
        if len(representations) != 546:
            raise ReferencePanelFault(
                "depth final-selection no longer spans 546 representations"
            )
    level = _level_for_progress_panel(panel)
    if level is not None:
        if (
            {task.level for task in tasks} != {level}
            or len({task.representation_id for task in tasks})
            != LEVEL_PROGRESS_ROWS[level]
        ):
            raise ReferencePanelFault(
                f"{panel} no longer contains one {level} row per representation"
            )
    if panel == PANEL_INKLING_PROMOTION:
        counts = Counter(task.level for task in tasks)
        expected_counts = {
            "BENCHMARK": 8,
            "L0": 6,
            "L1": 6,
            "L2": 6,
            "L3": 6,
            "L4": 36,
        }
        if counts != expected_counts:
            raise ReferencePanelFault(
                f"Inkling promotion panel changed: {dict(counts)}"
            )
    return tasks


def _task_manifest(tasks: Sequence[EvaluationTask], *, panel: str) -> dict[str, Any]:
    entries = [
        {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
            "image_sha256": task.observation.image_sha256,
            "target_image_sha256": task.reference.target_image_sha256,
            "footprint_um": list(task.observation.footprint_um),
        }
        for task in tasks
    ]
    return {
        "schema_version": "pixcell-training-evaluation-task-panel-v1",
        "panel": panel,
        "selection_seed": (
            _PANEL_SELECTION_SEED
            if panel == PANEL_INKLING_PROMOTION
            else (
                _LEVEL_PROGRESS_SELECTION
                if panel in LEVEL_PROGRESS_PANELS.values()
                else (
                    _DEPTH_FINAL_SELECTION
                    if panel == PANEL_DEPTH_FINAL_SELECTION
                    else None
                )
            )
        ),
        "task_count": len(entries),
        "task_ids": [item["task_id"] for item in entries],
        "logical_sha256": canonical_json_sha256(entries),
    }


def _load_checkpoint_binding(
    *,
    store: TrainingStore,
    protocol: dict[str, Any],
    stage_id: str,
    wave: str,
    checkpoint_name: str,
    replicate_id: str,
    expected_receipt_sha256: str,
    source_git_sha: str,
) -> CheckpointBinding:
    if not _SHA256.fullmatch(expected_receipt_sha256):
        raise CheckpointReceiptError(
            "wave receipt SHA-256 must be explicit and complete"
        )
    stage = stage_spec(protocol, stage_id)
    stage.wave(wave)
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    manifest = store.load_manifest(key)
    receipt = store.load_wave_receipt(key, wave=wave)
    if manifest is None or receipt is None:
        raise CheckpointReceiptError(
            f"{stage_id}/{wave}/{replicate_id} has no complete training receipt"
        )
    if receipt.record_sha256 != expected_receipt_sha256:
        raise CheckpointReceiptError(
            "the external wave receipt differs from the requested digest"
        )
    expected_manifest = receipt.payload.get("run_manifest_record_sha256")
    if expected_manifest != manifest.record_sha256:
        raise CheckpointReceiptError(
            "wave receipt and training run manifest differ"
        )
    expected_fields = {
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "contract_version": protocol["contract_version"],
    }
    for field, expected in expected_fields.items():
        if manifest.payload.get(field) != expected:
            raise CheckpointReceiptError(
                f"training manifest {field} differs from this evaluation"
            )
    manifest_stage = manifest.payload.get("stage")
    if (
        not isinstance(manifest_stage, Mapping)
        or manifest_stage.get("stage_id") != stage.stage_id
        or manifest_stage.get("model_key") != stage.model_key
    ):
        raise CheckpointReceiptError("training manifest has the wrong stage")
    manifest_dataset = manifest.payload.get("dataset")
    if (
        not isinstance(manifest_dataset, Mapping)
        or manifest_dataset.get("logical_release_sha256")
        != protocol["dataset"]["logical_release_sha256"]
    ):
        raise CheckpointReceiptError("training manifest has the wrong dataset")
    if not _IDENTIFIER.fullmatch(checkpoint_name):
        raise CheckpointReceiptError("checkpoint name is not a safe identifier")
    terminal = receipt.payload.get("checkpoint")
    inventory = receipt.payload.get("checkpoint_inventory")
    if not isinstance(terminal, Mapping) or not isinstance(inventory, Mapping):
        raise CheckpointReceiptError(
            "wave receipt has no immutable checkpoint inventory"
        )
    if set(inventory) != {"count", "entries", "logical_sha256"}:
        raise CheckpointReceiptError("checkpoint inventory schema changed")
    entries = inventory.get("entries")
    count = inventory.get("count")
    inventory_sha256 = str(inventory.get("logical_sha256", ""))
    if (
        not isinstance(entries, list)
        or not entries
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(entries)
        or inventory_sha256 != _canonical_sha256(entries)
        or not _SHA256.fullmatch(inventory_sha256)
    ):
        raise CheckpointReceiptError("checkpoint inventory digest or count changed")
    entry_fields = {
        "name",
        "batch",
        "epoch",
        "final",
        "state_path",
        "sampler_path",
        "role",
        "training_progress_fraction",
    }
    normalized_entries: list[dict[str, Any]] = []
    names: set[str] = set()
    previous_progress = -1.0
    terminal_name = (
        "final"
        if stage.kind == "sft"
        else f"{int(stage.wave(wave)['max_steps']):06d}"
    )
    if stage.kind == "rl" and len(entries) != 1:
        raise CheckpointReceiptError(
            "an RL wave must expose only its immutable ceiling checkpoint"
        )
    for index, value in enumerate(entries):
        if not isinstance(value, Mapping) or set(value) != entry_fields:
            raise CheckpointReceiptError("checkpoint inventory entry schema changed")
        entry = dict(value)
        name = str(entry["name"])
        role = str(entry["role"])
        progress = entry["training_progress_fraction"]
        if (
            not _IDENTIFIER.fullmatch(name)
            or name in names
            or role not in {"periodic", "terminal"}
            or isinstance(progress, bool)
            or not isinstance(progress, (int, float))
            or not math.isfinite(float(progress))
            or not 0.0 < float(progress) <= 1.0
            or float(progress) <= previous_progress
            or not _TINKER_PATH.fullmatch(str(entry["state_path"]))
            or not _TINKER_PATH.fullmatch(str(entry["sampler_path"]))
        ):
            raise CheckpointReceiptError("checkpoint inventory entry is invalid")
        if role == "periodic":
            if (
                stage.kind != "sft"
                or not re.fullmatch(r"[0-9]{6}", name)
                or entry["final"] is not False
                or float(progress) >= 1.0
                or index == len(entries) - 1
            ):
                raise CheckpointReceiptError(
                    "periodic checkpoint inventory entry is invalid"
                )
        elif (
            name != terminal_name
            or entry["final"] is not True
            or float(progress) != 1.0
            or index != len(entries) - 1
            or (
                stage.kind == "rl"
                and entry["batch"] != int(stage.wave(wave)["max_steps"])
            )
        ):
            raise CheckpointReceiptError(
                "terminal checkpoint inventory entry is invalid"
            )
        names.add(name)
        previous_progress = float(progress)
        normalized_entries.append(entry)
    terminal_fields = {
        key: normalized_entries[-1][key]
        for key in (
            "name",
            "batch",
            "epoch",
            "final",
            "state_path",
            "sampler_path",
        )
    }
    if dict(terminal) != terminal_fields:
        raise CheckpointReceiptError(
            "terminal checkpoint alias differs from the inventory"
        )
    selected = next(
        (entry for entry in normalized_entries if entry["name"] == checkpoint_name),
        None,
    )
    if selected is None:
        raise CheckpointReceiptError(
            f"checkpoint {checkpoint_name!r} is not in the wave receipt"
        )
    sampler_path = str(selected["sampler_path"])
    if (
        receipt.payload.get("stage_id") != stage.stage_id
        or receipt.payload.get("wave") != wave
    ):
        raise CheckpointReceiptError("wave receipt identity differs from its path")
    return CheckpointBinding(
        key=key,
        stage=stage,
        wave=wave,
        checkpoint_name=checkpoint_name,
        checkpoint=selected,
        checkpoint_inventory_sha256=inventory_sha256,
        sampler_path=sampler_path,
        run_manifest=manifest,
        wave_receipt=receipt,
    )


def _base_model_binding(
    *,
    protocol: dict[str, Any],
    stage_id: str,
    replicate_id: str,
    source_git_sha: str,
) -> BaseModelBinding:
    stage = stage_spec(protocol, stage_id)
    if (
        stage.stage_id != "qwen-base-rl-l0"
        or stage.model_key != "qwen"
        or stage.parent != "base:qwen"
    ):
        raise CheckpointReceiptError(
            "base-model evaluation is restricted to qwen-base-rl-l0"
        )
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    model = dict(protocol["models"]["qwen"])
    checkpoint = {
        "name": "base",
        "model": model["model"],
        "renderer": model["renderer"],
        "thinking": model["thinking"],
    }
    inventory_sha256 = _canonical_sha256([checkpoint])
    identity = {
        "schema_version": "pixcell-training-base-model-binding-v1",
        "study_id": STUDY_ID,
        "stage_id": stage.stage_id,
        "replicate_id": replicate_id,
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "model": checkpoint,
        "checkpoint_inventory_sha256": inventory_sha256,
    }
    return BaseModelBinding(
        key=key,
        stage=stage,
        wave="base",
        checkpoint_name="base",
        checkpoint=checkpoint,
        checkpoint_inventory_sha256=inventory_sha256,
        sampler_path=str(model["model"]),
        binding_sha256=_canonical_sha256(identity),
    )


def _sample_binding_identity(binding: EvaluationBinding) -> dict[str, Any]:
    common = {
        "checkpoint_name": binding.checkpoint_name,
        "checkpoint_inventory_sha256": binding.checkpoint_inventory_sha256,
        "checkpoint": binding.checkpoint,
    }
    if isinstance(binding, CheckpointBinding):
        return {
            "training_wave_receipt_record_sha256": (
                binding.wave_receipt.record_sha256
            ),
            **common,
        }
    return {
        "base_model_binding_sha256": binding.binding_sha256,
        **common,
    }


def _sampler_provenance(binding: EvaluationBinding) -> dict[str, Any]:
    common = {
        "sampler_path": binding.sampler_path,
        "checkpoint_name": binding.checkpoint_name,
        "checkpoint": binding.checkpoint,
        "checkpoint_inventory_sha256": binding.checkpoint_inventory_sha256,
    }
    if isinstance(binding, CheckpointBinding):
        return {
            **common,
            "training_run_manifest_record_sha256": (
                binding.run_manifest.record_sha256
            ),
            "training_wave_receipt_record_sha256": (
                binding.wave_receipt.record_sha256
            ),
            "training_wave_receipt_relative_path": str(
                binding.wave_receipt.relative_path
            ),
        }
    return {
        **common,
        "binding_kind": "base-model",
        "base_model_binding_sha256": binding.binding_sha256,
    }


def _sampling_client_kwargs(binding: EvaluationBinding) -> dict[str, str]:
    if isinstance(binding, BaseModelBinding):
        return {"base_model": binding.sampler_path}
    return {"model_path": binding.sampler_path}


def _model_binding(
    protocol: Mapping[str, Any],
    stage: StageSpec,
) -> dict[str, Any]:
    model = dict(protocol["models"][stage.model_key])
    exact = {
        "max_image_long_edge": MAX_IMAGE_LONG_EDGE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "context_tokens": 65_536,
    }
    for field, expected in exact.items():
        if model.get(field) != expected:
            raise CheckpointEvaluationError(
                f"{stage.model_key} {field} differs from the evaluation contract"
            )
    if model.get("thinking") is not True:
        raise CheckpointEvaluationError("checkpoint evaluation requires thinking on")
    return model


def _direct_prompt_text(observation: ModelObservation) -> str:
    text = build_prompt_text(observation)
    leaked = [fragment for fragment in _FORBIDDEN_PROMPT_FRAGMENTS if fragment in text]
    if leaked:
        raise CheckpointEvaluationError(
            f"direct Phase-A prompt leaked verifier fields: {leaked}"
        )
    return text


def _preflight_tasks(
    *,
    tasks: Sequence[EvaluationTask],
    renderer: Any,
    evaluator: PixCellEvaluator,
    context_tokens: int,
) -> tuple[list[PreparedTask], dict[str, Any]]:
    """Check every prompt and reference before any sampling client is created."""

    prepared: list[PreparedTask] = []
    prompt_digest = hashlib.sha256()
    reference_digest = hashlib.sha256()
    for task in tasks:
        prompt_text = _direct_prompt_text(task.observation)
        prompt_text_sha256 = hashlib.sha256(
            prompt_text.encode("utf-8")
        ).hexdigest()
        try:
            evidence = evaluator.validate_reference(task.reference)
        except Exception as exc:
            raise ReferencePanelFault(
                f"{task.task_id} reference validation failed: {exc}"
            ) from exc
        if (
            evidence.get("target_image_sha256")
            != task.reference.target_image_sha256
        ):
            raise ReferencePanelFault(
                f"{task.task_id} reference digest changed during validation"
            )
        prompt = renderer.build_generation_prompt(
            [_message(task, max_image=MAX_IMAGE_LONG_EDGE)]
        )
        prompt_tokens = int(prompt.length)
        if prompt_tokens + MAX_OUTPUT_TOKENS > context_tokens:
            raise CheckpointEvaluationError(
                f"{task.task_id} exceeds context: "
                f"{prompt_tokens}+{MAX_OUTPUT_TOKENS}>{context_tokens}"
            )
        prompt_digest.update(task.task_id.encode("utf-8"))
        prompt_digest.update(str(prompt_tokens).encode("ascii"))
        prompt_digest.update(bytes.fromhex(prompt_text_sha256))
        prompt_digest.update(bytes.fromhex(task.observation.image_sha256))
        reference_digest.update(task.task_id.encode("utf-8"))
        reference_digest.update(
            _canonical_bytes(
                {
                    "target_image_sha256": task.reference.target_image_sha256,
                    "evidence": evidence,
                }
            )
        )
        prepared.append(
            PreparedTask(
                task=task,
                prompt_tokens=prompt_tokens,
                prompt_text_sha256=prompt_text_sha256,
                reference_evidence=dict(evidence),
            )
        )
    prompt_lengths = [item.prompt_tokens for item in prepared]
    return prepared, {
        "task_count": len(prepared),
        "prompt_tokens": {
            "min": min(prompt_lengths),
            "max": max(prompt_lengths),
        },
        "minimum_context_headroom": (
            context_tokens - MAX_OUTPUT_TOKENS - max(prompt_lengths)
        ),
        "prompt_set_sha256": prompt_digest.hexdigest(),
        "reference_set_sha256": reference_digest.hexdigest(),
    }


def _sample_seed(
    *,
    protocol_sha256: str,
    binding: EvaluationBinding,
    panel: str,
    task_id: str,
) -> int:
    digest = hashlib.sha256(
        "\0".join(
            (
                "pixcell-checkpoint-evaluation-seed-v1",
                protocol_sha256,
                binding.stage.stage_id,
                binding.wave,
                binding.checkpoint_name,
                binding.checkpoint_inventory_sha256,
                binding.key.replicate_id,
                panel,
                task_id,
            )
        ).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _message_reasoning(message: Any) -> str:
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(part.get("thinking", ""))
        for part in content
        if isinstance(part, Mapping) and part.get("type") == "thinking"
    )


def _decode_sample(renderer: Any, sequence: Any) -> dict[str, Any]:
    from tinker_cookbook.renderers import get_text_content

    tokens = [int(token) for token in sequence.tokens]
    raw_text = str(renderer.tokenizer.decode(tokens))
    try:
        message, termination = renderer.parse_response(tokens)
    except Exception as exc:
        raise SamplingInfrastructureFault(
            f"renderer could not parse a sampled response: {exc}"
        ) from exc
    answer_text = str(get_text_content(message))
    reasoning_text = _message_reasoning(message)
    stop_reason = str(sequence.stop_reason)
    cap_hit = (
        len(tokens) >= MAX_OUTPUT_TOKENS
        or "length" in stop_reason.lower()
        or "max_token" in stop_reason.lower()
    )
    return {
        "completion_tokens": len(tokens),
        "stop_reason": stop_reason,
        "cap_hit": cap_hit,
        "raw_text": raw_text,
        "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "answer_text": answer_text,
        "answer_text_sha256": hashlib.sha256(
            answer_text.encode("utf-8")
        ).hexdigest(),
        "reasoning_text": reasoning_text,
        "reasoning_text_sha256": hashlib.sha256(
            reasoning_text.encode("utf-8")
        ).hexdigest(),
        "channel_parse_complete": bool(termination.is_clean),
    }


def _sample_payload(
    *,
    prepared: PreparedTask,
    response: dict[str, Any],
    seed: int,
    manifest_record_sha256: str,
    binding: EvaluationBinding,
) -> dict[str, Any]:
    return {
        "evaluation_manifest_record_sha256": manifest_record_sha256,
        **_sample_binding_identity(binding),
        "task": {
            "task_id": prepared.task.task_id,
            "level": prepared.task.level,
            "representation_id": prepared.task.representation_id,
            "image_sha256": prepared.task.observation.image_sha256,
            "target_image_sha256": prepared.task.reference.target_image_sha256,
        },
        "request": {
            "num_samples": 1,
            "seed": seed,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "prompt_tokens": prepared.prompt_tokens,
            "prompt_text_sha256": prepared.prompt_text_sha256,
        },
        "response": response,
    }


def _evaluation_payload(
    *,
    task: EvaluationTask,
    result: EvaluationResult,
    sample_record_sha256: str,
    manifest_record_sha256: str,
) -> dict[str, Any]:
    if result.attribution is Attribution.REFERENCE:
        raise ReferencePanelFault(
            f"{task.task_id}: {result.status.value}: {result.error}"
        )
    if result.attribution is Attribution.EVALUATOR:
        raise EvaluationInfrastructureFault(
            f"{task.task_id}: {result.status.value}: {result.error}"
        )
    if result.attribution is not Attribution.MODEL:
        raise EvaluationInfrastructureFault(
            f"{task.task_id}: evaluator returned an unknown attribution"
        )
    iou = 0.0 if result.iou is None else float(result.iou)
    if not math.isfinite(iou) or not 0.0 <= iou <= 1.0:
        raise EvaluationInfrastructureFault(
            f"{task.task_id}: evaluator returned invalid IoU {result.iou!r}"
        )
    if result.status is EvaluationStatus.OK and result.iou is None:
        raise EvaluationInfrastructureFault(
            f"{task.task_id}: successful evaluation has no IoU"
        )
    return {
        "evaluation_manifest_record_sha256": manifest_record_sha256,
        "sample_record_sha256": sample_record_sha256,
        "task_id": task.task_id,
        "level": task.level,
        "representation_id": task.representation_id,
        "status": result.status.value,
        "attribution": result.attribution.value,
        "pure_executable": result.status is EvaluationStatus.OK,
        "raw_absolute_scale_iou": iou,
        "dice": float(result.dice) if result.dice is not None else None,
        "render_sha256": result.metrics.get("render_sha256"),
        "reference_sha256": result.metrics.get("reference_sha256"),
        "violations": list(result.violations),
        "error": result.error,
        "latency_seconds": float(result.latency_seconds),
        "diagnostics": _safe_json(result.metrics),
    }


def _validate_sample_record(
    *,
    record: Mapping[str, Any],
    prepared: PreparedTask,
    seed: int,
    manifest_record_sha256: str,
    binding: EvaluationBinding,
) -> None:
    payload = record["payload"]
    expected = {
        "evaluation_manifest_record_sha256": manifest_record_sha256,
        **_sample_binding_identity(binding),
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ImmutableEvaluationRecordError(
                f"{prepared.task.task_id} sample belongs to another evaluation"
            )
    task = payload.get("task")
    request = payload.get("request")
    if not isinstance(task, Mapping) or not isinstance(request, Mapping):
        raise ImmutableEvaluationRecordError("sample record is incomplete")
    expected_task = {
        "task_id": prepared.task.task_id,
        "level": prepared.task.level,
        "representation_id": prepared.task.representation_id,
        "image_sha256": prepared.task.observation.image_sha256,
        "target_image_sha256": prepared.task.reference.target_image_sha256,
    }
    expected_request = {
        "num_samples": 1,
        "seed": seed,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "prompt_tokens": prepared.prompt_tokens,
        "prompt_text_sha256": prepared.prompt_text_sha256,
    }
    if task != expected_task or request != expected_request:
        raise ImmutableEvaluationRecordError(
            f"{prepared.task.task_id} sample request changed"
        )


def _validate_evaluation_record(
    *,
    record: Mapping[str, Any],
    task: EvaluationTask,
    sample_record_sha256: str,
    manifest_record_sha256: str,
) -> None:
    payload = record["payload"]
    expected = {
        "evaluation_manifest_record_sha256": manifest_record_sha256,
        "sample_record_sha256": sample_record_sha256,
        "task_id": task.task_id,
        "level": task.level,
        "representation_id": task.representation_id,
        "attribution": Attribution.MODEL.value,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ImmutableEvaluationRecordError(
                f"{task.task_id} evaluation record changed"
            )
    status = str(payload.get("status", ""))
    if status not in _MODEL_EVALUATION_STATUSES:
        raise ImmutableEvaluationRecordError(
            f"{task.task_id} has a non-model evaluation status"
        )
    if payload.get("pure_executable") != (status == EvaluationStatus.OK.value):
        raise ImmutableEvaluationRecordError(
            f"{task.task_id} status and pure-executable flag differ"
        )
    iou = payload.get("raw_absolute_scale_iou")
    if (
        isinstance(iou, bool)
        or not isinstance(iou, (int, float))
        or not math.isfinite(float(iou))
        or not 0.0 <= float(iou) <= 1.0
    ):
        raise ImmutableEvaluationRecordError(
            f"{task.task_id} has an invalid stored IoU"
        )
    if status != EvaluationStatus.OK.value and float(iou) != 0.0:
        raise ImmutableEvaluationRecordError(
            f"{task.task_id} failed model output has nonzero IoU"
        )


async def _sample_missing(
    *,
    prepared: Sequence[PreparedTask],
    renderer: Any,
    sampling_client: Any,
    store: CheckpointEvaluationStore,
    manifest_record_sha256: str,
    binding: EvaluationBinding,
    protocol_sha256: str,
    panel: str,
) -> None:
    import tinker

    semaphore = asyncio.Semaphore(SAMPLE_CONCURRENCY)

    async def sample_one(item: PreparedTask) -> None:
        seed = _sample_seed(
            protocol_sha256=protocol_sha256,
            binding=binding,
            panel=panel,
            task_id=item.task.task_id,
        )
        existing = store.load_sample(item.task.task_id)
        if existing is not None:
            _validate_sample_record(
                record=existing,
                prepared=item,
                seed=seed,
                manifest_record_sha256=manifest_record_sha256,
                binding=binding,
            )
            return
        messages = [_message(item.task, max_image=MAX_IMAGE_LONG_EDGE)]
        prompt_text = str(messages[0]["content"][1]["text"])
        if (
            hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            != item.prompt_text_sha256
        ):
            raise SamplingInfrastructureFault(
                f"{item.task.task_id} prompt text changed after preflight"
            )
        prompt = renderer.build_generation_prompt(messages)
        if int(prompt.length) != item.prompt_tokens:
            raise SamplingInfrastructureFault(
                f"{item.task.task_id} prompt changed after preflight"
            )
        async with semaphore:
            try:
                result = await sampling_client.sample_async(
                    prompt=prompt,
                    num_samples=1,
                    sampling_params=tinker.SamplingParams(
                        stop=renderer.get_stop_sequences(),
                        max_tokens=MAX_OUTPUT_TOKENS,
                        temperature=TEMPERATURE,
                        top_p=TOP_P,
                        seed=seed,
                    ),
                )
            except Exception as exc:
                raise SamplingInfrastructureFault(
                    f"{item.task.task_id} sampling failed: {exc}"
                ) from exc
        sequences = list(result.sequences)
        if len(sequences) != 1:
            raise SamplingInfrastructureFault(
                f"{item.task.task_id} returned {len(sequences)} samples, expected 1"
            )
        response = _decode_sample(renderer, sequences[0])
        store.create_or_verify_sample(
            item.task.task_id,
            _sample_payload(
                prepared=item,
                response=response,
                seed=seed,
                manifest_record_sha256=manifest_record_sha256,
                binding=binding,
            ),
        )

    await asyncio.gather(*(sample_one(item) for item in prepared))


def _score_missing(
    *,
    prepared: Sequence[PreparedTask],
    evaluator: PixCellEvaluator,
    store: CheckpointEvaluationStore,
    manifest_record_sha256: str,
) -> None:
    pending: list[tuple[PreparedTask, dict[str, Any]]] = []
    for item in prepared:
        sample = store.load_sample(item.task.task_id)
        if sample is None:
            raise CheckpointEvaluationError(
                f"{item.task.task_id} has no resumable sample"
            )
        existing = store.load_evaluation(item.task.task_id)
        if existing is not None:
            _validate_evaluation_record(
                record=existing,
                task=item.task,
                sample_record_sha256=str(sample["record_sha256"]),
                manifest_record_sha256=manifest_record_sha256,
            )
            continue
        pending.append((item, sample))

    for offset in range(0, len(pending), EVALUATION_BATCH_SIZE):
        batch = pending[offset : offset + EVALUATION_BATCH_SIZE]
        requests = [
            (
                item.task.reference,
                str(sample["payload"]["response"]["answer_text"]),
            )
            for item, sample in batch
        ]
        try:
            results = evaluator.evaluate_batch(requests)
        except Exception as exc:
            raise EvaluationInfrastructureFault(
                f"isolated evaluation batch failed: {exc}"
            ) from exc
        if len(results) != len(batch):
            raise EvaluationInfrastructureFault(
                "isolated evaluator returned a different result count"
            )
        faults: list[CheckpointEvaluationError] = []
        for (item, sample), result in zip(batch, results, strict=True):
            try:
                payload = _evaluation_payload(
                    task=item.task,
                    result=result,
                    sample_record_sha256=str(sample["record_sha256"]),
                    manifest_record_sha256=manifest_record_sha256,
                )
            except (ReferencePanelFault, EvaluationInfrastructureFault) as exc:
                faults.append(exc)
                continue
            store.create_or_verify_evaluation(item.task.task_id, payload)
        if faults:
            raise faults[0]


def _aggregate(values: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not values:
        raise CheckpointEvaluationError("cannot aggregate an empty panel")
    ious = [float(value["raw_absolute_scale_iou"]) for value in values]
    pure = [bool(value["pure_executable"]) for value in values]
    return {
        "tasks": len(values),
        "mean_raw_absolute_scale_iou": sum(ious) / len(ious),
        "pure_executable": sum(pure),
        "pure_executable_rate": sum(pure) / len(pure),
        "statuses": dict(
            sorted(Counter(str(value["status"]) for value in values).items())
        ),
    }


def validate_checkpoint_report(
    record: Mapping[str, Any],
    *,
    manifest_record_sha256: str,
    binding: EvaluationBinding,
    panel: str,
    expected_task_ids: Sequence[str],
) -> dict[str, Any]:
    """Validate the immutable report identity used by promotion gates."""

    validated = _validate_record(
        record,
        record_type="checkpoint_report",
        key={},
    )
    payload = validated["payload"]
    expected_identity = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "study_id": STUDY_ID,
        "stage_id": binding.stage.stage_id,
        "wave": binding.wave,
        "checkpoint_name": binding.checkpoint_name,
        "replicate_id": binding.key.replicate_id,
        "panel": panel,
    }
    for field, expected in expected_identity.items():
        if payload.get(field) != expected:
            raise CheckpointEvaluationError(
                f"checkpoint report {field} differs from its request"
            )
    provenance = payload.get("provenance")
    summary = payload.get("summary")
    records = payload.get("records")
    if (
        not isinstance(provenance, Mapping)
        or not isinstance(summary, Mapping)
        or not isinstance(records, list)
    ):
        raise CheckpointEvaluationError("checkpoint report is incomplete")
    sampler = provenance.get("sampler")
    task_panel = provenance.get("task_panel")
    if not isinstance(sampler, Mapping) or not isinstance(task_panel, Mapping):
        raise CheckpointEvaluationError(
            "checkpoint report has incomplete provenance"
        )
    expected_provenance = {
        "evaluation_manifest_record_sha256": manifest_record_sha256,
    }
    for field, expected in expected_provenance.items():
        if provenance.get(field) != expected:
            raise CheckpointEvaluationError(
                f"checkpoint report {field} differs from its manifest"
            )
    expected_sampler = _sampler_provenance(binding)
    if any(
        sampler.get(field) != expected
        for field, expected in expected_sampler.items()
    ):
        raise CheckpointEvaluationError(
            "checkpoint report sampler provenance differs from training"
        )
    if isinstance(binding, BaseModelBinding) and any(
        field in sampler
        for field in (
            "training_run_manifest_record_sha256",
            "training_wave_receipt_record_sha256",
            "training_wave_receipt_relative_path",
        )
    ):
        raise CheckpointEvaluationError(
            "base-model report fabricates training provenance"
        )
    task_ids = [str(value) for value in expected_task_ids]
    if (
        task_panel.get("task_ids") != task_ids
        or task_panel.get("task_count") != len(task_ids)
        or summary.get("tasks") != len(task_ids)
        or [item.get("task_id") for item in records] != task_ids
    ):
        raise CheckpointEvaluationError(
            "checkpoint report task inventory differs from the sealed panel"
        )
    iou = summary.get("mean_raw_absolute_scale_iou")
    pure_rate = summary.get("pure_executable_rate")
    representation_macro = payload.get("representation_macro_mean_iou")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
        for value in (iou, pure_rate, representation_macro)
    ):
        raise CheckpointEvaluationError(
            "checkpoint report summary contains invalid metrics"
        )
    return validated


def _report_payload(
    *,
    repo_root: Path,
    prepared: Sequence[PreparedTask],
    store: CheckpointEvaluationStore,
    manifest_record: Mapping[str, Any],
    binding: EvaluationBinding,
    protocol: Mapping[str, Any],
    source_git_sha: str,
    panel: str,
    dataset: Mapping[str, Any],
    sandbox: Mapping[str, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_representation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in prepared:
        sample = store.load_sample(item.task.task_id)
        evaluation = store.load_evaluation(item.task.task_id)
        if sample is None or evaluation is None:
            raise CheckpointEvaluationError(
                f"{item.task.task_id} is incomplete"
            )
        _validate_evaluation_record(
            record=evaluation,
            task=item.task,
            sample_record_sha256=str(sample["record_sha256"]),
            manifest_record_sha256=str(manifest_record["record_sha256"]),
        )
        payload = evaluation["payload"]
        response = sample["payload"]["response"]
        record = {
            "task_id": item.task.task_id,
            "level": item.task.level,
            "representation_id": item.task.representation_id,
            "status": payload["status"],
            "pure_executable": payload["pure_executable"],
            "raw_absolute_scale_iou": payload["raw_absolute_scale_iou"],
            "completion_tokens": response["completion_tokens"],
            "stop_reason": response["stop_reason"],
            "cap_hit": response["cap_hit"],
            "channel_parse_complete": response["channel_parse_complete"],
            "answer_text_sha256": response["answer_text_sha256"],
            "render_sha256": payload["render_sha256"],
            "sample_record_sha256": sample["record_sha256"],
            "evaluation_record_sha256": evaluation["record_sha256"],
        }
        records.append(record)
        by_level[item.task.level].append(record)
        by_representation[item.task.representation_id].append(record)
    representation_summaries = {
        key: _aggregate(values)
        for key, values in sorted(by_representation.items())
    }
    return {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "study_id": STUDY_ID,
        "stage_id": binding.stage.stage_id,
        "wave": binding.wave,
        "checkpoint_name": binding.checkpoint_name,
        "replicate_id": binding.key.replicate_id,
        "panel": panel,
        "summary": _aggregate(records),
        "representation_macro_mean_iou": (
            sum(
                value["mean_raw_absolute_scale_iou"]
                for value in representation_summaries.values()
            )
            / len(representation_summaries)
        ),
        "levels": {
            key: _aggregate(values) for key, values in sorted(by_level.items())
        },
        "representations": representation_summaries,
        "records": records,
        "provenance": {
            "source_git_sha": source_git_sha,
            "protocol": {
                "logical_sha256": protocol["logical_sha256"],
                "file_sha256": file_sha256(protocol_path(repo_root)),
                "contract_version": protocol["contract_version"],
            },
            "dataset": {
                "repo_id": protocol["dataset"]["repo_id"],
                "revision": protocol["dataset"]["revision"],
                "configuration": protocol["dataset"]["configuration"],
                "split": (
                    "fixed-f1-f8"
                    if panel == PANEL_PROGRESS
                    else (
                        "depth/validation+fixed-f1-f8"
                        if panel == PANEL_INKLING_PROMOTION
                        else (
                            "depth/validation/slot-7"
                            if panel == PANEL_DEPTH_FINAL_SELECTION
                            else (
                                f"depth/validation/{_level_for_progress_panel(panel)}/slot-6"
                                if _level_for_progress_panel(panel) is not None
                                else "depth/validation"
                            )
                        )
                    )
                ),
                "logical_release_sha256": dataset["logical_release_sha256"],
                "freeze_file_sha256": dataset["freeze_file_sha256"],
                "parquet_shards": dataset["parquet_shards"],
            },
            "task_panel": _task_manifest(
                [item.task for item in prepared],
                panel=panel,
            ),
            "sampler": {
                "model": protocol["models"][binding.stage.model_key]["model"],
                "renderer": protocol["models"][binding.stage.model_key]["renderer"],
                "effort": protocol["models"][binding.stage.model_key].get("effort"),
                **_sampler_provenance(binding),
            },
            "sampling": {
                "attempts_per_task": 1,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "max_image_long_edge": MAX_IMAGE_LONG_EDGE,
                "seed_algorithm": "sha256-bound deterministic 31-bit seed",
            },
            "prompt_assets": prompt_asset_hashes(),
            "sandbox": dict(sandbox),
            "evaluation_manifest_record_sha256": manifest_record["record_sha256"],
        },
    }


def _sandbox_provenance(evaluator: PixCellEvaluator) -> dict[str, Any]:
    boundary = evaluator.execution_boundary
    if boundary is None:
        raise EvaluationInfrastructureFault(
            "checkpoint evaluation has no execution isolation boundary"
        )
    return {
        "runtime_path": str(boundary.runtime_path),
        "daemon_endpoint": boundary.daemon_endpoint,
        "image_ref": boundary.image_ref,
        "image_id": boundary.image_id,
        "workspace_root": str(boundary.workspace_root),
    }


def _default_evaluator_factory() -> PixCellEvaluator:
    return PixCellEvaluator(
        max_workers=EVALUATOR_WORKERS,
        evaluator_retries=1,
        require_isolation=True,
    )


def _default_service_client_factory() -> Any:
    import tinker

    return tinker.ServiceClient()


async def run_checkpoint_evaluation(
    *,
    repo_root: Path,
    stage_id: str,
    wave: str,
    checkpoint_name: str,
    replicate_id: str,
    panel: str,
    expected_source_sha: str,
    expected_wave_receipt_sha256: str,
    external_root: Path,
    confirmation: str,
    service_client_factory: Callable[[], Any] = _default_service_client_factory,
    evaluator_factory: Callable[[], PixCellEvaluator] = _default_evaluator_factory,
    base_model: bool = False,
) -> dict[str, Any]:
    """Run or resume one exact checkpoint panel.

    ``service_client_factory`` is intentionally injectable so tests can prove
    the entire zero-spend preflight precedes the first paid client.
    """

    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    source_git_sha = validate_source_sha(root, expected_source_sha)
    if confirmation != protocol["launch"]["confirmation_token"]:
        raise CheckpointEvaluationError(
            "explicit paid-evaluation confirmation is missing"
        )
    if replicate_id not in protocol["launch"]["replicates"]:
        raise CheckpointEvaluationError("replicate is not declared in the protocol")
    training_store = TrainingStore(
        repo_root=root,
        external_root=external_root,
    )
    if base_model:
        if (
            wave != "base"
            or checkpoint_name != "base"
            or expected_wave_receipt_sha256
        ):
            raise CheckpointReceiptError(
                "base-model evaluation must use wave/checkpoint 'base' and no receipt"
            )
        binding: EvaluationBinding = _base_model_binding(
            protocol=protocol,
            stage_id=stage_id,
            replicate_id=replicate_id,
            source_git_sha=source_git_sha,
        )
        if panel != LEVEL_PROGRESS_PANELS["L0"]:
            raise CheckpointEvaluationError(
                "base Qwen evaluation is restricted to level-progress-l0"
            )
    else:
        binding = _load_checkpoint_binding(
            store=training_store,
            protocol=protocol,
            stage_id=stage_id,
            wave=wave,
            checkpoint_name=checkpoint_name,
            replicate_id=replicate_id,
            expected_receipt_sha256=expected_wave_receipt_sha256,
            source_git_sha=source_git_sha,
        )
    if panel == PANEL_INKLING_PROMOTION and binding.stage.model_key != "inkling":
        raise CheckpointEvaluationError(
            "inkling-promotion is restricted to an Inkling checkpoint"
        )
    model = _model_binding(protocol, binding.stage)
    dataset = _dataset_binding(root / "dataset", protocol)
    tasks = build_panel_tasks(repo_root=root, protocol=protocol, panel=panel)
    renderer = _renderer(
        model["model"],
        model["renderer"],
        effort=model.get("effort"),
    )
    base_stage_lock = (
        training_store.acquire_stage_lock(binding.key)
        if isinstance(binding, BaseModelBinding)
        else None
    )
    if base_stage_lock is not None:
        base_stage_lock.__enter__()
    try:
        evaluator = evaluator_factory()
    except Exception:
        if base_stage_lock is not None:
            base_stage_lock.__exit__(None, None, None)
        raise
    try:
        prepared, preflight = _preflight_tasks(
            tasks=tasks,
            renderer=renderer,
            evaluator=evaluator,
            context_tokens=int(model["context_tokens"]),
        )
        sandbox = _sandbox_provenance(evaluator)
        panel_manifest = _task_manifest(tasks, panel=panel)
        evaluation_stage_path = training_store.stage_path(binding.key)
        if isinstance(binding, BaseModelBinding):
            evaluation_stage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        evaluation_store = CheckpointEvaluationStore(
            stage_path=evaluation_stage_path,
            wave=wave,
            checkpoint_name=binding.checkpoint_name,
            panel=panel,
        )
        with evaluation_store.acquire_lock():
            manifest_payload = {
                "study_id": STUDY_ID,
                "stage_id": binding.stage.stage_id,
                "wave": wave,
                "checkpoint_name": binding.checkpoint_name,
                "replicate_id": replicate_id,
                "panel": panel,
                "source_git_sha": source_git_sha,
                "protocol_logical_sha256": protocol["logical_sha256"],
                "protocol_file_sha256": file_sha256(protocol_path(root)),
                "contract_version": protocol["contract_version"],
                "dataset": dataset,
                "task_panel": panel_manifest,
                "model": model,
                "sampling": {
                    "attempts_per_task": 1,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "temperature": TEMPERATURE,
                    "top_p": TOP_P,
                    "max_image_long_edge": MAX_IMAGE_LONG_EDGE,
                    "sample_concurrency": SAMPLE_CONCURRENCY,
                    "evaluation_batch_size": EVALUATION_BATCH_SIZE,
                    "evaluator_workers": EVALUATOR_WORKERS,
                },
                "prompt_assets": prompt_asset_hashes(),
                "preflight": preflight,
                "sandbox": sandbox,
                "sampler": _sampler_provenance(binding),
            }
            manifest = evaluation_store.create_or_verify_manifest(
                manifest_payload
            )
            existing_report = evaluation_store.load_report()
            if existing_report is not None:
                validate_checkpoint_report(
                    existing_report,
                    manifest_record_sha256=str(manifest["record_sha256"]),
                    binding=binding,
                    panel=panel,
                    expected_task_ids=[item.task.task_id for item in prepared],
                )
                return {
                    "status": "already_complete",
                    "stage_id": binding.stage.stage_id,
                    "wave": wave,
                    "checkpoint_name": binding.checkpoint_name,
                    "panel": panel,
                    "report": str(
                        evaluation_store.root / "report.json"
                    ),
                    "report_record_sha256": existing_report["record_sha256"],
                    "summary": existing_report["payload"]["summary"],
                }

            missing_samples = [
                item
                for item in prepared
                if evaluation_store.load_sample(item.task.task_id) is None
            ]
            if missing_samples:
                if not os.environ.get("TINKER_API_KEY"):
                    raise CheckpointEvaluationError("TINKER_API_KEY is not present")
                try:
                    validate_source_sha(root, source_git_sha)
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    raise CheckpointEvaluationError(
                        "source changed after evaluation preflight; refusing "
                        "paid sampling access"
                    ) from exc
                # The first paid-capable object is created only after all
                # prompts, references, records, and sandbox provenance pass.
                service = service_client_factory()
                sampling_client = service.create_sampling_client(
                    **_sampling_client_kwargs(binding)
                )
                await _sample_missing(
                    prepared=missing_samples,
                    renderer=renderer,
                    sampling_client=sampling_client,
                    store=evaluation_store,
                    manifest_record_sha256=str(manifest["record_sha256"]),
                    binding=binding,
                    protocol_sha256=str(protocol["logical_sha256"]),
                    panel=panel,
                )

            # Validate every existing sample against this exact manifest before
            # execution. A resumed run therefore cannot silently mix requests.
            for item in prepared:
                seed = _sample_seed(
                    protocol_sha256=str(protocol["logical_sha256"]),
                    binding=binding,
                    panel=panel,
                    task_id=item.task.task_id,
                )
                sample = evaluation_store.load_sample(item.task.task_id)
                if sample is None:
                    raise CheckpointEvaluationError(
                        f"{item.task.task_id} sampling did not persist a record"
                    )
                _validate_sample_record(
                    record=sample,
                    prepared=item,
                    seed=seed,
                    manifest_record_sha256=str(manifest["record_sha256"]),
                    binding=binding,
                )
            _score_missing(
                prepared=prepared,
                evaluator=evaluator,
                store=evaluation_store,
                manifest_record_sha256=str(manifest["record_sha256"]),
            )
            report_payload = _report_payload(
                repo_root=root,
                prepared=prepared,
                store=evaluation_store,
                manifest_record=manifest,
                binding=binding,
                protocol=protocol,
                source_git_sha=source_git_sha,
                panel=panel,
                dataset=dataset,
                sandbox=sandbox,
            )
            report = evaluation_store.create_or_verify_report(report_payload)
            validate_checkpoint_report(
                report,
                manifest_record_sha256=str(manifest["record_sha256"]),
                binding=binding,
                panel=panel,
                expected_task_ids=[item.task.task_id for item in prepared],
            )
            return {
                "status": "complete",
                "stage_id": binding.stage.stage_id,
                "wave": wave,
                "checkpoint_name": binding.checkpoint_name,
                "panel": panel,
                "report": str(evaluation_store.root / "report.json"),
                "report_record_sha256": report["record_sha256"],
                "summary": report_payload["summary"],
            }
    finally:
        try:
            evaluator.close()
        finally:
            if base_stage_lock is not None:
                base_stage_lock.__exit__(None, None, None)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--stage", required=True)
    result.add_argument("--wave", required=True)
    result.add_argument("--checkpoint-name", required=True)
    result.add_argument("--replicate", default="r0")
    result.add_argument("--panel", choices=SUPPORTED_PANELS, required=True)
    result.add_argument("--source-git-sha", required=True)
    result.add_argument("--wave-receipt-record-sha256", default="")
    result.add_argument("--base-model", action="store_true")
    result.add_argument("--external-root", type=Path, required=True)
    result.add_argument("--confirm-spend", default="")
    return result


def main() -> None:
    args = parser().parse_args()
    report = asyncio.run(
        run_checkpoint_evaluation(
            repo_root=args.repo_root,
            stage_id=args.stage,
            wave=args.wave,
            checkpoint_name=args.checkpoint_name,
            replicate_id=args.replicate,
            panel=args.panel,
            expected_source_sha=args.source_git_sha,
            expected_wave_receipt_sha256=args.wave_receipt_record_sha256,
            external_root=args.external_root,
            confirmation=args.confirm_spend,
            base_model=args.base_model,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
