from __future__ import annotations

import hashlib

import pytest

from rl.common.contracts import (
    ModelObservation,
    SamplerMetadata,
    TaskRecord,
    VerifierReference,
)
from rl.track_a.curriculum import (
    balanced_effective_pass,
    hierarchical_sft_weights,
    stratified_physical_pass,
)
pytest.importorskip("tinker", reason="Tinker SDK env (rl/requirements-lock.txt) not installed")
pytest.importorskip("chz", reason="chz env (rl/requirements-lock.txt) not installed")

from rl.track_a.recipe import (
    first_unmastered_level,
    validate_curriculum_selection,
)
from rl.track_a.tinker_data import TrackARLDataset


def _task(index: int, level: str, representation: str) -> TaskRecord:
    payload = f"image-{index}".encode()
    target = f"target-{index}".encode()
    return TaskRecord(
        observation=ModelObservation(
            payload,
            (10.0, 5.0),
            hashlib.sha256(payload).hexdigest(),
        ),
        label=f"# code {index}",
        reference=VerifierReference(
            target,
            (10.0, 5.0),
            hashlib.sha256(target).hexdigest(),
        ),
        sampler=SamplerMetadata(
            opaque_id=f"id-{index}",
            level=level,
            representation_id=representation,
            leakage_group_id=representation,
            realization_slot=index,
            split_role="train",
        ),
    )


def test_stratified_pass_visits_every_row_once():
    tasks = [
        _task(0, "L0", "a"),
        _task(1, "L0", "a"),
        _task(2, "L0", "b"),
        _task(3, "L1", "c"),
        _task(4, "L1", "d"),
    ]
    order = stratified_physical_pass(tasks, seed=9)
    assert len(order) == len(tasks)
    assert {item.sampler.opaque_id for item in order} == {
        item.sampler.opaque_id for item in tasks
    }
    assert [item.sampler.level for item in order[:2]] == ["L0", "L1"]


def test_hierarchical_weights_equalize_levels_and_representations():
    tasks = [
        _task(0, "L0", "a"),
        _task(1, "L0", "a"),
        _task(2, "L0", "b"),
        _task(3, "L1", "c"),
        _task(4, "L1", "d"),
        _task(5, "L1", "d"),
        _task(6, "L1", "d"),
    ]
    weights = hierarchical_sft_weights(tasks)
    assert sum(weights.values()) / len(tasks) == pytest.approx(1.0)
    masses: dict[tuple[str, str], float] = {}
    for task in tasks:
        key = (task.sampler.level, task.sampler.representation_id)
        masses[key] = masses.get(key, 0.0) + weights[task.sampler.opaque_id]
    assert masses[("L0", "a")] == pytest.approx(masses[("L0", "b")])
    assert masses[("L1", "c")] == pytest.approx(masses[("L1", "d")])
    assert sum(value for (level, _), value in masses.items() if level == "L0") == (
        pytest.approx(
            sum(value for (level, _), value in masses.items() if level == "L1")
        )
    )


def test_balanced_effective_pass_never_wraps_or_duplicates():
    tasks = [
        _task(0, "L0", "a"),
        _task(1, "L0", "a"),
        _task(2, "L0", "b"),
        _task(3, "L1", "c"),
        _task(4, "L1", "d"),
    ]
    full = balanced_effective_pass(tasks, seed=3, draws=len(tasks))
    assert len(full) == len(tasks)
    assert len({item.sampler.opaque_id for item in full}) == len(tasks)
    with pytest.raises(ValueError, match="unique available tasks"):
        balanced_effective_pass(tasks, seed=3, draws=len(tasks) + 1)


def test_first_unmastered_and_replay_contract_are_computed():
    report = {
        "levels_summary": {
            level: {
                "mean_iou_at_1": 0.9,
                "pure_executable_rate": 0.99,
            }
            for level in ("L0", "L1", "L2", "L3", "L4")
        }
    }
    report["levels_summary"]["L2"]["mean_iou_at_1"] = 0.7
    recipe = {
        "rl": {
            "curriculum": {
                "minimum_iou": 0.8,
                "minimum_pure_executable_rate": 0.95,
            }
        }
    }
    assert first_unmastered_level(
        report,
        minimum_iou=0.8,
        minimum_pure_executable_rate=0.95,
    ) == "L2"
    assert validate_curriculum_selection(
        recipe,
        report,
        current_level="L2",
        replay_levels="L0,L1",
    ) == ("L2", ("L0", "L1"))
    with pytest.raises(ValueError, match="computed first unmastered"):
        validate_curriculum_selection(
            recipe,
            report,
            current_level="L3",
            replay_levels="L0,L1,L2",
        )
    with pytest.raises(ValueError, match="exactly the earlier levels"):
        validate_curriculum_selection(
            recipe,
            report,
            current_level="L2",
            replay_levels="L1",
        )


def test_rl_five_step_cycle_is_exactly_eighty_twenty():
    current = [_task(index, "L2", f"current-{index}") for index in range(16)]
    replay = [
        _task(100 + index, "L1", f"replay-{index}") for index in range(8)
    ]
    dataset = TrackARLDataset(
        current,
        replay,
        renderer=None,
        groups_per_batch=8,
        group_size=4,
        max_image=1440,
        n_batches=5,
        shuffle=True,
    )
    expected_replay = [2, 2, 2, 1, 1]
    for index, expected in enumerate(expected_replay):
        group = dataset.get_batch(index)
        levels = [item.dataset_name for item in group]
        assert len(group) == 8
        assert levels.count("L1") == expected
        assert levels.count("L2") == 8 - expected
        assert all(item.num_envs == 4 for item in group)
