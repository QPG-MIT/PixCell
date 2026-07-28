"""Fail-closed, human-confirmed promotion gates for the training study.

This module never samples a model and never creates a Tinker client.  It turns
one already-sealed checkpoint-evaluation report into the immutable approval
record consumed by :mod:`launcher`.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl.common.prompt import prompt_asset_hashes
from rl.evaluation.tasks import canonical_json_sha256

from .protocol import (
    LEVELS,
    STUDY_ID,
    StageSpec,
    file_sha256,
    load_protocol,
    protocol_path,
    stage_spec,
    validate_source_sha,
)
from .store import (
    StageKey,
    TrainingRecord,
    TrainingStore,
    canonical_sha256,
)


APPROVAL_SCHEMA_VERSION = "pixcell-training-wave-approval-v1"
APPROVAL_CONFIRMATION_TOKEN = "PIXCELL_APPROVE_TRAINING_V1"
MASTERED_MINIMUM_IOU = 0.80
MASTERED_MINIMUM_PURE_EXECUTABLE_RATE = 0.95

PANEL_PROGRESS = "progress"
PANEL_DEPTH_VALIDATION = "depth-validation"
PANEL_INKLING_PROMOTION = "inkling-promotion"
EXPECTED_PANEL_ROWS = {
    PANEL_PROGRESS: 8,
    PANEL_DEPTH_VALIDATION: 1_092,
    PANEL_INKLING_PROMOTION: 68,
}

_REPORT_SCHEMA = "pixcell-training-checkpoint-evaluation-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TINKER_PATH = re.compile(r"^tinker://[^\s]+$")
_IMMUTABLE_IMAGE = re.compile(
    r"^(?:sha256:[0-9a-f]{64}|[^\s@]+@sha256:[0-9a-f]{64})$"
)


class PromotionError(RuntimeError):
    """An evaluation cannot authorize the requested training transition."""


@dataclass(frozen=True)
class PanelTaskIdentity:
    task_id: str
    level: str
    representation_id: str
    image_sha256: str
    target_image_sha256: str
    footprint_um: tuple[float, float]


@dataclass(frozen=True)
class EvaluationEvidence:
    """A fully checked immutable checkpoint report."""

    key: StageKey
    wave: str
    checkpoint_name: str
    checkpoint: dict[str, Any]
    checkpoint_inventory_sha256: str
    panel: str
    report: dict[str, Any]
    report_payload: dict[str, Any]
    report_record_sha256: str
    report_payload_sha256: str
    report_relative_path: str
    training_manifest: TrainingRecord
    training_receipt: TrainingRecord


@dataclass(frozen=True)
class ApprovalPlan:
    gate: str
    storage_wave: str
    expected_panel: str
    allowed_evaluation_checkpoints: tuple[tuple[str, str], ...]


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PromotionError(f"{path} must be an object")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PromotionError(f"{path} must be an integer >= {minimum}")
    return value


def _unit(value: Any, path: str) -> float:
    if isinstance(value, bool):
        raise PromotionError(f"{path} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PromotionError(f"{path} must be numeric") from exc
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise PromotionError(f"{path} must be finite and in [0, 1]")
    return result


def _close(actual: Any, expected: float, path: str) -> None:
    value = _unit(actual, path)
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12):
        raise PromotionError(f"{path}={value!r}; expected {expected!r}")


def _sha(value: Any, path: str) -> str:
    result = str(value)
    if not _SHA256.fullmatch(result):
        raise PromotionError(f"{path} must be a lowercase SHA-256")
    return result


def _required_prior_wave(stage: StageSpec, wave_name: str) -> str | None:
    target = int(stage.wave(wave_name)["max_steps"])
    earlier = [
        (int(wave["max_steps"]), name)
        for name, wave in stage.waves.items()
        if int(wave["max_steps"]) < target
    ]
    return max(earlier)[1] if earlier else None


def _mixed_allowed_checkpoints(current_level: str) -> tuple[tuple[str, str], ...]:
    index = LEVELS.index(current_level)
    return (
        ("qwen-mixed-sft", "complete"),
        *tuple(
            (f"qwen-mixed-rl-l{prior}", "complete")
            for prior in range(index)
        ),
    )


def approval_plan(stage: StageSpec, wave_name: str) -> ApprovalPlan:
    """Resolve the exact report and approval-record location for one wave."""

    gate = str(stage.wave(wave_name)["approval"])
    if gate == "initial":
        raise PromotionError(f"{stage.stage_id}/{wave_name} needs no approval")

    if gate == "clean-smoke-receipt":
        prior = _required_prior_wave(stage, wave_name)
        if prior is None:
            raise PromotionError("clean-smoke gate has no preceding wave")
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=PANEL_PROGRESS,
            allowed_evaluation_checkpoints=((stage.stage_id, prior),),
        )

    if gate == "promotion-receipt-and-explicit-human-approval":
        prior = _required_prior_wave(stage, wave_name)
        if (
            stage.stage_id != "inkling-l4-rl"
            or wave_name != "coverage-extension"
            or prior != "pilot"
        ):
            raise PromotionError("unknown advanced-policy promotion gate")
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=PANEL_INKLING_PROMOTION,
            allowed_evaluation_checkpoints=((stage.stage_id, prior),),
        )

    if gate in {
        "entry-evaluation-and-promotion-receipt",
        "parent-evaluation-receipt",
    }:
        parent_stage, parent_wave = stage.parent.split(":", 1)
        if parent_stage == "base" or parent_wave == "complete-or-skip":
            raise PromotionError(f"{gate} requires one exact trained parent")
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=PANEL_DEPTH_VALIDATION,
            allowed_evaluation_checkpoints=((parent_stage, parent_wave),),
        )

    if gate == "first-unmastered-entry-receipt":
        if (
            stage.current_level not in LEVELS
            or not stage.stage_id.startswith("qwen-mixed-rl-")
        ):
            raise PromotionError("first-unmastered gate is not a mixed-Qwen stage")
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=PANEL_DEPTH_VALIDATION,
            allowed_evaluation_checkpoints=_mixed_allowed_checkpoints(
                stage.current_level
            ),
        )

    raise PromotionError(f"unsupported approval gate: {gate!r}")


def _expected_panel_tasks(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    panel: str,
) -> list[PanelTaskIdentity]:
    # Import lazily: loading/recording approvals must remain importable when
    # the optional Tinker training stack is not installed.
    from .evaluation import build_panel_tasks

    tasks = build_panel_tasks(
        repo_root=repo_root,
        protocol=protocol,
        panel=panel,
    )
    return [
        PanelTaskIdentity(
            task_id=task.task_id,
            level=task.level,
            representation_id=task.representation_id,
            image_sha256=task.observation.image_sha256,
            target_image_sha256=task.reference.target_image_sha256,
            footprint_um=tuple(float(value) for value in task.observation.footprint_um),
        )
        for task in tasks
    ]


def _panel_manifest(
    tasks: Sequence[PanelTaskIdentity],
    *,
    panel: str,
) -> dict[str, Any]:
    entries = [
        {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
            "image_sha256": task.image_sha256,
            "target_image_sha256": task.target_image_sha256,
            "footprint_um": list(task.footprint_um),
        }
        for task in tasks
    ]
    return {
        "panel": panel,
        "task_count": len(tasks),
        "task_ids": [task.task_id for task in tasks],
        "logical_sha256": canonical_json_sha256(entries),
    }


def _aggregate(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not records:
        raise PromotionError("evaluation aggregate is empty")
    ious = [
        _unit(record.get("raw_absolute_scale_iou"), "record.raw_absolute_scale_iou")
        for record in records
    ]
    pure: list[bool] = []
    statuses: Counter[str] = Counter()
    for record in records:
        observed = record.get("pure_executable")
        if not isinstance(observed, bool):
            raise PromotionError("record.pure_executable must be boolean")
        status = str(record.get("status", ""))
        if not status or observed != (status == "ok"):
            raise PromotionError("record status and pure-executable flag differ")
        pure.append(observed)
        statuses[status] += 1
    return {
        "tasks": len(records),
        "mean_raw_absolute_scale_iou": sum(ious) / len(ious),
        "pure_executable": sum(pure),
        "pure_executable_rate": sum(pure) / len(pure),
        "statuses": dict(sorted(statuses.items())),
    }


def _validate_aggregate(
    observed: Any,
    expected: Mapping[str, Any],
    *,
    path: str,
) -> None:
    value = _mapping(observed, path)
    for field in ("tasks", "pure_executable"):
        actual = _integer(value.get(field), f"{path}.{field}")
        if actual != expected[field]:
            raise PromotionError(
                f"{path}.{field}={actual}; expected {expected[field]}"
            )
    _close(
        value.get("mean_raw_absolute_scale_iou"),
        float(expected["mean_raw_absolute_scale_iou"]),
        f"{path}.mean_raw_absolute_scale_iou",
    )
    _close(
        value.get("pure_executable_rate"),
        float(expected["pure_executable_rate"]),
        f"{path}.pure_executable_rate",
    )
    statuses = _mapping(value.get("statuses"), f"{path}.statuses")
    if dict(statuses) != expected["statuses"]:
        raise PromotionError(f"{path}.statuses differs from its records")


def _validate_report_metrics(
    report: Mapping[str, Any],
    *,
    expected_tasks: Sequence[PanelTaskIdentity],
) -> None:
    raw_records = report.get("records")
    if not isinstance(raw_records, list) or len(raw_records) != len(expected_tasks):
        raise PromotionError(
            f"report.records must contain all {len(expected_tasks)} tasks"
        )
    records: list[Mapping[str, Any]] = []
    for index, (raw, task) in enumerate(
        zip(raw_records, expected_tasks, strict=True)
    ):
        path = f"records[{index}]"
        record = _mapping(raw, path)
        expected_identity = {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
        }
        for field, expected in expected_identity.items():
            if record.get(field) != expected:
                raise PromotionError(
                    f"{path}.{field}={record.get(field)!r}; expected {expected!r}"
                )
        _unit(
            record.get("raw_absolute_scale_iou"),
            f"{path}.raw_absolute_scale_iou",
        )
        tokens = _integer(record.get("completion_tokens"), f"{path}.completion_tokens")
        if tokens > 60_000:
            raise PromotionError(f"{path}.completion_tokens exceeds the sealed cap")
        for field in ("cap_hit", "channel_parse_complete"):
            if not isinstance(record.get(field), bool):
                raise PromotionError(f"{path}.{field} must be boolean")
        for field in (
            "answer_text_sha256",
            "sample_record_sha256",
            "evaluation_record_sha256",
        ):
            _sha(record.get(field), f"{path}.{field}")
        render = record.get("render_sha256")
        if render is not None:
            _sha(render, f"{path}.render_sha256")
        # This also enforces the status/purity relationship.
        _aggregate([record])
        records.append(record)

    expected_summary = _aggregate(records)
    _validate_aggregate(report.get("summary"), expected_summary, path="summary")

    by_level: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_representation: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_level[str(record["level"])].append(record)
        by_representation[str(record["representation_id"])].append(record)
    observed_levels = _mapping(report.get("levels"), "levels")
    expected_levels = {
        key: _aggregate(values) for key, values in sorted(by_level.items())
    }
    if set(observed_levels) != set(expected_levels):
        raise PromotionError("report.levels differs from the panel")
    for key, expected in expected_levels.items():
        _validate_aggregate(observed_levels[key], expected, path=f"levels.{key}")

    observed_representations = _mapping(
        report.get("representations"),
        "representations",
    )
    expected_representations = {
        key: _aggregate(values)
        for key, values in sorted(by_representation.items())
    }
    if set(observed_representations) != set(expected_representations):
        raise PromotionError("report.representations differs from the panel")
    for key, expected in expected_representations.items():
        _validate_aggregate(
            observed_representations[key],
            expected,
            path=f"representations.{key}",
        )
    macro = sum(
        value["mean_raw_absolute_scale_iou"]
        for value in expected_representations.values()
    ) / len(expected_representations)
    _close(
        report.get("representation_macro_mean_iou"),
        macro,
        "representation_macro_mean_iou",
    )


def _validate_report_payload(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    expected_source_sha: str,
    key: StageKey,
    wave: str,
    checkpoint_name: str,
    selected_checkpoint: Mapping[str, Any],
    checkpoint_inventory_sha256: str,
    panel: str,
    report: Mapping[str, Any],
    evaluation_manifest: Mapping[str, Any],
    training_manifest: TrainingRecord,
    training_receipt: TrainingRecord,
    expected_tasks: Sequence[PanelTaskIdentity],
) -> None:
    if report.get("schema_version") != _REPORT_SCHEMA:
        raise PromotionError("checkpoint report has a foreign schema")
    expected_identity = {
        "study_id": STUDY_ID,
        "stage_id": key.stage_id,
        "wave": wave,
        "checkpoint_name": checkpoint_name,
        "replicate_id": key.replicate_id,
        "panel": panel,
    }
    for field, expected in expected_identity.items():
        if report.get(field) != expected:
            raise PromotionError(f"report {field} differs from its path")

    expected_rows = EXPECTED_PANEL_ROWS[panel]
    if len(expected_tasks) != expected_rows:
        raise PromotionError(
            f"{panel} local task set has {len(expected_tasks)} rows, "
            f"expected {expected_rows}"
        )
    panel_document = _panel_manifest(expected_tasks, panel=panel)
    provenance = _mapping(report.get("provenance"), "provenance")
    observed_panel = _mapping(provenance.get("task_panel"), "provenance.task_panel")
    for field, expected in panel_document.items():
        if observed_panel.get(field) != expected:
            raise PromotionError(f"provenance.task_panel.{field} changed")

    if provenance.get("source_git_sha") != expected_source_sha:
        raise PromotionError("report source commit differs")
    protocol_binding = _mapping(provenance.get("protocol"), "provenance.protocol")
    expected_protocol = {
        "logical_sha256": protocol["logical_sha256"],
        "file_sha256": file_sha256(protocol_path(repo_root)),
        "contract_version": protocol["contract_version"],
    }
    for field, expected in expected_protocol.items():
        if protocol_binding.get(field) != expected:
            raise PromotionError(f"report protocol {field} differs")

    manifest_payload = _mapping(evaluation_manifest.get("payload"), "eval_manifest")
    for field, expected in {
        **expected_identity,
        "source_git_sha": expected_source_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "protocol_file_sha256": expected_protocol["file_sha256"],
        "contract_version": protocol["contract_version"],
    }.items():
        if manifest_payload.get(field) != expected:
            raise PromotionError(f"evaluation manifest {field} differs")
    if manifest_payload.get("task_panel") != dict(observed_panel):
        raise PromotionError("report and evaluation-manifest task panels differ")

    expected_assets = prompt_asset_hashes()
    if (
        provenance.get("prompt_assets") != expected_assets
        or manifest_payload.get("prompt_assets") != expected_assets
    ):
        raise PromotionError("evaluation prompt assets differ from this source")

    dataset = _mapping(provenance.get("dataset"), "provenance.dataset")
    manifest_dataset = _mapping(
        manifest_payload.get("dataset"),
        "evaluation_manifest.dataset",
    )
    for field, expected in manifest_dataset.items():
        if dataset.get(field) != expected:
            raise PromotionError(
                f"report and evaluation-manifest dataset {field} differ"
            )
    expected_dataset = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "logical_release_sha256": protocol["dataset"]["logical_release_sha256"],
    }
    for field, expected in expected_dataset.items():
        if dataset.get(field) != expected:
            raise PromotionError(f"evaluation dataset {field} differs")
    expected_split = {
        PANEL_PROGRESS: "fixed-f1-f8",
        PANEL_DEPTH_VALIDATION: "depth/validation",
        PANEL_INKLING_PROMOTION: "depth/validation+fixed-f1-f8",
    }[panel]
    if dataset.get("split") != expected_split:
        raise PromotionError("evaluation dataset split differs from its panel")

    if (
        training_manifest.payload.get("source_git_sha") != expected_source_sha
        or training_manifest.payload.get("protocol_logical_sha256")
        != protocol["logical_sha256"]
    ):
        raise PromotionError("training manifest provenance differs")
    manifest_training_dataset = _mapping(
        training_manifest.payload.get("dataset"),
        "training_manifest.dataset",
    )
    if (
        manifest_training_dataset.get("logical_release_sha256")
        != protocol["dataset"]["logical_release_sha256"]
    ):
        raise PromotionError("training manifest dataset differs")

    sampler = _mapping(provenance.get("sampler"), "provenance.sampler")
    evaluation_sampler = _mapping(
        manifest_payload.get("sampler"),
        "evaluation_manifest.sampler",
    )
    sampler_path = str(selected_checkpoint.get("sampler_path", ""))
    if not _TINKER_PATH.fullmatch(sampler_path):
        raise PromotionError("selected inventory entry has no sampler checkpoint")
    expected_sampler = {
        "sampler_path": sampler_path,
        "checkpoint_name": checkpoint_name,
        "checkpoint": dict(selected_checkpoint),
        "checkpoint_inventory_sha256": checkpoint_inventory_sha256,
        "training_run_manifest_record_sha256": training_manifest.record_sha256,
        "training_wave_receipt_record_sha256": training_receipt.record_sha256,
    }
    for field, expected in expected_sampler.items():
        if sampler.get(field) != expected or evaluation_sampler.get(field) != expected:
            raise PromotionError(f"evaluation sampler {field} differs")
    if (
        sampler.get("training_wave_receipt_relative_path")
        != str(training_receipt.relative_path)
    ):
        raise PromotionError("evaluation sampler receipt path differs")

    evaluated_stage = stage_spec(protocol, key.stage_id)
    model = protocol["models"][evaluated_stage.model_key]
    for field in ("model", "renderer", "effort"):
        if sampler.get(field) != model.get(field):
            raise PromotionError(f"evaluation sampler {field} differs")
    if manifest_payload.get("model") != model:
        raise PromotionError("evaluation manifest model differs")

    sampling = _mapping(provenance.get("sampling"), "provenance.sampling")
    expected_sampling = {
        "attempts_per_task": 1,
        "max_output_tokens": 60_000,
        "temperature": 1.0,
        "top_p": 1.0,
        "max_image_long_edge": 1_920,
    }
    for field, expected in expected_sampling.items():
        if sampling.get(field) != expected:
            raise PromotionError(f"evaluation sampling {field} differs")
    manifest_sampling = _mapping(
        manifest_payload.get("sampling"),
        "evaluation_manifest.sampling",
    )
    for field, expected in expected_sampling.items():
        if manifest_sampling.get(field) != expected:
            raise PromotionError(f"evaluation manifest sampling {field} differs")

    sandbox = _mapping(provenance.get("sandbox"), "provenance.sandbox")
    if dict(sandbox) != manifest_payload.get("sandbox"):
        raise PromotionError("report and evaluation-manifest sandboxes differ")
    if not _IMMUTABLE_IMAGE.fullmatch(str(sandbox.get("image_ref", ""))):
        raise PromotionError("evaluation sandbox image_ref is not immutable")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(sandbox.get("image_id", ""))):
        raise PromotionError("evaluation sandbox image_id is not immutable")
    if (
        provenance.get("evaluation_manifest_record_sha256")
        != evaluation_manifest.get("record_sha256")
    ):
        raise PromotionError("report is not bound to its evaluation manifest")

    if (
        training_receipt.payload.get("stage_id") != key.stage_id
        or training_receipt.payload.get("wave") != wave
        or training_receipt.payload.get("run_manifest_record_sha256")
        != training_manifest.record_sha256
    ):
        raise PromotionError("training receipt identity differs")
    _validate_report_metrics(report, expected_tasks=expected_tasks)


def validate_checkpoint_report(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    stage_id: str,
    wave: str,
    checkpoint_name: str,
    replicate_id: str,
    panel: str,
    expected_source_sha: str,
    expected_report_record_sha256: str,
) -> EvaluationEvidence:
    """Load and fully validate one sealed report from its canonical path."""

    if panel not in EXPECTED_PANEL_ROWS:
        raise PromotionError(f"unsupported evaluation panel: {panel!r}")
    _sha(expected_report_record_sha256, "expected_report_record_sha256")
    stage = stage_spec(dict(protocol), stage_id)
    stage.wave(wave)
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    training_manifest = store.load_manifest(key)
    training_receipt = store.load_wave_receipt(key, wave=wave)
    if training_manifest is None or training_receipt is None:
        raise PromotionError(
            f"{stage_id}/{wave}/{replicate_id} has no training receipt"
        )

    from .evaluation import (
        CheckpointEvaluationError,
        CheckpointEvaluationStore,
        _load_checkpoint_binding,
        validate_checkpoint_report as validate_evaluation_report,
    )

    evaluation_store = CheckpointEvaluationStore(
        stage_path=store.stage_path(key),
        wave=wave,
        checkpoint_name=checkpoint_name,
        panel=panel,
    )
    evaluation_manifest = evaluation_store.load_manifest()
    report = evaluation_store.load_report()
    if evaluation_manifest is None or report is None:
        raise PromotionError(
            f"{stage_id}/{wave}/{panel} has no complete evaluation report"
        )
    if report.get("record_sha256") != expected_report_record_sha256:
        raise PromotionError("evaluation report digest differs from the reviewed one")
    expected_tasks = _expected_panel_tasks(
        repo_root=repo_root,
        protocol=protocol,
        panel=panel,
    )
    try:
        binding = _load_checkpoint_binding(
            store=store,
            protocol=dict(protocol),
            stage_id=stage_id,
            wave=wave,
            checkpoint_name=checkpoint_name,
            replicate_id=replicate_id,
            expected_receipt_sha256=training_receipt.record_sha256,
            source_git_sha=expected_source_sha,
        )
        validate_evaluation_report(
            report,
            manifest_record_sha256=str(evaluation_manifest["record_sha256"]),
            binding=binding,
            panel=panel,
            expected_task_ids=[task.task_id for task in expected_tasks],
        )
    except CheckpointEvaluationError as exc:
        raise PromotionError(f"checkpoint report failed its native validator: {exc}") from exc
    payload = _mapping(report.get("payload"), "report.payload")
    _validate_report_payload(
        repo_root=repo_root,
        protocol=protocol,
        expected_source_sha=expected_source_sha,
        key=key,
        wave=wave,
        checkpoint_name=checkpoint_name,
        selected_checkpoint=binding.checkpoint,
        checkpoint_inventory_sha256=binding.checkpoint_inventory_sha256,
        panel=panel,
        report=payload,
        evaluation_manifest=evaluation_manifest,
        training_manifest=training_manifest,
        training_receipt=training_receipt,
        expected_tasks=expected_tasks,
    )
    return EvaluationEvidence(
        key=key,
        wave=wave,
        checkpoint_name=checkpoint_name,
        checkpoint=dict(binding.checkpoint),
        checkpoint_inventory_sha256=binding.checkpoint_inventory_sha256,
        panel=panel,
        report=dict(report),
        report_payload=dict(payload),
        report_record_sha256=str(report["record_sha256"]),
        report_payload_sha256=str(report["payload_sha256"]),
        report_relative_path=str(
            (
                TrainingStore.stage_relative_path(key)
                / "evaluations"
                / wave
                / checkpoint_name
                / panel
                / "report.json"
            )
        ),
        training_manifest=training_manifest,
        training_receipt=training_receipt,
    )


def first_unmastered_level(
    report: Mapping[str, Any],
    *,
    minimum_iou: float = MASTERED_MINIMUM_IOU,
    minimum_pure_executable_rate: float = (
        MASTERED_MINIMUM_PURE_EXECUTABLE_RATE
    ),
) -> str | None:
    """Return the first L0→L4 level missing either established threshold."""

    minimum_iou = _unit(minimum_iou, "minimum_iou")
    minimum_pure_executable_rate = _unit(
        minimum_pure_executable_rate,
        "minimum_pure_executable_rate",
    )
    summaries = _mapping(report.get("levels"), "report.levels")
    for level in LEVELS:
        summary = _mapping(summaries.get(level), f"report.levels.{level}")
        iou = _unit(
            summary.get("mean_raw_absolute_scale_iou"),
            f"report.levels.{level}.mean_raw_absolute_scale_iou",
        )
        pure = _unit(
            summary.get("pure_executable_rate"),
            f"report.levels.{level}.pure_executable_rate",
        )
        if iou < minimum_iou or pure < minimum_pure_executable_rate:
            return level
    return None


def _terminal_checkpoint(evidence: EvaluationEvidence) -> None:
    terminal = _mapping(
        evidence.training_receipt.payload.get("checkpoint"),
        "training_receipt.checkpoint",
    )
    fields = (
        "name",
        "batch",
        "epoch",
        "final",
        "state_path",
        "sampler_path",
    )
    selected_alias = {
        field: evidence.checkpoint.get(field)
        for field in fields
    }
    if selected_alias != dict(terminal):
        raise PromotionError(
            f"{evidence.key.stage_id}/{evidence.wave} must use its "
            "terminal checkpoint"
        )


def _best_mixed_checkpoint(
    candidates: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    if not candidates:
        raise PromotionError("mixed-SFT checkpoint ranking is empty")

    def rank(candidate: Mapping[str, Any]) -> tuple[float, float, float]:
        return (
            _unit(
                candidate.get("representation_macro_mean_iou"),
                "checkpoint.representation_macro_mean_iou",
            ),
            _unit(
                candidate.get("pure_executable_rate"),
                "checkpoint.pure_executable_rate",
            ),
            _unit(
                candidate.get("training_progress_fraction"),
                "checkpoint.training_progress_fraction",
            ),
        )

    return max(candidates, key=rank)


def _mixed_checkpoint_selection(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    selected: EvaluationEvidence,
    expected_source_sha: str,
) -> dict[str, Any]:
    if selected.key.stage_id != "qwen-mixed-sft":
        raise PromotionError("mixed checkpoint ranking received another stage")
    inventory = _mapping(
        selected.training_receipt.payload.get("checkpoint_inventory"),
        "training_receipt.checkpoint_inventory",
    )
    entries = inventory.get("entries")
    if not isinstance(entries, list) or not entries:
        raise PromotionError("mixed-SFT receipt has no checkpoint inventory")
    inventory_sha = _sha(
        inventory.get("logical_sha256"),
        "training_receipt.checkpoint_inventory.logical_sha256",
    )
    if (
        inventory_sha != canonical_sha256(entries)
        or inventory_sha != selected.checkpoint_inventory_sha256
    ):
        raise PromotionError("mixed-SFT checkpoint inventory digest differs")

    reports: list[EvaluationEvidence] = []
    for raw_entry in entries:
        entry = _mapping(raw_entry, "checkpoint_inventory.entries[]")
        checkpoint_name = str(entry.get("name", ""))
        if checkpoint_name == selected.checkpoint_name:
            evidence = selected
        else:
            from .evaluation import CheckpointEvaluationStore

            report_store = CheckpointEvaluationStore(
                stage_path=store.stage_path(selected.key),
                wave=selected.wave,
                checkpoint_name=checkpoint_name,
                panel=PANEL_DEPTH_VALIDATION,
            )
            report = report_store.load_report()
            if report is None:
                raise PromotionError(
                    "mixed-SFT promotion requires a complete depth-validation "
                    f"report for checkpoint {checkpoint_name!r}"
                )
            evidence = validate_checkpoint_report(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                stage_id=selected.key.stage_id,
                wave=selected.wave,
                checkpoint_name=checkpoint_name,
                replicate_id=selected.key.replicate_id,
                panel=PANEL_DEPTH_VALIDATION,
                expected_source_sha=expected_source_sha,
                expected_report_record_sha256=str(report["record_sha256"]),
            )
        if evidence.checkpoint != dict(entry):
            raise PromotionError(
                f"checkpoint {checkpoint_name!r} report and inventory differ"
            )
        reports.append(evidence)

    candidates = [
        {
            "checkpoint_name": evidence.checkpoint_name,
            "checkpoint": evidence.checkpoint,
            "report_record_sha256": evidence.report_record_sha256,
            "representation_macro_mean_iou": _unit(
                evidence.report_payload.get("representation_macro_mean_iou"),
                "report.representation_macro_mean_iou",
            ),
            "pure_executable_rate": _unit(
                _mapping(
                    evidence.report_payload.get("summary"),
                    "report.summary",
                ).get("pure_executable_rate"),
                "report.summary.pure_executable_rate",
            ),
            "training_progress_fraction": _unit(
                evidence.checkpoint.get("training_progress_fraction"),
                "checkpoint.training_progress_fraction",
            ),
        }
        for evidence in reports
    ]
    winner = _best_mixed_checkpoint(candidates)
    if winner["checkpoint_name"] != selected.checkpoint_name:
        raise PromotionError(
            f"mixed-SFT checkpoint {selected.checkpoint_name!r} is not the "
            f"deterministic best; expected {winner['checkpoint_name']!r}"
        )
    selection = {
        "schema_version": "pixcell-mixed-sft-checkpoint-selection-v1",
        "selection_rule": (
            "maximize full-depth-validation representation-macro raw IoU; "
            "break ties by pure-executable rate, then later training progress"
        ),
        "all_inventory_checkpoints_required": True,
        "inventory_logical_sha256": inventory_sha,
        "candidates": candidates,
        "selected_checkpoint_name": selected.checkpoint_name,
    }
    selection["logical_sha256"] = canonical_sha256(selection)
    return selection


def _approval_payload(
    *,
    stage: StageSpec,
    wave_name: str,
    plan: ApprovalPlan,
    evidence: EvaluationEvidence,
    source_git_sha: str,
    protocol: Mapping[str, Any],
    checkpoint_selection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        evidence.key.stage_id,
        evidence.wave,
    ) not in plan.allowed_evaluation_checkpoints:
        raise PromotionError(
            f"{evidence.key.stage_id}/{evidence.wave} cannot approve "
            f"{stage.stage_id}/{wave_name}"
        )
    if evidence.panel != plan.expected_panel:
        raise PromotionError(
            f"{stage.stage_id}/{wave_name} requires {plan.expected_panel}, "
            f"not {evidence.panel}"
        )

    mastery: dict[str, Any] | None = None
    if plan.gate == "first-unmastered-entry-receipt":
        thresholds = _mapping(
            protocol["evaluation"].get("mastery_thresholds"),
            "protocol.evaluation.mastery_thresholds",
        )
        minimum_iou = _unit(
            thresholds.get("minimum_mean_raw_absolute_scale_iou"),
            "mastery_thresholds.minimum_mean_raw_absolute_scale_iou",
        )
        minimum_pure = _unit(
            thresholds.get("minimum_pure_executable_rate"),
            "mastery_thresholds.minimum_pure_executable_rate",
        )
        selected = first_unmastered_level(
            evidence.report_payload,
            minimum_iou=minimum_iou,
            minimum_pure_executable_rate=minimum_pure,
        )
        if selected is None:
            raise PromotionError(
                "all L0–L4 levels are mastered; mixed curriculum RL must not start"
            )
        if selected != stage.current_level:
            raise PromotionError(
                f"first unmastered level is {selected}, not {stage.current_level}"
            )
        mastery = {
            "selection": "first-unmastered-l0-to-l4",
            "selected_level": selected,
            "minimum_mean_raw_absolute_scale_iou": minimum_iou,
            "minimum_pure_executable_rate": minimum_pure,
        }
    elif plan.gate == "entry-evaluation-and-promotion-receipt":
        if stage.current_level not in LEVELS:
            raise PromotionError("curriculum entry stage has no current level")
        mastery = {
            "selection": "fixed-curriculum-entry-after-reviewed-parent-evaluation",
            "entry_level": stage.current_level,
            "hard_mastery_threshold_applied": False,
        }

    payload: dict[str, Any] = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "decision": "approve",
        "approval_gate": plan.gate,
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "explicit_human_confirmation": True,
        "evaluation": {
            "stage_id": evidence.key.stage_id,
            "wave": evidence.wave,
            "checkpoint_name": evidence.checkpoint_name,
            "checkpoint": evidence.checkpoint,
            "checkpoint_inventory_sha256": (
                evidence.checkpoint_inventory_sha256
            ),
            "replicate_id": evidence.key.replicate_id,
            "panel": evidence.panel,
            "report_relative_path": evidence.report_relative_path,
            "report_payload_sha256": evidence.report_payload_sha256,
            "report_record_sha256": evidence.report_record_sha256,
            "training_wave_receipt_record_sha256": (
                evidence.training_receipt.record_sha256
            ),
        },
        "mastery": mastery,
        "checkpoint_selection": (
            dict(checkpoint_selection)
            if checkpoint_selection is not None
            else None
        ),
    }
    # The launcher uses these top-level fields to resolve dynamic parents and
    # to bind exact-parent gates.  A same-stage smoke continuation must not
    # claim its smoke receipt as the stage's external parent.
    if plan.gate in {
        "first-unmastered-entry-receipt",
        "entry-evaluation-and-promotion-receipt",
        "parent-evaluation-receipt",
    }:
        payload.update(
            {
                "parent_stage_id": evidence.key.stage_id,
                "parent_wave": evidence.wave,
                "parent_receipt_record_sha256": (
                    evidence.training_receipt.record_sha256
                ),
                "selected_parent_checkpoint": evidence.checkpoint,
                "selected_parent_checkpoint_inventory_sha256": (
                    evidence.checkpoint_inventory_sha256
                ),
            }
        )
    elif plan.gate == "clean-smoke-receipt":
        payload.update(
            {
                "prior_wave": evidence.wave,
                "prior_receipt_record_sha256": (
                    evidence.training_receipt.record_sha256
                ),
            }
        )
    return payload


def record_wave_approval(
    *,
    repo_root: Path,
    external_root: Path,
    stage_id: str,
    wave_name: str,
    replicate_id: str,
    evaluation_stage_id: str,
    evaluation_wave: str,
    evaluation_checkpoint_name: str,
    evaluation_report_record_sha256: str,
    expected_source_sha: str,
    confirmation: str,
) -> dict[str, Any]:
    """Validate reviewed evidence and atomically record one approval."""

    if confirmation != APPROVAL_CONFIRMATION_TOKEN:
        raise PromotionError("explicit human approval confirmation is missing")
    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    source_git_sha = validate_source_sha(root, expected_source_sha)
    if replicate_id not in protocol["launch"]["replicates"]:
        raise PromotionError("replicate is not declared in the protocol")
    stage = stage_spec(protocol, stage_id)
    plan = approval_plan(stage, wave_name)
    store = TrainingStore(repo_root=root, external_root=external_root)
    evidence = validate_checkpoint_report(
        repo_root=root,
        protocol=protocol,
        store=store,
        stage_id=evaluation_stage_id,
        wave=evaluation_wave,
        checkpoint_name=evaluation_checkpoint_name,
        replicate_id=replicate_id,
        panel=plan.expected_panel,
        expected_source_sha=source_git_sha,
        expected_report_record_sha256=evaluation_report_record_sha256,
    )
    checkpoint_selection: dict[str, Any] | None = None
    if (
        plan.gate == "first-unmastered-entry-receipt"
        and evidence.key.stage_id == "qwen-mixed-sft"
    ):
        checkpoint_selection = _mixed_checkpoint_selection(
            repo_root=root,
            protocol=protocol,
            store=store,
            selected=evidence,
            expected_source_sha=source_git_sha,
        )
    else:
        _terminal_checkpoint(evidence)
    payload = _approval_payload(
        stage=stage,
        wave_name=wave_name,
        plan=plan,
        evidence=evidence,
        source_git_sha=source_git_sha,
        protocol=protocol,
        checkpoint_selection=checkpoint_selection,
    )
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    with store.acquire_stage_lock(key):
        approval = store.write_wave_approval(
            key,
            wave=plan.storage_wave,
            payload=payload,
        )
    return {
        "status": "approved",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "approval_storage_wave": plan.storage_wave,
        "approval": str(approval.relative_path),
        "approval_record_sha256": approval.record_sha256,
        "evaluation_report_record_sha256": evidence.report_record_sha256,
    }
