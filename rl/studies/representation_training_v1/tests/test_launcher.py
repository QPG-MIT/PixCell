from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
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
        "dataset": {"logical_release_sha256": protocol["dataset"]["logical_release_sha256"]},
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


def _cross_source_parent_records(
    protocol: dict,
    *,
    producer_source_git_sha: str,
    consumer_source_git_sha: str,
) -> tuple[dict, SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    checkpoint = {
        "name": "final",
        "batch": 11,
        "epoch": 1,
        "final": True,
        "state_path": "tinker://unit/weights/final",
        "sampler_path": "tinker://unit/sampler_weights/final",
        "role": "terminal",
        "training_progress_fraction": 1.0,
    }
    inventory_sha = launcher.canonical_sha256([checkpoint])
    parent_manifest = SimpleNamespace(
        payload={
            "source_git_sha": producer_source_git_sha,
            "protocol_logical_sha256": protocol["logical_sha256"],
            "contract_version": protocol["contract_version"],
            "stage": {
                "stage_id": "qwen-l0-sft",
                "model_key": "qwen",
            },
        },
        payload_sha256="1" * 64,
        record_sha256="2" * 64,
        relative_path=(
            "studies/representation-training-v1/stages/qwen-l0-sft/runs/r0/run_manifest.json"
        ),
    )
    receipt = SimpleNamespace(
        payload={
            "stage_id": "qwen-l0-sft",
            "wave": "complete",
            "run_manifest_record_sha256": parent_manifest.record_sha256,
            "checkpoint": {
                key: checkpoint[key]
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
                "count": 1,
                "entries": [checkpoint],
                "logical_sha256": inventory_sha,
            },
        },
        payload_sha256="3" * 64,
        record_sha256="4" * 64,
        relative_path=(
            "studies/representation-training-v1/stages/"
            "qwen-l0-sft/runs/r0/waves/complete/receipt.json"
        ),
    )
    approval_payload = {
        "schema_version": (launcher.SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION),
        "stage_id": "qwen-l0-rl-l1",
        "wave": "smoke",
        "source_git_sha": consumer_source_git_sha,
        "evidence_source_git_sha": producer_source_git_sha,
        "parent_stage_id": "qwen-l0-sft",
        "parent_wave": "complete",
        "parent_receipt_record_sha256": receipt.record_sha256,
        "selected_parent_checkpoint": checkpoint,
        "selected_parent_checkpoint_inventory_sha256": inventory_sha,
        "source_transition": {"logical_sha256": "5" * 64},
    }
    approval = SimpleNamespace(
        payload=approval_payload,
        payload_sha256="6" * 64,
        record_sha256="7" * 64,
        relative_path=(
            "studies/representation-training-v1/stages/"
            "qwen-l0-rl-l1/runs/r0/waves/smoke/approval.json"
        ),
    )
    return checkpoint, parent_manifest, receipt, approval


def _write_unit_sft_artifacts(config) -> None:
    log = Path(config.log_path)
    log.mkdir(parents=True, exist_ok=True)
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


class _FakeRun:
    def __init__(self, module, kwargs):
        self._module = module
        self.id = kwargs["id"]
        self.entity = kwargs["entity"]
        self.project = kwargs["project"]
        self.name = kwargs["name"]
        self.group = kwargs["group"]
        self.job_type = kwargs["job_type"]
        self.tags = kwargs["tags"]
        self.resumed = kwargs["resume"] == "must"
        self.url = f"https://wandb.example/{self.id}"
        self.settings = SimpleNamespace(
            root_dir=kwargs["dir"],
            resume=kwargs["resume"],
        )
        self.dir = str(Path(kwargs["dir"]) / "wandb" / self.id / "files")
        Path(self.dir).mkdir(parents=True, exist_ok=True)
        self.finished = False

    def finish(self):
        self.finished = True
        self._module.run = None


class _FakeConfig:
    def __init__(self, initial=None):
        self.values = dict(initial or {})
        self.updates = []

    def update(self, value, allow_val_change=None):
        payload = dict(value)
        changed = [
            key for key, item in payload.items() if key in self.values and self.values[key] != item
        ]
        if changed and allow_val_change is not True:
            raise RuntimeError("config changed without allow_val_change: " + ", ".join(changed))
        self.values.update(payload)
        self.updates.append(
            {
                "value": payload,
                "allow_val_change": allow_val_change,
            }
        )


class _FakeWandb:
    def __init__(self, *, initial_config=None):
        self.run = None
        self.calls = []
        self.config = _FakeConfig(initial_config)

    def init(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("config") is not None:
            self.config.update(kwargs["config"])
        self.run = _FakeRun(self, kwargs)
        return self.run

    def finish(self):
        if self.run is not None:
            self.run.finish()


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
        assert os.environ["WANDB_ENTITY"] == expected_entity
        assert os.environ["WANDB_PROJECT"] == protocol["tracking"]["project"]
        assert os.environ["WANDB_RUN_ID"].startswith("pxct-")
        assert os.environ["WANDB_RESUME"] == "never"
        return {"username": "test", "entity": expected_entity}

    async def fake_main(config):
        log = Path(config.log_path)
        assert (log.parent / "run_manifest.json").is_file()
        assert os.environ["WANDB_RUN_ID"].startswith("pxct-")
        assert os.environ["WANDB_RESUME"] == "never"
        assert os.environ["WANDB_MODE"] == "online"
        assert os.environ["WANDB_JOB_TYPE"] == "sft"
        _write_unit_sft_artifacts(config)

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


def test_source_is_revalidated_after_preflight_before_any_live_boundary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    source_sha = "9" * 40
    events: list[str] = []
    source_checks = 0
    monkeypatch.setenv("TINKER_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setattr(launcher, "load_protocol", lambda *_a, **_k: protocol)

    def validate_source(_root, expected):
        nonlocal source_checks
        source_checks += 1
        events.append(f"source-{source_checks}")
        if source_checks == 1:
            return expected
        raise ValueError("paid training requires a completely clean worktree")

    monkeypatch.setattr(launcher, "validate_source_sha", validate_source)
    monkeypatch.setattr(
        launcher,
        "stage_preflight",
        lambda **_kwargs: (
            events.append("preflight") or _preflight(protocol, "qwen-mixed-sft", "complete")
        ),
    )

    async def forbidden_main(_config):
        events.append("training")
        raise AssertionError("source race reached training")

    def forbidden_wandb(**_kwargs):
        events.append("wandb")
        raise AssertionError("source race reached W&B")

    with pytest.raises(
        launcher.TrainingLaunchError,
        match="source changed after preflight",
    ):
        asyncio.run(
            launcher.run_training_stage(
                repo_root=REPO_ROOT,
                stage_id="qwen-mixed-sft",
                wave_name="complete",
                replicate_id="r0",
                expected_source_sha=source_sha,
                external_root=tmp_path / "external",
                confirmation=protocol["launch"]["confirmation_token"],
                sft_main=forbidden_main,
                wandb_access_validator=forbidden_wandb,
            )
        )
    assert events == ["source-1", "preflight", "source-2"]


def test_already_complete_rejects_minimal_receipt_before_live_boundaries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    source_sha = "8" * 40
    external = tmp_path / "external"
    stage = stage_spec(protocol, "qwen-mixed-sft")
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    preflight = _preflight(protocol, stage.stage_id, "complete")
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    tracking = launcher._tracking_binding(
        protocol=protocol,
        source_git_sha=source_sha,
        key=key,
        stage=stage,
        store=store,
    )
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            launcher._manifest_payload(
                protocol=protocol,
                source_git_sha=source_sha,
                stage=stage,
                preflight=preflight,
                tracking=tracking,
                parent=None,
            ),
        )
        store.write_wave_receipt(
            key,
            wave="complete",
            payload={
                "stage_id": stage.stage_id,
                "wave": "complete",
                "run_manifest_record_sha256": manifest.record_sha256,
            },
        )
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
        lambda **_kwargs: preflight,
    )
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="receipt fields differ",
    ):
        asyncio.run(
            launcher.run_training_stage(
                repo_root=REPO_ROOT,
                stage_id=stage.stage_id,
                wave_name="complete",
                replicate_id="r0",
                expected_source_sha=source_sha,
                external_root=external,
                confirmation=protocol["launch"]["confirmation_token"],
                sft_main=lambda _config: (_ for _ in ()).throw(
                    AssertionError("minimal receipt reached training")
                ),
                wandb_access_validator=lambda **_kwargs: (_ for _ in ()).throw(
                    AssertionError("minimal receipt reached W&B")
                ),
            )
        )


