"""Sealed, resumable launch controller for representation-training-v1."""

from __future__ import annotations

import json
import math
import os
import re
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
from .protocol import (
    STUDY_ID,
    StageSpec,
    file_sha256,
    load_protocol,
    stage_spec,
    validate_source_sha,
)
from .schedule import SCHEDULE_SEED
from .store import StageKey, TrainingRecord, TrainingStore, canonical_sha256


WANDB_RUN_ID_PREFIX = "pxct-"
_TINKER_PATH = re.compile(r"^tinker://[^\s]+$")
_ENVIRONMENT_FIELDS = (
    "WANDB_DIR",
    "WANDB_DISABLE_CODE",
    "WANDB_DISABLE_GIT",
    "WANDB_ENTITY",
    "WANDB_JOB_TYPE",
    "WANDB_MODE",
    "WANDB_NAME",
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
    receipt: TrainingRecord
    checkpoint: dict[str, Any]


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
        "name": (
            f"{STUDY_ID}/{stage.stage_id}/{key.replicate_id}"
            f"@{source_git_sha[:12]}"
        ),
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
        raise TrainingLaunchError(
            "selected parent checkpoint is not in the parent receipt"
        )
    checkpoint = dict(selected)
    if (
        not _TINKER_PATH.fullmatch(str(checkpoint.get("state_path", "")))
        or not _TINKER_PATH.fullmatch(str(checkpoint.get("sampler_path", "")))
    ):
        raise TrainingLaunchError("selected parent checkpoint has invalid URIs")
    return checkpoint


def _parent_binding(
    *,
    store: TrainingStore,
    key: StageKey,
    stage: StageSpec,
    approval: TrainingRecord | None,
    existing_manifest: TrainingRecord | None,
) -> ParentBinding | None:
    if stage.parent.startswith("base:"):
        expected_model = stage.parent.split(":", 1)[1]
        if expected_model != stage.model_key:
            raise TrainingLaunchError("base parent and stage model differ")
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
            raise TrainingLaunchError(
                f"{stage.stage_id} requires an approved dynamic parent"
            )
        allowed = {"qwen-mixed-sft"}
        target_index = int(str(stage.current_level)[1:])
        allowed.update(
            f"qwen-mixed-rl-l{index}" for index in range(target_index)
        )
        if selected_stage not in allowed or selected_wave != "complete":
            raise TrainingLaunchError(
                f"{stage.stage_id} approval selected an invalid parent"
            )
        parent_stage_id, parent_wave = selected_stage, selected_wave

    parent_key = StageKey(key.study_id, parent_stage_id, key.replicate_id)
    receipt = store.load_wave_receipt(parent_key, wave=parent_wave)
    if receipt is None:
        raise TrainingLaunchError(
            f"{stage.stage_id} requires {parent_stage_id}/{parent_wave}"
        )
    checkpoint: dict[str, Any]
    frozen_parent = (
        existing_manifest.payload.get("parent_receipt")
        if existing_manifest is not None
        else None
    )
    if isinstance(frozen_parent, Mapping):
        if (
            frozen_parent.get("stage_id") != parent_stage_id
            or frozen_parent.get("wave") != parent_wave
            or frozen_parent.get("record_sha256") != receipt.record_sha256
        ):
            raise TrainingLaunchError(
                "frozen stage manifest and current parent receipt differ"
            )
        frozen_checkpoint = frozen_parent.get("checkpoint")
        if not isinstance(frozen_checkpoint, Mapping):
            raise TrainingLaunchError("frozen stage parent has no checkpoint")
        checkpoint = _checkpoint_from_inventory(
            receipt,
            frozen_checkpoint,
            inventory_sha256=frozen_parent.get(
                "checkpoint_inventory_logical_sha256"
            ),
        )
    else:
        if approval is None:
            raise TrainingLaunchError(
                f"{stage.stage_id} requires a selected parent checkpoint"
            )
        selected = approval.payload.get("selected_parent_checkpoint")
        if not isinstance(selected, Mapping):
            raise TrainingLaunchError(
                f"{stage.stage_id} approval has no selected parent checkpoint"
            )
        checkpoint = _checkpoint_from_inventory(
            receipt,
            selected,
            inventory_sha256=approval.payload.get(
                "selected_parent_checkpoint_inventory_sha256"
            ),
        )
    if approval is not None:
        claimed = approval.payload.get("parent_receipt_record_sha256")
        if claimed is not None and claimed != receipt.record_sha256:
            raise TrainingLaunchError("approval and parent receipt differ")
    return ParentBinding(
        stage_id=parent_stage_id,
        wave=parent_wave,
        receipt=receipt,
        checkpoint=checkpoint,
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
    approval = store.load_wave_approval(key, wave=wave_name)
    if approval is None:
        raise TrainingLaunchError(
            f"{stage.stage_id}/{wave_name} requires an immutable {gate} approval"
        )
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
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} approval has wrong {field}"
            )
    if gate == "clean-smoke-receipt":
        if prior_wave is None or prior is None:
            raise TrainingLaunchError("clean-smoke gate has no prior wave receipt")
        if (
            approval.payload.get("prior_wave") != prior_wave
            or approval.payload.get("prior_receipt_record_sha256")
            != prior.record_sha256
        ):
            raise TrainingLaunchError(
                f"{stage.stage_id}/{wave_name} approval is not bound "
                f"to its {prior_wave} receipt"
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
        if any(
            evidence.get(field) != value
            for field, value in expected_evidence.items()
        ):
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
    return {
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
        "dataset_logical_release_sha256": protocol["dataset"][
            "logical_release_sha256"
        ],
        "schedule_seed": SCHEDULE_SEED,
        "tinker_log_relative_path": str(
            store.tinker_log_path(key).relative_to(store.external_root)
        ),
        "initial_checkpoint": checkpoint,
        "resume_batch": resume_batch,
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
            "optimizer_reset_each_stage": bool(
                recipe["optimizer_reset_each_stage"]
            ),
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
            "remove_constant_reward_groups": bool(
                recipe["remove_constant_reward_groups"]
            ),
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
    common["logical_sha256"] = canonical_sha256(common)
    return common


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
    load_checkpoint_path = (
        str(checkpoint["state_path"]) if checkpoint is not None else None
    )
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
            if invocation is not None
            and invocation.payload.get("resume_batch") is not None
            else None
        ),
    )
    if (
        invocation is not None
        and invocation.payload.get("resolved_launch") != resolved_launch
    ):
        raise TrainingLaunchError(
            "immutable invocation differs from the resolved Tinker launch"
        )
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
                    "run_manifest_record_sha256": invocation.payload[
                        "run_manifest_record_sha256"
                    ],
                    "source_git_sha": invocation.payload["source_git_sha"],
                    "protocol_logical_sha256": invocation.payload[
                        "protocol_logical_sha256"
                    ],
                    "policy": invocation.payload["policy"],
                    "initial_checkpoint": invocation.payload[
                        "initial_checkpoint"
                    ],
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


