"""Fail-closed, human-confirmed promotion gates for the training study.

This module never samples a model and never creates a Tinker client.  It turns
one already-sealed checkpoint-evaluation report into the immutable approval
record consumed by :mod:`launcher`.
"""

from __future__ import annotations

import math
import re
import subprocess
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl.common.prompt import prompt_asset_hashes
from rl.evaluation.tasks import canonical_json_sha256

from .dataset_binding import _dataset_binding
from .protocol import (
    LEVELS,
    STUDY_ID,
    StageSpec,
    file_sha256,
    load_protocol,
    parent_replicate_id,
    protocol_path,
    stage_spec,
    validate_stage_replicate,
    validate_source_sha,
)
from .store import (
    StageKey,
    TrainingRecord,
    TrainingStore,
    canonical_sha256,
)
from .source_transition import (
    SourceTransitionError,
    approved_change_scope,
    build_source_transition,
    source_transition_git_facts,
)


APPROVAL_SCHEMA_VERSION = "pixcell-training-wave-approval-v1"
SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION = "pixcell-training-wave-approval-v2"
PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION = (
    "pixcell-training-parent-receipt-transition-approval-v1"
)
ROLLOUT_HEALTH_APPROVAL_SCHEMA_VERSION = (
    "pixcell-training-rollout-health-approval-v1"
)
BASE_BASELINE_APPROVAL_SCHEMA_VERSION = (
    "pixcell-training-base-baseline-approval-v1"
)
APPROVAL_CONFIRMATION_TOKEN = "PIXCELL_APPROVE_TRAINING_V1"
MASTERED_MINIMUM_IOU = 0.80
MASTERED_MINIMUM_PURE_EXECUTABLE_RATE = 0.95

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
_INKLING_PANEL_SELECTION_SEED = (
    "pixcell-representation-training-v1-inkling-promotion-20260728"
)
_LEVEL_PROGRESS_SELECTION = "validation-realization-slot-6"
_DEPTH_FINAL_SELECTION = "validation-realization-slot-7"
_MODEL_EVALUATION_STATUSES = frozenset(
    {
        "ok",
        "syntax_error",
        "source_rejected",
        "runtime_timeout",
        "runtime_error",
        "no_gds",
        "bad_gds",
    }
)
EXPECTED_PANEL_ROWS = {
    PANEL_PROGRESS: 8,
    PANEL_DEPTH_VALIDATION: 1_092,
    PANEL_INKLING_PROMOTION: 68,
    "level-progress-l0": 93,
    "level-progress-l1": 127,
    "level-progress-l2": 98,
    "level-progress-l3": 120,
    "level-progress-l4": 108,
    PANEL_DEPTH_FINAL_SELECTION: 546,
}

_REPORT_SCHEMA = "pixcell-training-checkpoint-evaluation-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TINKER_PATH = re.compile(r"^tinker://[^\s]+$")
_IMMUTABLE_IMAGE = re.compile(r"^(?:sha256:[0-9a-f]{64}|[^\s@]+@sha256:[0-9a-f]{64})$")


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
    evaluation_manifest_payload_sha256: str
    evaluation_manifest_record_sha256: str
    evaluation_manifest_relative_path: str
    training_manifest: TrainingRecord
    training_receipt: TrainingRecord


@dataclass(frozen=True)
class ApprovalPlan:
    gate: str
    storage_wave: str
    expected_panel: str
    allowed_evaluation_checkpoints: tuple[tuple[str, str], ...]
    entry_baseline_panel: str | None = None


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


