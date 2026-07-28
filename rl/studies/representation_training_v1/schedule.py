"""Deterministic task selection and schedule digests for training stages."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from rl.common.contracts import TaskRecord
from rl.common.dataset_io import load_tasks
from rl.track_a.curriculum import deterministic_rl_batch, stratified_physical_pass

from .protocol import StageSpec


SCHEDULE_SCHEMA_VERSION = "pixcell-training-schedule-v1"
SCHEDULE_SEED = 90210


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _select(tasks: list[TaskRecord], levels: tuple[str, ...]) -> list[TaskRecord]:
    allowed = set(levels)
    selected = [task for task in tasks if task.sampler.level.upper() in allowed]
    if not selected:
        raise ValueError(f"no depth/train rows match levels={levels}")
    return selected


def stage_tasks(dataset_root: Path, stage: StageSpec) -> list[TaskRecord]:
    all_train = load_tasks(
        dataset_root.expanduser().resolve(),
        configuration="depth",
        split="train",
    )
    levels = stage.levels if stage.kind == "sft" else (str(stage.current_level),)
    return _select(all_train, levels)


def stage_replay_tasks(
    dataset_root: Path,
    stage: StageSpec,
) -> list[TaskRecord]:
    if stage.kind != "rl" or not stage.replay_levels:
        return []
    all_train = load_tasks(
        dataset_root.expanduser().resolve(),
        configuration="depth",
        split="train",
    )
    return _select(all_train, stage.replay_levels)


def ordered_stage_tasks(dataset_root: Path, stage: StageSpec) -> list[TaskRecord]:
    return stratified_physical_pass(
        stage_tasks(dataset_root, stage),
        seed=SCHEDULE_SEED,
    )


def stage_schedule_document(
    dataset_root: Path,
    stage: StageSpec,
    *,
    groups_per_batch: int | None = None,
) -> dict[str, Any]:
    tasks = (
        ordered_stage_tasks(dataset_root, stage)
        if stage.kind == "sft"
        else stage_tasks(dataset_root, stage)
    )
    rows_by_level = Counter(task.sampler.level.upper() for task in tasks)
    representations = {
        task.sampler.representation_id
        for task in tasks
    }
    slots = Counter(
        str(task.sampler.realization_slot)
        for task in tasks
    )
    document: dict[str, Any] = {
        "schema_version": SCHEDULE_SCHEMA_VERSION,
        "stage_id": stage.stage_id,
        "kind": stage.kind,
        "seed": SCHEDULE_SEED,
        "rows": len(tasks),
        "rows_by_level": dict(sorted(rows_by_level.items())),
        "representations": len(representations),
        "realization_slots": dict(sorted(slots.items())),
        "ordered_task_ids": [task.sampler.opaque_id for task in tasks],
    }
    if stage.kind == "sft":
        document["batch_size"] = 64
        document["batches"] = math.ceil(len(tasks) / 64)
    else:
        if groups_per_batch is None or groups_per_batch < 1:
            raise ValueError("RL schedule requires groups_per_batch")
        document["groups_per_batch"] = groups_per_batch
        document["coverage_steps"] = math.ceil(len(tasks) / groups_per_batch)
        replay = stage_replay_tasks(dataset_root, stage)
        maximum_steps = max(
            int(wave["max_steps"]) for wave in stage.waves.values()
        )
        training_batches: list[dict[str, Any]] = []
        for step in range(maximum_steps):
            selected = deterministic_rl_batch(
                tasks,
                replay,
                step=step,
                groups_per_batch=groups_per_batch,
                schedule_seed=SCHEDULE_SEED,
            )
            ids = [task.sampler.opaque_id for _role, task in selected]
            if len(ids) != len(set(ids)):
                raise RuntimeError(f"{stage.stage_id} step {step} repeats a task")
            training_batches.append(
                {
                    "step": step,
                    "groups": [
                        {
                            "role": role,
                            "task_id": task.sampler.opaque_id,
                            "level": task.sampler.level.upper(),
                        }
                        for role, task in selected
                    ],
                }
            )
        document["maximum_steps"] = maximum_steps
        document["replay_pool_rows"] = len(replay)
        document["replay_levels"] = list(stage.replay_levels)
        document["training_batches"] = training_batches
    document["logical_sha256"] = canonical_sha256(document)
    return document


def verify_sft_step_count(
    dataset_root: Path,
    stage: StageSpec,
    *,
    max_steps: int,
) -> None:
    schedule = stage_schedule_document(dataset_root, stage)
    expected = int(schedule["batches"])
    if max_steps != expected:
        raise ValueError(
            f"{stage.stage_id} must visit one complete physical pass: "
            f"max_steps={expected}, got {max_steps}"
        )
