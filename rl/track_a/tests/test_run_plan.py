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
    assert _sft_gate(base, good, "L0", relative=False)[0] is True
    assert _sft_gate(base, weak_exec, "L0", relative=False)[0] is False
    assert _sft_gate(base, no_gain, "L0", relative=False)[0] is False


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


def test_fork_seeds_l0_and_drops_sft(tmp_path):
    import json as _json

    from rl.track_a.run import _fork_l0_stage

    source = tmp_path / "src-run"
    (source / "stages" / "rl-l0").mkdir(parents=True)
    (source / "stages" / "rl-l0" / "DONE").write_text("ok\n")
    (source / "stages" / "rl-l0" / "checkpoints.jsonl").write_text(
        '{"name": "000030", "batch": 30, "state_path": "tinker://m/weights/000030", '
        '"sampler_path": "tinker://m/sampler_weights/000030"}\n'
    )
    (source / "stages" / "rl-l0" / "metrics.jsonl").write_text('{"progress/batch": 29}\n')
    target = tmp_path / "dst-run"
    _fork_l0_stage(source, target)
    assert (target / "stages" / "rl-l0" / "checkpoints.jsonl").exists()
    assert not (target / "stages" / "rl-l0" / "DONE").exists()
    fork = _json.loads((target / "provenance" / "fork.json").read_text())
    assert "rl-l0" in fork["rl_l0_forked_from"]


def test_run_e_interleaves_l1_sft_after_forked_l0(tmp_path):
    stages = build_stages(
        RUN_PLANS["E"], run_root=tmp_path, wandb_project="pixcell-rl"
    )
    assert [stage.name for stage in stages] == [
        "sft-l0",
        "rl-l0",
        "sft-l1",
        "rl-l1",
        "rl-l2",
        "rl-l3",
        "rl-l4",
    ]
    sft_l1 = stages[2]
    assert sft_l1.args["levels"] == "L1"
    assert sft_l1.args["num_epochs"] == "1"
    assert sft_l1.sft_level == "L1"
    assert RUN_PLANS["E"].fork_from == "runA-l0sft-rl"


def test_run_f_uses_fifty_percent_backward_mix(tmp_path):
    stages = build_stages(
        RUN_PLANS["F"], run_root=tmp_path, wandb_project="pixcell-rl"
    )
    rl_l1 = [stage for stage in stages if stage.name == "rl-l1"][0]
    assert rl_l1.args["replay_groups_per_step"] == "4"
    assert not any(stage.name == "sft-l1" for stage in stages)


def test_run_g_is_the_full_ladder(tmp_path):
    stages = build_stages(
        RUN_PLANS["G"], run_root=tmp_path, wandb_project="pixcell-rl"
    )
    names = [stage.name for stage in stages]
    for level in ("l1", "l2", "l3", "l4"):
        assert f"sft-{level}" in names and names.index(f"sft-{level}") == names.index(f"rl-{level}") - 1


def test_fork_stages_through_seeds_prefix_and_reference(tmp_path):
    import json as _json

    from rl.track_a.run import _fork_stages_through

    source = tmp_path / "src-run"
    for name in ("sft-l0", "rl-l0"):
        d = source / "stages" / name
        d.mkdir(parents=True)
        (d / "DONE").write_text("ok\n")
        (d / "checkpoints.jsonl").write_text(
            '{"name": "final", "batch": 30, "state_path": "tinker://m/weights/final", '
            '"sampler_path": "tinker://m/sampler_weights/final"}\n'
        )
        (d / "metrics.jsonl").write_text("{}\n")
    (source / "probes").mkdir()
    (source / "probes" / "rl-l0.json").write_text('{"per_level": {"L1": {"executable_rate": 0.6, "mean_iou": 0.1}}}')
    target = tmp_path / "dst-run"
    _fork_stages_through(source, target, "rl-l0")
    assert (target / "stages" / "sft-l0" / "DONE").exists()
    assert (target / "stages" / "rl-l0" / "DONE").exists()
    origin = _json.loads((target / "probes" / "fork-origin.json").read_text())
    assert origin["per_level"]["L1"]["executable_rate"] == 0.6
    fork = _json.loads((target / "provenance" / "fork.json").read_text())
    assert fork["stages"] == ["sft-l0", "rl-l0"]


def test_relative_gate_allows_small_exec_loss_but_demands_iou_gain():
    from rl.track_a.run import _sft_gate

    reference = {"per_level": {"L1": {"executable_rate": 0.60, "mean_iou": 0.10}}}
    better = {"per_level": {"L1": {"executable_rate": 0.55, "mean_iou": 0.16}}}
    lost_exec = {"per_level": {"L1": {"executable_rate": 0.40, "mean_iou": 0.30}}}
    no_gain = {"per_level": {"L1": {"executable_rate": 0.70, "mean_iou": 0.08}}}
    assert _sft_gate(reference, better, "L1", relative=True)[0] is True
    assert _sft_gate(reference, lost_exec, "L1", relative=True)[0] is False
    assert _sft_gate(reference, no_gain, "L1", relative=True)[0] is False