def _finite_json(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PromotionError(f"{path} contains a non-finite number")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _finite_json(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _finite_json(item, f"{path}[{index}]")
        return
    raise PromotionError(f"{path} contains unsupported metric data")


def _parent_receipt_transition_evidence(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    replicate_id: str,
) -> tuple[TrainingRecord, TrainingRecord, TrainingRecord, dict[str, Any], dict[str, Any]]:
    """Revalidate the completed historical L0-SFT parent without an evaluation."""

    parent_key = StageKey(STUDY_ID, "qwen-l0-sft", replicate_id)
    manifest = store.load_manifest(parent_key)
    receipt = store.load_wave_receipt(parent_key, wave="complete")
    if manifest is None or receipt is None:
        raise PromotionError("the exact qwen-l0-sft/complete parent receipt is missing")

    parent_source = str(manifest.payload.get("source_git_sha", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", parent_source):
        raise PromotionError("parent manifest has an invalid source commit")
    if (
        receipt.payload.get("stage_id") != "qwen-l0-sft"
        or receipt.payload.get("wave") != "complete"
        or receipt.payload.get("run_manifest_record_sha256") != manifest.record_sha256
    ):
        raise PromotionError("parent receipt and manifest identities differ")

    parent_stage = _mapping(manifest.payload.get("stage"), "parent_manifest.stage")
    current_parent = stage_spec(dict(protocol), "qwen-l0-sft")
    expected_stage = {
        "stage_id": current_parent.stage_id,
        "kind": current_parent.kind,
        "model_key": current_parent.model_key,
        "recipe_key": current_parent.recipe_key,
        "hypotheses": list(current_parent.hypotheses),
        "parent_policy": current_parent.parent,
        "levels": list(current_parent.levels),
        "current_level": current_parent.current_level,
        "replay_levels": list(current_parent.replay_levels),
        "waves": current_parent.waves,
    }
    local_dataset = _dataset_binding(repo_root / "dataset", protocol)
    stable_equivalence = {
        "contract_version": protocol["contract_version"],
        "prompt_assets": prompt_asset_hashes(),
        "dataset": local_dataset,
        "model": dict(protocol["models"]["qwen"]),
        "recipe": dict(protocol["recipes"]["qwen_sft"]),
        "stage": expected_stage,
    }
    observed_equivalence = {
        "contract_version": manifest.payload.get("contract_version"),
        "prompt_assets": manifest.payload.get("prompt_assets"),
        "dataset": manifest.payload.get("dataset"),
        "model": manifest.payload.get("model"),
        "recipe": manifest.payload.get("recipe"),
        "stage": dict(parent_stage),
    }
    if observed_equivalence != stable_equivalence:
        raise PromotionError(
            "historical L0-SFT parent differs from the current stable "
            "contract, prompt, dataset, model, recipe, or stage"
        )

    inventory = _mapping(
        receipt.payload.get("checkpoint_inventory"),
        "parent_receipt.checkpoint_inventory",
    )
    entries = inventory.get("entries")
    logical_sha256 = _sha(
        inventory.get("logical_sha256"),
        "parent_receipt.checkpoint_inventory.logical_sha256",
    )
    if (
        not isinstance(entries, list)
        or inventory.get("count") != len(entries)
        or canonical_sha256(entries) != logical_sha256
    ):
        raise PromotionError("parent checkpoint inventory digest differs")
    terminals = [
        item
        for item in entries
        if isinstance(item, Mapping)
        and item.get("role") == "terminal"
        and item.get("final") is True
    ]
    if len(terminals) != 1:
        raise PromotionError("parent checkpoint inventory has no unique terminal")
    checkpoint = dict(terminals[0])
    selected = _mapping(receipt.payload.get("checkpoint"), "parent_receipt.checkpoint")
    selected_fields = ("name", "batch", "epoch", "final", "state_path", "sampler_path")
    if (
        any(selected.get(field) != checkpoint.get(field) for field in selected_fields)
        or checkpoint.get("name") != "final"
        or checkpoint.get("epoch") != 1
        or not _TINKER_PATH.fullmatch(str(checkpoint.get("state_path", "")))
        or not _TINKER_PATH.fullmatch(str(checkpoint.get("sampler_path", "")))
    ):
        raise PromotionError("parent selected checkpoint is not the completed SFT terminal")

    invocation_id = str(receipt.payload.get("invocation_id", ""))
    try:
        invocation = store.load_invocation(parent_key, invocation_id=invocation_id)
    except ValueError as exc:
        raise PromotionError("parent receipt has an invalid invocation ID") from exc
    if (
        invocation is None
        or receipt.payload.get("invocation_record_sha256") != invocation.record_sha256
        or invocation.payload.get("run_manifest_record_sha256") != manifest.record_sha256
        or invocation.payload.get("source_git_sha") != parent_source
    ):
        raise PromotionError("parent invocation is missing or differs")

    artifacts = _mapping(
        receipt.payload.get("local_artifact_sha256"),
        "parent_receipt.local_artifact_sha256",
    )
    if not {"checkpoints.jsonl", "metrics.jsonl"}.issubset(artifacts):
        raise PromotionError("parent receipt lacks its local checkpoint evidence")
    for name, expected_sha in artifacts.items():
        _sha(expected_sha, f"parent_receipt.local_artifact_sha256.{name}")
        path = store.tinker_log_path(parent_key) / str(name)
        if not path.is_file() or file_sha256(path) != expected_sha:
            raise PromotionError(f"parent local artifact {name} differs from its receipt")

    evidence = {
        "parent_run_manifest": {
            "relative_path": str(manifest.relative_path),
            "payload_sha256": manifest.payload_sha256,
            "record_sha256": manifest.record_sha256,
        },
        "parent_wave_receipt": {
            "relative_path": str(receipt.relative_path),
            "payload_sha256": receipt.payload_sha256,
            "record_sha256": receipt.record_sha256,
        },
        "parent_invocation": {
            "relative_path": str(invocation.relative_path),
            "payload_sha256": invocation.payload_sha256,
            "record_sha256": invocation.record_sha256,
        },
        "local_artifact_sha256": dict(artifacts),
        "checkpoint_inventory": dict(inventory),
        "selected_checkpoint": checkpoint,
    }
    return manifest, receipt, invocation, checkpoint, {
        "stable_equivalence": stable_equivalence,
        "evidence": evidence,
    }


def _parent_receipt_transition_payload(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    stage: StageSpec,
    wave_name: str,
    replicate_id: str,
    consumer_source_git_sha: str,
    approved_change_paths: Sequence[str] | None,
) -> dict[str, Any]:
    if (
        stage.stage_id != "qwen-l0-rl-l1"
        or stage.parent != "qwen-l0-sft:complete"
        or wave_name != "smoke"
        or str(stage.wave(wave_name)["approval"])
        != "parent-receipt-and-source-transition"
    ):
        raise PromotionError("parent-receipt transition is not the L0-SFT→L1-RL entry")
    producer_replicate_id = parent_replicate_id(
        protocol,
        stage_id=stage.stage_id,
        replicate_id=replicate_id,
    )
    manifest, receipt, invocation, checkpoint, documents = (
        _parent_receipt_transition_evidence(
            repo_root=repo_root,
            protocol=protocol,
            store=store,
            replicate_id=producer_replicate_id,
        )
    )
    producer_source_git_sha = str(manifest.payload["source_git_sha"])
    if producer_source_git_sha == consumer_source_git_sha:
        raise PromotionError(
            "historical-parent transition requires different producer and consumer commits"
        )
    scope = {
        "study_id": STUDY_ID,
        "child": {
            "stage_id": stage.stage_id,
            "wave": wave_name,
            "replicate_id": replicate_id,
            "approval_gate": "parent-receipt-and-source-transition",
        },
        "producer_training": {
            "stage_id": "qwen-l0-sft",
            "wave": "complete",
            "replicate_id": producer_replicate_id,
        },
    }
    equivalence = {
        "producer_protocol": {
            "logical_sha256": manifest.payload.get("protocol_logical_sha256"),
            "file_sha256": manifest.payload.get("protocol_file_sha256"),
        },
        "consumer_protocol": {
            "logical_sha256": protocol["logical_sha256"],
            "file_sha256": file_sha256(protocol_path(repo_root)),
        },
        **documents["stable_equivalence"],
    }
    try:
        transition = build_source_transition(
            repo_root=repo_root,
            producer_source_git_sha=producer_source_git_sha,
            consumer_source_git_sha=consumer_source_git_sha,
            scope=scope,
            approved_change_paths=approved_change_paths,
            equivalence=equivalence,
            evidence=documents["evidence"],
        )
    except SourceTransitionError as exc:
        raise PromotionError(f"parent source transition is invalid: {exc}") from exc
    inventory = _mapping(
        receipt.payload.get("checkpoint_inventory"),
        "parent_receipt.checkpoint_inventory",
    )
    return {
        "schema_version": PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION,
        "decision": "approve",
        "approval_gate": "parent-receipt-and-source-transition",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "source_git_sha": consumer_source_git_sha,
        "evidence_source_git_sha": producer_source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "explicit_human_confirmation": True,
        "parent_stage_id": "qwen-l0-sft",
        "parent_wave": "complete",
        "parent_replicate_id": producer_replicate_id,
        "parent_manifest_record_sha256": manifest.record_sha256,
        "parent_receipt_record_sha256": receipt.record_sha256,
        "parent_invocation_record_sha256": invocation.record_sha256,
        "selected_parent_checkpoint": checkpoint,
        "selected_parent_checkpoint_inventory_sha256": inventory["logical_sha256"],
        "source_transition": transition,
    }


def validate_parent_receipt_transition_approval(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    stage: StageSpec,
    wave_name: str,
    replicate_id: str,
    consumer_source_git_sha: str,
    approval: TrainingRecord,
) -> None:
    """Recompute the receipt-only historical-parent bridge at launch time."""

    if (
        approval.payload.get("schema_version")
        != PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
    ):
        raise PromotionError("parent-receipt transition approval has a foreign schema")
    if approval.payload.get("source_git_sha") != consumer_source_git_sha:
        raise PromotionError("parent-receipt transition names another consumer")
    try:
        validate_source_sha(repo_root, consumer_source_git_sha)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PromotionError(
            f"parent-receipt transition consumer is not the clean HEAD: {exc}"
        ) from exc
    approved_paths = _approved_change_paths_from_transition(
        approval.payload.get("source_transition")
    )
    expected = _parent_receipt_transition_payload(
        repo_root=repo_root,
        protocol=protocol,
        store=store,
        stage=stage,
        wave_name=wave_name,
        replicate_id=replicate_id,
        consumer_source_git_sha=consumer_source_git_sha,
        approved_change_paths=approved_paths,
    )
    if approval.payload != expected:
        raise PromotionError(
            "parent-receipt transition approval differs from recomputed evidence"
        )


def record_parent_receipt_transition_approval(
    *,
    repo_root: Path,
    external_root: Path,
    stage_id: str,
    wave_name: str,
    replicate_id: str,
    expected_source_sha: str,
    approved_change_paths: Sequence[str] | None,
    confirmation: str,
) -> dict[str, Any]:
    """Record the one explicit bridge from historical L0 SFT to current L1 RL."""

    if confirmation != APPROVAL_CONFIRMATION_TOKEN:
        raise PromotionError("explicit human approval confirmation is missing")
    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    source_git_sha = validate_source_sha(root, expected_source_sha)
    stage = stage_spec(protocol, stage_id)
    try:
        validate_stage_replicate(
            protocol,
            stage_id=stage.stage_id,
            replicate_id=replicate_id,
        )
    except ValueError as exc:
        raise PromotionError(str(exc)) from exc
    store = TrainingStore(repo_root=root, external_root=external_root)
    payload = _parent_receipt_transition_payload(
        repo_root=root,
        protocol=protocol,
        store=store,
        stage=stage,
        wave_name=wave_name,
        replicate_id=replicate_id,
        consumer_source_git_sha=source_git_sha,
        approved_change_paths=approved_change_paths,
    )
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    with store.acquire_stage_lock(key):
        validate_source_sha(root, source_git_sha)
        rebuilt = _parent_receipt_transition_payload(
            repo_root=root,
            protocol=protocol,
            store=store,
            stage=stage,
            wave_name=wave_name,
            replicate_id=replicate_id,
            consumer_source_git_sha=source_git_sha,
            approved_change_paths=approved_change_paths,
        )
        if rebuilt != payload:
            raise PromotionError("parent-receipt transition changed before recording")
        approval = store.write_wave_approval(
            key,
            wave=wave_name,
            payload=payload,
        )
    return {
        "status": "approved",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "approval": str(approval.relative_path),
        "approval_record_sha256": approval.record_sha256,
        "parent_receipt_record_sha256": payload["parent_receipt_record_sha256"],
        "source_transition_logical_sha256": payload["source_transition"][
            "logical_sha256"
        ],
    }


def record_rollout_health_approval(
    *,
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    wave_name: str,
    prior_wave: str,
    prior_receipt: TrainingRecord,
    source_git_sha: str,
    protocol: Mapping[str, Any],
) -> TrainingRecord:
    """Derive the smoke→step-5 decision from exactly one sealed G4 receipt."""

    if (
        stage.kind != "rl"
        or stage.model_key != "qwen"
        or wave_name != "step-5"
        or prior_wave != "smoke"
        or str(stage.wave(wave_name)["approval"]) != "rollout-health-receipt"
        or int(stage.wave(prior_wave)["max_steps"]) != 1
    ):
        raise PromotionError("rollout-health gate is not the Qwen smoke→step-5 transition")
    recipe = _mapping(protocol["recipes"].get(stage.recipe_key), "recipe")
    group_size = _integer(recipe.get("group_size"), "recipe.group_size", minimum=1)
    groups_per_batch = _integer(
        recipe.get("groups_per_batch"),
        "recipe.groups_per_batch",
        minimum=1,
    )
    if group_size != 4 or groups_per_batch != 8:
        raise PromotionError("rollout-health gate requires the sealed 8×G4 recipe")
    expected_candidates = group_size * groups_per_batch

    if (
        prior_receipt.payload.get("stage_id") != stage.stage_id
        or prior_receipt.payload.get("wave") != prior_wave
        or prior_receipt.payload.get("max_steps") != 1
    ):
        raise PromotionError("rollout-health receipt identity differs")
    invocation_id = str(prior_receipt.payload.get("invocation_id", ""))
    invocation = store.load_invocation(key, invocation_id=invocation_id)
    if (
        invocation is None
        or prior_receipt.payload.get("invocation_record_sha256")
        != invocation.record_sha256
    ):
        raise PromotionError("rollout-health receipt invocation is missing or differs")
    manifest = store.load_manifest(key)
    if (
        manifest is None
        or prior_receipt.payload.get("run_manifest_record_sha256")
        != manifest.record_sha256
        or manifest.payload.get("protocol_logical_sha256")
        != protocol["logical_sha256"]
    ):
        raise PromotionError("rollout-health receipt manifest differs")

    recorded_inventory = _mapping(
        prior_receipt.payload.get("candidate_inventory"),
        "receipt.candidate_inventory",
    )
    recorded_samples = _mapping(
        prior_receipt.payload.get("sample_inventory"),
        "receipt.sample_inventory",
    )
    for name, inventory in (
        ("candidate", recorded_inventory),
        ("sample", recorded_samples),
    ):
        if (
            _integer(inventory.get("count"), f"{name}_inventory.count")
            != expected_candidates
            or _integer(
                inventory.get("expected_count"),
                f"{name}_inventory.expected_count",
            )
            != expected_candidates
        ):
            raise PromotionError(
                f"rollout-health {name} inventory does not contain exactly "
                f"{expected_candidates} records"
            )
        _sha(inventory.get("logical_sha256"), f"{name}_inventory.logical_sha256")

    candidate_root = store.candidate_root(key) / invocation_id
    candidate_files = (
        sorted(candidate_root.rglob("evaluation.json"))
        if candidate_root.is_dir()
        else []
    )
    sample_files = (
        sorted(candidate_root.rglob("sample.json"))
        if candidate_root.is_dir()
        else []
    )
    observed_inventory = [
        {
            "path": str(path.relative_to(store.stage_path(key))),
            "sha256": file_sha256(path),
        }
        for path in candidate_files
    ]
    if (
        len(candidate_files) != expected_candidates
        or canonical_sha256(observed_inventory)
        != recorded_inventory["logical_sha256"]
    ):
        raise PromotionError(
            "rollout-health candidate files differ from the sealed receipt"
        )
    observed_sample_inventory = [
        {
            "path": str(path.relative_to(store.stage_path(key))),
            "sha256": file_sha256(path),
        }
        for path in sample_files
    ]
    if (
        len(sample_files) != expected_candidates
        or canonical_sha256(observed_sample_inventory)
        != recorded_samples["logical_sha256"]
    ):
        raise PromotionError(
            "rollout-health sample files differ from the sealed receipt"
        )

    rewards_by_group: dict[tuple[int, str], dict[int, float]] = defaultdict(dict)
    executable = 0
    rewards: list[float] = []
    record_bindings: list[dict[str, Any]] = []
    sample_record_bindings: list[dict[str, Any]] = []
    from rl.common.evaluator import EvaluationStatus

    allowed_statuses = {item.value for item in EvaluationStatus}
    for path in candidate_files:
        relative = path.relative_to(candidate_root)
        parts = relative.parts
        if (
            len(parts) != 4
            or not re.fullmatch(r"step-[0-9]{6}", parts[0])
            or not re.fullmatch(r"attempt-[0-9]{2}", parts[2])
            or parts[3] != "evaluation.json"
        ):
            raise PromotionError("rollout-health candidate path is not canonical")
        step = int(parts[0].removeprefix("step-"))
        task_id = parts[1]
        attempt = int(parts[2].removeprefix("attempt-"))
        if step != 0:
            raise PromotionError("rollout-health smoke contains a nonzero step")
        record = store.load_candidate(
            key,
            invocation_id=invocation_id,
            step=step,
            task_id=task_id,
            attempt=attempt,
        )
        if record is None:
            raise PromotionError("rollout-health candidate record disappeared")
        payload = _mapping(record.payload, "candidate.payload")
        sample_binding = _mapping(payload.get("sample_record"), "candidate.sample_record")
        sample = store.load_candidate_sample(
            key,
            invocation_id=invocation_id,
            step=step,
            task_id=task_id,
            attempt=attempt,
        )
        if (
            sample is None
            or sample_binding.get("relative_path") != str(sample.relative_path)
            or sample_binding.get("payload_sha256") != sample.payload_sha256
            or sample_binding.get("record_sha256") != sample.record_sha256
        ):
            raise PromotionError(
                "rollout-health candidate is not bound to its paid sample"
            )
        evaluation = _mapping(payload.get("evaluation"), "candidate.evaluation")
        _finite_json(evaluation, "candidate.evaluation")
        attribution = str(evaluation.get("attribution", ""))
        if attribution != "model":
            raise PromotionError(
                "rollout-health contains an evaluator or reference fault"
            )
        reward = _unit(evaluation.get("reward"), "candidate.evaluation.reward")
        status = str(evaluation.get("status", ""))
        if status not in allowed_statuses:
            raise PromotionError("rollout-health contains an unknown evaluator status")
        if status not in _MODEL_EVALUATION_STATUSES:
            raise PromotionError(
                "rollout-health contains an evaluator or reference status "
                "mislabeled as model-attributed"
            )
        iou = evaluation.get("iou")
        dice = evaluation.get("dice")
        if status == "ok":
            if iou is None or dice is None:
                raise PromotionError(
                    "rollout-health successful evaluation lacks IoU or Dice"
                )
            measured_iou = _unit(iou, "candidate.evaluation.iou")
            _unit(dice, "candidate.evaluation.dice")
            if not math.isclose(
                reward,
                measured_iou,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise PromotionError(
                    "rollout-health reward differs from raw IoU"
                )
            executable += 1
        else:
            if reward != 0.0:
                raise PromotionError(
                    "rollout-health model failure has nonzero reward"
                )
            if iou is not None or dice is not None:
                raise PromotionError(
                    "rollout-health model failure contains geometry metrics"
                )
        rewards.append(reward)
        group = (step, task_id)
        if attempt in rewards_by_group[group]:
            raise PromotionError("rollout-health repeats a group attempt")
        rewards_by_group[group][attempt] = reward
        record_bindings.append(
            {
                "relative_path": str(record.relative_path),
                "payload_sha256": record.payload_sha256,
                "record_sha256": record.record_sha256,
            }
        )
        sample_record_bindings.append(
            {
                "relative_path": str(sample.relative_path),
                "payload_sha256": sample.payload_sha256,
                "record_sha256": sample.record_sha256,
            }
        )

    if len(rewards_by_group) != groups_per_batch or any(
        set(attempts) != set(range(1, group_size + 1))
        for attempts in rewards_by_group.values()
    ):
        raise PromotionError("rollout-health candidates are not exactly eight G4 groups")
    nonconstant = sum(
        max(attempts.values()) - min(attempts.values()) > 1e-12
        for attempts in rewards_by_group.values()
    )
    if executable < 1:
        raise PromotionError("rollout-health smoke has no pure executable candidate")
    if nonconstant < 1:
        raise PromotionError("rollout-health smoke has no nonconstant G4 group")

    payload = {
        "schema_version": ROLLOUT_HEALTH_APPROVAL_SCHEMA_VERSION,
        "decision": "approve",
        "approval_gate": "rollout-health-receipt",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "source_git_sha": source_git_sha,
        "evidence_source_git_sha": manifest.payload.get("source_git_sha"),
        "protocol_logical_sha256": protocol["logical_sha256"],
        "prior_wave": prior_wave,
        "prior_receipt_record_sha256": prior_receipt.record_sha256,
        "invocation_id": invocation_id,
        "candidate_inventory_logical_sha256": recorded_inventory[
            "logical_sha256"
        ],
        "sample_inventory_logical_sha256": recorded_samples[
            "logical_sha256"
        ],
        "candidate_record_bindings_sha256": canonical_sha256(record_bindings),
        "sample_record_bindings_sha256": canonical_sha256(
            sample_record_bindings
        ),
        "metrics": {
            "candidates": expected_candidates,
            "groups": groups_per_batch,
            "group_size": group_size,
            "mean_raw_absolute_scale_iou_including_zeros": (
                sum(rewards) / len(rewards)
            ),
            "pure_executable": executable,
            "pure_executable_rate": executable / expected_candidates,
            "nonconstant_reward_groups": nonconstant,
            "nonconstant_reward_group_fraction": (
                nonconstant / groups_per_batch
            ),
            "evaluator_or_reference_faults": 0,
        },
    }
    return store.write_rollout_health_approval(
        key,
        wave=wave_name,
        payload=payload,
    )


def record_base_baseline_approval(
    *,
    repo_root: Path,
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    wave_name: str,
    source_git_sha: str,
    protocol: Mapping[str, Any],
) -> TrainingRecord:
    """Validate and bind the pre-update base-Qwen L0 held-out report."""

    if (
        stage.stage_id != "qwen-base-rl-l0"
        or stage.parent != "base:qwen"
        or stage.current_level != "L0"
        or wave_name != "smoke"
        or str(stage.wave(wave_name)["approval"])
        != "base-level-held-out-baseline-receipt"
    ):
        raise PromotionError("base baseline gate is not qwen-base-rl-l0/smoke")

    from .evaluation import (
        CheckpointEvaluationError,
        CheckpointEvaluationStore,
        _base_model_binding,
        _sampler_provenance,
        validate_checkpoint_report as validate_native_report,
    )

    panel = LEVEL_PROGRESS_PANELS["L0"]
    binding = _base_model_binding(
        protocol=dict(protocol),
        stage_id=stage.stage_id,
        replicate_id=key.replicate_id,
        source_git_sha=source_git_sha,
    )
    report_store = CheckpointEvaluationStore(
        stage_path=store.stage_path(key),
        wave="base",
        checkpoint_name="base",
        panel=panel,
    )
    manifest = report_store.load_manifest()
    report = report_store.load_report()
    if manifest is None or report is None:
        raise PromotionError(
            "qwen-base-rl-l0/smoke requires the completed base L0 panel"
        )
    expected_tasks = _expected_panel_tasks(
        repo_root=repo_root,
        protocol=protocol,
        panel=panel,
    )
    try:
        validate_native_report(
            report,
            manifest_record_sha256=str(manifest["record_sha256"]),
            binding=binding,
            panel=panel,
            expected_task_ids=[task.task_id for task in expected_tasks],
        )
    except CheckpointEvaluationError as exc:
        raise PromotionError(f"base L0 report failed its native validator: {exc}") from exc

    report_payload = _mapping(report.get("payload"), "base_report.payload")
    provenance = _mapping(report_payload.get("provenance"), "base_report.provenance")
    manifest_payload = _mapping(manifest.get("payload"), "base_manifest.payload")
    expected_identity = {
        "study_id": STUDY_ID,
        "stage_id": stage.stage_id,
        "wave": "base",
        "checkpoint_name": "base",
        "replicate_id": key.replicate_id,
        "panel": panel,
    }
    for document_name, document in (
        ("report", report_payload),
        ("manifest", manifest_payload),
    ):
        for field, expected in expected_identity.items():
            if document.get(field) != expected:
                raise PromotionError(
                    f"base {document_name} {field} differs from its request"
                )
    expected_protocol = {
        "logical_sha256": protocol["logical_sha256"],
        "file_sha256": file_sha256(protocol_path(repo_root)),
        "contract_version": protocol["contract_version"],
    }
    if (
        provenance.get("source_git_sha") != source_git_sha
        or manifest_payload.get("source_git_sha") != source_git_sha
        or dict(_mapping(provenance.get("protocol"), "base_report.protocol"))
        != expected_protocol
        or any(
            manifest_payload.get(field) != expected
            for field, expected in {
                "protocol_logical_sha256": expected_protocol["logical_sha256"],
                "protocol_file_sha256": expected_protocol["file_sha256"],
                "contract_version": expected_protocol["contract_version"],
            }.items()
        )
    ):
        raise PromotionError("base L0 report source or protocol differs")
    panel_document = _panel_manifest(expected_tasks, panel=panel)
    observed_panel = _mapping(
        provenance.get("task_panel"),
        "base_report.task_panel",
    )
    if (
        dict(observed_panel) != panel_document
        or manifest_payload.get("task_panel") != panel_document
    ):
        raise PromotionError("base L0 report task panel differs")

    local_dataset = _dataset_binding(repo_root / "dataset", protocol)
    if manifest_payload.get("dataset") != local_dataset:
        raise PromotionError("base L0 manifest dataset differs")
    expected_report_dataset = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "split": "depth/validation/L0/slot-6",
        "logical_release_sha256": local_dataset["logical_release_sha256"],
        "freeze_file_sha256": local_dataset["freeze_file_sha256"],
        "parquet_shards": local_dataset["parquet_shards"],
    }
    if provenance.get("dataset") != expected_report_dataset:
        raise PromotionError("base L0 report dataset projection differs")

    model = dict(protocol["models"]["qwen"])
    expected_sampler = {
        "model": model["model"],
        "renderer": model["renderer"],
        "effort": model.get("effort"),
        **_sampler_provenance(binding),
    }
    if (
        manifest_payload.get("model") != model
        or manifest_payload.get("sampler") != _sampler_provenance(binding)
        or provenance.get("sampler") != expected_sampler
    ):
        raise PromotionError("base L0 report sampler differs")
    expected_report_sampling = {
        "attempts_per_task": 1,
        "max_output_tokens": 60_000,
        "temperature": 1.0,
        "top_p": 1.0,
        "max_image_long_edge": 1_920,
        "seed_algorithm": "sha256-bound deterministic 31-bit seed",
    }
    expected_manifest_sampling = {
        "attempts_per_task": 1,
        "max_output_tokens": 60_000,
        "temperature": 1.0,
        "top_p": 1.0,
        "max_image_long_edge": 1_920,
        "sample_concurrency": 8,
        "evaluation_batch_size": 32,
        "evaluator_workers": 8,
    }
    if (
        provenance.get("sampling") != expected_report_sampling
        or manifest_payload.get("sampling") != expected_manifest_sampling
    ):
        raise PromotionError("base L0 report sampling policy differs")
    sandbox = _mapping(provenance.get("sandbox"), "base_report.sandbox")
    if (
        manifest_payload.get("prompt_assets") != prompt_asset_hashes()
        or provenance.get("prompt_assets") != prompt_asset_hashes()
        or dict(sandbox) != manifest_payload.get("sandbox")
        or provenance.get("evaluation_manifest_record_sha256")
        != manifest.get("record_sha256")
    ):
        raise PromotionError("base L0 report runtime provenance differs")
    if (
        not _IMMUTABLE_IMAGE.fullmatch(str(sandbox.get("image_ref", "")))
        or not re.fullmatch(
            r"sha256:[0-9a-f]{64}",
            str(sandbox.get("image_id", "")),
        )
    ):
        raise PromotionError("base L0 report sandbox is not immutable")
    _validate_report_metrics(report_payload, expected_tasks=expected_tasks)

    payload = {
        "schema_version": BASE_BASELINE_APPROVAL_SCHEMA_VERSION,
        "decision": "approve",
        "approval_gate": "base-level-held-out-baseline-receipt",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "evaluation": {
            "wave": "base",
            "checkpoint_name": "base",
            "panel": panel,
            "base_model_binding_sha256": binding.binding_sha256,
            "manifest_relative_path": str(
                report_store.root.relative_to(store.external_root)
                / "manifest.json"
            ),
            "manifest_payload_sha256": manifest["payload_sha256"],
            "manifest_record_sha256": manifest["record_sha256"],
            "report_relative_path": str(
                report_store.root.relative_to(store.external_root)
                / "report.json"
            ),
            "report_payload_sha256": report["payload_sha256"],
            "report_record_sha256": report["record_sha256"],
        },
    }
    return store.write_base_baseline_approval(
        key,
        wave=wave_name,
        payload=payload,
    )


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
        *tuple((f"qwen-mixed-rl-l{prior}", "complete") for prior in range(index)),
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

    if gate == "rollout-health-receipt":
        raise PromotionError(
            "rollout-health-receipt is derived automatically from the prior "
            "wave receipt; it does not accept a human checkpoint approval"
        )

    if gate == "current-level-held-out-promotion-receipt":
        prior = _required_prior_wave(stage, wave_name)
        if prior is None or stage.current_level not in LEVEL_PROGRESS_PANELS:
            raise PromotionError("current-level gate has no prior wave or level")
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=LEVEL_PROGRESS_PANELS[stage.current_level],
            allowed_evaluation_checkpoints=((stage.stage_id, prior),),
        )

    if gate == "prior-level-held-out-promotion-receipt":
        parent_stage, parent_wave = stage.parent.split(":", 1)
        if (
            parent_stage == "base"
            or parent_wave != "complete"
            or stage.current_level not in LEVELS[1:]
        ):
            raise PromotionError("prior-level gate has no exact curriculum parent")
        prior_level = LEVELS[LEVELS.index(stage.current_level) - 1]
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=LEVEL_PROGRESS_PANELS[prior_level],
            allowed_evaluation_checkpoints=((parent_stage, parent_wave),),
        )

    if gate == "prior-and-current-level-held-out-transition-receipt":
        parent_stage, parent_wave = stage.parent.split(":", 1)
        if (
            stage.stage_id not in {
                "qwen-base-rl-l1",
                "qwen-base-rl-l2",
                "qwen-base-rl-l3",
                "qwen-base-rl-l4",
            }
            or parent_wave != "complete"
            or stage.current_level not in LEVELS[1:]
        ):
            raise PromotionError(
                "dual level-transition gate has no exact pure-RL parent"
            )
        prior_level = LEVELS[LEVELS.index(stage.current_level) - 1]
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=LEVEL_PROGRESS_PANELS[prior_level],
            allowed_evaluation_checkpoints=((parent_stage, parent_wave),),
            entry_baseline_panel=LEVEL_PROGRESS_PANELS[stage.current_level],
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
        if stage.current_level not in LEVELS or not stage.stage_id.startswith("qwen-mixed-rl-"):
            raise PromotionError("first-unmastered gate is not a mixed-Qwen stage")
        return ApprovalPlan(
            gate=gate,
            storage_wave=wave_name,
            expected_panel=PANEL_DEPTH_VALIDATION,
            allowed_evaluation_checkpoints=_mixed_allowed_checkpoints(stage.current_level),
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
        "schema_version": "pixcell-training-evaluation-task-panel-v1",
        "panel": panel,
        "selection_seed": (
            _INKLING_PANEL_SELECTION_SEED
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
    for index, record in enumerate(records):
        observed = record.get("pure_executable")
        if not isinstance(observed, bool):
            raise PromotionError("record.pure_executable must be boolean")
        status = str(record.get("status", ""))
        if status not in _MODEL_EVALUATION_STATUSES:
            raise PromotionError("record contains a non-model evaluation status")
        if observed != (status == "ok"):
            raise PromotionError("record status and pure-executable flag differ")
        if status != "ok" and float(ious[index]) != 0.0:
            raise PromotionError("failed model output has nonzero IoU")
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
            raise PromotionError(f"{path}.{field}={actual}; expected {expected[field]}")
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
        raise PromotionError(f"report.records must contain all {len(expected_tasks)} tasks")
    records: list[Mapping[str, Any]] = []
    for index, (raw, task) in enumerate(zip(raw_records, expected_tasks, strict=True)):
        path = f"records[{index}]"
        record = _mapping(raw, path)
        expected_identity = {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
        }
        for field, expected in expected_identity.items():
            if record.get(field) != expected:
                raise PromotionError(f"{path}.{field}={record.get(field)!r}; expected {expected!r}")
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
    expected_levels = {key: _aggregate(values) for key, values in sorted(by_level.items())}
    if set(observed_levels) != set(expected_levels):
        raise PromotionError("report.levels differs from the panel")
    for key, expected in expected_levels.items():
        _validate_aggregate(observed_levels[key], expected, path=f"levels.{key}")

    observed_representations = _mapping(
        report.get("representations"),
        "representations",
    )
    expected_representations = {
        key: _aggregate(values) for key, values in sorted(by_representation.items())
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
        value["mean_raw_absolute_scale_iou"] for value in expected_representations.values()
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
            f"{panel} local task set has {len(expected_tasks)} rows, expected {expected_rows}"
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
    try:
        expected_local_dataset = _dataset_binding(repo_root / "dataset", protocol)
    except Exception as exc:
        raise PromotionError("local evaluation dataset could not be verified") from exc
    if dict(manifest_dataset) != expected_local_dataset:
        raise PromotionError("evaluation-manifest dataset differs from the frozen release")

    expected_report_dataset = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "split": {
            PANEL_PROGRESS: "fixed-f1-f8",
            PANEL_DEPTH_VALIDATION: "depth/validation",
            PANEL_INKLING_PROMOTION: "depth/validation+fixed-f1-f8",
            PANEL_DEPTH_FINAL_SELECTION: "depth/validation/slot-7",
            **{
                panel_id: f"depth/validation/{level}/slot-6"
                for level, panel_id in LEVEL_PROGRESS_PANELS.items()
            },
        }[panel],
        "logical_release_sha256": expected_local_dataset[
            "logical_release_sha256"
        ],
        "freeze_file_sha256": expected_local_dataset["freeze_file_sha256"],
        "parquet_shards": expected_local_dataset["parquet_shards"],
    }
    if dict(dataset) != expected_report_dataset:
        raise PromotionError(
            "report dataset projection differs from the evaluation manifest"
        )

    if (
        training_manifest.payload.get("source_git_sha") != expected_source_sha
        or training_manifest.payload.get("protocol_logical_sha256") != protocol["logical_sha256"]
    ):
        raise PromotionError("training manifest provenance differs")
    manifest_training_dataset = _mapping(
        training_manifest.payload.get("dataset"),
        "training_manifest.dataset",
    )
    if dict(manifest_training_dataset) != expected_local_dataset:
        raise PromotionError("training manifest dataset differs from the frozen release")

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
    if sampler.get("training_wave_receipt_relative_path") != str(training_receipt.relative_path):
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
    if provenance.get("evaluation_manifest_record_sha256") != evaluation_manifest.get(
        "record_sha256"
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
        raise PromotionError(f"{stage_id}/{wave}/{replicate_id} has no training receipt")

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
        raise PromotionError(f"{stage_id}/{wave}/{panel} has no complete evaluation report")
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
        evaluation_manifest_payload_sha256=_sha(
            evaluation_manifest.get("payload_sha256"),
            "evaluation_manifest.payload_sha256",
        ),
        evaluation_manifest_record_sha256=_sha(
            evaluation_manifest.get("record_sha256"),
            "evaluation_manifest.record_sha256",
        ),
        evaluation_manifest_relative_path=str(
            (
                TrainingStore.stage_relative_path(key)
                / "evaluations"
                / wave
                / checkpoint_name
                / panel
                / "manifest.json"
            )
        ),
        training_manifest=training_manifest,
        training_receipt=training_receipt,
    )


def first_unmastered_level(
    report: Mapping[str, Any],
    *,
    minimum_iou: float = MASTERED_MINIMUM_IOU,
    minimum_pure_executable_rate: float = (MASTERED_MINIMUM_PURE_EXECUTABLE_RATE),
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
    selected_alias = {field: evidence.checkpoint.get(field) for field in fields}
    if selected_alias != dict(terminal):
        raise PromotionError(
            f"{evidence.key.stage_id}/{evidence.wave} must use its terminal checkpoint"
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
            raise PromotionError(f"checkpoint {checkpoint_name!r} report and inventory differ")
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


def _source_transition_document(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    stage: StageSpec,
    wave_name: str,
    plan: ApprovalPlan,
    evidence: EvaluationEvidence,
    producer_source_git_sha: str,
    consumer_source_git_sha: str,
    approved_change_paths: Sequence[str] | None,
) -> dict[str, Any]:
    """Bind one ancestor-produced report to one exact consumer wave."""

    provenance = _mapping(
        evidence.report_payload.get("provenance"),
        "report.provenance",
    )
    report_protocol = _mapping(
        provenance.get("protocol"),
        "report.provenance.protocol",
    )
    report_dataset = _mapping(
        provenance.get("dataset"),
        "report.provenance.dataset",
    )
    report_sampler = _mapping(
        provenance.get("sampler"),
        "report.provenance.sampler",
    )
    report_sampling = _mapping(
        provenance.get("sampling"),
        "report.provenance.sampling",
    )
    report_prompt_assets = _mapping(
        provenance.get("prompt_assets"),
        "report.provenance.prompt_assets",
    )
    report_sandbox = _mapping(
        provenance.get("sandbox"),
        "report.provenance.sandbox",
    )
    training_dataset = _mapping(
        evidence.training_manifest.payload.get("dataset"),
        "training_manifest.dataset",
    )
    training_model = _mapping(
        evidence.training_manifest.payload.get("model"),
        "training_manifest.model",
    )
    checkpoint_inventory = _mapping(
        evidence.training_receipt.payload.get("checkpoint_inventory"),
        "training_receipt.checkpoint_inventory",
    )
    evaluation_manifest_record_sha256 = _sha(
        provenance.get("evaluation_manifest_record_sha256"),
        "report.provenance.evaluation_manifest_record_sha256",
    )
    if evaluation_manifest_record_sha256 != evidence.evaluation_manifest_record_sha256:
        raise PromotionError("report and evaluation manifest record digests differ")
    evaluated_stage = stage_spec(dict(protocol), evidence.key.stage_id)
    consumer_protocol = {
        "logical_sha256": protocol["logical_sha256"],
        "file_sha256": file_sha256(protocol_path(repo_root)),
        "contract_version": protocol["contract_version"],
    }
    consumer_prompt_assets = prompt_asset_hashes()
    parent_model = dict(protocol["models"][evaluated_stage.model_key])
    if (
        provenance.get("source_git_sha") != producer_source_git_sha
        or evidence.training_manifest.payload.get("source_git_sha") != producer_source_git_sha
    ):
        raise PromotionError("source transition evidence is not producer-source-bound")
    if dict(report_protocol) != consumer_protocol:
        raise PromotionError("producer evaluation protocol differs from the consumer")
    training_protocol = {
        "logical_sha256": evidence.training_manifest.payload.get("protocol_logical_sha256"),
        "file_sha256": evidence.training_manifest.payload.get("protocol_file_sha256"),
        "contract_version": evidence.training_manifest.payload.get("contract_version"),
    }
    if training_protocol != consumer_protocol:
        raise PromotionError("producer training protocol differs from the consumer")
    if (
        dict(report_prompt_assets) != consumer_prompt_assets
        or evidence.training_manifest.payload.get("prompt_assets") != consumer_prompt_assets
    ):
        raise PromotionError("producer prompt assets differ from the consumer")
    if dict(training_model) != parent_model:
        raise PromotionError("producer training model differs from the consumer parent model")
    renderer_contract = {
        field: parent_model.get(field) for field in ("model", "renderer", "effort")
    }
    if any(report_sampler.get(field) != expected for field, expected in renderer_contract.items()):
        raise PromotionError("producer evaluation renderer differs from the consumer")
    expected_dataset = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "logical_release_sha256": protocol["dataset"]["logical_release_sha256"],
    }
    if any(
        report_dataset.get(field) != expected for field, expected in expected_dataset.items()
    ) or (
        training_dataset.get("logical_release_sha256") != expected_dataset["logical_release_sha256"]
    ):
        raise PromotionError("producer dataset differs from the consumer")
    scope = {
        "study_id": STUDY_ID,
        "child": {
            "stage_id": stage.stage_id,
            "wave": wave_name,
            "replicate_id": evidence.key.replicate_id,
            "approval_gate": plan.gate,
        },
        "producer_evaluation": {
            "stage_id": evidence.key.stage_id,
            "wave": evidence.wave,
            "checkpoint_name": evidence.checkpoint_name,
            "replicate_id": evidence.key.replicate_id,
            "panel": evidence.panel,
        },
    }
    equivalence = {
        "protocol": {
            "producer_training": {
                **training_protocol,
            },
            "producer_evaluation": dict(report_protocol),
            "consumer": consumer_protocol,
        },
        "prompt_assets": {
            "producer_training": dict(
                _mapping(
                    evidence.training_manifest.payload.get("prompt_assets"),
                    "training_manifest.prompt_assets",
                )
            ),
            "producer_evaluation": dict(report_prompt_assets),
            "consumer": consumer_prompt_assets,
        },
        "dataset": {
            "producer_training": dict(training_dataset),
            "producer_evaluation": dict(report_dataset),
            "consumer": {
                "repo_id": protocol["dataset"]["repo_id"],
                "revision": protocol["dataset"]["revision"],
                "configuration": protocol["dataset"]["configuration"],
                "logical_release_sha256": protocol["dataset"]["logical_release_sha256"],
            },
        },
        "task_panel": dict(
            _mapping(
                provenance.get("task_panel"),
                "report.provenance.task_panel",
            )
        ),
        "model": {
            "producer_training": dict(training_model),
            "producer_evaluation": parent_model,
            "consumer_parent": parent_model,
            "consumer_child": dict(protocol["models"][stage.model_key]),
        },
        "renderer": {
            "producer_evaluation": {
                field: report_sampler.get(field) for field in ("model", "renderer", "effort")
            },
            "consumer_parent": {
                field: protocol["models"][evaluated_stage.model_key].get(field)
                for field in ("model", "renderer", "effort")
            },
            "consumer_child": {
                field: protocol["models"][stage.model_key].get(field)
                for field in ("model", "renderer", "effort")
            },
        },
        "sampling": dict(report_sampling),
        "sandbox": {
            "producer_training": evidence.training_manifest.payload.get("sandbox"),
            "producer_evaluation": dict(report_sandbox),
        },
    }
    evidence_binding = {
        "training_run_manifest": {
            "relative_path": str(evidence.training_manifest.relative_path),
            "payload_sha256": evidence.training_manifest.payload_sha256,
            "record_sha256": evidence.training_manifest.record_sha256,
        },
        "training_wave_receipt": {
            "relative_path": str(evidence.training_receipt.relative_path),
            "payload_sha256": evidence.training_receipt.payload_sha256,
            "record_sha256": evidence.training_receipt.record_sha256,
        },
        "checkpoint_inventory": dict(checkpoint_inventory),
        "evaluation_manifest": {
            "relative_path": evidence.evaluation_manifest_relative_path,
            "payload_sha256": (evidence.evaluation_manifest_payload_sha256),
            "record_sha256": evaluation_manifest_record_sha256,
        },
        "evaluation_report": {
            "relative_path": evidence.report_relative_path,
            "payload_sha256": evidence.report_payload_sha256,
            "record_sha256": evidence.report_record_sha256,
        },
        "checkpoint": dict(evidence.checkpoint),
        "checkpoint_inventory_logical_sha256": (evidence.checkpoint_inventory_sha256),
    }
    try:
        return build_source_transition(
            repo_root=repo_root,
            producer_source_git_sha=producer_source_git_sha,
            consumer_source_git_sha=consumer_source_git_sha,
            scope=scope,
            approved_change_paths=approved_change_paths,
            equivalence=equivalence,
            evidence=evidence_binding,
        )
    except SourceTransitionError as exc:
        raise PromotionError(f"source transition is invalid: {exc}") from exc


def _approved_change_paths_from_transition(
    value: Any,
) -> tuple[str, ...]:
    transition = _mapping(value, "approval.source_transition")
    scope = _mapping(
        transition.get("scope"),
        "approval.source_transition.scope",
    )
    approved = _mapping(
        scope.get("approved_changes"),
        "approval.source_transition.scope.approved_changes",
    )
    paths = approved.get("paths")
    if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
        raise PromotionError("approval source transition has no approved path inventory")
    return tuple(paths)


def _require_same_evaluated_checkpoint(
    primary: EvaluationEvidence,
    baseline: EvaluationEvidence,
) -> None:
    """Require two panel reports to share one exact parent artifact chain."""

    fields = (
        ("stage key", primary.key, baseline.key),
        ("wave", primary.wave, baseline.wave),
        ("checkpoint name", primary.checkpoint_name, baseline.checkpoint_name),
        ("checkpoint", primary.checkpoint, baseline.checkpoint),
        (
            "checkpoint inventory",
            primary.checkpoint_inventory_sha256,
            baseline.checkpoint_inventory_sha256,
        ),
        (
            "training manifest",
            primary.training_manifest.record_sha256,
            baseline.training_manifest.record_sha256,
        ),
        (
            "training receipt",
            primary.training_receipt.record_sha256,
            baseline.training_receipt.record_sha256,
        ),
    )
    for field, primary_value, baseline_value in fields:
        if baseline_value != primary_value:
            raise PromotionError(
                "prior-level promotion and current-level entry baseline "
                f"must evaluate the exact same parent checkpoint ({field} differs)"
            )


def _approval_payload(
    *,
    stage: StageSpec,
    wave_name: str,
    plan: ApprovalPlan,
    evidence: EvaluationEvidence,
    source_git_sha: str,
    protocol: Mapping[str, Any],
    checkpoint_selection: Mapping[str, Any] | None = None,
    entry_baseline_evidence: EvaluationEvidence | None = None,
    evidence_source_git_sha: str | None = None,
    source_transition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        evidence.key.stage_id,
        evidence.wave,
    ) not in plan.allowed_evaluation_checkpoints:
        raise PromotionError(
            f"{evidence.key.stage_id}/{evidence.wave} cannot approve {stage.stage_id}/{wave_name}"
        )
    if evidence.panel != plan.expected_panel:
        raise PromotionError(
            f"{stage.stage_id}/{wave_name} requires {plan.expected_panel}, not {evidence.panel}"
        )
    if plan.entry_baseline_panel is None:
        if entry_baseline_evidence is not None:
            raise PromotionError("this approval gate does not accept an entry baseline")
    else:
        if entry_baseline_evidence is None:
            raise PromotionError(
                f"{stage.stage_id}/{wave_name} requires the "
                f"{plan.entry_baseline_panel} pre-update baseline"
            )
        if entry_baseline_evidence.panel != plan.entry_baseline_panel:
            raise PromotionError(
                f"{stage.stage_id}/{wave_name} entry baseline requires "
                f"{plan.entry_baseline_panel}, not {entry_baseline_evidence.panel}"
            )
        _require_same_evaluated_checkpoint(
            evidence,
            entry_baseline_evidence,
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
            raise PromotionError(f"first unmastered level is {selected}, not {stage.current_level}")
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

    cross_source = source_transition is not None
    if cross_source != (evidence_source_git_sha is not None):
        raise PromotionError("source transition and evidence source must be supplied together")
    if evidence_source_git_sha is not None and evidence_source_git_sha == source_git_sha:
        raise PromotionError("same-source approvals must retain the v1 schema")

    payload: dict[str, Any] = {
        "schema_version": (
            SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION if cross_source else APPROVAL_SCHEMA_VERSION
        ),
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
            "checkpoint_inventory_sha256": (evidence.checkpoint_inventory_sha256),
            "replicate_id": evidence.key.replicate_id,
            "panel": evidence.panel,
            "report_relative_path": evidence.report_relative_path,
            "report_payload_sha256": evidence.report_payload_sha256,
            "report_record_sha256": evidence.report_record_sha256,
            "training_wave_receipt_record_sha256": (evidence.training_receipt.record_sha256),
        },
        "mastery": mastery,
        "checkpoint_selection": (
            dict(checkpoint_selection) if checkpoint_selection is not None else None
        ),
    }
    if entry_baseline_evidence is not None:
        payload["entry_baseline"] = {
            "stage_id": entry_baseline_evidence.key.stage_id,
            "wave": entry_baseline_evidence.wave,
            "checkpoint_name": entry_baseline_evidence.checkpoint_name,
            "checkpoint": entry_baseline_evidence.checkpoint,
            "checkpoint_inventory_sha256": (
                entry_baseline_evidence.checkpoint_inventory_sha256
            ),
            "replicate_id": entry_baseline_evidence.key.replicate_id,
            "panel": entry_baseline_evidence.panel,
            "report_relative_path": entry_baseline_evidence.report_relative_path,
            "report_payload_sha256": (
                entry_baseline_evidence.report_payload_sha256
            ),
            "report_record_sha256": (
                entry_baseline_evidence.report_record_sha256
            ),
            "training_wave_receipt_record_sha256": (
                entry_baseline_evidence.training_receipt.record_sha256
            ),
        }
    if cross_source:
        payload["evidence_source_git_sha"] = evidence_source_git_sha
        payload["source_transition"] = dict(source_transition)
        payload["evaluation"].update(
            {
                "training_run_manifest_record_sha256": (evidence.training_manifest.record_sha256),
                "evaluation_manifest_relative_path": (evidence.evaluation_manifest_relative_path),
                "evaluation_manifest_payload_sha256": (evidence.evaluation_manifest_payload_sha256),
                "evaluation_manifest_record_sha256": (evidence.evaluation_manifest_record_sha256),
            }
        )
    # The launcher uses these top-level fields to resolve dynamic parents and
    # to bind exact-parent gates.  A same-stage smoke continuation must not
    # claim its smoke receipt as the stage's external parent.
    if plan.gate in {
        "first-unmastered-entry-receipt",
        "entry-evaluation-and-promotion-receipt",
        "parent-evaluation-receipt",
        "prior-level-held-out-promotion-receipt",
        "prior-and-current-level-held-out-transition-receipt",
    }:
        payload.update(
            {
                "parent_stage_id": evidence.key.stage_id,
                "parent_wave": evidence.wave,
                "parent_receipt_record_sha256": (evidence.training_receipt.record_sha256),
                "selected_parent_checkpoint": evidence.checkpoint,
                "selected_parent_checkpoint_inventory_sha256": (
                    evidence.checkpoint_inventory_sha256
                ),
            }
        )
    elif plan.gate in {
        "clean-smoke-receipt",
        "current-level-held-out-promotion-receipt",
    }:
        payload.update(
            {
                "prior_wave": evidence.wave,
                "prior_receipt_record_sha256": (evidence.training_receipt.record_sha256),
            }
        )
    return payload


def validate_source_transition_approval(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    stage: StageSpec,
    wave_name: str,
    replicate_id: str,
    consumer_source_git_sha: str,
    approval: TrainingRecord,
) -> EvaluationEvidence:
    """Revalidate every fact in one cross-source approval at launch time."""

    payload = approval.payload
    if payload.get("schema_version") != SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION:
        raise PromotionError("cross-source approval has a foreign schema")
    if payload.get("source_git_sha") != consumer_source_git_sha:
        raise PromotionError("cross-source approval names another consumer")
    try:
        validate_source_sha(repo_root, consumer_source_git_sha)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PromotionError(
            f"cross-source approval consumer is not the clean HEAD: {exc}"
        ) from exc
    producer_source_git_sha = str(payload.get("evidence_source_git_sha", ""))
    if producer_source_git_sha == consumer_source_git_sha:
        raise PromotionError("same-source approval cannot use the v2 schema")
    approved_change_paths = _approved_change_paths_from_transition(payload.get("source_transition"))
    try:
        git_facts = source_transition_git_facts(
            repo_root=repo_root,
            producer_source_git_sha=producer_source_git_sha,
            consumer_source_git_sha=consumer_source_git_sha,
        )
        approved_change_scope(git_facts, approved_change_paths)
    except SourceTransitionError as exc:
        raise PromotionError(f"source transition is invalid: {exc}") from exc

    plan = approval_plan(stage, wave_name)
    evaluation = _mapping(payload.get("evaluation"), "approval.evaluation")
    if evaluation.get("replicate_id") != replicate_id:
        raise PromotionError("cross-source approval names another replicate")
    evidence = validate_checkpoint_report(
        repo_root=repo_root,
        protocol=protocol,
        store=store,
        stage_id=str(evaluation.get("stage_id", "")),
        wave=str(evaluation.get("wave", "")),
        checkpoint_name=str(evaluation.get("checkpoint_name", "")),
        replicate_id=replicate_id,
        panel=str(evaluation.get("panel", "")),
        expected_source_sha=producer_source_git_sha,
        expected_report_record_sha256=str(evaluation.get("report_record_sha256", "")),
    )
    checkpoint_selection: dict[str, Any] | None = None
    if plan.gate == "first-unmastered-entry-receipt" and evidence.key.stage_id == "qwen-mixed-sft":
        checkpoint_selection = _mixed_checkpoint_selection(
            repo_root=repo_root,
            protocol=protocol,
            store=store,
            selected=evidence,
            expected_source_sha=producer_source_git_sha,
        )
    else:
        _terminal_checkpoint(evidence)
    transition = _source_transition_document(
        repo_root=repo_root,
        protocol=protocol,
        stage=stage,
        wave_name=wave_name,
        plan=plan,
        evidence=evidence,
        producer_source_git_sha=producer_source_git_sha,
        consumer_source_git_sha=consumer_source_git_sha,
        approved_change_paths=approved_change_paths,
    )
    expected = _approval_payload(
        stage=stage,
        wave_name=wave_name,
        plan=plan,
        evidence=evidence,
        source_git_sha=consumer_source_git_sha,
        protocol=protocol,
        checkpoint_selection=checkpoint_selection,
        evidence_source_git_sha=producer_source_git_sha,
        source_transition=transition,
    )
    if payload != expected:
        raise PromotionError("cross-source approval differs from its recomputed evidence")
    return evidence


def validate_same_source_wave_approval(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    stage: StageSpec,
    wave_name: str,
    replicate_id: str,
    source_git_sha: str,
    approval: TrainingRecord,
) -> EvaluationEvidence:
    """Recompute a same-source approval from its sealed reports at launch.

    The approval JSON is an index, not authority.  Every report, manifest,
    checkpoint inventory, receipt, aggregate, and task-panel fact is loaded
    from its canonical external-ledger path and validated again before the
    approval may authorize a paid launch.
    """

    payload = approval.payload
    if payload.get("schema_version") != APPROVAL_SCHEMA_VERSION:
        raise PromotionError("same-source approval has a foreign schema")
    if payload.get("source_git_sha") != source_git_sha:
        raise PromotionError("same-source approval names another source")
    try:
        validate_source_sha(repo_root, source_git_sha)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PromotionError(
            f"same-source approval source is not the clean HEAD: {exc}"
        ) from exc

    plan = approval_plan(stage, wave_name)
    evaluation = _mapping(payload.get("evaluation"), "approval.evaluation")
    if evaluation.get("replicate_id") != replicate_id:
        raise PromotionError("same-source approval names another replicate")
    if evaluation.get("panel") != plan.expected_panel:
        raise PromotionError("same-source approval names the wrong promotion panel")
    evidence = validate_checkpoint_report(
        repo_root=repo_root,
        protocol=protocol,
        store=store,
        stage_id=str(evaluation.get("stage_id", "")),
        wave=str(evaluation.get("wave", "")),
        checkpoint_name=str(evaluation.get("checkpoint_name", "")),
        replicate_id=replicate_id,
        panel=plan.expected_panel,
        expected_source_sha=source_git_sha,
        expected_report_record_sha256=str(
            evaluation.get("report_record_sha256", "")
        ),
    )

    entry_baseline_evidence: EvaluationEvidence | None = None
    if plan.entry_baseline_panel is not None:
        entry = _mapping(
            payload.get("entry_baseline"),
            "approval.entry_baseline",
        )
        if entry.get("replicate_id") != replicate_id:
            raise PromotionError("entry baseline names another replicate")
        if entry.get("panel") != plan.entry_baseline_panel:
            raise PromotionError("entry baseline names the wrong current-level panel")
        entry_baseline_evidence = validate_checkpoint_report(
            repo_root=repo_root,
            protocol=protocol,
            store=store,
            stage_id=str(entry.get("stage_id", "")),
            wave=str(entry.get("wave", "")),
            checkpoint_name=str(entry.get("checkpoint_name", "")),
            replicate_id=replicate_id,
            panel=plan.entry_baseline_panel,
            expected_source_sha=source_git_sha,
            expected_report_record_sha256=str(
                entry.get("report_record_sha256", "")
            ),
        )
    elif "entry_baseline" in payload:
        raise PromotionError("approval unexpectedly contains an entry baseline")

    checkpoint_selection: dict[str, Any] | None = None
    if (
        plan.gate == "first-unmastered-entry-receipt"
        and evidence.key.stage_id == "qwen-mixed-sft"
    ):
        checkpoint_selection = _mixed_checkpoint_selection(
            repo_root=repo_root,
            protocol=protocol,
            store=store,
            selected=evidence,
            expected_source_sha=source_git_sha,
        )
    else:
        _terminal_checkpoint(evidence)

    expected = _approval_payload(
        stage=stage,
        wave_name=wave_name,
        plan=plan,
        evidence=evidence,
        source_git_sha=source_git_sha,
        protocol=protocol,
        checkpoint_selection=checkpoint_selection,
        entry_baseline_evidence=entry_baseline_evidence,
    )
    if payload != expected:
        raise PromotionError(
            "same-source approval differs from its canonically recomputed evidence"
        )
    return evidence


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
    entry_baseline_report_record_sha256: str | None = None,
    expected_source_sha: str,
    evidence_source_sha: str | None = None,
    approved_change_paths: Sequence[str] | None = None,
    confirmation: str,
) -> dict[str, Any]:
    """Validate reviewed evidence and atomically record one approval."""

    if confirmation != APPROVAL_CONFIRMATION_TOKEN:
        raise PromotionError("explicit human approval confirmation is missing")
    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    source_git_sha = validate_source_sha(root, expected_source_sha)
    evidence_git_sha = source_git_sha if evidence_source_sha is None else evidence_source_sha
    if evidence_git_sha != source_git_sha:
        try:
            git_facts = source_transition_git_facts(
                repo_root=root,
                producer_source_git_sha=evidence_git_sha,
                consumer_source_git_sha=source_git_sha,
            )
            approved_change_scope(git_facts, approved_change_paths)
        except SourceTransitionError as exc:
            raise PromotionError(f"source transition is invalid: {exc}") from exc
    elif approved_change_paths is not None:
        raise PromotionError("same-source v1 approval cannot include an approved change scope")
    stage = stage_spec(protocol, stage_id)
    try:
        validate_stage_replicate(
            protocol,
            stage_id=stage.stage_id,
            replicate_id=replicate_id,
        )
    except ValueError as exc:
        raise PromotionError(str(exc)) from exc
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
        expected_source_sha=evidence_git_sha,
        expected_report_record_sha256=evaluation_report_record_sha256,
    )
    entry_baseline_evidence: EvaluationEvidence | None = None
    if plan.entry_baseline_panel is not None:
        if entry_baseline_report_record_sha256 is None:
            raise PromotionError(
                f"{stage.stage_id}/{wave_name} requires a reviewed "
                "current-level entry-baseline report"
            )
        if evidence_git_sha != source_git_sha:
            raise PromotionError(
                "dual level-transition approval must be produced and consumed "
                "at the same source commit"
            )
        entry_baseline_evidence = validate_checkpoint_report(
            repo_root=root,
            protocol=protocol,
            store=store,
            stage_id=evaluation_stage_id,
            wave=evaluation_wave,
            checkpoint_name=evaluation_checkpoint_name,
            replicate_id=replicate_id,
            panel=plan.entry_baseline_panel,
            expected_source_sha=evidence_git_sha,
            expected_report_record_sha256=(
                entry_baseline_report_record_sha256
            ),
        )
    elif entry_baseline_report_record_sha256 is not None:
        raise PromotionError(
            "entry-baseline report was supplied for a single-panel gate"
        )
    checkpoint_selection: dict[str, Any] | None = None
    if plan.gate == "first-unmastered-entry-receipt" and evidence.key.stage_id == "qwen-mixed-sft":
        checkpoint_selection = _mixed_checkpoint_selection(
            repo_root=root,
            protocol=protocol,
            store=store,
            selected=evidence,
            expected_source_sha=evidence_git_sha,
        )
    else:
        _terminal_checkpoint(evidence)
    transition = (
        _source_transition_document(
            repo_root=root,
            protocol=protocol,
            stage=stage,
            wave_name=wave_name,
            plan=plan,
            evidence=evidence,
            producer_source_git_sha=evidence_git_sha,
            consumer_source_git_sha=source_git_sha,
            approved_change_paths=approved_change_paths,
        )
        if evidence_git_sha != source_git_sha
        else None
    )
    payload = _approval_payload(
        stage=stage,
        wave_name=wave_name,
        plan=plan,
        evidence=evidence,
        source_git_sha=source_git_sha,
        protocol=protocol,
        checkpoint_selection=checkpoint_selection,
        entry_baseline_evidence=entry_baseline_evidence,
        evidence_source_git_sha=(evidence_git_sha if transition is not None else None),
        source_transition=transition,
    )
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    with store.acquire_stage_lock(key):
        # Close the approval-time HEAD/dirty-tree gap immediately before the
        # immutable external record is created.
        validate_source_sha(root, source_git_sha)
        if transition is not None:
            rebuilt_transition = _source_transition_document(
                repo_root=root,
                protocol=protocol,
                stage=stage,
                wave_name=wave_name,
                plan=plan,
                evidence=evidence,
                producer_source_git_sha=evidence_git_sha,
                consumer_source_git_sha=source_git_sha,
                approved_change_paths=approved_change_paths,
            )
            if rebuilt_transition != transition:
                raise PromotionError("source transition changed before approval recording")
        approval = store.write_wave_approval(
            key,
            wave=plan.storage_wave,
            payload=payload,
        )
    result = {
        "status": "approved",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "approval_storage_wave": plan.storage_wave,
        "approval": str(approval.relative_path),
        "approval_record_sha256": approval.record_sha256,
        "evaluation_report_record_sha256": evidence.report_record_sha256,
    }
    if transition is not None:
        result.update(
            {
                "approval_schema_version": payload["schema_version"],
                "evidence_source_git_sha": evidence_git_sha,
                "consumer_source_git_sha": source_git_sha,
                "source_transition_logical_sha256": transition["logical_sha256"],
            }
        )
    return result
