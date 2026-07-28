from __future__ import annotations

import json
import os
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
pytest.importorskip(
    "tinker_cookbook",
    reason="Tinker Cookbook is an optional RL dependency",
)

from rl.studies.representation_training_v1 import launcher
from rl.studies.representation_training_v1.protocol import (
    STUDY_ID,
    load_protocol,
    stage_spec,
)
from rl.studies.representation_training_v1.store import StageKey, TrainingStore


REPO_ROOT = Path(__file__).resolve().parents[4]


def _preflight(protocol: dict, stage_id: str, wave: str) -> dict:
    stage = stage_spec(protocol, stage_id)
    return {
        "protocol_file_sha256": "1" * 64,
        "prompt_assets": {"prompt": "2" * 64},
        "dataset": {
            "logical_release_sha256": protocol["dataset"][
                "logical_release_sha256"
            ]
        },
        "runtime": {"python": "3.13"},
        "sandbox": None,
        "schedule": {
            "stage_id": stage_id,
            "logical_sha256": "3" * 64,
        },
        "model": protocol["models"][stage.model_key],
        "recipe": protocol["recipes"][stage.recipe_key],
        "preflight_sha256": "4" * 64,
    }


def test_sft_launch_records_before_main_and_binds_wandb(
    tmp_path: Path,
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    source_sha = "a" * 40
    external = tmp_path / "external"
    monkeypatch.setenv("TINKER_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.delenv("WANDB_RUN_ID", raising=False)
    monkeypatch.setattr(launcher, "load_protocol", lambda *_a, **_k: protocol)
    monkeypatch.setattr(
        launcher,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(
        launcher,
        "stage_preflight",
        lambda **_kwargs: _preflight(
            protocol,
            "qwen-l0-sft",
            "complete",
        ),
    )
    access_calls: list[str] = []

    def validate_access(*, expected_entity):
        access_calls.append(expected_entity)
        return {"username": "test", "entity": expected_entity}

    async def fake_main(config):
        log = Path(config.log_path)
        assert (log.parent / "run_manifest.json").is_file()
        assert os.environ["WANDB_RUN_ID"].startswith("pxct-")
        assert os.environ["WANDB_RESUME"] == "never"
        assert os.environ["WANDB_MODE"] == "online"
        assert os.environ["WANDB_JOB_TYPE"] == "sft"
        log.mkdir(parents=True)
        checkpoints = [
            {
                "name": f"{step:06d}",
                "batch": step,
                "epoch": 0,
                "state_path": f"tinker://unit/weights/{step:06d}",
                "sampler_path": f"tinker://unit/sampler_weights/{step:06d}",
            }
            for step in (3, 6, 9)
        ]
        checkpoints.append(
            {
                "name": "final",
                "batch": 0,
                "epoch": 1,
                "state_path": "tinker://unit/weights/final",
                "sampler_path": "tinker://unit/sampler_weights/final",
            }
        )
        (log / "checkpoints.jsonl").write_text(
            "".join(json.dumps(value) + "\n" for value in checkpoints),
            encoding="utf-8",
        )
        (log / "metrics.jsonl").write_text(
            json.dumps({"step": 10, "train_mean_nll": 0.5}) + "\n",
            encoding="utf-8",
        )

    report = asyncio.run(
        launcher.run_training_stage(
            repo_root=REPO_ROOT,
            stage_id="qwen-l0-sft",
            wave_name="complete",
            replicate_id="r0",
            expected_source_sha=source_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            sft_main=fake_main,
            wandb_access_validator=validate_access,
        )
    )
    assert report["status"] == "complete"
    assert access_calls == [protocol["tracking"]["entity"]]
    assert report["checkpoint"]["state_path"] == "tinker://unit/weights/final"
    assert "WANDB_RUN_ID" not in os.environ

    async def forbidden_main(_config):
        raise AssertionError("completed wave must not call Tinker again")

    replay = asyncio.run(
        launcher.run_training_stage(
            repo_root=REPO_ROOT,
            stage_id="qwen-l0-sft",
            wave_name="complete",
            replicate_id="r0",
            expected_source_sha=source_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            sft_main=forbidden_main,
            wandb_access_validator=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("completed wave must not touch W&B")
            ),
        )
    )
    assert replay["status"] == "already_complete"


def test_bad_confirmation_cannot_reach_preflight_or_main(
    tmp_path: Path,
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    monkeypatch.setenv("TINKER_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setattr(launcher, "load_protocol", lambda *_a, **_k: protocol)
    monkeypatch.setattr(
        launcher,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(
        launcher,
        "stage_preflight",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("preflight should not run")
        ),
    )
    with pytest.raises(launcher.TrainingLaunchError, match="confirmation"):
        asyncio.run(
            launcher.run_training_stage(
                repo_root=REPO_ROOT,
                stage_id="qwen-l0-sft",
                wave_name="complete",
                replicate_id="r0",
                expected_source_sha="a" * 40,
                external_root=tmp_path / "external",
                confirmation="wrong",
                sft_main=lambda _config: (_ for _ in ()).throw(
                    AssertionError("main should not run")
                ),
            )
        )


def test_resolved_configs_seal_no_hidden_validation_and_raw_iou(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    store = TrainingStore(
        repo_root=REPO_ROOT,
        external_root=tmp_path / "external",
    )
    for stage_id, wave in (
        ("qwen-mixed-sft", "complete"),
        ("inkling-l4-rl", "smoke"),
    ):
        key = StageKey(STUDY_ID, stage_id, "r0")
        with store.acquire_stage_lock(key):
            manifest = store.create_or_verify_manifest(
                key,
                {"source_git_sha": "a" * 40},
            )
            spec = stage_spec(protocol, stage_id)
            resolved_launch = launcher._resolved_launch_binding(
                repo_root=REPO_ROOT,
                protocol=protocol,
                stage=spec,
                wave_name=wave,
                store=store,
                key=key,
                parent=None,
                resume_batch=None,
            )
            invocation = store.begin_invocation(
                key,
                invocation_id="unit-invocation",
                payload={
                    "invocation_id": "unit-invocation",
                    "run_manifest_record_sha256": manifest.record_sha256,
                    "source_git_sha": "a" * 40,
                    "protocol_logical_sha256": protocol["logical_sha256"],
                    "policy": {},
                    "initial_checkpoint": None,
                    "resume_batch": None,
                    "resolved_launch": resolved_launch,
                },
            )
            config = launcher.build_tinker_config(
                repo_root=REPO_ROOT,
                protocol=protocol,
                stage=spec,
                wave_name=wave,
                store=store,
                key=key,
                parent=None,
                invocation=invocation,
            )
        if stage_id == "qwen-mixed-sft":
            assert config.max_steps == 55
            assert config.learning_rate == 1e-4
            assert config.eval_every == 0
            assert config.dataset_builder.include_validation is False
            assert config.dataset_builder.schedule_seed == 90210
        else:
            assert config.max_steps == 1
            assert config.max_tokens == 60_000
            assert config.eval_every == 0
            assert config.dataset_builder.validation_canaries == 0
            assert config.dataset_builder.require_prefix_replay is False
            assert config.dataset_builder.reward_policy == "raw_iou"
            assert config.dataset_builder.schedule_seed == 90210


def test_tinker_config_rejects_invocation_policy_drift(tmp_path: Path) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "inkling-l4-rl")
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    store = TrainingStore(
        repo_root=REPO_ROOT,
        external_root=tmp_path / "external",
    )
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            {"source_git_sha": "a" * 40},
        )
        resolved = launcher._resolved_launch_binding(
            repo_root=REPO_ROOT,
            protocol=protocol,
            stage=stage,
            wave_name="smoke",
            store=store,
            key=key,
            parent=None,
            resume_batch=None,
        )
        resolved["sampling"]["temperature"] = 0.5
        invocation = store.begin_invocation(
            key,
            invocation_id="unit-drift",
            payload={
                "invocation_id": "unit-drift",
                "run_manifest_record_sha256": manifest.record_sha256,
                "source_git_sha": "a" * 40,
                "protocol_logical_sha256": protocol["logical_sha256"],
                "policy": {},
                "initial_checkpoint": None,
                "resume_batch": None,
                "resolved_launch": resolved,
            },
        )
        with pytest.raises(
            launcher.TrainingLaunchError,
            match="differs from the resolved",
        ):
            launcher.build_tinker_config(
                repo_root=REPO_ROOT,
                protocol=protocol,
                stage=stage,
                wave_name="smoke",
                store=store,
                key=key,
                parent=None,
                invocation=invocation,
            )


def test_inkling_extension_rechecks_exact_pilot_evidence() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "inkling-l4-rl")
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    checkpoint = {
        "name": "000006",
        "batch": 6,
        "epoch": 0,
        "final": False,
        "state_path": "tinker://unit/weights/000006",
        "sampler_path": "tinker://unit/sampler_weights/000006",
    }
    prior = SimpleNamespace(
        record_sha256="b" * 64,
        payload={"checkpoint": checkpoint},
    )
    approval_payload = {
        "decision": "approve",
        "approval_gate": "promotion-receipt-and-explicit-human-approval",
        "stage_id": stage.stage_id,
        "wave": "coverage-extension",
        "source_git_sha": "a" * 40,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "evaluation": {
            "stage_id": stage.stage_id,
            "wave": "pilot",
            "panel": "inkling-promotion",
            "training_wave_receipt_record_sha256": prior.record_sha256,
            "checkpoint": {
                **checkpoint,
                "role": "wave-ceiling",
                "training_progress_fraction": 6 / 14,
            },
        },
    }

    class FakeStore:
        def __init__(self, approval):
            self.approval = approval

        def load_wave_receipt(self, _key, *, wave):
            assert wave == "pilot"
            return prior

        def load_wave_approval(self, _key, *, wave):
            assert wave == "coverage-extension"
            return self.approval

    approval = SimpleNamespace(payload=approval_payload)
    assert (
        launcher._approval_record(
            store=FakeStore(approval),
            key=key,
            stage=stage,
            wave_name="coverage-extension",
            source_git_sha="a" * 40,
            protocol=protocol,
        )
        is approval
    )

    changed = dict(approval_payload)
    changed["evaluation"] = {
        **approval_payload["evaluation"],
        "training_wave_receipt_record_sha256": "c" * 64,
    }
    with pytest.raises(launcher.TrainingLaunchError, match="not bound"):
        launcher._approval_record(
            store=FakeStore(SimpleNamespace(payload=changed)),
            key=key,
            stage=stage,
            wave_name="coverage-extension",
            source_git_sha="a" * 40,
            protocol=protocol,
        )