def test_already_complete_rejects_forged_receipt_bindings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    source_sha = "7" * 40
    external = tmp_path / "external"
    key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")
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
        lambda **_kwargs: _preflight(protocol, key.stage_id, "complete"),
    )

    async def fake_main(config):
        _write_unit_sft_artifacts(config)

    asyncio.run(
        launcher.run_training_stage(
            repo_root=REPO_ROOT,
            stage_id=key.stage_id,
            wave_name="complete",
            replicate_id="r0",
            expected_source_sha=source_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            sft_main=fake_main,
            wandb_access_validator=lambda **_kwargs: {"entity": "unit"},
        )
    )
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    original = store.load_wave_receipt(key, wave="complete")
    assert original is not None
    receipt_path = external.joinpath(*original.relative_path.parts)
    cases = [
        (
            "final optimizer metric",
            lambda payload: payload["final_training_metric"].update({"step": 0}),
        ),
        (
            "canonical training artifacts",
            lambda payload: payload["final_training_metric"].update({"train_mean_nll": 0.125}),
        ),
        (
            "canonical training artifacts",
            lambda payload: payload["local_artifact_sha256"].update({"metrics.jsonl": "f" * 64}),
        ),
        (
            "candidate_inventory",
            lambda payload: payload["candidate_inventory"].update({"expected_count": 1}),
        ),
        (
            "invocation is missing or differs",
            lambda payload: payload.update({"invocation_record_sha256": "0" * 64}),
        ),
    ]
    for message, mutate in cases:
        receipt_path.unlink()
        forged = copy.deepcopy(original.payload)
        mutate(forged)
        with store.acquire_stage_lock(key):
            store.write_wave_receipt(
                key,
                wave="complete",
                payload=forged,
            )
        with pytest.raises(launcher.TrainingLaunchError, match=message):
            asyncio.run(
                launcher.run_training_stage(
                    repo_root=REPO_ROOT,
                    stage_id=key.stage_id,
                    wave_name="complete",
                    replicate_id="r0",
                    expected_source_sha=source_sha,
                    external_root=external,
                    confirmation=protocol["launch"]["confirmation_token"],
                    sft_main=lambda _config: (_ for _ in ()).throw(
                        AssertionError("forged receipt reached training")
                    ),
                    wandb_access_validator=lambda **_kwargs: (_ for _ in ()).throw(
                        AssertionError("forged receipt reached W&B")
                    ),
                )
            )

    receipt_path.unlink()
    with store.acquire_stage_lock(key):
        store.write_wave_receipt(
            key,
            wave="complete",
            payload=original.payload,
        )
    metrics_path = store.tinker_log_path(key) / "metrics.jsonl"
    original_metrics = metrics_path.read_bytes()
    metrics_path.write_text(
        json.dumps({"step": 10, "train_mean_nll": 0.125}) + "\n",
        encoding="utf-8",
    )
    try:
        with pytest.raises(
            launcher.TrainingLaunchError,
            match="canonical training artifacts",
        ):
            asyncio.run(
                launcher.run_training_stage(
                    repo_root=REPO_ROOT,
                    stage_id=key.stage_id,
                    wave_name="complete",
                    replicate_id="r0",
                    expected_source_sha=source_sha,
                    external_root=external,
                    confirmation=protocol["launch"]["confirmation_token"],
                    sft_main=lambda _config: (_ for _ in ()).throw(
                        AssertionError("mutated metrics reached training")
                    ),
                    wandb_access_validator=lambda **_kwargs: (_ for _ in ()).throw(
                        AssertionError("mutated metrics reached W&B")
                    ),
                )
            )
    finally:
        metrics_path.write_bytes(original_metrics)