def _checkpoint_receipt(
    *,
    stage: StageSpec,
    wave_name: str,
    log_path: Path,
    manifest: TrainingRecord,
    preflight: Mapping[str, Any],
    invocation: TrainingRecord,
) -> dict[str, Any]:
    records = checkpoint_utils.load_checkpoints_file(str(log_path))
    complete = [
        item
        for item in records
        if item.state_path is not None and item.sampler_path is not None
    ]
    if not complete:
        raise TrainingLaunchError("training returned without a resumable checkpoint")
    checkpoint = complete[-1]
    target_steps = int(stage.wave(wave_name)["max_steps"])
    if stage.kind == "rl":
        unique_name = f"{target_steps:06d}"
        matching = [
            item
            for item in complete
            if item.name == unique_name and item.batch == target_steps
        ]
        if len(matching) != 1:
            raise TrainingLaunchError(
                f"RL wave has {len(matching)} unique {unique_name} checkpoints"
            )
        checkpoint = matching[0]
    if stage.kind == "sft":
        if checkpoint.name != "final" or checkpoint.epoch != 1:
            raise TrainingLaunchError(
                "SFT terminal checkpoint is not the completed epoch"
            )
    if not _TINKER_PATH.fullmatch(
        str(checkpoint.state_path)
    ) or not _TINKER_PATH.fullmatch(str(checkpoint.sampler_path)):
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
        [
            f"{step:06d}"
            for step in range(save_every, target_steps, save_every)
        ]
        if stage.kind == "sft"
        else []
    )
    periodic_by_name: dict[str, Any] = {}
    for item in complete:
        if item.name not in expected_periodic_names:
            continue
        if item.name in periodic_by_name:
            raise TrainingLaunchError(
                f"checkpoint inventory repeats {item.name}"
            )
        periodic_by_name[item.name] = item
    if set(periodic_by_name) != set(expected_periodic_names):
        raise TrainingLaunchError(
            "periodic checkpoint inventory differs from the sealed cadence"
        )

    def checkpoint_entry(item: Any, *, role: str) -> dict[str, Any]:
        if not _TINKER_PATH.fullmatch(
            str(item.state_path)
        ) or not _TINKER_PATH.fullmatch(str(item.sampler_path)):
            raise TrainingLaunchError("checkpoint inventory contains invalid URIs")
        progress = (
            1.0
            if role == "terminal"
            else int(item.name) / target_steps
        )
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
    local_artifacts: dict[str, str] = {}
    for name in ("checkpoints.jsonl", "metrics.jsonl", "hparams.json"):
        path = log_path / name
        if path.is_file():
            local_artifacts[name] = file_sha256(path)
    candidate_root = (
        log_path.parent
        / "candidates"
        / str(invocation.payload["invocation_id"])
    )
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
            target_steps - start
        ) * int(policy["groups_per_batch"]) * int(policy["group_size"])
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
    metrics_path = log_path / "metrics.jsonl"
    if not metrics_path.is_file():
        raise TrainingLaunchError("training returned without metrics.jsonl")
    last_metrics: dict[str, Any] | None = None
    with metrics_path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    last_metrics = value
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


