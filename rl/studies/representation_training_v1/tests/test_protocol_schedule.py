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
    parent_replicate_id,
    stage_spec,
    validate_stage_replicate,
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
    assert len(protocol["stages"]) == 21
    assert protocol["recipes"]["qwen_sft"]["learning_rate"] == 1e-4
    assert stage_spec(protocol, "qwen-mixed-sft").parent == "base:qwen"
    assert (
        stage_spec(protocol, "qwen-sequential-sft-l1").parent
        == "qwen-l0-sft:complete"
    )
    assert stage_spec(protocol, "qwen-l0-rl-l1").parent == "qwen-l0-sft:complete"
    assert stage_spec(protocol, "inkling-l4-rl").parent == "base:inkling"


def test_protocol_seals_the_pure_qwen_rl_curriculum() -> None:
    protocol = load_protocol(REPO_ROOT)
    expected_gates = {
        "step-5": "rollout-health-receipt",
        "step-10": "current-level-held-out-promotion-receipt",
        "step-15": "current-level-held-out-promotion-receipt",
        "step-20": "current-level-held-out-promotion-receipt",
        "step-25": "current-level-held-out-promotion-receipt",
        "complete": "current-level-held-out-promotion-receipt",
    }
    for level in range(5):
        stage = stage_spec(protocol, f"qwen-base-rl-l{level}")
        assert stage.hypotheses == ("RT-H06",)
        assert stage.parent == (
            "base:qwen"
            if level == 0
            else f"qwen-base-rl-l{level - 1}:complete"
        )
        assert stage.current_level == f"L{level}"
        assert stage.replay_levels == tuple(f"L{prior}" for prior in range(level))
        assert {
            name: wave["max_steps"] for name, wave in stage.waves.items()
        } == {
            "smoke": 1,
            "step-5": 5,
            "step-10": 10,
            "step-15": 15,
            "step-20": 20,
            "step-25": 25,
            "complete": 30,
        }
        assert stage.wave("smoke")["approval"] == (
            "initial"
            if level == 0
            else "prior-and-current-level-held-out-transition-receipt"
        )
        assert {
            wave: stage.wave(wave)["approval"] for wave in expected_gates
        } == expected_gates


def test_operational_retry_is_scoped_and_keeps_the_historical_r0_parent() -> None:
    protocol = load_protocol(REPO_ROOT)

    validate_stage_replicate(
        protocol,
        stage_id="qwen-l0-rl-l1",
        replicate_id="r0-retry1",
    )
    assert (
        parent_replicate_id(
            protocol,
            stage_id="qwen-l0-rl-l1",
            replicate_id="r0-retry1",
        )
        == "r0"
    )
    assert (
        parent_replicate_id(
            protocol,
            stage_id="qwen-l0-rl-l2",
            replicate_id="r0-retry1",
        )
        == "r0-retry1"
    )
    with pytest.raises(ValueError, match="not declared for this training stage"):
        validate_stage_replicate(
            protocol,
            stage_id="qwen-base-rl-l0",
            replicate_id="r0-retry1",
        )


def test_protocol_seals_fixed_progress_and_final_selection_panels() -> None:
    evaluation = load_protocol(REPO_ROOT)["evaluation"]
    progress = evaluation["curriculum_progress_holdout"]
    assert progress == {
        "baseline_checkpoints": {
            "L0": "base:qwen",
            "L1": "qwen-base-rl-l0:complete",
            "L2": "qwen-base-rl-l1:complete",
            "L3": "qwen-base-rl-l2:complete",
            "L4": "qwen-base-rl-l3:complete",
        },
        "configuration": "depth",
        "evaluation_waves": [
            "step-5",
            "step-10",
            "step-15",
            "step-20",
            "step-25",
            "complete",
        ],
        "panel_prefix": "level-progress",
        "realization_slot": 6,
        "representations_by_level": {
            "L0": 93,
            "L1": 127,
            "L2": 98,
            "L3": 120,
            "L4": 108,
        },
        "rows_by_level": {
            "L0": 93,
            "L1": 127,
            "L2": 98,
            "L3": 120,
            "L4": 108,
        },
        "split": "validation",
    }
    assert evaluation["final_selection_holdout"] == {
        "configuration": "depth",
        "panel": "depth-final-selection",
        "realization_slot": 7,
        "representations": 546,
        "rows": 546,
        "split": "validation",
    }


def test_pure_qwen_rl_schedule_uses_every_level_and_full_earlier_prefix() -> None:
    protocol = load_protocol(REPO_ROOT)
    expected_rows = {"L0": 642, "L1": 850, "L2": 608, "L3": 720, "L4": 648}
    expected_representations = {"L0": 93, "L1": 127, "L2": 99, "L3": 120, "L4": 108}
    for level in range(5):
        stage = stage_spec(protocol, f"qwen-base-rl-l{level}")
        schedule = stage_schedule_document(
            REPO_ROOT / "dataset",
            stage,
            groups_per_batch=8,
        )
        current = f"L{level}"
        assert schedule["maximum_steps"] == 30
        assert schedule["rows_by_level"] == {current: expected_rows[current]}
        assert schedule["representations"] == expected_representations[current]
        assert schedule["replay_levels"] == [
            f"L{prior}" for prior in range(level)
        ]
        assert len(schedule["training_batches"]) == 30
        assert all(
            len(batch["groups"]) == 8
            for batch in schedule["training_batches"]
        )


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