def test_completed_rl_receipt_requires_every_candidate_and_sample(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    source_sha = "6" * 40
    external = tmp_path / "external"
    stage = stage_spec(protocol, "inkling-l4-rl")
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    wave = "smoke"
    preflight = _preflight(protocol, stage.stage_id, wave)
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    tracking = launcher._tracking_binding(
        protocol=protocol,
        source_git_sha=source_sha,
        key=key,
        stage=stage,
        store=store,
    )
    invocation_id = "smoke-unit"
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            launcher._manifest_payload(
                protocol=protocol,
                source_git_sha=source_sha,
                stage=stage,
                preflight=preflight,
                tracking=tracking,
                parent=None,
            ),
        )
        resolved = launcher._resolved_launch_binding(
            repo_root=REPO_ROOT,
            protocol=protocol,
            stage=stage,
            wave_name=wave,
            store=store,
            key=key,
            parent=None,
            resume_batch=None,
        )
        invocation = store.begin_invocation(
            key,
            invocation_id=invocation_id,
            payload=launcher._invocation_payload(
                protocol=protocol,
                stage=stage,
                wave_name=wave,
                source_git_sha=source_sha,
                invocation_id=invocation_id,
                manifest=manifest,
                preflight=preflight,
                tracking=tracking,
                resume_batch=None,
                resolved_launch=resolved,
                parent=None,
            ),
        )
        recipe = protocol["recipes"][stage.recipe_key]
        expected = int(recipe["groups_per_batch"]) * int(recipe["group_size"])
        for index in range(expected):
            task_id = f"unit-{index:02d}"
            store.write_candidate_sample(
                key,
                invocation_id=invocation_id,
                step=0,
                task_id=task_id,
                attempt=1,
                payload={"index": index},
            )
            store.write_candidate(
                key,
                invocation_id=invocation_id,
                step=0,
                task_id=task_id,
                attempt=1,
                payload={"index": index},
            )
        candidate_root = store.tinker_log_path(key).parent / "candidates" / invocation_id
        candidate_files = sorted(candidate_root.rglob("evaluation.json"))
        log_path = store.tinker_log_path(key)
        log_path.mkdir(parents=True, exist_ok=True)
        (log_path / "checkpoints.jsonl").write_text(
            json.dumps(
                {
                    "name": "000001",
                    "batch": 1,
                    "epoch": None,
                    "state_path": "tinker://unit/weights/000001",
                    "sampler_path": "tinker://unit/sampler_weights/000001",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (log_path / "metrics.jsonl").write_text(
            json.dumps({"step": 0, "optim/entropy": 0.5}) + "\n",
            encoding="utf-8",
        )
        receipt = store.write_wave_receipt(
            key,
            wave=wave,
            payload=launcher._checkpoint_receipt(
                stage=stage,
                wave_name=wave,
                log_path=log_path,
                manifest=manifest,
                preflight=preflight,
                invocation=invocation,
                tracking=None,
            ),
        )
    launcher._validate_completed_wave_receipt(
        repo_root=REPO_ROOT,
        protocol=protocol,
        store=store,
        key=key,
        stage=stage,
        wave_name=wave,
        manifest=manifest,
        preflight=preflight,
        parent=None,
        receipt=receipt,
    )
    checkpoints_path = log_path / "checkpoints.jsonl"
    original_checkpoints = checkpoints_path.read_bytes()
    metrics_path = log_path / "metrics.jsonl"
    original_metrics = metrics_path.read_bytes()
    with checkpoints_path.open("ab") as stream:
        stream.write(
            (
                json.dumps(
                    {
                        "name": "final",
                        "batch": 1,
                        "state_path": "tinker://unit/weights/final",
                        "sampler_path": "tinker://unit/sampler_weights/final",
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "name": "000005",
                        "batch": 5,
                        "state_path": "tinker://unit/weights/000005",
                        "sampler_path": "tinker://unit/sampler_weights/000005",
                    }
                )
                + "\n"
            ).encode("utf-8")
        )
    with metrics_path.open("ab") as stream:
        stream.write(
            (json.dumps({"step": 4, "optim/entropy": 0.25}) + "\n").encode("utf-8")
        )
    # A later wave appends to Cookbook's shared log.  The earlier receipt
    # remains reconstructable from its immutable prefix snapshot.
    launcher._validate_completed_wave_receipt(
        repo_root=REPO_ROOT,
        protocol=protocol,
        store=store,
        key=key,
        stage=stage,
        wave_name=wave,
        manifest=manifest,
        preflight=preflight,
        parent=None,
        receipt=receipt,
    )
    checkpoints_path.write_bytes(original_checkpoints)
    metrics_path.write_bytes(original_metrics)
    metrics_path.write_text(
        json.dumps({"step": 0, "optim/entropy": 0.25}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="canonical training artifacts",
    ):
        launcher._validate_completed_wave_receipt(
            repo_root=REPO_ROOT,
            protocol=protocol,
            store=store,
            key=key,
            stage=stage,
            wave_name=wave,
            manifest=manifest,
            preflight=preflight,
            parent=None,
            receipt=receipt,
        )
    metrics_path.write_bytes(original_metrics)
    checkpoints_path.unlink()
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="without a resumable checkpoint",
    ):
        launcher._validate_completed_wave_receipt(
            repo_root=REPO_ROOT,
            protocol=protocol,
            store=store,
            key=key,
            stage=stage,
            wave_name=wave,
            manifest=manifest,
            preflight=preflight,
            parent=None,
            receipt=receipt,
        )
    checkpoints_path.write_bytes(original_checkpoints)
    candidate_files[0].unlink()
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="candidate_inventory",
    ):
        launcher._validate_completed_wave_receipt(
            repo_root=REPO_ROOT,
            protocol=protocol,
            store=store,
            key=key,
            stage=stage,
            wave_name=wave,
            manifest=manifest,
            preflight=preflight,
            parent=None,
            receipt=receipt,
        )


def test_resume_pins_receipt_checkpoint_instead_of_later_cookbook_final(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-base-rl-l0")
    log_path = tmp_path / "tinker"
    log_path.mkdir()
    numbered = {
        "name": "000001",
        "batch": 1,
        "state_path": "tinker://unit/weights/000001",
        "sampler_path": "tinker://unit/sampler_weights/000001",
    }
    terminal_final = {
        "name": "final",
        "batch": 1,
        "state_path": "tinker://unit/weights/final",
        "sampler_path": "tinker://unit/sampler_weights/final",
    }
    (log_path / "checkpoints.jsonl").write_text(
        json.dumps(numbered) + "\n" + json.dumps(terminal_final) + "\n",
        encoding="utf-8",
    )
    prior = SimpleNamespace(
        payload={
            "checkpoint": {
                **numbered,
                "epoch": None,
                "final": True,
            }
        }
    )

    # Unsealed Cookbook behavior selects the later, different final URI.
    assert (
        launcher.checkpoint_utils.get_last_checkpoint(str(log_path)).state_path
        == terminal_final["state_path"]
    )
    binding = launcher._validate_resume_state(
        stage=stage,
        wave_name="step-5",
        log_path=log_path,
        prior_wave_receipt=prior,
    )
    assert binding is not None
    assert binding.batch == 1
    assert binding.checkpoint["state_path"] == numbered["state_path"]
    invocation = launcher._invocation_payload(
        protocol=protocol,
        stage=stage,
        wave_name="step-5",
        source_git_sha="a" * 40,
        invocation_id="resume-unit",
        manifest=SimpleNamespace(record_sha256="b" * 64),
        preflight={"preflight_sha256": "c" * 64},
        tracking={"run_id": "unit"},
        resume_batch=binding.batch,
        resume_checkpoint=binding.checkpoint,
        resolved_launch={"logical_sha256": "d" * 64},
        parent=None,
    )
    assert invocation["resume_batch"] == 1
    assert invocation["resume_checkpoint"] == binding.checkpoint

    with launcher._sealed_cookbook_resume(
        stage=stage,
        wave_name="step-5",
        log_path=log_path,
        prior_wave_receipt=prior,
        expected=binding,
    ):
        selected = launcher.checkpoint_utils.get_last_checkpoint(str(log_path))
        assert selected.state_path == numbered["state_path"]
        assert selected.sampler_path == numbered["sampler_path"]

    with (log_path / "checkpoints.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "name": "000002",
                    "batch": 2,
                    "state_path": "tinker://unit/weights/000002",
                    "rolling": True,
                }
            )
            + "\n"
        )
    with launcher._sealed_cookbook_resume(
        stage=stage,
        wave_name="step-5",
        log_path=log_path,
        prior_wave_receipt=prior,
        expected=binding,
    ):
        with pytest.raises(
            launcher.TrainingLaunchError,
            match="changed after the immutable invocation",
        ):
            launcher.checkpoint_utils.get_last_checkpoint(str(log_path))


def test_resume_rejects_unreceipted_terminal_checkpoint(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-base-rl-l0")
    log_path = tmp_path / "tinker"
    log_path.mkdir()
    (log_path / "checkpoints.jsonl").write_text(
        json.dumps(
            {
                "name": "final",
                "batch": 1,
                "state_path": "tinker://unit/weights/final",
                "sampler_path": "tinker://unit/sampler_weights/final",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="wave ceiling without an immutable receipt",
    ):
        launcher._validate_resume_state(
            stage=stage,
            wave_name="smoke",
            log_path=log_path,
            prior_wave_receipt=None,
        )


def test_builtin_sft_records_observed_wandb_before_service_client(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tinker_cookbook.supervised import train as supervised_train
    from tinker_cookbook.utils import ml_log

    protocol = load_protocol(REPO_ROOT)
    source_sha = "b" * 40
    external = tmp_path / "external"
    fake_wandb = _FakeWandb()
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
        lambda **_kwargs: _preflight(
            protocol,
            "qwen-l0-sft",
            "complete",
        ),
    )
    monkeypatch.setattr(ml_log, "wandb", fake_wandb)
    monkeypatch.setattr(ml_log, "_wandb_available", True)
    real_import = launcher.importlib.import_module
    monkeypatch.setattr(
        launcher.importlib,
        "import_module",
        lambda name: fake_wandb if name == "wandb" else real_import(name),
    )
    service_client_markers = []

    def validate_access(*, expected_entity):
        assert os.environ["WANDB_ENTITY"] == expected_entity
        assert os.environ["WANDB_RUN_ID"].startswith("pxct-")
        return {"username": "test", "entity": expected_entity}

    async def fake_builtin_main(config):
        logger = ml_log.setup_logging(
            log_dir=config.log_path,
            wandb_project=config.wandb_project,
            wandb_name=config.wandb_name,
            config=config,
            do_configure_logging_module=False,
        )
        tracking_paths = list(external.rglob("tracking.json"))
        assert len(tracking_paths) == 1
        tracking_document = json.loads(tracking_paths[0].read_text(encoding="utf-8"))
        assert tracking_document["payload"]["observed"]["run_id"] == fake_wandb.calls[0]["id"]
        assert service_client_markers == []
        service_client_markers.append("created")
        logger.close()
        _write_unit_sft_artifacts(config)

    monkeypatch.setattr(supervised_train, "main", fake_builtin_main)
    report = asyncio.run(
        launcher.run_training_stage(
            repo_root=REPO_ROOT,
            stage_id="qwen-l0-sft",
            wave_name="complete",
            replicate_id="r0",
            expected_source_sha=source_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            wandb_access_validator=validate_access,
        )
    )
    assert report["status"] == "complete"
    assert service_client_markers == ["created"]
    assert fake_wandb.calls[0]["config"] is None
    assert len(fake_wandb.config.updates) == 2
    assert fake_wandb.config.updates[0]["allow_val_change"] is False
    assert fake_wandb.config.updates[1]["allow_val_change"] is None
    assert fake_wandb.config.updates[0]["value"] == fake_wandb.config.updates[1]["value"]
    assert "dataset_builder" in fake_wandb.config.values
    key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    tracking_paths = list(external.rglob("tracking.json"))
    tracking_document = json.loads(tracking_paths[0].read_text(encoding="utf-8"))
    invocation_id = tracking_document["key"]["invocation_id"]
    tracking = store.load_invocation_tracking(
        key,
        invocation_id=invocation_id,
    )
    receipt = store.load_wave_receipt(key, wave="complete")
    assert tracking is not None
    assert receipt is not None
    assert receipt.payload["invocation_tracking_record_sha256"] == tracking.record_sha256


def test_builtin_rl_records_observed_wandb_before_service_client(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from rl.track_b import tml_shim
    from tinker_cookbook.rl import train as rl_train
    from tinker_cookbook.utils import ml_log

    protocol = load_protocol(REPO_ROOT)
    source_sha = "c" * 40
    external = tmp_path / "external"
    fake_wandb = _FakeWandb()
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
        lambda **_kwargs: _preflight(
            protocol,
            "inkling-l4-rl",
            "smoke",
        ),
    )
    monkeypatch.setattr(
        tml_shim,
        "install_inkling_runtime",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(ml_log, "wandb", fake_wandb)
    monkeypatch.setattr(ml_log, "_wandb_available", True)
    real_import = launcher.importlib.import_module
    monkeypatch.setattr(
        launcher.importlib,
        "import_module",
        lambda name: fake_wandb if name == "wandb" else real_import(name),
    )
    service_client_markers = []

    async def fake_builtin_main(config):
        ml_log.setup_logging(
            log_dir=config.log_path,
            wandb_project=config.wandb_project,
            wandb_name=config.wandb_name,
            config=config,
            do_configure_logging_module=False,
        )
        tracking_paths = list(external.rglob("tracking.json"))
        assert len(tracking_paths) == 1
        tracking_document = json.loads(tracking_paths[0].read_text(encoding="utf-8"))
        assert tracking_document["payload"]["observed"]["run_id"] == fake_wandb.calls[0]["id"]
        service_client_markers.append("created")
        raise RuntimeError("stop before paid RL")

    monkeypatch.setattr(rl_train, "main", fake_builtin_main)
    with pytest.raises(RuntimeError, match="stop before paid RL"):
        asyncio.run(
            launcher.run_training_stage(
                repo_root=REPO_ROOT,
                stage_id="inkling-l4-rl",
                wave_name="smoke",
                replicate_id="r0",
                expected_source_sha=source_sha,
                external_root=external,
                confirmation=protocol["launch"]["confirmation_token"],
                wandb_access_validator=lambda **_kwargs: {},
            )
        )
    assert service_client_markers == ["created"]
    assert fake_wandb.run is None
    assert fake_wandb.calls[0]["config"] is None
    assert len(fake_wandb.config.updates) == 2
    assert fake_wandb.config.updates[0]["allow_val_change"] is False
    assert fake_wandb.config.updates[1]["allow_val_change"] is None
    assert fake_wandb.config.updates[0]["value"] == fake_wandb.config.updates[1]["value"]
    assert "dataset_builder" in fake_wandb.config.values
    assert len(list(external.rglob("tracking.json"))) == 1


def test_sealed_wandb_initialization_overrides_cookbook_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tinker_cookbook.utils import ml_log

    wandb_dir = tmp_path / "sealed-wandb"
    cookbook_dir = tmp_path / "cookbook-log"
    wandb_dir.mkdir()
    binding = {
        "entity": "unit-entity",
        "project": "unit-project",
        "run_id": "pxct-unit-run",
        "name": "unit/name",
        "group": "unit/group",
        "job_type": "sft",
        "tags": ["study", "stage", "r0"],
        "directory": str(wandb_dir),
    }

    fake = _FakeWandb()
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setattr(ml_log, "wandb", fake)
    monkeypatch.setattr(ml_log, "_wandb_available", True)
    original_init = fake.init
    observed = []
    with launcher._sealed_wandb_initialization(
        binding,
        resume=True,
        wandb_module=fake,
        on_initialized=observed.append,
    ):
        logger = ml_log.setup_logging(
            log_dir=str(cookbook_dir),
            wandb_project="unit-project",
            wandb_name="unit/name",
            config=None,
            do_configure_logging_module=False,
        )
        logger.close()

    assert fake.init == original_init
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["entity"] == binding["entity"]
    assert call["project"] == binding["project"]
    assert call["id"] == binding["run_id"]
    assert call["name"] == binding["name"]
    assert call["group"] == binding["group"]
    assert call["job_type"] == binding["job_type"]
    assert call["tags"] == tuple(binding["tags"])
    assert call["dir"] == binding["directory"]
    assert call["mode"] == "online"
    assert call["resume"] == "must"
    assert call["save_code"] is False
    assert call["config"] is None
    assert observed == [
        {
            "run_id": binding["run_id"],
            "entity": binding["entity"],
            "project": binding["project"],
            "name": binding["name"],
            "group": binding["group"],
            "job_type": binding["job_type"],
            "tags": binding["tags"],
            "resumed": True,
            "url": f"https://wandb.example/{binding['run_id']}",
            "requested_directory": binding["directory"],
            "resolved_root_directory": binding["directory"],
            "files_directory": str(
                Path(binding["directory"]) / "wandb" / binding["run_id"] / "files"
            ),
            "requested_resume": "must",
            "resolved_resume": "must",
            "hparams_preseeded": False,
            "hparams_allow_val_change": False,
        }
    ]


def test_sealed_wandb_initialization_allows_resume_hparam_changes_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tinker_cookbook.utils import ml_log

    wandb_dir = tmp_path / "sealed-wandb"
    cookbook_dir = tmp_path / "cookbook-log"
    wandb_dir.mkdir()
    binding = {
        "entity": "unit-entity",
        "project": "unit-project",
        "run_id": "pxct-unit-run",
        "name": "unit/name",
        "group": "unit/group",
        "job_type": "rl",
        "tags": ["study", "stage", "r0"],
        "directory": str(wandb_dir),
    }
    resumed_config = {
        "max_steps": 6,
        "wave": "pilot",
    }

    fake = _FakeWandb(
        initial_config={
            "max_steps": 1,
            "wave": "smoke",
        }
    )
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setattr(ml_log, "wandb", fake)
    monkeypatch.setattr(ml_log, "_wandb_available", True)
    observed = []
    with launcher._sealed_wandb_initialization(
        binding,
        resume=True,
        wandb_module=fake,
        on_initialized=observed.append,
    ):
        logger = ml_log.setup_logging(
            log_dir=str(cookbook_dir),
            wandb_project=binding["project"],
            wandb_name=binding["name"],
            config=resumed_config,
            do_configure_logging_module=False,
        )
        logger.close()

    assert fake.calls[0]["config"] is None
    assert len(fake.config.updates) == 2
    assert fake.config.updates[0] == {
        "value": resumed_config,
        "allow_val_change": True,
    }
    assert fake.config.updates[1] == {
        "value": resumed_config,
        "allow_val_change": None,
    }
    assert fake.config.values["max_steps"] == 6
    assert fake.config.values["wave"] == "pilot"
    assert observed[0]["hparams_preseeded"] is True
    assert observed[0]["hparams_allow_val_change"] is True


def test_sealed_wandb_initialization_rejects_live_identity_mismatch(
    tmp_path: Path,
) -> None:
    wandb_dir = tmp_path / "sealed-wandb"
    wandb_dir.mkdir()
    binding = {
        "entity": "unit-entity",
        "project": "unit-project",
        "run_id": "pxct-expected",
        "name": "unit/name",
        "group": "unit/group",
        "job_type": "rl",
        "tags": ["study"],
        "directory": str(wandb_dir),
    }

    class MismatchedRun:
        id = "random-id"
        entity = binding["entity"]
        project = binding["project"]
        name = binding["name"]
        group = binding["group"]
        job_type = binding["job_type"]
        tags = tuple(binding["tags"])
        resumed = False
        url = "https://wandb.example/random-id"
        settings = SimpleNamespace(
            root_dir=binding["directory"],
            resume="never",
        )
        dir = str(Path(binding["directory"]) / "wandb" / "random-id" / "files")

        def __init__(self):
            self.finished = False

        def finish(self):
            self.finished = True

    run = MismatchedRun()
    Path(run.dir).mkdir(parents=True)
    fake = SimpleNamespace(run=None, init=lambda **_kwargs: run)
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="live W&B run differs",
    ):
        with launcher._sealed_wandb_initialization(
            binding,
            resume=False,
            wandb_module=fake,
        ):
            fake.init(project=binding["project"], name=binding["name"])
    assert run.finished is True


def test_sealed_wandb_cleanup_does_not_mask_training_failure(
    tmp_path: Path,
) -> None:
    wandb_dir = tmp_path / "sealed-wandb"
    wandb_dir.mkdir()
    binding = {
        "entity": "unit-entity",
        "project": "unit-project",
        "run_id": "pxct-unit-run",
        "name": "unit/name",
        "group": "unit/group",
        "job_type": "sft",
        "tags": ["study"],
        "directory": str(wandb_dir),
    }

    class FailingFinishRun:
        id = binding["run_id"]
        entity = binding["entity"]
        project = binding["project"]
        name = binding["name"]
        group = binding["group"]
        job_type = binding["job_type"]
        tags = tuple(binding["tags"])
        resumed = False
        url = "https://wandb.example/pxct-unit-run"
        settings = SimpleNamespace(
            root_dir=binding["directory"],
            resume="never",
        )
        dir = str(Path(binding["directory"]) / "wandb" / id / "files")

        def finish(self):
            raise RuntimeError("finish failed")

    run = FailingFinishRun()
    Path(run.dir).mkdir(parents=True)

    def module_finish():
        raise RuntimeError("module finish failed")

    fake = SimpleNamespace(
        run=None,
        init=lambda **_kwargs: run,
        finish=module_finish,
    )
    original_init = fake.init
    with pytest.raises(RuntimeError, match="trainer failed"):
        with launcher._sealed_wandb_initialization(
            binding,
            resume=False,
            wandb_module=fake,
        ):
            fake.init(project=binding["project"], name=binding["name"])
            raise RuntimeError("trainer failed")
    assert fake.init == original_init


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
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("preflight should not run")),
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


def test_inkling_extension_rechecks_exact_pilot_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "inkling-l4-rl")
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    # This test isolates the launcher's downstream binding of an already
    # canonically validated approval to the exact pilot receipt.  Canonical
    # report reconstruction is covered independently; keep it out of this
    # deliberately synthetic store.
    monkeypatch.setattr(
        launcher,
        "validate_same_source_wave_approval",
        lambda **_kwargs: None,
    )
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
        "schema_version": launcher.APPROVAL_SCHEMA_VERSION,
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
            repo_root=REPO_ROOT,
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
            repo_root=REPO_ROOT,
            store=FakeStore(SimpleNamespace(payload=changed)),
            key=key,
            stage=stage,
            wave_name="coverage-extension",
            source_git_sha="a" * 40,
            protocol=protocol,
        )


def test_launcher_rejects_fabricated_minimal_same_source_approval() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "inkling-l4-rl")
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    source_git_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    prior = SimpleNamespace(
        record_sha256="b" * 64,
        payload={
            "checkpoint": {
                "name": "000006",
                "batch": 6,
                "epoch": 0,
                "final": False,
                "state_path": "tinker://unit/weights/000006",
                "sampler_path": "tinker://unit/sampler_weights/000006",
            },
        },
    )
    fabricated = SimpleNamespace(
        payload={
            "schema_version": launcher.APPROVAL_SCHEMA_VERSION,
            "decision": "approve",
            "approval_gate": "promotion-receipt-and-explicit-human-approval",
            "stage_id": stage.stage_id,
            "wave": "coverage-extension",
            "source_git_sha": source_git_sha,
            "protocol_logical_sha256": protocol["logical_sha256"],
        },
    )

    class FakeStore:
        @staticmethod
        def load_wave_receipt(_key, *, wave):
            assert wave == "pilot"
            return prior

        @staticmethod
        def load_wave_approval(_key, *, wave):
            assert wave == "coverage-extension"
            return fabricated

    with pytest.raises(
        launcher.TrainingLaunchError,
        match="same-source approval failed validation",
    ):
        launcher._approval_record(
            repo_root=REPO_ROOT,
            store=FakeStore(),
            key=key,
            stage=stage,
            wave_name="coverage-extension",
            source_git_sha=source_git_sha,
            protocol=protocol,
        )