def _validate_resume_state(
    *,
    stage: StageSpec,
    wave_name: str,
    log_path: Path,
    prior_wave_receipt: TrainingRecord | None,
) -> int | None:
    if not log_path.exists():
        return None
    records = checkpoint_utils.load_checkpoints_file(str(log_path))
    target = int(stage.wave(wave_name)["max_steps"])
    progress = [
        int(item.batch)
        for item in records
        if item.state_path is not None and item.batch is not None
    ]
    if progress and max(progress) > target:
        raise TrainingLaunchError("local optimizer state is ahead of this wave")
    if prior_wave_receipt is not None:
        expected = prior_wave_receipt.payload["checkpoint"]
        matched = any(
            item.state_path == expected["state_path"]
            and item.sampler_path == expected["sampler_path"]
            for item in records
        )
        if not matched:
            raise TrainingLaunchError(
                "optimizer log does not contain the prior-wave checkpoint"
            )
    if not records and any(log_path.iterdir()):
        raise TrainingLaunchError(
            "training log has no resumable checkpoint; reconcile it before retrying"
        )
    return max(progress) if progress else None


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
    if replicate_id not in protocol["launch"]["replicates"]:
        raise TrainingLaunchError("replicate is not declared in the protocol")
    stage = stage_spec(protocol, stage_id)
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
        existing = store.load_wave_receipt(key, wave=wave_name)
        if existing is not None:
            return {
                "status": "already_complete",
                "stage_id": stage.stage_id,
                "wave": wave_name,
                "receipt": str(existing.relative_path),
                "receipt_sha256": existing.record_sha256,
            }
        approval = _approval_record(
            store=store,
            key=key,
            stage=stage,
            wave_name=wave_name,
            source_git_sha=source_git_sha,
            protocol=protocol,
        )
        existing_manifest = store.load_manifest(key)
        parent = _parent_binding(
            store=store,
            key=key,
            stage=stage,
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
        # This network check authenticates observability only. It happens
        # after the authoritative local manifest and before any Tinker client.
        wandb_access_validator(expected_entity=tracking["entity"])
        log_path = store.tinker_log_path(key)
        prior_wave_name = _required_prior_wave(stage, wave_name)
        prior_wave_receipt = (
            store.load_wave_receipt(key, wave=prior_wave_name)
            if prior_wave_name is not None
            else None
        )
        resume_batch = _validate_resume_state(
            stage=stage,
            wave_name=wave_name,
            log_path=log_path,
            prior_wave_receipt=prior_wave_receipt,
        )
        resolved_launch = _resolved_launch_binding(
            repo_root=root,
            protocol=protocol,
            stage=stage,
            wave_name=wave_name,
            store=store,
            key=key,
            parent=parent,
            resume_batch=resume_batch,
        )
        invocation_id = f"{wave_name}-{uuid.uuid4().hex}"
        invocation = store.begin_invocation(
            key,
            invocation_id=invocation_id,
            payload={
                "invocation_id": invocation_id,
                "stage_id": stage.stage_id,
                "wave": wave_name,
                "source_git_sha": source_git_sha,
                "protocol_logical_sha256": protocol["logical_sha256"],
                "run_manifest_record_sha256": manifest.record_sha256,
                "preflight_sha256": preflight["preflight_sha256"],
                "wandb_run_id": tracking["run_id"],
                "resume_batch": resume_batch,
                "resolved_launch": resolved_launch,
                "resolved_launch_sha256": resolved_launch["logical_sha256"],
                "policy": {
                    "model": protocol["models"][stage.model_key]["model"],
                    "renderer": protocol["models"][stage.model_key]["renderer"],
                    "effort": protocol["models"][stage.model_key].get("effort"),
                    "max_output_tokens": protocol["models"][stage.model_key][
                        "max_output_tokens"
                    ],
                    "temperature": protocol["recipes"][stage.recipe_key].get(
                        "temperature"
                    ),
                    "top_p": protocol["recipes"][stage.recipe_key].get("top_p"),
                    "reward": protocol["recipes"][stage.recipe_key].get("reward"),
                    "group_size": protocol["recipes"][stage.recipe_key].get(
                        "group_size"
                    ),
                    "groups_per_batch": protocol["recipes"][stage.recipe_key].get(
                        "groups_per_batch"
                    ),
                },
                "initial_checkpoint": (
                    parent.checkpoint if parent is not None else None
                ),
            },
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
        with _wandb_environment(tracking, resume=resume_batch is not None):
            if stage.kind == "sft":
                if sft_main is None:
                    from tinker_cookbook.supervised.train import main as resolved_main
                else:
                    resolved_main = sft_main
                await resolved_main(config)
            else:
                if stage.model_key == "inkling":
                    from rl.track_b.tml_shim import install_inkling_runtime

                    install_inkling_runtime(effort=float(protocol["models"]["inkling"]["effort"]))
                if rl_main is None:
                    from tinker_cookbook.rl.train import main as resolved_main
                else:
                    resolved_main = rl_main
                await resolved_main(config)
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
