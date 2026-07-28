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
            key
            for key, item in payload.items()
            if key in self.values and self.values[key] != item
        ]
        if changed and allow_val_change is not True:
            raise RuntimeError(
                "config changed without allow_val_change: "
                + ", ".join(changed)
            )
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
        tracking_document = json.loads(
            tracking_paths[0].read_text(encoding="utf-8")
        )
        assert (
            tracking_document["payload"]["observed"]["run_id"]
            == fake_wandb.calls[0]["id"]
        )
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
    assert (
        fake_wandb.config.updates[0]["value"]
        == fake_wandb.config.updates[1]["value"]
    )
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
    assert (
        receipt.payload["invocation_tracking_record_sha256"]
        == tracking.record_sha256
    )


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
        tracking_document = json.loads(
            tracking_paths[0].read_text(encoding="utf-8")
        )
        assert (
            tracking_document["payload"]["observed"]["run_id"]
            == fake_wandb.calls[0]["id"]
        )
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
    assert (
        fake_wandb.config.updates[0]["value"]
        == fake_wandb.config.updates[1]["value"]
    )
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
                Path(binding["directory"])
                / "wandb"
                / binding["run_id"]
                / "files"
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
