"""Sealed, resumable launch controller for representation-training-v1."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import uuid
from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tinker_cookbook import checkpoint_utils
from tinker_cookbook.rl.train import Config as RLConfig
from tinker_cookbook.supervised.train import Config as SFTConfig

from rl.evaluation.tracking import validate_wandb_access
from rl.track_a.tinker_data import (
    TrackARLDatasetBuilder,
    TrackASupervisedDatasetBuilder,
)

from .preflight import stage_preflight
from .promotion import (
    APPROVAL_SCHEMA_VERSION,
    LEVEL_PROGRESS_PANELS,
    PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION,
    SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION,
    PromotionError,
    record_base_baseline_approval,
    record_rollout_health_approval,
    validate_parent_receipt_transition_approval,
    validate_same_source_wave_approval,
    validate_source_transition_approval,
)
from .protocol import (
    LEVELS,
    STUDY_ID,
    StageSpec,
    file_sha256,
    load_protocol,
    parent_replicate_id,
    stage_spec,
    validate_stage_replicate,
    validate_source_sha,
)
from .schedule import SCHEDULE_SEED
from .store import StageKey, TrainingRecord, TrainingStore, canonical_sha256


WANDB_RUN_ID_PREFIX = "pxct-"
_TINKER_PATH = re.compile(r"^tinker://[^\s]+$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CHILD_SOURCE_TRANSITION_SCHEMA_VERSION = "pixcell-training-child-source-transition-v1"
_WAVE_ARTIFACT_SNAPSHOT_SCHEMA_VERSION = "pixcell-training-wave-artifact-snapshot-v1"
_COOKBOOK_FRESH_RESUME_BOOTSTRAP_FILES = frozenset(
    {"code.diff", "config.json", "logs.log"}
)
_ENVIRONMENT_FIELDS = (
    "WANDB_DIR",
    "WANDB_DISABLE_CODE",
    "WANDB_DISABLE_GIT",
    "WANDB_ENTITY",
    "WANDB_JOB_TYPE",
    "WANDB_MODE",
    "WANDB_NAME",
    "WANDB_PROJECT",
    "WANDB_RESUME",
    "WANDB_RUN_GROUP",
    "WANDB_RUN_ID",
    "WANDB_SAVE_CODE",
    "WANDB_TAGS",
)


class TrainingLaunchError(RuntimeError):
    """A paid stage is ambiguous, inconsistent, or not approved."""


@dataclass(frozen=True)
class ParentBinding:
    stage_id: str
    wave: str
    replicate_id: str
    receipt: TrainingRecord
    checkpoint: dict[str, Any]
    source_git_sha: str
    run_manifest: TrainingRecord
    entry_approval: TrainingRecord | None = None
    source_transition: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResumeBinding:
    """Exact optimizer state the pinned Cookbook is allowed to resume."""

    batch: int
    checkpoint: dict[str, Any]


def _child_source_transition_binding(
    approval: TrainingRecord,
) -> dict[str, Any]:
    payload = approval.payload
    if payload.get("schema_version") not in {
        SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION,
        PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION,
    }:
        raise TrainingLaunchError(
            "child source transition is not backed by an approved transition"
        )
    transition = payload.get("source_transition")
    if not isinstance(transition, Mapping):
        raise TrainingLaunchError("transition approval has no source transition")
    logical_sha256 = str(transition.get("logical_sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", logical_sha256):
        raise TrainingLaunchError(
            "transition approval source transition has no logical digest"
        )
    return {
        "schema_version": _CHILD_SOURCE_TRANSITION_SCHEMA_VERSION,
        "authorized_child_wave": str(payload.get("wave", "")),
        "producer_source_git_sha": str(payload.get("evidence_source_git_sha", "")),
        "consumer_source_git_sha": str(payload.get("source_git_sha", "")),
        "approval_schema_version": str(payload.get("schema_version", "")),
        "approval": {
            "relative_path": str(approval.relative_path),
            "payload_sha256": approval.payload_sha256,
            "record_sha256": approval.record_sha256,
        },
        "source_transition_logical_sha256": logical_sha256,
        "source_transition": dict(transition),
    }


def deterministic_wandb_run_id(
    *,
    source_git_sha: str,
    protocol_logical_sha256: str,
    key: StageKey,
) -> str:
    digest = canonical_sha256(
        {
            "schema_version": "pixcell-training-wandb-identity-v1",
            "source_git_sha": source_git_sha,
            "protocol_logical_sha256": protocol_logical_sha256,
            **key.as_dict(),
        }
    )
    return WANDB_RUN_ID_PREFIX + digest[:27]


def _tracking_binding(
    *,
    protocol: Mapping[str, Any],
    source_git_sha: str,
    key: StageKey,
    stage: StageSpec,
    store: TrainingStore,
) -> dict[str, Any]:
    model_family = "inkling" if stage.model_key == "inkling" else "qwen-open"
    run_id = deterministic_wandb_run_id(
        source_git_sha=source_git_sha,
        protocol_logical_sha256=str(protocol["logical_sha256"]),
        key=key,
    )
    return {
        "provider": "wandb",
        "entity": protocol["tracking"]["entity"],
        "project": protocol["tracking"]["project"],
        "run_id": run_id,
        "name": (f"{STUDY_ID}/{stage.stage_id}/{key.replicate_id}@{source_git_sha[:12]}"),
        "group": f"{STUDY_ID}/{model_family}",
        "job_type": stage.kind,
        "tags": [
            STUDY_ID,
            stage.stage_id,
            stage.model_key,
            stage.kind,
            key.replicate_id,
            *stage.hypotheses,
        ],
        "directory": str(store.stage_path(key) / "wandb"),
    }


@contextmanager
def _wandb_environment(
    binding: Mapping[str, Any],
    *,
    resume: bool,
) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in _ENVIRONMENT_FIELDS}
    directory = Path(str(binding["directory"]))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.environ.update(
        {
            "WANDB_DIR": str(directory),
            "WANDB_DISABLE_CODE": "true",
            "WANDB_DISABLE_GIT": "true",
            "WANDB_ENTITY": str(binding["entity"]),
            "WANDB_JOB_TYPE": str(binding["job_type"]),
            "WANDB_MODE": "online",
            "WANDB_NAME": str(binding["name"]),
            "WANDB_PROJECT": str(binding["project"]),
            "WANDB_RESUME": "must" if resume else "never",
            "WANDB_RUN_GROUP": str(binding["group"]),
            "WANDB_RUN_ID": str(binding["run_id"]),
            "WANDB_SAVE_CODE": "false",
            "WANDB_TAGS": ",".join(str(item) for item in binding["tags"]),
        }
    )
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _finish_wandb_run(wandb_module: Any, run: Any) -> None:
    """Best-effort cleanup after rejecting a live W&B binding."""

    finish = getattr(run, "finish", None)
    if callable(finish):
        try:
            finish()
            return
        except BaseException:
            pass
    module_finish = getattr(wandb_module, "finish", None)
    if callable(module_finish):
        try:
            module_finish()
        except BaseException:
            pass


@contextmanager
def _sealed_wandb_initialization(
    binding: Mapping[str, Any],
    *,
    resume: bool,
    wandb_module: Any | None = None,
    on_initialized: Callable[[Mapping[str, Any]], None] | None = None,
) -> Iterator[None]:
    """Force Cookbook logging onto the exact run sealed in the manifest.

    The Cookbook intentionally owns the call to ``wandb.init``.  This narrow
    wrapper preserves that integration while replacing identity-bearing
    arguments with the immutable launch binding.  The observed live run is
    checked and recorded before the Cookbook can construct a Tinker client.
    """

    module = wandb_module if wandb_module is not None else importlib.import_module("wandb")
    if getattr(module, "run", None) is not None:
        raise TrainingLaunchError("a W&B run is already active before sealed initialization")
    original_init = getattr(module, "init", None)
    if not callable(original_init):
        raise TrainingLaunchError("the W&B module has no callable init")
    init_calls = 0
    initialized_run: Any | None = None

    def sealed_init(*args: Any, **kwargs: Any) -> Any:
        nonlocal init_calls, initialized_run
        init_calls += 1
        if init_calls != 1:
            raise TrainingLaunchError("the training process attempted multiple W&B initializations")
        if args:
            raise TrainingLaunchError("the training process used positional W&B identity arguments")
        for field in ("project", "name"):
            supplied = kwargs.get(field)
            if supplied is not None and str(supplied) != str(binding[field]):
                raise TrainingLaunchError(f"the training process supplied a different W&B {field}")
        cookbook_config = kwargs.get("config")
        sealed = dict(kwargs)
        sealed.update(
            {
                # Cookbook logs the same config again immediately after init.
                # RL callback fields are sanitized differently across the two
                # W&B calls, so initialize identity first and write hparams
                # through the same canonical post-init path both times.
                "config": None,
                "entity": str(binding["entity"]),
                "project": str(binding["project"]),
                "dir": str(binding["directory"]),
                "id": str(binding["run_id"]),
                "name": str(binding["name"]),
                "group": str(binding["group"]),
                "job_type": str(binding["job_type"]),
                "tags": tuple(str(item) for item in binding["tags"]),
                "mode": "online",
                "resume": "must" if resume else "never",
                "save_code": False,
            }
        )
        run = original_init(**sealed)
        initialized_run = run
        settings = getattr(run, "settings", None)
        observed = {
            "run_id": str(getattr(run, "id", "")),
            "entity": str(getattr(run, "entity", "")),
            "project": str(getattr(run, "project", "")),
            "name": str(getattr(run, "name", "")),
            "group": str(getattr(run, "group", "")),
            "job_type": str(getattr(run, "job_type", "")),
            "tags": [str(item) for item in getattr(run, "tags", ())],
            "resumed": bool(getattr(run, "resumed", False)),
            "url": str(getattr(run, "url", "")),
            "requested_directory": str(binding["directory"]),
            "resolved_root_directory": str(getattr(settings, "root_dir", "")),
            "files_directory": str(getattr(run, "dir", "")),
            "requested_resume": "must" if resume else "never",
            "resolved_resume": str(getattr(settings, "resume", "")),
        }
        expected = {
            "run_id": str(binding["run_id"]),
            "entity": str(binding["entity"]),
            "project": str(binding["project"]),
            "name": str(binding["name"]),
            "group": str(binding["group"]),
            "job_type": str(binding["job_type"]),
            "tags": [str(item) for item in binding["tags"]],
            "resumed": resume,
            "resolved_resume": "must" if resume else "never",
        }
        differences = [field for field, value in expected.items() if observed[field] != value]
        requested_directory = Path(str(binding["directory"])).resolve(strict=False)
        try:
            resolved_directory = Path(observed["resolved_root_directory"]).resolve(strict=True)
        except (OSError, RuntimeError):
            differences.append("resolved_root_directory")
        else:
            if resolved_directory != requested_directory:
                differences.append("resolved_root_directory")
        try:
            files_directory = Path(observed["files_directory"]).resolve(strict=True)
        except (OSError, RuntimeError):
            differences.append("files_directory")
        else:
            if not files_directory.is_relative_to(requested_directory):
                differences.append("files_directory")
        if differences:
            _finish_wandb_run(module, run)
            raise TrainingLaunchError(
                "the live W&B run differs from its sealed " + ", ".join(differences)
            )
        if cookbook_config is not None:
            config = getattr(module, "config", None)
            update = getattr(config, "update", None)
            if not callable(update):
                _finish_wandb_run(module, run)
                raise TrainingLaunchError("the live W&B run has no configurable hparam store")
            try:
                # Use Config.update for both writes. W&B sanitizes callable
                # fields differently in wandb.init, while the Cookbook writes
                # the same hparams again immediately after init. Continuation
                # waves intentionally change their ceiling and invocation
                # metadata, so only the preseed update may replace prior-wave
                # values; the Cookbook's following update is then identical.
                update(cookbook_config, allow_val_change=resume)
            except BaseException:
                _finish_wandb_run(module, run)
                raise
            observed["hparams_preseeded"] = True
            observed["hparams_allow_val_change"] = resume
        else:
            observed["hparams_preseeded"] = False
            observed["hparams_allow_val_change"] = False
        try:
            if on_initialized is not None:
                on_initialized(observed)
        except BaseException:
            _finish_wandb_run(module, run)
            raise
        return run

    module.init = sealed_init
    try:
        yield
    except BaseException:
        if initialized_run is not None:
            _finish_wandb_run(module, initialized_run)
        raise
    else:
        if init_calls != 1:
            if initialized_run is not None:
                _finish_wandb_run(module, initialized_run)
            raise TrainingLaunchError("training returned without initializing its sealed W&B run")
    finally:
        module.init = original_init


def _checkpoint_from_inventory(
    receipt: TrainingRecord,
    selected: Mapping[str, Any],
    *,
    inventory_sha256: Any,
) -> dict[str, Any]:
    inventory = receipt.payload.get("checkpoint_inventory")
    if not isinstance(inventory, Mapping):
        raise TrainingLaunchError("parent receipt has no checkpoint inventory")
    if (
        inventory.get("logical_sha256") != inventory_sha256
        or canonical_sha256(inventory.get("entries")) != inventory_sha256
    ):
        raise TrainingLaunchError("parent checkpoint inventory digest differs")
    entries = inventory.get("entries")
    if not isinstance(entries, list) or dict(selected) not in entries:
        raise TrainingLaunchError("selected parent checkpoint is not in the parent receipt")
    checkpoint = dict(selected)
    if not _TINKER_PATH.fullmatch(
        str(checkpoint.get("state_path", ""))
    ) or not _TINKER_PATH.fullmatch(str(checkpoint.get("sampler_path", ""))):
        raise TrainingLaunchError("selected parent checkpoint has invalid URIs")
    return checkpoint


def _manifest_transition_approval(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    source_git_sha: str,
    existing_manifest: TrainingRecord,
) -> TrainingRecord:
    observed = existing_manifest.payload.get("source_transition")
    if not isinstance(observed, Mapping):
        raise TrainingLaunchError("cross-source parent requires a transition in the child manifest")
    authorized_wave = str(observed.get("authorized_child_wave", ""))
    if authorized_wave not in stage.waves:
        raise TrainingLaunchError("child manifest transition names an unknown wave")
    approval = store.load_wave_approval(key, wave=authorized_wave)
    if approval is None:
        raise TrainingLaunchError("child manifest transition approval is missing")
    try:
        if (
            approval.payload.get("schema_version")
            == PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
        ):
            validate_parent_receipt_transition_approval(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                stage=stage,
                wave_name=authorized_wave,
                replicate_id=key.replicate_id,
                consumer_source_git_sha=source_git_sha,
                approval=approval,
            )
        else:
            validate_source_transition_approval(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                stage=stage,
                wave_name=authorized_wave,
                replicate_id=key.replicate_id,
                consumer_source_git_sha=source_git_sha,
                approval=approval,
            )
    except PromotionError as exc:
        raise TrainingLaunchError(
            f"child manifest source transition failed validation: {exc}"
        ) from exc
    expected = _child_source_transition_binding(approval)
    if dict(observed) != expected:
        raise TrainingLaunchError("child manifest source transition differs from its v2 approval")
    return approval


def _parent_binding(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    source_git_sha: str,
    approval: TrainingRecord | None,
    existing_manifest: TrainingRecord | None,
) -> ParentBinding | None:
    if stage.parent.startswith("base:"):
        expected_model = stage.parent.split(":", 1)[1]
        if expected_model != stage.model_key:
            raise TrainingLaunchError("base parent and stage model differ")
        if existing_manifest is not None and "source_transition" in existing_manifest.payload:
            raise TrainingLaunchError("base-parent child manifest contains a source transition")
        return None

    parent_stage_id, parent_wave = stage.parent.split(":", 1)
    if parent_wave == "complete-or-skip":
        frozen_parent = (
            existing_manifest.payload.get("parent_receipt")
            if existing_manifest is not None
            else None
        )
        if isinstance(frozen_parent, Mapping):
            selected_stage = str(frozen_parent.get("stage_id", ""))
            selected_wave = str(frozen_parent.get("wave", ""))
        elif approval is not None:
            selected_stage = str(approval.payload.get("parent_stage_id", ""))
            selected_wave = str(approval.payload.get("parent_wave", ""))
        else:
            raise TrainingLaunchError(f"{stage.stage_id} requires an approved dynamic parent")
        allowed = {"qwen-mixed-sft"}
        target_index = int(str(stage.current_level)[1:])
        allowed.update(f"qwen-mixed-rl-l{index}" for index in range(target_index))
        if selected_stage not in allowed or selected_wave != "complete":
            raise TrainingLaunchError(f"{stage.stage_id} approval selected an invalid parent")
        parent_stage_id, parent_wave = selected_stage, selected_wave

    parent_replicate = parent_replicate_id(
        protocol,
        stage_id=stage.stage_id,
        replicate_id=key.replicate_id,
    )
    parent_key = StageKey(key.study_id, parent_stage_id, parent_replicate)
    parent_manifest = store.load_manifest(parent_key)
    receipt = store.load_wave_receipt(parent_key, wave=parent_wave)
    if parent_manifest is None or receipt is None:
        raise TrainingLaunchError(f"{stage.stage_id} requires {parent_stage_id}/{parent_wave}")
    parent_source_git_sha = str(parent_manifest.payload.get("source_git_sha", ""))
    if not _GIT_SHA.fullmatch(parent_source_git_sha):
        raise TrainingLaunchError("parent run manifest has an invalid source commit")
    if (
        receipt.payload.get("stage_id") != parent_stage_id
        or receipt.payload.get("wave") != parent_wave
        or receipt.payload.get("run_manifest_record_sha256") != parent_manifest.record_sha256
    ):
        raise TrainingLaunchError("parent receipt and run manifest identities differ")
    if (
        parent_manifest.payload.get("contract_version") != protocol["contract_version"]
    ):
        raise TrainingLaunchError("parent run manifest differs from the consumer protocol")
    historical_parent_transition = (
        (
            (
                approval is not None
                and approval.payload.get("schema_version")
                == PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
            )
            or (
                existing_manifest is not None
                and isinstance(
                    existing_manifest.payload.get("source_transition"),
                    Mapping,
                )
                and existing_manifest.payload["source_transition"].get(
                    "approval_schema_version"
                )
                == PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
            )
        )
        and stage.stage_id == "qwen-l0-rl-l1"
        and parent_stage_id == "qwen-l0-sft"
        and parent_wave == "complete"
    )
    if (
        parent_manifest.payload.get("protocol_logical_sha256")
        != protocol["logical_sha256"]
        and not historical_parent_transition
    ):
        raise TrainingLaunchError("parent run manifest differs from the consumer protocol")
    parent_stage = parent_manifest.payload.get("stage")
    if (
        not isinstance(parent_stage, Mapping)
        or parent_stage.get("stage_id") != parent_stage_id
        or parent_stage.get("model_key") != stage.model_key
    ):
        raise TrainingLaunchError("parent run manifest has the wrong stage or model")
    checkpoint: dict[str, Any]
    frozen_parent = (
        existing_manifest.payload.get("parent_receipt") if existing_manifest is not None else None
    )
    if isinstance(frozen_parent, Mapping):
        if (
            frozen_parent.get("stage_id") != parent_stage_id
            or frozen_parent.get("wave") != parent_wave
            or frozen_parent.get("replicate_id", parent_replicate)
            != parent_replicate
            or frozen_parent.get("record_sha256") != receipt.record_sha256
        ):
            raise TrainingLaunchError("frozen stage manifest and current parent receipt differ")
        frozen_checkpoint = frozen_parent.get("checkpoint")
        if not isinstance(frozen_checkpoint, Mapping):
            raise TrainingLaunchError("frozen stage parent has no checkpoint")
        checkpoint = _checkpoint_from_inventory(
            receipt,
            frozen_checkpoint,
            inventory_sha256=frozen_parent.get("checkpoint_inventory_logical_sha256"),
        )
    else:
        if approval is None:
            raise TrainingLaunchError(f"{stage.stage_id} requires a selected parent checkpoint")
        selected = approval.payload.get("selected_parent_checkpoint")
        if not isinstance(selected, Mapping):
            raise TrainingLaunchError(
                f"{stage.stage_id} approval has no selected parent checkpoint"
            )
        checkpoint = _checkpoint_from_inventory(
            receipt,
            selected,
            inventory_sha256=approval.payload.get("selected_parent_checkpoint_inventory_sha256"),
        )
    inventory = receipt.payload.get("checkpoint_inventory")
    if not isinstance(inventory, Mapping):
        raise TrainingLaunchError("parent receipt has no checkpoint inventory")
    inventory_sha256 = str(inventory.get("logical_sha256", ""))
    if approval is not None:
        claimed = approval.payload.get("parent_receipt_record_sha256")
        if claimed is not None and claimed != receipt.record_sha256:
            raise TrainingLaunchError("approval and parent receipt differ")
        claimed_parent_replicate = approval.payload.get("parent_replicate_id")
        if (
            claimed_parent_replicate is not None
            and claimed_parent_replicate != parent_replicate
        ):
            raise TrainingLaunchError("approval and parent execution identity differ")
        selected = approval.payload.get("selected_parent_checkpoint")
        if selected is not None and selected != checkpoint:
            raise TrainingLaunchError("approval and selected parent checkpoint differ")
        selected_inventory = approval.payload.get("selected_parent_checkpoint_inventory_sha256")
        if selected_inventory is not None and selected_inventory != inventory_sha256:
            raise TrainingLaunchError("approval and parent checkpoint inventory differ")

    entry_approval: TrainingRecord | None = None
    source_transition: dict[str, Any] | None = None
    if parent_source_git_sha != source_git_sha:
        if existing_manifest is None:
            if (
                approval is None
                or approval.payload.get("schema_version")
                not in {
                    SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION,
                    PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION,
                }
            ):
                raise TrainingLaunchError(
                    "cross-source parent requires a v2 transition approval"
                )
            entry_approval = approval
        else:
            entry_approval = _manifest_transition_approval(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                key=key,
                stage=stage,
                source_git_sha=source_git_sha,
                existing_manifest=existing_manifest,
            )
        if (
            entry_approval.payload.get("evidence_source_git_sha") != parent_source_git_sha
            or entry_approval.payload.get("parent_stage_id") != parent_stage_id
            or entry_approval.payload.get("parent_wave") != parent_wave
            or entry_approval.payload.get("parent_receipt_record_sha256") != receipt.record_sha256
            or entry_approval.payload.get("selected_parent_checkpoint") != checkpoint
            or entry_approval.payload.get("selected_parent_checkpoint_inventory_sha256")
            != inventory_sha256
        ):
            raise TrainingLaunchError("v2 transition approval differs from the selected parent")
        raw_transition = entry_approval.payload.get("source_transition")
        if not isinstance(raw_transition, Mapping):
            raise TrainingLaunchError("v2 transition approval has no source transition")
        source_transition = dict(raw_transition)
    elif existing_manifest is not None and "source_transition" in existing_manifest.payload:
        raise TrainingLaunchError("same-source parent cannot reuse a child source transition")
    return ParentBinding(
        stage_id=parent_stage_id,
        wave=parent_wave,
        replicate_id=parent_replicate,
        receipt=receipt,
        checkpoint=checkpoint,
        source_git_sha=parent_source_git_sha,
        run_manifest=parent_manifest,
        entry_approval=entry_approval,
        source_transition=source_transition,
    )


def _required_prior_wave(stage: StageSpec, wave_name: str) -> str | None:
    target = int(stage.wave(wave_name)["max_steps"])
    earlier = [
        (int(wave["max_steps"]), name)
        for name, wave in stage.waves.items()
        if int(wave["max_steps"]) < target
    ]
    return max(earlier)[1] if earlier else None


def _approval_record(
    *,
    repo_root: Path,
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    wave_name: str,
    source_git_sha: str,
    protocol: Mapping[str, Any],
) -> TrainingRecord | None:
    gate = str(stage.wave(wave_name)["approval"])
    prior_wave = _required_prior_wave(stage, wave_name)
    prior: TrainingRecord | None = None
    if prior_wave is not None:
        prior = store.load_wave_receipt(key, wave=prior_wave)
        if prior is None:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} requires its {prior_wave} receipt"
            )
    if gate == "initial":
        return None
    if gate == "base-level-held-out-baseline-receipt":
        if prior_wave is not None:
            raise TrainingLaunchError("base baseline gate cannot follow a training wave")
        try:
            return record_base_baseline_approval(
                repo_root=repo_root,
                store=store,
                key=key,
                stage=stage,
                wave_name=wave_name,
                source_git_sha=source_git_sha,
                protocol=protocol,
            )
        except (PromotionError, ValueError) as exc:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} base baseline gate failed: {exc}"
            ) from exc
    if gate == "rollout-health-receipt":
        if prior_wave != "smoke" or prior is None:
            raise TrainingLaunchError(
                "rollout-health gate requires the exact smoke receipt"
            )
        try:
            return record_rollout_health_approval(
                store=store,
                key=key,
                stage=stage,
                wave_name=wave_name,
                prior_wave=prior_wave,
                prior_receipt=prior,
                source_git_sha=source_git_sha,
                protocol=protocol,
            )
        except (PromotionError, ValueError) as exc:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} rollout-health gate failed: {exc}"
            ) from exc
    if gate == "parent-receipt-and-source-transition":
        if prior_wave is not None:
            raise TrainingLaunchError(
                "historical-parent transition cannot follow a child training wave"
            )
        approval = store.load_wave_approval(key, wave=wave_name)
        if approval is None:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} requires an immutable {gate} approval"
            )
        try:
            validate_parent_receipt_transition_approval(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                stage=stage,
                wave_name=wave_name,
                replicate_id=key.replicate_id,
                consumer_source_git_sha=source_git_sha,
                approval=approval,
            )
        except PromotionError as exc:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} parent transition failed: {exc}"
            ) from exc
        return approval
    approval = store.load_wave_approval(key, wave=wave_name)
    if approval is None:
        raise TrainingLaunchError(
            f"{stage.stage_id}/{wave_name} requires an immutable {gate} approval"
        )
    schema_version = approval.payload.get("schema_version")
    if schema_version == APPROVAL_SCHEMA_VERSION:
        if any(
            field in approval.payload for field in ("evidence_source_git_sha", "source_transition")
        ):
            raise TrainingLaunchError("same-source v1 approval contains source-transition fields")
        try:
            validate_same_source_wave_approval(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                stage=stage,
                wave_name=wave_name,
                replicate_id=key.replicate_id,
                source_git_sha=source_git_sha,
                approval=approval,
            )
        except PromotionError as exc:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} same-source approval "
                f"failed validation: {exc}"
            ) from exc
    elif schema_version == SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION:
        try:
            validate_source_transition_approval(
                repo_root=repo_root,
                protocol=protocol,
                store=store,
                stage=stage,
                wave_name=wave_name,
                replicate_id=key.replicate_id,
                consumer_source_git_sha=source_git_sha,
                approval=approval,
            )
        except PromotionError as exc:
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} source-transition approval failed validation: {exc}"
            ) from exc
    else:
        raise TrainingLaunchError(f"{stage.stage_id}/{wave_name} approval has a foreign schema")
    expected = {
        "decision": "approve",
        "approval_gate": gate,
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
    }
    for field, value in expected.items():
        if approval.payload.get(field) != value:
            raise TrainingLaunchError(f"{stage.stage_id}/{wave_name} approval has wrong {field}")
    if gate == "clean-smoke-receipt":
        if prior_wave is None or prior is None:
            raise TrainingLaunchError("clean-smoke gate has no prior wave receipt")
        if (
            approval.payload.get("prior_wave") != prior_wave
            or approval.payload.get("prior_receipt_record_sha256") != prior.record_sha256
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} approval is not bound to its {prior_wave} receipt"
            )
    elif gate == "promotion-receipt-and-explicit-human-approval":
        if prior_wave is None or prior is None:
            raise TrainingLaunchError("promotion gate has no prior wave receipt")
        evidence = approval.payload.get("evaluation")
        if not isinstance(evidence, Mapping):
            raise TrainingLaunchError("promotion approval has no evaluation evidence")
        expected_evidence = {
            "stage_id": stage.stage_id,
            "wave": prior_wave,
            "panel": "inkling-promotion",
            "training_wave_receipt_record_sha256": prior.record_sha256,
        }
        if any(evidence.get(field) != value for field, value in expected_evidence.items()):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} promotion is not bound "
                f"to its {prior_wave} evaluation"
            )
        evaluated_checkpoint = evidence.get("checkpoint")
        receipt_checkpoint = prior.payload.get("checkpoint")
        checkpoint_fields = (
            "name",
            "batch",
            "epoch",
            "final",
            "state_path",
            "sampler_path",
        )
        if (
            not isinstance(evaluated_checkpoint, Mapping)
            or not isinstance(receipt_checkpoint, Mapping)
            or any(
                evaluated_checkpoint.get(field) != receipt_checkpoint.get(field)
                for field in checkpoint_fields
            )
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} promotion checkpoint differs "
                f"from its {prior_wave} receipt"
            )
    elif gate == "current-level-held-out-promotion-receipt":
        if (
            prior_wave is None
            or prior is None
            or stage.current_level not in LEVEL_PROGRESS_PANELS
        ):
            raise TrainingLaunchError("current-level promotion has no prior receipt")
        evidence = approval.payload.get("evaluation")
        expected_evidence = {
            "stage_id": stage.stage_id,
            "wave": prior_wave,
            "panel": LEVEL_PROGRESS_PANELS[stage.current_level],
            "training_wave_receipt_record_sha256": prior.record_sha256,
        }
        if not isinstance(evidence, Mapping) or any(
            evidence.get(field) != value
            for field, value in expected_evidence.items()
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} is not bound to its "
                f"{stage.current_level} held-out report"
            )
        checkpoint_fields = (
            "name",
            "batch",
            "epoch",
            "final",
            "state_path",
            "sampler_path",
        )
        evaluated_checkpoint = evidence.get("checkpoint")
        receipt_checkpoint = prior.payload.get("checkpoint")
        if (
            approval.payload.get("prior_wave") != prior_wave
            or approval.payload.get("prior_receipt_record_sha256")
            != prior.record_sha256
            or not isinstance(evaluated_checkpoint, Mapping)
            or not isinstance(receipt_checkpoint, Mapping)
            or any(
                evaluated_checkpoint.get(field) != receipt_checkpoint.get(field)
                for field in checkpoint_fields
            )
            or not _SHA256.fullmatch(
                str(evidence.get("report_record_sha256", ""))
            )
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} held-out evidence differs "
                f"from its {prior_wave} checkpoint"
            )
    elif gate == "prior-level-held-out-promotion-receipt":
        if stage.current_level not in LEVELS[1:]:
            raise TrainingLaunchError("prior-level promotion has no prior level")
        parent_stage_id, parent_wave = stage.parent.split(":", 1)
        parent_key = StageKey(key.study_id, parent_stage_id, key.replicate_id)
        parent_receipt = store.load_wave_receipt(parent_key, wave=parent_wave)
        prior_level = LEVELS[LEVELS.index(stage.current_level) - 1]
        evidence = approval.payload.get("evaluation")
        expected_evidence = {
            "stage_id": parent_stage_id,
            "wave": parent_wave,
            "panel": LEVEL_PROGRESS_PANELS[prior_level],
            "training_wave_receipt_record_sha256": (
                parent_receipt.record_sha256 if parent_receipt is not None else None
            ),
        }
        if parent_receipt is None or not isinstance(evidence, Mapping) or any(
            evidence.get(field) != value
            for field, value in expected_evidence.items()
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} is not bound to its "
                f"{prior_level} parent held-out report"
            )
        checkpoint_fields = (
            "name",
            "batch",
            "epoch",
            "final",
            "state_path",
            "sampler_path",
        )
        evaluated_checkpoint = evidence.get("checkpoint")
        receipt_checkpoint = parent_receipt.payload.get("checkpoint")
        if (
            approval.payload.get("parent_stage_id") != parent_stage_id
            or approval.payload.get("parent_wave") != parent_wave
            or approval.payload.get("parent_receipt_record_sha256")
            != parent_receipt.record_sha256
            or approval.payload.get("selected_parent_checkpoint")
            != evaluated_checkpoint
            or not isinstance(evaluated_checkpoint, Mapping)
            or not isinstance(receipt_checkpoint, Mapping)
            or any(
                evaluated_checkpoint.get(field) != receipt_checkpoint.get(field)
                for field in checkpoint_fields
            )
            or not _SHA256.fullmatch(
                str(evidence.get("report_record_sha256", ""))
            )
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} parent held-out evidence differs "
                f"from its {parent_stage_id}/{parent_wave} checkpoint"
            )
    return approval


def _manifest_payload(
    *,
    protocol: Mapping[str, Any],
    source_git_sha: str,
    stage: StageSpec,
    preflight: Mapping[str, Any],
    tracking: Mapping[str, Any],
    parent: ParentBinding | None,
) -> dict[str, Any]:
    payload = {
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "protocol_file_sha256": preflight["protocol_file_sha256"],
        "contract_version": protocol["contract_version"],
        "prompt_assets": preflight["prompt_assets"],
        "dataset": preflight["dataset"],
        "runtime": preflight["runtime"],
        "sandbox": preflight["sandbox"],
        "stage": {
            "stage_id": stage.stage_id,
            "kind": stage.kind,
            "model_key": stage.model_key,
            "recipe_key": stage.recipe_key,
            "hypotheses": list(stage.hypotheses),
            "parent_policy": stage.parent,
            "levels": list(stage.levels),
            "current_level": stage.current_level,
            "replay_levels": list(stage.replay_levels),
            "waves": stage.waves,
        },
        "model": preflight["model"],
        "recipe": preflight["recipe"],
        "schedule": preflight["schedule"],
        "tracking": dict(tracking),
        "parent_receipt": (
            {
                "relative_path": str(parent.receipt.relative_path),
                "stage_id": parent.stage_id,
                "wave": parent.wave,
                "replicate_id": parent.replicate_id,
                "record_sha256": parent.receipt.record_sha256,
                "checkpoint": parent.checkpoint,
                "checkpoint_inventory_logical_sha256": parent.receipt.payload[
                    "checkpoint_inventory"
                ]["logical_sha256"],
            }
            if parent is not None
            else None
        ),
    }
    if parent is not None and parent.source_transition is not None:
        if parent.entry_approval is None:
            raise TrainingLaunchError("cross-source parent has no v2 entry approval")
        payload["source_transition"] = _child_source_transition_binding(parent.entry_approval)
    return payload


def _candidate_recorder(
    store: TrainingStore,
    key: StageKey,
    *,
    invocation_id: str,
) -> Callable[[Mapping[str, object]], None]:
    def record(value: Mapping[str, object]) -> None:
        payload = dict(value)
        try:
            step = int(payload["step"])
            attempt = int(payload["attempt"])
            task = payload["task"]
            if not isinstance(task, Mapping):
                raise TypeError("task is not an object")
            task_id = str(task["opaque_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise TrainingLaunchError("candidate record has no immutable key") from exc
        sample_payload = dict(payload)
        evaluation = sample_payload.pop("evaluation", None)
        if not isinstance(evaluation, Mapping):
            raise TrainingLaunchError("candidate record has no evaluation")
        sample = store.load_candidate_sample(
            key,
            invocation_id=invocation_id,
            step=step,
            task_id=task_id,
            attempt=attempt,
        )
        if sample is None or canonical_sha256(sample_payload) != sample.payload_sha256:
            raise TrainingLaunchError(
                "candidate evaluation does not match its persisted paid sample"
            )
        store.write_candidate(
            key,
            invocation_id=invocation_id,
            step=step,
            task_id=task_id,
            attempt=attempt,
            payload={
                "sample_record": {
                    "relative_path": str(sample.relative_path),
                    "payload_sha256": sample.payload_sha256,
                    "record_sha256": sample.record_sha256,
                },
                "evaluation": dict(evaluation),
            },
        )

    return record


def _candidate_sample_recorder(
    store: TrainingStore,
    key: StageKey,
    *,
    invocation_id: str,
) -> Callable[[Mapping[str, object]], None]:
    def record(value: Mapping[str, object]) -> None:
        payload = dict(value)
        try:
            step = int(payload["step"])
            attempt = int(payload["attempt"])
            task = payload["task"]
            if not isinstance(task, Mapping):
                raise TypeError("task is not an object")
            task_id = str(task["opaque_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise TrainingLaunchError("candidate sample has no immutable key") from exc
        store.write_candidate_sample(
            key,
            invocation_id=invocation_id,
            step=step,
            task_id=task_id,
            attempt=attempt,
            payload=payload,
        )

    return record


def _resolved_launch_binding(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    stage: StageSpec,
    wave_name: str,
    store: TrainingStore,
    key: StageKey,
    parent: ParentBinding | None,
    resume_batch: int | None,
    resume_checkpoint: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the complete scientific policy consumed by the Cookbook config."""

    model = protocol["models"][stage.model_key]
    recipe = protocol["recipes"][stage.recipe_key]
    max_steps = int(stage.wave(wave_name)["max_steps"])
    checkpoint = parent.checkpoint if parent is not None else None
    manifest = store.load_manifest(key)
    if manifest is None:
        raise TrainingLaunchError("resolved launch cannot precede its run manifest")
    common: dict[str, Any] = {
        "schema_version": "pixcell-resolved-training-launch-v1",
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "kind": stage.kind,
        "model_name": model["model"],
        "renderer_name": model["renderer"],
        "renderer_effort": model.get("effort"),
        "thinking": bool(model["thinking"]),
        "context_tokens": int(model["context_tokens"]),
        "max_image_long_edge": int(model["max_image_long_edge"]),
        "lora_rank": int(model["lora_rank"]),
        "learning_rate": float(recipe["learning_rate"]),
        "max_steps": max_steps,
        "dataset_root": str((repo_root / "dataset").relative_to(repo_root)),
        "dataset_configuration": protocol["dataset"]["configuration"],
        "dataset_revision": protocol["dataset"]["revision"],
        "dataset_logical_release_sha256": protocol["dataset"]["logical_release_sha256"],
        "schedule_seed": SCHEDULE_SEED,
        "tinker_log_relative_path": str(
            store.tinker_log_path(key).relative_to(store.external_root)
        ),
        "initial_checkpoint": checkpoint,
        "resume_batch": resume_batch,
        "resume_checkpoint": (
            dict(resume_checkpoint) if resume_checkpoint is not None else None
        ),
        "wandb_run_id": deterministic_wandb_run_id(
            source_git_sha=str(manifest.payload["source_git_sha"]),
            protocol_logical_sha256=str(protocol["logical_sha256"]),
            key=key,
        ),
    }
    if stage.kind == "sft":
        common["dataset"] = {
            "split": "train",
            "levels": list(stage.levels),
            "batch_size": int(recipe["batch_size"]),
            "max_sequence_tokens": int(recipe["max_sequence_tokens"]),
            "include_validation": bool(recipe["automatic_nll_validation"]),
            "loss_mass": recipe["loss_mass"],
            "target": recipe["target"],
        }
        common["optimizer"] = {
            "name": "adam",
            "beta1": float(recipe["adam_beta1"]),
            "beta2": float(recipe["adam_beta2"]),
            "epsilon": float(recipe["adam_epsilon"]),
            "lr_schedule": recipe["lr_schedule"],
            "num_epochs": int(recipe["effective_passes"]),
            "optimizer_reset_each_stage": bool(recipe["optimizer_reset_each_stage"]),
        }
        common["checkpointing"] = {
            "save_every": max(
                1,
                round(max_steps * float(recipe["checkpoint_fraction"])),
            ),
            "rolling_save_every": int(recipe["rolling_save_every_steps"]),
            "periodic_ttl_seconds": recipe["checkpoint_ttl_seconds"],
        }
        common["automatic_evaluation"] = {
            "eval_every": 0,
            "automatic_nll_validation": False,
        }
    else:
        common["dataset"] = {
            "split": "train",
            "current_level": stage.current_level,
            "replay_levels": list(stage.replay_levels),
            "groups_per_batch": int(recipe["groups_per_batch"]),
            "group_size": int(recipe["group_size"]),
            "replay_fraction": float(recipe["replay_fraction"]),
            "require_prefix_replay": stage.model_key == "qwen",
            "validation_canaries": int(recipe["automatic_validation_rows"]),
        }
        common["sampling"] = {
            "max_output_tokens": int(model["max_output_tokens"]),
            "temperature": float(recipe["temperature"]),
            # The pinned Cookbook constructs SamplingParams without top_p;
            # Tinker's pinned default is 1.0 and preflight verifies that fact.
            "top_p": float(recipe["top_p"]),
        }
        common["optimizer"] = {
            "loss_fn": recipe["loss_fn"],
            "kl_coefficient": float(recipe["kl_coefficient"]),
            "remove_constant_reward_groups": bool(recipe["remove_constant_reward_groups"]),
            "reward": recipe["reward"],
        }
        common["checkpointing"] = {
            "policy": recipe["checkpoint_policy"],
            "save_every": max_steps,
            "rolling_save_every": int(recipe["rolling_save_every_steps"]),
            "periodic_ttl_seconds": recipe["checkpoint_ttl_seconds"],
        }
        common["automatic_evaluation"] = {
            "eval_every": 0,
            "validation_rows": 0,
        }
        common["rollout"] = {
            "error_policy": recipe["rollout_error_policy"],
            "json_export": bool(recipe["rollout_json_export"]),
            "groups_to_log": 0,
        }
    if stage.stage_id.startswith(("qwen-base-rl-", "qwen-l0-rl-")):
        gate = str(stage.wave(wave_name)["approval"])
        gate_record = (
            store.load_base_baseline_approval(key, wave=wave_name)
            if gate == "base-level-held-out-baseline-receipt"
            else (
                store.load_rollout_health_approval(key, wave=wave_name)
                if gate == "rollout-health-receipt"
                else (
                    store.load_wave_approval(key, wave=wave_name)
                    if gate
                    in {
                        "current-level-held-out-promotion-receipt",
                        "parent-receipt-and-source-transition",
                        "prior-level-held-out-promotion-receipt",
                        "prior-and-current-level-held-out-transition-receipt",
                    }
                    else None
                )
            )
        )
        if gate != "initial":
            if gate_record is None:
                raise TrainingLaunchError(
                    f"{stage.stage_id}/{wave_name} has no immutable gate evidence"
                )
            common["wave_gate_evidence"] = {
                "approval_gate": gate,
                "relative_path": str(gate_record.relative_path),
                "payload_sha256": gate_record.payload_sha256,
                "record_sha256": gate_record.record_sha256,
            }
    common["logical_sha256"] = canonical_sha256(common)
    return common


