from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.track_a.recipe import (
    file_sha256,
    load_recipe,
    validate_evaluation_cli,
    validate_rl_cli,
    validate_resolved_binding,
    validate_sft_cli,
)
import rl.track_a.recipe as recipe_module


REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_PATH = REPO_ROOT / "rl" / "track_a" / "preflight.py"


def _preflight_module():
    spec = importlib.util.spec_from_file_location(
        "pixcell_track_a_preflight_test",
        PREFLIGHT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paid_launch_clean_gate_includes_untracked_files(monkeypatch, tmp_path):
    module = _preflight_module()
    calls: list[list[str]] = []

    def fake_check_output(command, **_kwargs):
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return "abc123\n"
        return "?? rl/new_training_code.py\n"

    monkeypatch.setattr(module.subprocess, "check_output", fake_check_output)

    state = module._git_state(tmp_path, require_clean=False)
    assert state == {"head": "abc123", "clean": False}
    assert ["git", "status", "--porcelain", "--untracked-files=all"] in calls

    with pytest.raises(RuntimeError, match="including untracked files"):
        module._git_state(tmp_path, require_clean=True)


def _canonical_sft_config() -> SimpleNamespace:
    recipe = load_recipe(REPO_ROOT)
    return SimpleNamespace(
        confirm_spend=recipe["launch"]["confirmation_tokens"]["sft"],
        dataset_root=str(REPO_ROOT / "dataset"),
        model_name=recipe["model"]["name"],
        renderer_name=recipe["model"]["renderer"],
        lora_rank=recipe["model"]["lora_rank"],
        learning_rate=recipe["sft"]["learning_rate"],
        lr_schedule=recipe["sft"]["tinker_lr_schedule"],
        num_epochs=recipe["sft"]["effective_passes"],
        batch_size=recipe["sft"]["batch_size"],
        max_length=recipe["sft"]["max_sequence_tokens"],
        max_image=recipe["model"]["max_image_long_edge"],
        save_every=recipe["sft"]["save_every_steps"],
        eval_every=recipe["sft"]["evaluate_every_steps"],
        max_steps=recipe["sft"]["max_steps"],
        log_path=str(REPO_ROOT / "rl" / "track_a" / "runs" / "test-run"),
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("dataset_root", "/tmp/other-dataset"),
        ("model_name", "another/model"),
        ("renderer_name", "another-renderer"),
        ("max_length", 1024),
        ("batch_size", 1),
        ("max_steps", 1),
    ],
)
def test_paid_sft_rejects_preflight_launch_mismatches(name, value):
    cfg = _canonical_sft_config()
    setattr(cfg, name, value)
    with pytest.raises(ValueError, match=name):
        validate_sft_cli(REPO_ROOT, cfg)


def test_resolved_launch_is_revalidated_in_preflight():
    binding = validate_sft_cli(REPO_ROOT, _canonical_sft_config())
    assert validate_resolved_binding(REPO_ROOT, binding) == binding
    tampered = json.loads(json.dumps(binding))
    tampered["max_length"] = 512
    with pytest.raises(ValueError, match="max_length"):
        validate_resolved_binding(REPO_ROOT, tampered)


def _mastery_report(sampler_path: str) -> dict:
    mastered = {
        "mean_iou_at_1": 0.9,
        "pure_executable_rate": 1.0,
    }
    unmastered = {
        "mean_iou_at_1": 0.5,
        "pure_executable_rate": 1.0,
    }
    return {
        "sampler_path": sampler_path,
        "levels_summary": {
            "L0": mastered,
            "L1": unmastered,
            "L2": unmastered,
            "L3": unmastered,
            "L4": unmastered,
        },
    }


def _canonical_rl_config(mastery_path: Path) -> SimpleNamespace:
    recipe = load_recipe(REPO_ROOT)
    sampler = "tinker://run-id:train:0/sampler_weights/000014"
    return SimpleNamespace(
        confirm_spend=recipe["launch"]["confirmation_tokens"]["rl"],
        dataset_root=str(REPO_ROOT / "dataset"),
        model_name=recipe["model"]["name"],
        renderer_name=recipe["model"]["renderer"],
        lora_rank=recipe["model"]["lora_rank"],
        group_size=recipe["rl"]["group_size"],
        groups_per_batch=recipe["rl"]["groups_per_batch"],
        learning_rate=recipe["rl"]["learning_rate"],
        max_tokens=recipe["rl"]["max_output_tokens"],
        temperature=recipe["rl"]["temperature"],
        max_steps=recipe["rl"]["stage_max_steps"],
        eval_every=recipe["rl"]["evaluate_every_steps"],
        save_every=recipe["rl"]["save_every_steps"],
        log_path=str(REPO_ROOT / "rl" / "track_a" / "runs" / "test-rl"),
        loss_fn=recipe["rl"]["loss_fn"],
        load_checkpoint_path=sampler.replace("/sampler_weights/", "/weights/"),
        mastery_report=str(mastery_path),
        current_level="L1",
        replay_levels="L0",
    )