def test_cross_source_parent_requires_v2_and_child_manifest_records_it() -> None:
    protocol = load_protocol(REPO_ROOT)
    producer = "b" * 40
    consumer = "c" * 40
    checkpoint, parent_manifest, receipt, approval = _cross_source_parent_records(
        protocol,
        producer_source_git_sha=producer,
        consumer_source_git_sha=consumer,
    )
    key = StageKey(STUDY_ID, "qwen-l0-rl-l1", "r0")
    stage = stage_spec(protocol, key.stage_id)
    parent_key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")

    class ParentStore:
        def load_manifest(self, observed_key):
            assert observed_key == parent_key
            return parent_manifest

        def load_wave_receipt(self, observed_key, *, wave):
            assert observed_key == parent_key
            assert wave == "complete"
            return receipt

    v1_payload = {
        key: value
        for key, value in approval.payload.items()
        if key not in {"evidence_source_git_sha", "source_transition"}
    }
    v1_payload["schema_version"] = launcher.APPROVAL_SCHEMA_VERSION
    v1 = SimpleNamespace(
        payload=v1_payload,
        payload_sha256=approval.payload_sha256,
        record_sha256=approval.record_sha256,
        relative_path=approval.relative_path,
    )
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="requires a v2 transition approval",
    ):
        launcher._parent_binding(
            repo_root=REPO_ROOT,
            protocol=protocol,
            store=ParentStore(),
            key=key,
            stage=stage,
            source_git_sha=consumer,
            approval=v1,
            existing_manifest=None,
        )

    parent = launcher._parent_binding(
        repo_root=REPO_ROOT,
        protocol=protocol,
        store=ParentStore(),
        key=key,
        stage=stage,
        source_git_sha=consumer,
        approval=approval,
        existing_manifest=None,
    )
    assert parent is not None
    assert parent.source_git_sha == producer
    assert parent.checkpoint == checkpoint
    assert parent.entry_approval is approval
    manifest = launcher._manifest_payload(
        protocol=protocol,
        source_git_sha=consumer,
        stage=stage,
        preflight=_preflight(protocol, stage.stage_id, "smoke"),
        tracking={"run_id": "unit"},
        parent=parent,
    )
    assert manifest["source_transition"] == (launcher._child_source_transition_binding(approval))
    assert manifest["source_transition"]["producer_source_git_sha"] == (producer)
    assert manifest["source_transition"]["consumer_source_git_sha"] == (consumer)
    assert manifest["source_transition"]["authorized_child_wave"] == "smoke"
    assert manifest["parent_receipt"]["record_sha256"] == (receipt.record_sha256)


