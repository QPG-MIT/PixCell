"""Campaign plan construction and probe determinism (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("tinker", reason="Tinker SDK env not installed")
pytest.importorskip("chz", reason="chz env not installed")

from rl.track_a.probe_eval import select_probe_tasks
from rl.track_a.run import RUN_PLANS, _sft_gate, build_stages


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_a_plan_is_sft_then_five_rl_stages(tmp_path):
    stages = build_stages(
        RUN_PLANS["A"], run_root=tmp_path, wandb_project="pixcell-rl"
    )
    assert [stage.name for stage in stages] == [
        "sft-l0",
        "rl-l0",
        "rl-l1",
        "rl-l2",
        "rl-l3",
        "rl-l4",
    ]
    sft = stages[0]
    assert sft.args["levels"] == "L0"
    assert sft.args["num_epochs"] == "2"
    assert sft.args["renderer_name"] == "qwen3_5_disable_thinking"
    last = stages[-1]
    assert last.args["current_level"] == "L4"
    assert last.args["max_steps"] == "30"
    assert last.args["group_size"] == "8"
    assert last.args["groups_per_batch"] == "8"
    assert last.args["reward_policy"] == "shaped_v3b"
    assert last.args["wandb_name"] == "runA-l0sft-rl-rl-l4"


def test_think_pair_uses_thinking_renderer_and_budget(tmp_path):
    for key in ("C", "D"):
        stages = build_stages(
            RUN_PLANS[key], run_root=tmp_path, wandb_project="pixcell-rl"
        )
        rl_stage = [stage for stage in stages if stage.name == "rl-l0"][0]
        assert rl_stage.args["renderer_name"] == "qwen3_5"
        assert rl_stage.args["max_tokens"] == "60000"
    assert RUN_PLANS["C"].sft is False
    assert RUN_PLANS["D"].sft is True


def test_smoke_plan_is_two_steps_two_groups(tmp_path):
    stages = build_stages(
        RUN_PLANS["B"], run_root=tmp_path, wandb_project="pixcell-rl", smoke=True
    )
    assert [stage.name for stage in stages] == ["rl-l0"]
    assert stages[0].args["max_steps"] == "2"
    assert stages[0].args["groups_per_batch"] == "2"
    assert stages[0].args["validation_canaries"] == "8"


def test_probe_selection_is_deterministic_and_stratified():
    first = select_probe_tasks(REPO_ROOT / "dataset", per_level=4)
    second = select_probe_tasks(REPO_ROOT / "dataset", per_level=4)
    assert [task.sampler.opaque_id for task in first] == [
        task.sampler.opaque_id for task in second
    ]
    assert len(first) == 20
    by_level: dict[str, int] = {}
    for task in first:
        by_level[task.sampler.level] = by_level.get(task.sampler.level, 0) + 1
    assert by_level == {"L0": 4, "L1": 4, "L2": 4, "L3": 4, "L4": 4}


def test_sft_gate_compares_l0_against_base():
    base = {"per_level": {"L0": {"executable_rate": 0.9, "mean_iou": 0.30}}}
    good = {"per_level": {"L0": {"executable_rate": 0.9, "mean_iou": 0.45}}}
    weak_exec = {"per_level": {"L0": {"executable_rate": 0.5, "mean_iou": 0.60}}}
    no_gain = {"per_level": {"L0": {"executable_rate": 0.9, "mean_iou": 0.25}}}
    assert _sft_gate(base, good)[0] is True
    assert _sft_gate(base, weak_exec)[0] is False
    assert _sft_gate(base, no_gain)[0] is False


def test_chaining_uses_training_weights_and_probes_use_sampler(tmp_path):
    from rl.track_a.run import _last_sampler_path, _last_weights_path

    record = (
        '{"name": "final", "batch": 2, '
        '"state_path": "tinker://m:train:0/weights/final", '
        '"sampler_path": "tinker://m:train:0/sampler_weights/final"}\n'
    )
    (tmp_path / "checkpoints.jsonl").write_text(record, encoding="utf-8")
    assert _last_weights_path(str(tmp_path)) == "tinker://m:train:0/weights/final"
    assert (
        _last_sampler_path(str(tmp_path))
        == "tinker://m:train:0/sampler_weights/final"
    )