def test_rl_binding_pins_checkpoint_and_mastery_bytes(tmp_path):
    sampler = "tinker://run-id:train:0/sampler_weights/000014"
    mastery_path = tmp_path / "mastery.json"
    mastery_path.write_text(
        json.dumps(_mastery_report(sampler)),
        encoding="utf-8",
    )
    cfg = _canonical_rl_config(mastery_path)

    binding = validate_rl_cli(
        REPO_ROOT,
        cfg,
        mastery_report=_mastery_report(sampler),
    )

    assert binding["load_checkpoint_path"] == (
        "tinker://run-id:train:0/weights/000014"
    )
    assert binding["mastery_report"] == str(mastery_path.resolve())
    assert binding["mastery_report_sha256"] == file_sha256(mastery_path)

    cfg.load_checkpoint_path = "tinker://other:train:0/weights/000014"
    with pytest.raises(ValueError, match="load_checkpoint_path"):
        validate_rl_cli(
            REPO_ROOT,
            cfg,
            mastery_report=_mastery_report(sampler),
        )


def test_preflight_rejects_mastery_report_changed_after_binding(tmp_path):
    sampler = "tinker://run-id:train:0/sampler_weights/000014"
    mastery_path = tmp_path / "mastery.json"
    mastery_path.write_text(
        json.dumps(_mastery_report(sampler)),
        encoding="utf-8",
    )
    cfg = _canonical_rl_config(mastery_path)
    binding = validate_rl_cli(
        REPO_ROOT,
        cfg,
        mastery_report=_mastery_report(sampler),
    )
    binding["candidate_sandbox"] = {
        "runtime_path": "/usr/bin/docker",
        "daemon_endpoint": "unix:///tmp/docker.sock",
        "image_ref": "sha256:" + "a" * 64,
        "image_id": "sha256:" + "a" * 64,
        "workspace_root": "/tmp/evaluator",
    }
    mastery_path.write_text(
        json.dumps({**_mastery_report(sampler), "changed": True}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="mastery_report_sha256"):
        validate_resolved_binding(REPO_ROOT, binding)


def test_preflight_recomputes_first_unmastered_level(
    monkeypatch,
    tmp_path,
):
    import rl.track_a.evaluation_contract as evaluation_contract

    sampler = "tinker://run-id:train:0/sampler_weights/000014"
    mastery_path = tmp_path / "mastery.json"
    mastery_path.write_text(
        json.dumps(_mastery_report(sampler)),
        encoding="utf-8",
    )
    binding = validate_rl_cli(
        REPO_ROOT,
        _canonical_rl_config(mastery_path),
        mastery_report=_mastery_report(sampler),
    )
    boundary = SimpleNamespace(
        runtime_path=Path("/usr/bin/docker"),
        daemon_endpoint="unix:///tmp/docker.sock",
        image_ref="sha256:" + "a" * 64,
        image_id="sha256:" + "a" * 64,
        workspace_root=Path("/tmp/evaluator"),
    )
    binding["candidate_sandbox"] = {
        "runtime_path": str(boundary.runtime_path),
        "daemon_endpoint": boundary.daemon_endpoint,
        "image_ref": boundary.image_ref,
        "image_id": boundary.image_id,
        "workspace_root": str(boundary.workspace_root),
    }
    binding["current_level"] = "L2"
    binding["replay_levels"] = ["L0", "L1"]
    monkeypatch.setattr(
        evaluation_contract,
        "build_checkpoint_selection_contract",
        lambda *_args: object(),
    )
    monkeypatch.setattr(
        evaluation_contract,
        "validate_evaluation_report",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        recipe_module,
        "require_execution_boundary",
        lambda: boundary,
    )

    with pytest.raises(ValueError, match="first unmastered level L1"):
        validate_resolved_binding(REPO_ROOT, binding)


def _canonical_evaluation_args(output: Path) -> SimpleNamespace:
    recipe = load_recipe(REPO_ROOT)
    return SimpleNamespace(
        confirm_spend=recipe["launch"]["confirmation_tokens"]["evaluation"],
        dataset_root=REPO_ROOT / "dataset",
        model_name=recipe["model"]["name"],
        renderer_name=recipe["model"]["renderer"],
        sampler_path="tinker://run-id:train:0/sampler_weights/000014",
        behavioral_probe=False,
        levels="",
        rows=0,
        k=recipe["checkpoint_evaluation"]["geometry_k"],
        temperature=recipe["rl"]["temperature"],
        max_tokens=recipe["rl"]["max_output_tokens"],
        concurrency=recipe["checkpoint_evaluation"]["sampling_concurrency"],
        evaluator_workers=recipe["checkpoint_evaluation"]["evaluator_workers"],
        seed=recipe["checkpoint_evaluation"]["task_selection_seed"],
        include_records=recipe["checkpoint_evaluation"]["include_records"],
        output=output,
    )


def test_evaluation_binding_pins_sampler_and_new_contained_output(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(recipe_module, "RUNS_RELATIVE_PATH", tmp_path)
    output = tmp_path / "checkpoint.json"
    args = _canonical_evaluation_args(output)

    binding = validate_evaluation_cli(REPO_ROOT, args)

    assert binding["sampler_path"] == args.sampler_path
    assert binding["output"] == str(output.resolve())

    output.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(ValueError, match="must not already exist"):
        validate_evaluation_cli(REPO_ROOT, args)


def test_evaluation_output_must_stay_in_report_directory(
    monkeypatch,
    tmp_path,
):
    report_root = tmp_path / "reports"
    monkeypatch.setattr(recipe_module, "RUNS_RELATIVE_PATH", report_root)
    args = _canonical_evaluation_args(tmp_path / "outside.json")

    with pytest.raises(ValueError, match="JSON child"):
        validate_evaluation_cli(REPO_ROOT, args)