def _invocation_payload(
    *,
    protocol: Mapping[str, Any],
    stage: StageSpec,
    wave_name: str,
    source_git_sha: str,
    invocation_id: str,
    manifest: TrainingRecord,
    preflight: Mapping[str, Any],
    tracking: Mapping[str, Any],
    resume_batch: int | None,
    resolved_launch: Mapping[str, Any],
    parent: ParentBinding | None,
    resume_checkpoint: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the immutable invocation record shared by launch and replay."""

    return {
        "invocation_id": invocation_id,
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "source_git_sha": source_git_sha,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "run_manifest_record_sha256": manifest.record_sha256,
        "preflight_sha256": preflight["preflight_sha256"],
        "wandb_run_id": tracking["run_id"],
        "resume_batch": resume_batch,
        "resume_checkpoint": (
            dict(resume_checkpoint) if resume_checkpoint is not None else None
        ),
        "resolved_launch": dict(resolved_launch),
        "resolved_launch_sha256": resolved_launch["logical_sha256"],
        "policy": {
            "model": protocol["models"][stage.model_key]["model"],
            "renderer": protocol["models"][stage.model_key]["renderer"],
            "effort": protocol["models"][stage.model_key].get("effort"),
            "max_output_tokens": protocol["models"][stage.model_key]["max_output_tokens"],
            "temperature": protocol["recipes"][stage.recipe_key].get("temperature"),
            "top_p": protocol["recipes"][stage.recipe_key].get("top_p"),
            "reward": protocol["recipes"][stage.recipe_key].get("reward"),
            "group_size": protocol["recipes"][stage.recipe_key].get("group_size"),
            "groups_per_batch": protocol["recipes"][stage.recipe_key].get("groups_per_batch"),
        },
        "initial_checkpoint": parent.checkpoint if parent is not None else None,
    }


def build_tinker_config(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    stage: StageSpec,
    wave_name: str,
    store: TrainingStore,
    key: StageKey,
    parent: ParentBinding | None,
    invocation: TrainingRecord | None = None,
) -> SFTConfig | RLConfig:
    """Resolve one sealed Cookbook config without creating a service client."""

    model = protocol["models"][stage.model_key]
    recipe = protocol["recipes"][stage.recipe_key]
    max_steps = int(stage.wave(wave_name)["max_steps"])
    checkpoint = parent.checkpoint if parent is not None else None
    load_checkpoint_path = str(checkpoint["state_path"]) if checkpoint is not None else None
    log_path = str(store.tinker_log_path(key))
    manifest = store.load_manifest(key)
    if manifest is None:
        raise TrainingLaunchError("Tinker config cannot precede its run manifest")
    resolved_launch = _resolved_launch_binding(
        repo_root=repo_root,
        protocol=protocol,
        stage=stage,
        wave_name=wave_name,
        store=store,
        key=key,
        parent=parent,
        resume_batch=(
            int(invocation.payload["resume_batch"])
            if invocation is not None and invocation.payload.get("resume_batch") is not None
            else None
        ),
        resume_checkpoint=(
            invocation.payload.get("resume_checkpoint")
            if invocation is not None
            else None
        ),
    )
    if invocation is not None and invocation.payload.get("resolved_launch") != resolved_launch:
        raise TrainingLaunchError("immutable invocation differs from the resolved Tinker launch")
    tracking = _tracking_binding(
        protocol=protocol,
        source_git_sha=str(manifest.payload["source_git_sha"]),
        key=key,
        stage=stage,
        store=store,
    )
    common = {
        "log_path": log_path,
        "model_name": model["model"],
        "recipe_name": f"pixcell_{STUDY_ID}_{stage.stage_id}",
        "renderer_name": model["renderer"],
        "load_checkpoint_path": load_checkpoint_path,
        "learning_rate": float(recipe["learning_rate"]),
        "lora_rank": int(model["lora_rank"]),
        "wandb_project": tracking["project"],
        "wandb_name": tracking["name"],
        "max_steps": max_steps,
    }
    if stage.kind == "sft":
        save_every = max(
            1,
            round(max_steps * float(recipe["checkpoint_fraction"])),
        )
        return SFTConfig(
            **common,
            dataset_builder=TrackASupervisedDatasetBuilder(
                dataset_root=str(repo_root / "dataset"),
                model_name=model["model"],
                renderer_name=model["renderer"],
                batch_size=int(recipe["batch_size"]),
                max_length=int(recipe["max_sequence_tokens"]),
                max_image=int(model["max_image_long_edge"]),
                levels=",".join(stage.levels),
                include_validation=bool(recipe["automatic_nll_validation"]),
                schedule_seed=SCHEDULE_SEED,
            ),
            lr_schedule=str(recipe["lr_schedule"]),
            num_epochs=int(recipe["effective_passes"]),
            adam_beta1=float(recipe["adam_beta1"]),
            adam_beta2=float(recipe["adam_beta2"]),
            adam_eps=float(recipe["adam_epsilon"]),
            save_every=save_every,
            eval_every=0,
            rolling_save_every=int(recipe["rolling_save_every_steps"]),
            ttl_seconds=recipe["checkpoint_ttl_seconds"],
        )
    return RLConfig(
        **common,
        dataset_builder=TrackARLDatasetBuilder(
            dataset_root=str(repo_root / "dataset"),
            batch_size=int(recipe["groups_per_batch"]),
            group_size=int(recipe["group_size"]),
            model_name=model["model"],
            renderer_name=model["renderer"],
            model_effort=model.get("effort"),
            max_image=int(model["max_image_long_edge"]),
            current_level=str(stage.current_level),
            replay_levels=",".join(stage.replay_levels),
            validation_canaries=int(recipe["automatic_validation_rows"]),
            attempt_recorder=(
                _candidate_recorder(
                    store,
                    key,
                    invocation_id=str(invocation.payload["invocation_id"]),
                )
                if invocation is not None
                else None
            ),
            sample_recorder=(
                _candidate_sample_recorder(
                    store,
                    key,
                    invocation_id=str(invocation.payload["invocation_id"]),
                )
                if invocation is not None
                else None
            ),
            reward_policy="raw_iou",
            require_prefix_replay=stage.model_key == "qwen",
            schedule_seed=SCHEDULE_SEED,
            attempt_metadata=(
                {
                    "invocation_id": invocation.payload["invocation_id"],
                    "run_manifest_record_sha256": invocation.payload["run_manifest_record_sha256"],
                    "source_git_sha": invocation.payload["source_git_sha"],
                    "protocol_logical_sha256": invocation.payload["protocol_logical_sha256"],
                    "policy": invocation.payload["policy"],
                    "initial_checkpoint": invocation.payload["initial_checkpoint"],
                }
                if invocation is not None
                else {}
            ),
        ),
        max_tokens=int(model["max_output_tokens"]),
        temperature=float(recipe["temperature"]),
        eval_every=0,
        save_every=max_steps,
        rolling_save_every=int(recipe["rolling_save_every_steps"]),
        loss_fn=str(recipe["loss_fn"]),
        remove_constant_reward_groups=bool(recipe["remove_constant_reward_groups"]),
        rollout_error_tolerance=(
            False
            if recipe["rollout_error_policy"] == "fail_fast"
            else recipe["rollout_error_policy"]
        ),
        kl_penalty_coef=float(recipe["kl_coefficient"]),
        num_groups_to_log=0,
        rollout_json_export=bool(recipe["rollout_json_export"]),
        ttl_seconds=recipe["checkpoint_ttl_seconds"],
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _wave_artifact_snapshot(
    *,
    log_path: Path,
    wave_name: str,
    recorded: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Freeze or verify the append-only log prefix belonging to one wave.

    Cookbook deliberately reuses ``log_path`` across resumable waves.  A
    receipt therefore cannot hash the live files directly: later waves append
    to them.  Each receipt instead binds create-only copies under its own wave
    directory.  During replay, the copies must still match their receipt and
    the append-only live logs must retain the exact frozen prefix.
    """

    relative_root = Path("waves") / wave_name / "artifacts"
    snapshot_root = log_path.parent / relative_root
    expected_names = ("checkpoints.jsonl", "metrics.jsonl", "hparams.json")
    stage_root = log_path.parent.resolve(strict=True)
    resolved_snapshot_root = snapshot_root.resolve(strict=False)
    if (
        resolved_snapshot_root == stage_root
        or not resolved_snapshot_root.is_relative_to(stage_root)
    ):
        raise TrainingLaunchError("completed wave artifact snapshot escapes its stage")

    if recorded is None:
        source_bytes: dict[str, bytes] = {}
        for name in expected_names:
            source = log_path / name
            if source.is_symlink():
                raise TrainingLaunchError("live training artifact cannot be a symlink")
            if source.is_file():
                source_bytes[name] = source.read_bytes()
        if not {"checkpoints.jsonl", "metrics.jsonl"}.issubset(source_bytes):
            raise TrainingLaunchError(
                "training returned without checkpoint and metric artifacts"
            )
        snapshot_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, value in source_bytes.items():
            destination = snapshot_root / name
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(destination, flags, 0o600)
            except FileExistsError:
                if destination.is_symlink() or destination.read_bytes() != value:
                    raise TrainingLaunchError(
                        f"{wave_name} immutable artifact snapshot already differs"
                    )
            else:
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(value)
                        stream.flush()
                        os.fsync(stream.fileno())
                except BaseException:
                    destination.unlink(missing_ok=True)
                    raise
        snapshot = {
            "schema_version": _WAVE_ARTIFACT_SNAPSHOT_SCHEMA_VERSION,
            "relative_root": relative_root.as_posix(),
            "files": {
                name: {
                    "byte_count": len(value),
                    "sha256": _sha256_bytes(value),
                }
                for name, value in sorted(source_bytes.items())
            },
        }
    else:
        snapshot = dict(recorded)

    if (
        set(snapshot) != {"schema_version", "relative_root", "files"}
        or snapshot.get("schema_version") != _WAVE_ARTIFACT_SNAPSHOT_SCHEMA_VERSION
        or snapshot.get("relative_root") != relative_root.as_posix()
        or not isinstance(snapshot.get("files"), Mapping)
    ):
        raise TrainingLaunchError("completed wave artifact snapshot is malformed")
    files = snapshot["files"]
    if (
        not {"checkpoints.jsonl", "metrics.jsonl"}.issubset(files)
        or not set(files).issubset(expected_names)
    ):
        raise TrainingLaunchError("completed wave artifact snapshot files differ")

    verified: dict[str, bytes] = {}
    for name, metadata in files.items():
        if (
            not isinstance(name, str)
            or not isinstance(metadata, Mapping)
            or set(metadata) != {"byte_count", "sha256"}
            or isinstance(metadata.get("byte_count"), bool)
            or not isinstance(metadata.get("byte_count"), int)
            or int(metadata["byte_count"]) < 0
            or not _SHA256.fullmatch(str(metadata.get("sha256", "")))
        ):
            raise TrainingLaunchError("completed wave artifact snapshot entry is malformed")
        snapshot_path = snapshot_root / name
        if not snapshot_path.is_file() or snapshot_path.is_symlink():
            raise TrainingLaunchError("completed wave artifact snapshot is missing")
        value = snapshot_path.read_bytes()
        if (
            len(value) != int(metadata["byte_count"])
            or _sha256_bytes(value) != metadata["sha256"]
        ):
            raise TrainingLaunchError("completed wave artifact snapshot digest differs")
        if name in {"checkpoints.jsonl", "metrics.jsonl"}:
            live_path = log_path / name
            if not live_path.is_file():
                if name == "checkpoints.jsonl":
                    raise TrainingLaunchError(
                        "completed wave is without a resumable checkpoint artifact"
                    )
                raise TrainingLaunchError("completed wave live artifact is missing")
            with live_path.open("rb") as stream:
                live_prefix = stream.read(len(value))
            if live_prefix != value:
                raise TrainingLaunchError(
                    "completed wave canonical training artifacts no longer have "
                    "their frozen prefix"
                )
        verified[name] = value
    return snapshot, verified


def _checkpoint_records_from_bytes(value: bytes) -> list[Any]:
    records: list[Any] = []
    try:
        for raw_line in value.decode("utf-8").splitlines():
            if raw_line.strip():
                item = json.loads(raw_line)
                if not isinstance(item, dict):
                    raise ValueError("checkpoint row is not an object")
                records.append(checkpoint_utils.CheckpointRecord.from_dict(item))
    except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise TrainingLaunchError("checkpoint snapshot is not valid JSONL") from exc
    return records


def _metrics_from_bytes(value: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        for raw_line in value.decode("utf-8").splitlines():
            if raw_line.strip():
                item = json.loads(raw_line)
                if not isinstance(item, dict):
                    raise ValueError("metric row is not an object")
                records.append(item)
    except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise TrainingLaunchError("metric snapshot is not valid JSONL") from exc
    return records


def _checkpoint_receipt(
    *,
    stage: StageSpec,
    wave_name: str,
    log_path: Path,
    manifest: TrainingRecord,
    preflight: Mapping[str, Any],
    invocation: TrainingRecord,
    tracking: TrainingRecord | None,
    artifact_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot, snapshot_files = _wave_artifact_snapshot(
        log_path=log_path,
        wave_name=wave_name,
        recorded=artifact_snapshot,
    )
    records = _checkpoint_records_from_bytes(snapshot_files["checkpoints.jsonl"])
    complete = [
        item for item in records if item.state_path is not None and item.sampler_path is not None
    ]
    if not complete:
        raise TrainingLaunchError("training returned without a resumable checkpoint")
    checkpoint = complete[-1]
    target_steps = int(stage.wave(wave_name)["max_steps"])
    if stage.kind == "rl":
        unique_name = f"{target_steps:06d}"
        matching = [
            item for item in complete if item.name == unique_name and item.batch == target_steps
        ]
        if len(matching) != 1:
            raise TrainingLaunchError(
                f"RL wave has {len(matching)} unique {unique_name} checkpoints"
            )
        checkpoint = matching[0]
    if stage.kind == "sft":
        if checkpoint.name != "final" or checkpoint.epoch != 1:
            raise TrainingLaunchError("SFT terminal checkpoint is not the completed epoch")
    if not _TINKER_PATH.fullmatch(str(checkpoint.state_path)) or not _TINKER_PATH.fullmatch(
        str(checkpoint.sampler_path)
    ):
        raise TrainingLaunchError("checkpoint paths are not Tinker URIs")
    recipe = preflight["recipe"]
    save_every = (
        max(
            1,
            round(target_steps * float(recipe["checkpoint_fraction"])),
        )
        if stage.kind == "sft"
        else target_steps
    )
    expected_periodic_names = (
        [f"{step:06d}" for step in range(save_every, target_steps, save_every)]
        if stage.kind == "sft"
        else []
    )
    periodic_by_name: dict[str, Any] = {}
    for item in complete:
        if item.name not in expected_periodic_names:
            continue
        if item.name in periodic_by_name:
            raise TrainingLaunchError(f"checkpoint inventory repeats {item.name}")
        periodic_by_name[item.name] = item
    if set(periodic_by_name) != set(expected_periodic_names):
        raise TrainingLaunchError("periodic checkpoint inventory differs from the sealed cadence")

    def checkpoint_entry(item: Any, *, role: str) -> dict[str, Any]:
        if not _TINKER_PATH.fullmatch(str(item.state_path)) or not _TINKER_PATH.fullmatch(
            str(item.sampler_path)
        ):
            raise TrainingLaunchError("checkpoint inventory contains invalid URIs")
        progress = 1.0 if role == "terminal" else int(item.name) / target_steps
        return {
            "name": str(item.name),
            "batch": item.batch,
            "epoch": item.epoch,
            "final": role == "terminal",
            "state_path": str(item.state_path),
            "sampler_path": str(item.sampler_path),
            "role": role,
            "training_progress_fraction": progress,
        }

    checkpoint_entries = [
        checkpoint_entry(periodic_by_name[name], role="periodic")
        for name in expected_periodic_names
    ]
    terminal_entry = checkpoint_entry(checkpoint, role="terminal")
    checkpoint_entries.append(terminal_entry)
    local_artifacts = {
        name: str(metadata["sha256"])
        for name, metadata in snapshot["files"].items()
    }
    candidate_root = log_path.parent / "candidates" / str(invocation.payload["invocation_id"])
    candidate_files = (
        sorted(candidate_root.rglob("evaluation.json")) if candidate_root.is_dir() else []
    )
    sample_files = sorted(candidate_root.rglob("sample.json")) if candidate_root.is_dir() else []
    candidate_inventory = [
        {
            "path": str(path.relative_to(log_path.parent)),
            "sha256": file_sha256(path),
        }
        for path in candidate_files
    ]
    if stage.kind == "rl":
        start_batch = invocation.payload.get("resume_batch")
        start = int(start_batch) if start_batch is not None else 0
        policy = invocation.payload["policy"]
        expected_candidates = (
            (target_steps - start) * int(policy["groups_per_batch"]) * int(policy["group_size"])
        )
        if len(candidate_inventory) != expected_candidates:
            raise TrainingLaunchError(
                "candidate inventory does not cover every sampled rollout: "
                f"{len(candidate_inventory)} != {expected_candidates}"
            )
        if len(sample_files) != expected_candidates:
            raise TrainingLaunchError(
                "sample inventory does not cover every sampled rollout: "
                f"{len(sample_files)} != {expected_candidates}"
            )
    else:
        expected_candidates = 0
    metrics = _metrics_from_bytes(snapshot_files["metrics.jsonl"])
    last_metrics = metrics[-1] if metrics else None
    if last_metrics is None or last_metrics.get("step") != target_steps - 1:
        raise TrainingLaunchError("metrics do not reach the exact wave ceiling")
    required_metric = "optim/entropy" if stage.kind == "rl" else "train_mean_nll"
    metric = last_metrics.get(required_metric)
    if (
        isinstance(metric, bool)
        or not isinstance(metric, (int, float))
        or not math.isfinite(float(metric))
    ):
        raise TrainingLaunchError(
            f"final metrics do not prove an optimizer update ({required_metric})"
        )
    return {
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "max_steps": target_steps,
        "run_manifest_record_sha256": manifest.record_sha256,
        "invocation_record_sha256": invocation.record_sha256,
        "invocation_id": invocation.payload["invocation_id"],
        "invocation_tracking_record_sha256": (
            tracking.record_sha256 if tracking is not None else None
        ),
        "preflight_sha256": preflight["preflight_sha256"],
        "checkpoint": {
            key: terminal_entry[key]
            for key in (
                "name",
                "batch",
                "epoch",
                "final",
                "state_path",
                "sampler_path",
            )
        },
        "checkpoint_inventory": {
            "count": len(checkpoint_entries),
            "entries": checkpoint_entries,
            "logical_sha256": canonical_sha256(checkpoint_entries),
        },
        "artifact_snapshot": snapshot,
        "local_artifact_sha256": local_artifacts,
        "candidate_inventory": {
            "count": len(candidate_inventory),
            "expected_count": expected_candidates,
            "logical_sha256": canonical_sha256(candidate_inventory),
        },
        "sample_inventory": {
            "count": len(sample_files),
            "expected_count": expected_candidates,
            "logical_sha256": canonical_sha256(
                [
                    {
                        "path": str(path.relative_to(log_path.parent)),
                        "sha256": file_sha256(path),
                    }
                    for path in sample_files
                ]
            ),
        },
        "final_training_metric": {
            "step": last_metrics["step"],
            required_metric: float(metric),
        },
    }


def _validate_completed_wave_receipt(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    wave_name: str,
    manifest: TrainingRecord,
    preflight: Mapping[str, Any],
    parent: ParentBinding | None,
    receipt: TrainingRecord,
) -> None:
    """Fully validate an immutable completed-wave claim before replaying it."""

    payload = receipt.payload
    required_fields = {
        "stage_id",
        "wave",
        "max_steps",
        "run_manifest_record_sha256",
        "invocation_record_sha256",
        "invocation_id",
        "invocation_tracking_record_sha256",
        "preflight_sha256",
        "checkpoint",
        "checkpoint_inventory",
        "artifact_snapshot",
        "local_artifact_sha256",
        "candidate_inventory",
        "sample_inventory",
        "final_training_metric",
    }
    if set(payload) != required_fields:
        raise TrainingLaunchError("completed wave receipt fields differ from the canonical schema")
    target_steps = int(stage.wave(wave_name)["max_steps"])
    if (
        payload.get("stage_id") != stage.stage_id
        or payload.get("wave") != wave_name
        or payload.get("max_steps") != target_steps
        or payload.get("run_manifest_record_sha256") != manifest.record_sha256
        or payload.get("preflight_sha256") != preflight.get("preflight_sha256")
    ):
        raise TrainingLaunchError("completed wave receipt identity or preflight differs")

    invocation_id = payload.get("invocation_id")
    if not isinstance(invocation_id, str):
        raise TrainingLaunchError("completed wave receipt has no invocation ID")
    try:
        invocation = store.load_invocation(key, invocation_id=invocation_id)
    except ValueError as exc:
        raise TrainingLaunchError("completed wave receipt has an invalid invocation ID") from exc
    if invocation is None or payload.get("invocation_record_sha256") != invocation.record_sha256:
        raise TrainingLaunchError("completed wave receipt invocation is missing or differs")
    resume_batch = invocation.payload.get("resume_batch")
    if resume_batch is not None and (
        isinstance(resume_batch, bool)
        or not isinstance(resume_batch, int)
        or not 0 <= resume_batch <= target_steps
    ):
        raise TrainingLaunchError("completed wave invocation has an invalid resume batch")
    resume_checkpoint = invocation.payload.get("resume_checkpoint")
    if (resume_batch is None) != (resume_checkpoint is None):
        raise TrainingLaunchError(
            "completed wave invocation has an incomplete optimizer-resume binding"
        )
    if resume_checkpoint is not None and not isinstance(resume_checkpoint, Mapping):
        raise TrainingLaunchError(
            "completed wave invocation optimizer-resume checkpoint is malformed"
        )
    resolved_launch = _resolved_launch_binding(
        repo_root=repo_root,
        protocol=protocol,
        stage=stage,
        wave_name=wave_name,
        store=store,
        key=key,
        parent=parent,
        resume_batch=resume_batch,
        resume_checkpoint=resume_checkpoint,
    )
    tracking_binding = manifest.payload.get("tracking")
    if not isinstance(tracking_binding, Mapping):
        raise TrainingLaunchError("completed wave manifest has no tracking binding")
    expected_invocation = _invocation_payload(
        protocol=protocol,
        stage=stage,
        wave_name=wave_name,
        source_git_sha=str(manifest.payload.get("source_git_sha", "")),
        invocation_id=invocation_id,
        manifest=manifest,
        preflight=preflight,
        tracking=tracking_binding,
        resume_batch=resume_batch,
        resolved_launch=resolved_launch,
        parent=parent,
        resume_checkpoint=resume_checkpoint,
    )
    if invocation.payload != expected_invocation:
        raise TrainingLaunchError("completed wave invocation differs from the resolved launch")

    tracking_sha256 = payload.get("invocation_tracking_record_sha256")
    tracking = store.load_invocation_tracking(key, invocation_id=invocation_id)
    if tracking_sha256 is None:
        if tracking is not None:
            raise TrainingLaunchError("completed wave receipt omits existing tracking evidence")
    else:
        if (
            not isinstance(tracking_sha256, str)
            or not _SHA256.fullmatch(tracking_sha256)
            or tracking is None
            or tracking.record_sha256 != tracking_sha256
        ):
            raise TrainingLaunchError("completed wave tracking evidence is missing or differs")
        expected_tracking = {
            "invocation_record_sha256": invocation.record_sha256,
            "run_manifest_record_sha256": manifest.record_sha256,
            "source_git_sha": manifest.payload.get("source_git_sha"),
            "protocol_logical_sha256": protocol["logical_sha256"],
            "expected": dict(tracking_binding),
        }
        for field, expected in expected_tracking.items():
            if tracking.payload.get(field) != expected:
                raise TrainingLaunchError(f"completed wave tracking evidence has wrong {field}")
        observed = tracking.payload.get("observed")
        if not isinstance(observed, Mapping):
            raise TrainingLaunchError("completed wave tracking evidence has no live observation")
        observed_expected = {
            field: tracking_binding[field]
            for field in ("run_id", "entity", "project", "name", "group", "job_type", "tags")
        }
        for field, expected in observed_expected.items():
            if observed.get(field) != expected:
                raise TrainingLaunchError(f"completed wave live tracking has wrong {field}")
        expected_resume = resume_batch is not None
        if (
            observed.get("resumed") is not expected_resume
            or observed.get("requested_resume") != ("must" if expected_resume else "never")
            or observed.get("resolved_resume") != ("must" if expected_resume else "never")
            or observed.get("requested_directory") != tracking_binding["directory"]
        ):
            raise TrainingLaunchError("completed wave live tracking resume binding differs")

    inventory = payload.get("checkpoint_inventory")
    if not isinstance(inventory, Mapping) or set(inventory) != {
        "count",
        "entries",
        "logical_sha256",
    }:
        raise TrainingLaunchError("completed wave checkpoint inventory is malformed")
    entries = inventory.get("entries")
    if (
        isinstance(inventory.get("count"), bool)
        or not isinstance(inventory.get("count"), int)
        or not isinstance(entries, list)
        or inventory.get("count") != len(entries)
        or inventory.get("logical_sha256") != canonical_sha256(entries)
    ):
        raise TrainingLaunchError("completed wave checkpoint inventory digest differs")
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
    names: set[str] = set()
    terminal_entries: list[Mapping[str, Any]] = []
    periodic_entries: list[Mapping[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or set(entry) != entry_fields:
            raise TrainingLaunchError(f"completed wave checkpoint {index} is malformed")
        name = entry.get("name")
        role = entry.get("role")
        progress = entry.get("training_progress_fraction")
        if (
            not isinstance(name, str)
            or name in names
            or role not in {"periodic", "terminal"}
            or entry.get("final") is not (role == "terminal")
            or isinstance(entry.get("batch"), bool)
            or (
                entry.get("batch") is not None
                and (not isinstance(entry.get("batch"), int) or int(entry["batch"]) < 0)
            )
            or isinstance(entry.get("epoch"), bool)
            or (
                entry.get("epoch") is not None
                and (not isinstance(entry.get("epoch"), int) or int(entry["epoch"]) < 0)
            )
            or not _TINKER_PATH.fullmatch(str(entry.get("state_path", "")))
            or not _TINKER_PATH.fullmatch(str(entry.get("sampler_path", "")))
            or isinstance(progress, bool)
            or not isinstance(progress, (int, float))
            or not math.isfinite(float(progress))
            or not 0.0 <= float(progress) <= 1.0
        ):
            raise TrainingLaunchError(f"completed wave checkpoint {index} is invalid")
        names.add(name)
        if role == "terminal":
            terminal_entries.append(entry)
            if float(progress) != 1.0:
                raise TrainingLaunchError("terminal checkpoint has wrong progress")
        else:
            periodic_entries.append(entry)
    if len(terminal_entries) != 1:
        raise TrainingLaunchError("completed wave must have one terminal checkpoint")
    terminal = terminal_entries[0]
    if stage.kind == "rl":
        if (
            len(entries) != 1
            or terminal.get("name") != f"{target_steps:06d}"
            or terminal.get("batch") != target_steps
        ):
            raise TrainingLaunchError("completed RL wave checkpoint differs from its ceiling")
    else:
        save_every = max(
            1,
            round(
                target_steps * float(protocol["recipes"][stage.recipe_key]["checkpoint_fraction"])
            ),
        )
        expected_periodic = [f"{step:06d}" for step in range(save_every, target_steps, save_every)]
        if (
            [str(entry["name"]) for entry in entries] != [*expected_periodic, "final"]
            or terminal.get("name") != "final"
            or terminal.get("epoch") != 1
        ):
            raise TrainingLaunchError("completed SFT checkpoint cadence differs")
        for entry in periodic_entries:
            expected_progress = int(str(entry["name"])) / target_steps
            if not math.isclose(
                float(entry["training_progress_fraction"]),
                expected_progress,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise TrainingLaunchError("periodic checkpoint progress differs")
    selected = payload.get("checkpoint")
    checkpoint_fields = {
        "name",
        "batch",
        "epoch",
        "final",
        "state_path",
        "sampler_path",
    }
    if not isinstance(selected, Mapping) or set(selected) != checkpoint_fields:
        raise TrainingLaunchError("completed wave selected checkpoint is malformed")
    if any(selected[field] != terminal[field] for field in checkpoint_fields):
        raise TrainingLaunchError("completed wave selected checkpoint is not terminal")

    local_artifacts = payload.get("local_artifact_sha256")
    if (
        not isinstance(local_artifacts, Mapping)
        or not {"checkpoints.jsonl", "metrics.jsonl"}.issubset(local_artifacts)
        or not set(local_artifacts).issubset({"checkpoints.jsonl", "metrics.jsonl", "hparams.json"})
        or any(
            not isinstance(value, str) or not _SHA256.fullmatch(value)
            for value in local_artifacts.values()
        )
    ):
        raise TrainingLaunchError("completed wave local artifact inventory is malformed")

    start = resume_batch if resume_batch is not None else 0
    recipe = protocol["recipes"][stage.recipe_key]
    expected_candidates = (
        (target_steps - start) * int(recipe["groups_per_batch"]) * int(recipe["group_size"])
        if stage.kind == "rl"
        else 0
    )
    candidate_root = store.tinker_log_path(key).parent / "candidates" / invocation_id
    candidate_files = (
        sorted(candidate_root.rglob("evaluation.json")) if candidate_root.is_dir() else []
    )
    sample_files = sorted(candidate_root.rglob("sample.json")) if candidate_root.is_dir() else []
    for field, files in (
        ("candidate_inventory", candidate_files),
        ("sample_inventory", sample_files),
    ):
        observed_inventory = [
            {
                "path": str(path.relative_to(store.tinker_log_path(key).parent)),
                "sha256": file_sha256(path),
            }
            for path in files
        ]
        recorded = payload.get(field)
        if (
            not isinstance(recorded, Mapping)
            or set(recorded) != {"count", "expected_count", "logical_sha256"}
            or isinstance(recorded.get("count"), bool)
            or not isinstance(recorded.get("count"), int)
            or isinstance(recorded.get("expected_count"), bool)
            or not isinstance(recorded.get("expected_count"), int)
            or recorded.get("count") != len(observed_inventory)
            or recorded.get("expected_count") != expected_candidates
            or len(observed_inventory) != expected_candidates
            or recorded.get("logical_sha256") != canonical_sha256(observed_inventory)
        ):
            raise TrainingLaunchError(f"completed wave {field} does not prove full coverage")

    final_metric = payload.get("final_training_metric")
    required_metric = "optim/entropy" if stage.kind == "rl" else "train_mean_nll"
    if (
        not isinstance(final_metric, Mapping)
        or set(final_metric) != {"step", required_metric}
        or final_metric.get("step") != target_steps - 1
    ):
        raise TrainingLaunchError("completed wave final optimizer metric is malformed")
    metric = final_metric.get(required_metric)
    if (
        isinstance(metric, bool)
        or not isinstance(metric, (int, float))
        or not math.isfinite(float(metric))
    ):
        raise TrainingLaunchError("completed wave final optimizer metric is not finite")

    # A receipt is only a cache of facts reconstructed from the immutable
    # invocation and the local training artifacts.  Rebuild the canonical
    # payload so a well-formed but forged hash, metric, checkpoint inventory,
    # or rollout count cannot turn an incomplete run into ``already_complete``.
    try:
        reconstructed = _checkpoint_receipt(
            stage=stage,
            wave_name=wave_name,
            log_path=store.tinker_log_path(key),
            manifest=manifest,
            preflight=preflight,
            invocation=invocation,
            tracking=tracking,
            artifact_snapshot=payload.get("artifact_snapshot"),
        )
    except TrainingLaunchError:
        raise
    except Exception as exc:
        raise TrainingLaunchError(
            "completed wave artifacts could not reconstruct the canonical receipt"
        ) from exc
    if payload != reconstructed:
        raise TrainingLaunchError(
            "completed wave receipt differs from the current canonical training artifacts"
        )


def _checkpoint_identity(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict"):
        value = item.to_dict()
    elif isinstance(item, Mapping):
        value = dict(item)
    else:
        raise TrainingLaunchError("optimizer checkpoint has an unsupported record type")
    try:
        normalized = json.loads(
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    except (TypeError, ValueError) as exc:
        raise TrainingLaunchError("optimizer checkpoint is not finite JSON") from exc
    if not isinstance(normalized, dict):
        raise TrainingLaunchError("optimizer checkpoint is not an object")
    return normalized


def _matches_receipt_checkpoint(item: Any, expected: Mapping[str, Any]) -> bool:
    return all(
        getattr(item, field, None) == expected.get(field)
        for field in (
            "name",
            "batch",
            "epoch",
            "state_path",
            "sampler_path",
        )
    )


def _validate_resume_state(
    *,
    stage: StageSpec,
    wave_name: str,
    log_path: Path,
    prior_wave_receipt: TrainingRecord | None,
) -> ResumeBinding | None:
    if not log_path.exists():
        return None
    records = checkpoint_utils.load_checkpoints_file(str(log_path))
    target = int(stage.wave(wave_name)["max_steps"])
    resumable = [
        (index, item)
        for index, item in enumerate(records)
        if item.state_path is not None
    ]
    progress: list[int] = []
    for _index, item in resumable:
        if isinstance(item.batch, bool) or not isinstance(item.batch, int):
            raise TrainingLaunchError("resumable optimizer checkpoint has no integer batch")
        progress.append(item.batch)
    if progress and max(progress) > target:
        raise TrainingLaunchError("local optimizer state is ahead of this wave")

    selected: Any | None = None
    if prior_wave_receipt is not None:
        expected = prior_wave_receipt.payload["checkpoint"]
        matches = [
            (index, item)
            for index, item in resumable
            if _matches_receipt_checkpoint(item, expected)
        ]
        if len(matches) != 1:
            raise TrainingLaunchError("optimizer log does not contain the prior-wave checkpoint")
        expected_index, expected_item = matches[0]
        expected_batch = expected.get("batch")
        if (
            isinstance(expected_batch, bool)
            or not isinstance(expected_batch, int)
            or expected_batch < 0
            or expected_batch >= target
        ):
            raise TrainingLaunchError("prior-wave checkpoint cannot precede this wave")
        maximum = max(progress) if progress else expected_batch
        if maximum == expected_batch:
            later = [
                item
                for index, item in resumable
                if index > expected_index
            ]
            if later:
                # The pinned Cookbook always appends a permanent ``final``
                # checkpoint after the numbered wave-ceiling checkpoint.
                # It represents the same completed batch, but it is a
                # different URI.  We recognize exactly that one safe shape
                # and still pin the next launch to the receipt's numbered URI.
                if (
                    len(later) != 1
                    or later[0].name != "final"
                    or later[0].batch != expected_batch
                    or later[0].state_path is None
                    or later[0].sampler_path is None
                ):
                    raise TrainingLaunchError(
                        "optimizer log has ambiguous state after the prior-wave checkpoint"
                    )
            selected = expected_item
        else:
            selected_index, candidate = resumable[-1]
            if (
                selected_index <= expected_index
                or candidate.batch != maximum
                or candidate.name == "final"
                or candidate.batch >= target
            ):
                raise TrainingLaunchError(
                    "optimizer log does not have an exact in-wave resume checkpoint"
                )
            selected = candidate
    elif resumable:
        maximum = max(progress)
        _selected_index, candidate = resumable[-1]
        if (
            candidate.batch != maximum
            or candidate.name == "final"
            or candidate.batch >= target
        ):
            raise TrainingLaunchError(
                "training reached its wave ceiling without an immutable receipt"
            )
        selected = candidate

    if not records and any(log_path.iterdir()):
        raise TrainingLaunchError(
            "training log has no resumable checkpoint; reconcile it before retrying"
        )
    if selected is None:
        return None
    return ResumeBinding(
        batch=int(selected.batch),
        checkpoint=_checkpoint_identity(selected),
    )


@contextmanager
def _sealed_cookbook_resume(
    *,
    stage: StageSpec,
    wave_name: str,
    log_path: Path,
    prior_wave_receipt: TrainingRecord | None,
    expected: ResumeBinding | None,
) -> Iterator[None]:
    """Make Cookbook consume exactly the optimizer state in the invocation."""

    original = checkpoint_utils.get_last_checkpoint
    expected_log = log_path.expanduser().resolve(strict=False)
    fresh_at_entry = False
    if expected is None:
        observed_at_entry = _validate_resume_state(
            stage=stage,
            wave_name=wave_name,
            log_path=log_path,
            prior_wave_receipt=prior_wave_receipt,
        )
        if observed_at_entry is not None:
            raise TrainingLaunchError(
                "optimizer state changed after the immutable invocation was recorded"
            )
        fresh_at_entry = not log_path.exists() or not any(log_path.iterdir())

    def sealed(log_dir: str, required_key: str = "state_path") -> Any:
        requested = Path(log_dir).expanduser().resolve(strict=False)
        if requested != expected_log:
            return original(log_dir, required_key=required_key)
        if fresh_at_entry:
            if stage.kind == "sft":
                if log_path.exists() and (
                    not log_path.is_dir() or any(log_path.iterdir())
                ):
                    raise TrainingLaunchError(
                        "fresh SFT resume boundary contains unexpected training artifacts"
                    )
                return None
            if not log_path.is_dir():
                raise TrainingLaunchError(
                    "fresh Cookbook bootstrap did not create its training log directory"
                )
            entries = tuple(log_path.iterdir())
            names = {entry.name for entry in entries}
            if (
                names != _COOKBOOK_FRESH_RESUME_BOOTSTRAP_FILES
                or any(entry.is_symlink() or not entry.is_file() for entry in entries)
            ):
                raise TrainingLaunchError(
                    "fresh Cookbook bootstrap created unexpected training artifacts"
                )
            try:
                config = json.loads(
                    (log_path / "config.json").read_text(encoding="utf-8")
                )
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise TrainingLaunchError(
                    "fresh Cookbook bootstrap config is not valid JSON"
                ) from exc
            if not isinstance(config, dict):
                raise TrainingLaunchError(
                    "fresh Cookbook bootstrap config is not a JSON object"
                )
            return None
        observed = _validate_resume_state(
            stage=stage,
            wave_name=wave_name,
            log_path=log_path,
            prior_wave_receipt=prior_wave_receipt,
        )
        if observed != expected:
            raise TrainingLaunchError(
                "optimizer state changed after the immutable invocation was recorded"
            )
        if observed is None:
            return None
        records = checkpoint_utils.load_checkpoints_file(str(log_path))
        matches = [
            item
            for item in records
            if item.state_path is not None
            and _checkpoint_identity(item) == observed.checkpoint
        ]
        if len(matches) != 1 or not matches[0].has(required_key):
            raise TrainingLaunchError(
                "sealed optimizer checkpoint is missing at the Cookbook boundary"
            )
        return matches[0]

    checkpoint_utils.get_last_checkpoint = sealed
    try:
        yield
    finally:
        checkpoint_utils.get_last_checkpoint = original


async def run_training_stage(
    *,
    repo_root: Path,
    stage_id: str,
    wave_name: str,
    replicate_id: str,
    expected_source_sha: str,
    external_root: Path,
    confirmation: str,
    sft_main: Callable[[SFTConfig], Awaitable[None]] | None = None,
    rl_main: Callable[[RLConfig], Awaitable[None]] | None = None,
    wandb_access_validator: Callable[..., Mapping[str, Any]] = validate_wandb_access,
) -> dict[str, Any]:
    """Run or resume one exact paid wave after every local gate succeeds."""

    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    source_git_sha = validate_source_sha(root, expected_source_sha)
    if confirmation != protocol["launch"]["confirmation_token"]:
        raise TrainingLaunchError("explicit paid-training confirmation is missing")
    stage = stage_spec(protocol, stage_id)
    try:
        validate_stage_replicate(
            protocol,
            stage_id=stage.stage_id,
            replicate_id=replicate_id,
        )
    except ValueError as exc:
        raise TrainingLaunchError(str(exc)) from exc
    if wave_name not in stage.waves:
        stage.wave(wave_name)
    if not os.environ.get("TINKER_API_KEY"):
        raise TrainingLaunchError("TINKER_API_KEY is not present")
    if not os.environ.get("WANDB_API_KEY"):
        raise TrainingLaunchError("WANDB_API_KEY is not present")

    preflight = stage_preflight(
        repo_root=root,
        protocol=protocol,
        stage=stage,
        wave_name=wave_name,
        require_sandbox=stage.kind == "rl",
    )
    store = TrainingStore(repo_root=root, external_root=external_root)
    key = StageKey(STUDY_ID, stage.stage_id, replicate_id)
    with store.acquire_stage_lock(key):
        existing_manifest = store.load_manifest(key)
        if (
            existing_manifest is not None
            and existing_manifest.payload.get("source_git_sha") != source_git_sha
        ):
            raise TrainingLaunchError("existing child manifest belongs to another source commit")
        if str(stage.wave(wave_name)["approval"]) == "rollout-health-receipt":
            if existing_manifest is None:
                raise TrainingLaunchError(
                    "rollout-health continuation has no completed smoke manifest"
                )
            smoke_receipt = store.load_wave_receipt(key, wave="smoke")
            if smoke_receipt is None:
                raise TrainingLaunchError(
                    "rollout-health continuation has no smoke receipt"
                )
            smoke_preflight = stage_preflight(
                repo_root=root,
                protocol=protocol,
                stage=stage,
                wave_name="smoke",
                require_sandbox=True,
            )
            smoke_parent = _parent_binding(
                repo_root=root,
                protocol=protocol,
                store=store,
                key=key,
                stage=stage,
                source_git_sha=source_git_sha,
                approval=None,
                existing_manifest=existing_manifest,
            )
            _validate_completed_wave_receipt(
                repo_root=root,
                protocol=protocol,
                store=store,
                key=key,
                stage=stage,
                wave_name="smoke",
                manifest=existing_manifest,
                preflight=smoke_preflight,
                parent=smoke_parent,
                receipt=smoke_receipt,
            )
        approval = _approval_record(
            repo_root=root,
            store=store,
            key=key,
            stage=stage,
            wave_name=wave_name,
            source_git_sha=source_git_sha,
            protocol=protocol,
        )
        parent = _parent_binding(
            repo_root=root,
            protocol=protocol,
            store=store,
            key=key,
            stage=stage,
            source_git_sha=source_git_sha,
            approval=approval,
            existing_manifest=existing_manifest,
        )
        tracking = _tracking_binding(
            protocol=protocol,
            source_git_sha=source_git_sha,
            key=key,
            stage=stage,
            store=store,
        )
        manifest = store.create_or_verify_manifest(
            key,
            _manifest_payload(
                protocol=protocol,
                source_git_sha=source_git_sha,
                stage=stage,
                preflight=preflight,
                tracking=tracking,
                parent=parent,
            ),
        )
        existing = store.load_wave_receipt(key, wave=wave_name)
        if existing is not None:
            _validate_completed_wave_receipt(
                repo_root=root,
                protocol=protocol,
                store=store,
                key=key,
                stage=stage,
                wave_name=wave_name,
                manifest=manifest,
                preflight=preflight,
                parent=parent,
                receipt=existing,
            )
            return {
                "status": "already_complete",
                "stage_id": stage.stage_id,
                "wave": wave_name,
                "receipt": str(existing.relative_path),
                "receipt_sha256": existing.record_sha256,
            }
        log_path = store.tinker_log_path(key)
        prior_wave_name = _required_prior_wave(stage, wave_name)
        prior_wave_receipt = (
            store.load_wave_receipt(key, wave=prior_wave_name)
            if prior_wave_name is not None
            else None
        )
        resume_binding = _validate_resume_state(
            stage=stage,
            wave_name=wave_name,
            log_path=log_path,
            prior_wave_receipt=prior_wave_receipt,
        )
        resume_batch = resume_binding.batch if resume_binding is not None else None
        resume_checkpoint = (
            resume_binding.checkpoint if resume_binding is not None else None
        )
        resume = resume_batch is not None
        # Install one continuous environment before the first W&B SDK call.
        # This avoids the SDK caching an unbound session during access
        # validation. Programmatic init arguments below are a second,
        # independently checked identity boundary.
        with _wandb_environment(tracking, resume=resume):
            try:
                # Preflight and transition validation can be lengthy.  Bind
                # the actual live boundary to the clean commit once more
                # after every local record has been resolved.
                validate_source_sha(root, source_git_sha)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise TrainingLaunchError(
                    "source changed after preflight; refusing live W&B or Tinker access"
                ) from exc
            wandb_access_validator(expected_entity=tracking["entity"])
            resolved_launch = _resolved_launch_binding(
                repo_root=root,
                protocol=protocol,
                stage=stage,
                wave_name=wave_name,
                store=store,
                key=key,
                parent=parent,
                resume_batch=resume_batch,
                resume_checkpoint=resume_checkpoint,
            )
            invocation_id = f"{wave_name}-{uuid.uuid4().hex}"
            invocation = store.begin_invocation(
                key,
                invocation_id=invocation_id,
                payload=_invocation_payload(
                    protocol=protocol,
                    stage=stage,
                    wave_name=wave_name,
                    source_git_sha=source_git_sha,
                    invocation_id=invocation_id,
                    manifest=manifest,
                    preflight=preflight,
                    tracking=tracking,
                    resume_batch=resume_batch,
                    resolved_launch=resolved_launch,
                    parent=parent,
                    resume_checkpoint=resume_checkpoint,
                ),
            )
            config = build_tinker_config(
                repo_root=root,
                protocol=protocol,
                stage=stage,
                wave_name=wave_name,
                store=store,
                key=key,
                parent=parent,
                invocation=invocation,
            )

            def record_live_tracking(observed: Mapping[str, Any]) -> None:
                store.write_invocation_tracking(
                    key,
                    invocation_id=invocation_id,
                    payload={
                        "invocation_record_sha256": invocation.record_sha256,
                        "run_manifest_record_sha256": manifest.record_sha256,
                        "source_git_sha": source_git_sha,
                        "protocol_logical_sha256": protocol["logical_sha256"],
                        "expected": dict(tracking),
                        "observed": dict(observed),
                    },
                )

            with _sealed_cookbook_resume(
                stage=stage,
                wave_name=wave_name,
                log_path=log_path,
                prior_wave_receipt=prior_wave_receipt,
                expected=resume_binding,
            ):
                if stage.kind == "sft":
                    if sft_main is None:
                        from tinker_cookbook.supervised.train import main as resolved_main
                    else:
                        resolved_main = sft_main
                    if sft_main is None:
                        with _sealed_wandb_initialization(
                            tracking,
                            resume=resume,
                            on_initialized=record_live_tracking,
                        ):
                            await resolved_main(config)
                    else:
                        await resolved_main(config)
                else:
                    if stage.model_key == "inkling":
                        from rl.track_b.tml_shim import install_inkling_runtime

                        install_inkling_runtime(
                            effort=float(protocol["models"]["inkling"]["effort"])
                        )
                    if rl_main is None:
                        from tinker_cookbook.rl.train import main as resolved_main
                    else:
                        resolved_main = rl_main
                    if rl_main is None:
                        with _sealed_wandb_initialization(
                            tracking,
                            resume=resume,
                            on_initialized=record_live_tracking,
                        ):
                            await resolved_main(config)
                    else:
                        await resolved_main(config)
        live_tracking = store.load_invocation_tracking(
            key,
            invocation_id=invocation_id,
        )
        built_in_main = sft_main is None if stage.kind == "sft" else rl_main is None
        if built_in_main and live_tracking is None:
            raise TrainingLaunchError("training returned without an observed W&B tracking record")
        receipt = store.write_wave_receipt(
            key,
            wave=wave_name,
            payload=_checkpoint_receipt(
                stage=stage,
                wave_name=wave_name,
                log_path=log_path,
                manifest=manifest,
                preflight=preflight,
                invocation=invocation,
                tracking=live_tracking,
            ),
        )
        return {
            "status": "complete",
            "stage_id": stage.stage_id,
            "wave": wave_name,
            "manifest": str(manifest.relative_path),
            "manifest_sha256": manifest.record_sha256,
            "receipt": str(receipt.relative_path),
            "receipt_sha256": receipt.record_sha256,
            "wandb_run_id": tracking["run_id"],
            "checkpoint": receipt.payload["checkpoint"],
        }
