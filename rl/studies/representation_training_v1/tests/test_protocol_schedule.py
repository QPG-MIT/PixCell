from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")

import tinker

from rl.studies.representation_training_v1.launcher import (
    deterministic_wandb_run_id,
)
from rl.studies.representation_training_v1.protocol import (
    STUDY_ID,
    load_protocol,
    stage_spec,
)
from rl.studies.representation_training_v1.schedule import (
    SCHEDULE_SEED,
    stage_schedule_document,
    stage_tasks,
)
from rl.studies.representation_training_v1.store import StageKey
from rl.track_a.tinker_data import TrackARLDataset


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_protocol_seals_the_shared_branch_graph() -> None:
    protocol = load_protocol(REPO_ROOT)
    assert len(protocol["stages"]) == 16
    assert protocol["recipes"]["qwen_sft"]["learning_rate"] == 1e-4
    assert stage_spec(protocol, "qwen-mixed-sft").parent == "base:qwen"
    assert (
        stage_spec(protocol, "qwen-sequential-sft-l1").parent
        == "qwen-l0-sft:complete"
    )
    assert stage_spec(protocol, "qwen-l0-rl-l1").parent == "qwen-l0-sft:complete"
    assert stage_spec(protocol, "inkling-l4-rl").parent == "base:inkling"


def test_qwen_rl_schedule_is_the_exact_dataset_batch_schedule() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-l0-rl-l3")
    schedule = stage_schedule_document(
        REPO_ROOT / "dataset",
        stage,
        groups_per_batch=8,
    )
    assert schedule["maximum_steps"] == 30
    assert len(schedule["training_batches"]) == 30
    assert all(len(batch["groups"]) == 8 for batch in schedule["training_batches"])
    assert all(
        len({group["task_id"] for group in batch["groups"]}) == 8
        for batch in schedule["training_batches"]
    )
    replay_groups = sum(
        group["role"] == "replay"
        for batch in schedule["training_batches"]
        for group in batch["groups"]
    )
    assert replay_groups == 48

    current = stage_tasks(REPO_ROOT / "dataset", stage)
    from rl.studies.representation_training_v1.schedule import stage_replay_tasks

    replay = stage_replay_tasks(REPO_ROOT / "dataset", stage)
    dataset = TrackARLDataset(
        current,
        replay,
        renderer=object(),
        groups_per_batch=8,
        group_size=4,
        max_image=1920,
        n_batches=30,
        shuffle=True,
        reward_policy="raw_iou",
        schedule_seed=SCHEDULE_SEED,
    )
    for step, expected in enumerate(schedule["training_batches"]):
        observed = [builder.task.sampler.opaque_id for builder in dataset.get_batch(step)]
        assert observed == [group["task_id"] for group in expected["groups"]]


def test_sft_stage_counts_are_one_physical_pass() -> None:
    protocol = load_protocol(REPO_ROOT)
    expected = {
        "qwen-l0-sft": (642, 11),
        "qwen-mixed-sft": (3468, 55),
        "qwen-sequential-sft-l1": (850, 14),
        "qwen-sequential-sft-l2": (608, 10),
        "qwen-sequential-sft-l3": (720, 12),
        "qwen-sequential-sft-l4": (648, 11),
    }
    for stage_id, (rows, batches) in expected.items():
        stage = stage_spec(protocol, stage_id)
        schedule = stage_schedule_document(REPO_ROOT / "dataset", stage)
        assert (schedule["rows"], schedule["batches"]) == (rows, batches)
        assert stage.wave("complete")["max_steps"] == batches


def test_pinned_tinker_top_p_default_is_one() -> None:
    params = tinker.SamplingParams(max_tokens=1, temperature=1.0)
    assert params.top_p == 1


def test_wandb_identity_binds_protocol_source_stage_and_replicate() -> None:
    key = StageKey(STUDY_ID, "qwen-mixed-sft", "r0")
    values = {
        deterministic_wandb_run_id(
            source_git_sha="1" * 40,
            protocol_logical_sha256="2" * 64,
            key=key,
        ),
        deterministic_wandb_run_id(
            source_git_sha="3" * 40,
            protocol_logical_sha256="2" * 64,
            key=key,
        ),
        deterministic_wandb_run_id(
            source_git_sha="1" * 40,
            protocol_logical_sha256="4" * 64,
            key=key,
        ),
    }
    assert len(values) == 3