def test_historical_l0_parent_uses_receipt_transition_without_evaluation(
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    producer = "1" * 40
    consumer = "2" * 40
    checkpoint, parent_manifest, receipt, approval = _cross_source_parent_records(
        protocol,
        producer_source_git_sha=producer,
        consumer_source_git_sha=consumer,
    )
    parent_manifest.payload["protocol_logical_sha256"] = "3" * 64
    approval.payload.update(
        {
            "schema_version": (
                launcher.PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
            ),
            "decision": "approve",
            "approval_gate": "parent-receipt-and-source-transition",
            "protocol_logical_sha256": protocol["logical_sha256"],
            "explicit_human_confirmation": True,
        }
    )
    key = StageKey(STUDY_ID, "qwen-l0-rl-l1", "r0")
    parent_key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")
    stage = stage_spec(protocol, key.stage_id)
    validation_calls: list[dict] = []
    monkeypatch.setattr(
        launcher,
        "validate_parent_receipt_transition_approval",
        lambda **kwargs: validation_calls.append(dict(kwargs)),
    )

    class ParentStore:
        @staticmethod
        def load_wave_approval(observed_key, *, wave):
            assert observed_key == key
            assert wave == "smoke"
            return approval

        @staticmethod
        def load_manifest(observed_key):
            assert observed_key == parent_key
            return parent_manifest

        @staticmethod
        def load_wave_receipt(observed_key, *, wave):
            assert observed_key == parent_key
            assert wave == "complete"
            return receipt

    observed_approval = launcher._approval_record(
        repo_root=REPO_ROOT,
        store=ParentStore(),
        key=key,
        stage=stage,
        wave_name="smoke",
        source_git_sha=consumer,
        protocol=protocol,
    )
    assert observed_approval is approval
    assert len(validation_calls) == 1

    parent = launcher._parent_binding(
        repo_root=REPO_ROOT,
        protocol=protocol,
        store=ParentStore(),
        key=key,
        stage=stage,
        source_git_sha=consumer,
        approval=approval,
        existing_manifest=None,
    )
    assert parent is not None
    assert parent.checkpoint == checkpoint
    assert parent.entry_approval is approval
    child_transition = launcher._child_source_transition_binding(approval)
    assert child_transition["approval_schema_version"] == (
        launcher.PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
    )
    assert child_transition["producer_source_git_sha"] == producer
    assert child_transition["consumer_source_git_sha"] == consumer


def test_existing_child_manifest_revalidates_exact_v2_transition(
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    producer = "d" * 40
    consumer = "e" * 40
    checkpoint, parent_manifest, receipt, approval = _cross_source_parent_records(
        protocol,
        producer_source_git_sha=producer,
        consumer_source_git_sha=consumer,
    )
    key = StageKey(STUDY_ID, "qwen-l0-rl-l1", "r0")
    parent_key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")
    stage = stage_spec(protocol, key.stage_id)
    transition_binding = launcher._child_source_transition_binding(approval)
    existing_manifest = SimpleNamespace(
        payload={
            "source_git_sha": consumer,
            "parent_receipt": {
                "stage_id": "qwen-l0-sft",
                "wave": "complete",
                "record_sha256": receipt.record_sha256,
                "checkpoint": checkpoint,
                "checkpoint_inventory_logical_sha256": (
                    receipt.payload["checkpoint_inventory"]["logical_sha256"]
                ),
            },
            "source_transition": transition_binding,
        },
    )
    validation_calls: list[dict] = []
    monkeypatch.setattr(
        launcher,
        "validate_source_transition_approval",
        lambda **kwargs: validation_calls.append(dict(kwargs)),
    )

    class ExistingStore:
        def load_manifest(self, observed_key):
            assert observed_key == parent_key
            return parent_manifest

        def load_wave_receipt(self, observed_key, *, wave):
            assert observed_key == parent_key
            assert wave == "complete"
            return receipt

        def load_wave_approval(self, observed_key, *, wave):
            assert observed_key == key
            assert wave == "smoke"
            return approval

    parent = launcher._parent_binding(
        repo_root=REPO_ROOT,
        protocol=protocol,
        store=ExistingStore(),
        key=key,
        stage=stage,
        source_git_sha=consumer,
        approval=None,
        existing_manifest=existing_manifest,
    )
    assert parent is not None
    assert parent.entry_approval is approval
    assert len(validation_calls) == 1
    assert validation_calls[0]["replicate_id"] == "r0"
    assert validation_calls[0]["wave_name"] == "smoke"

    tampered_manifest = SimpleNamespace(payload=copy.deepcopy(existing_manifest.payload))
    tampered_manifest.payload["source_transition"]["source_transition_logical_sha256"] = "0" * 64
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="differs from its v2 approval",
    ):
        launcher._parent_binding(
            repo_root=REPO_ROOT,
            protocol=protocol,
            store=ExistingStore(),
            key=key,
            stage=stage,
            source_git_sha=consumer,
            approval=None,
            existing_manifest=tampered_manifest,
        )


def test_completed_wave_cannot_bypass_transition_checks_or_preflight(
    tmp_path: Path,
    monkeypatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    source_sha = "f" * 40
    external = tmp_path / "external"
    key = StageKey(STUDY_ID, "qwen-l0-rl-l1", "r0")
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            {"source_git_sha": source_sha},
        )
        store.write_wave_receipt(
            key,
            wave="smoke",
            payload={
                "stage_id": key.stage_id,
                "wave": "smoke",
                "run_manifest_record_sha256": manifest.record_sha256,
            },
        )
    monkeypatch.setenv("TINKER_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setattr(
        launcher,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(
        launcher,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    events: list[str] = []
    monkeypatch.setattr(
        launcher,
        "stage_preflight",
        lambda **_kwargs: events.append("preflight") or _preflight(protocol, key.stage_id, "smoke"),
    )

    def reject_transition(**_kwargs):
        events.append("approval")
        raise launcher.TrainingLaunchError("v2 transition required")

    monkeypatch.setattr(launcher, "_approval_record", reject_transition)
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="v2 transition required",
    ):
        asyncio.run(
            launcher.run_training_stage(
                repo_root=REPO_ROOT,
                stage_id=key.stage_id,
                wave_name="smoke",
                replicate_id="r0",
                expected_source_sha=source_sha,
                external_root=external,
                confirmation=protocol["launch"]["confirmation_token"],
                rl_main=lambda _config: (_ for _ in ()).throw(
                    AssertionError("completed bypass reached Tinker")
                ),
                wandb_access_validator=lambda **_kwargs: (_ for _ in ()).throw(
                    AssertionError("completed bypass reached W&B")
                ),
            )
        )
    assert events == ["preflight", "approval"]

    wrong_source_root = tmp_path / "wrong-source"
    wrong_store = TrainingStore(
        repo_root=REPO_ROOT,
        external_root=wrong_source_root,
    )
    with wrong_store.acquire_stage_lock(key):
        wrong_manifest = wrong_store.create_or_verify_manifest(
            key,
            {"source_git_sha": "0" * 40},
        )
        wrong_store.write_wave_receipt(
            key,
            wave="smoke",
            payload={
                "stage_id": key.stage_id,
                "wave": "smoke",
                "run_manifest_record_sha256": (wrong_manifest.record_sha256),
            },
        )
    with pytest.raises(
        launcher.TrainingLaunchError,
        match="another source commit",
    ):
        asyncio.run(
            launcher.run_training_stage(
                repo_root=REPO_ROOT,
                stage_id=key.stage_id,
                wave_name="smoke",
                replicate_id="r0",
                expected_source_sha=source_sha,
                external_root=wrong_source_root,
                confirmation=protocol["launch"]["confirmation_token"],
            )
        )
