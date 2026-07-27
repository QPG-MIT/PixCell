from __future__ import annotations

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.evaluation.attempt_store import AttemptKey, AttemptStore
from rl.evaluation.tracking import (
    TrackingContractError,
    WandbMetricsMirror,
    deterministic_wandb_run_id,
    validate_wandb_access,
)

SOURCE_GIT_SHA = "a" * 40


class FakeSettings:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class FakeRun:
    def __init__(self, owner: FakeWandb) -> None:
        self.owner = owner

    def log(
        self,
        metrics: dict[str, int | float],
        *,
        step: int,
        commit: bool,
    ) -> None:
        if self.owner.fail_log:
            raise RuntimeError("log failed")
        self.owner.logs.append((metrics, step, commit))

    def finish(self) -> None:
        self.owner.finished += 1
        if self.owner.fail_finish:
            raise RuntimeError("finish failed")


class FakeWandb:
    Settings = FakeSettings

    def __init__(
        self,
        *,
        fail: bool = False,
        fail_log: bool = False,
        fail_finish: bool = False,
    ) -> None:
        self.fail = fail
        self.fail_log = fail_log
        self.fail_finish = fail_finish
        self.init_calls: list[dict] = []
        self.logs: list[tuple[dict[str, int | float], int, bool]] = []
        self.finished = 0
        self.environment: dict[str, str | None] = {}

    def init(self, **kwargs: object) -> FakeRun:
        self.init_calls.append(kwargs)
        self.environment = {
            name: os.environ.get(name)
            for name in (
                "WANDB_DIR",
                "WANDB_DISABLE_GIT",
                "WANDB_DISABLE_CODE",
                "WANDB_SAVE_CODE",
            )
        }
        if self.fail:
            raise ConnectionError("offline")
        return FakeRun(self)


def _store(tmp_path: Path) -> AttemptStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    return AttemptStore(
        repo_root=repo,
        external_root=tmp_path / "external-record",
    )


def _key() -> AttemptKey:
    return AttemptKey("study-v1", "H-QWEN-ZERO", "off-4k", "F1", 1)


def test_wandb_run_id_is_bound_to_the_exact_source_commit() -> None:
    first = deterministic_wandb_run_id(
        _key().run_key,
        source_git_sha="a" * 40,
    )
    second = deterministic_wandb_run_id(
        _key().run_key,
        source_git_sha="b" * 40,
    )

    assert first != second
    with pytest.raises(TrackingContractError, match="Git object SHA"):
        deterministic_wandb_run_id(
            _key().run_key,
            source_git_sha="not-a-sha",
        )


def test_wandb_access_preflight_binds_the_expected_entity() -> None:
    class FakeAccess:
        @staticmethod
        def Api(*, timeout: int) -> SimpleNamespace:
            assert timeout == 20
            return SimpleNamespace(
                viewer=SimpleNamespace(username="aadarwal", entity="qpaig-mit"),
                default_entity="qpaig-mit",
            )

    assert validate_wandb_access(
        expected_entity="qpaig-mit",
        wandb_module=FakeAccess,
    ) == {"username": "aadarwal", "entity": "qpaig-mit"}
    with pytest.raises(TrackingContractError, match="entity mismatch"):
        validate_wandb_access(
            expected_entity="another-team",
            wandb_module=FakeAccess,
        )


def test_wandb_access_preflight_fails_closed() -> None:
    class OfflineAccess:
        @staticmethod
        def Api(*, timeout: int) -> None:
            assert timeout == 20
            raise ConnectionError("offline")

    with pytest.raises(TrackingContractError, match="credential preflight"):
        validate_wandb_access(
            expected_entity=None,
            wandb_module=OfflineAccess,
        )


def test_tracking_refuses_to_run_before_local_record_exists(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    fake = FakeWandb()
    mirror = WandbMetricsMirror(
        store=store,
        project="pixcell",
        source_git_sha=SOURCE_GIT_SHA,
        wandb_module=fake,
    )

    with pytest.raises(TrackingContractError, match="before local state"):
        mirror.mirror_saved_metrics(
            key=_key(),
            source="sampling_receipt",
            metrics={"output_tokens": 10},
            step=0,
        )
    assert fake.init_calls == []


def test_metrics_only_mirror_uses_resumable_id_and_disables_source_upload(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    key = _key()
    store.write_sampling_receipt(
        key,
        {
            "raw_completion": "secret program",
            "output_tokens": 10,
        },
    )
    fake = FakeWandb()
    mirror = WandbMetricsMirror(
        store=store,
        project="pixcell-baselines",
        source_git_sha=SOURCE_GIT_SHA,
        entity="qpaig-mit",
        group="phase1-zero-shot",
        wandb_module=fake,
    )

    result = mirror.mirror_saved_metrics(
        key=key,
        source="sampling_receipt",
        metrics={"output_tokens": 10, "latency_seconds": 1.25},
        step=3,
    )

    assert result.mirrored is True
    assert result.wandb_run_id == deterministic_wandb_run_id(
        key.run_key,
        source_git_sha=SOURCE_GIT_SHA,
    )
    assert fake.logs == [
        ({"output_tokens": 10, "latency_seconds": 1.25}, 3, True)
    ]
    assert fake.finished == 1
    call = fake.init_calls[0]
    assert call["id"] == result.wandb_run_id
    assert call["reinit"] == "create_new"
    assert call["resume"] == "allow"
    assert call["group"] == "phase1-zero-shot"
    assert call["dir"] == str(store.external_root / ".wandb")
    assert "config" not in call
    assert "secret program" not in repr(call)
    assert call["settings"].kwargs == {
        "disable_code": True,
        "disable_git": True,
        "disable_job_creation": True,
        "save_code": False,
        "x_disable_machine_info": True,
        "x_disable_stats": True,
        "x_save_requirements": False,
    }
    assert fake.environment == {
        "WANDB_DIR": str(store.external_root / ".wandb"),
        "WANDB_DISABLE_GIT": "true",
        "WANDB_DISABLE_CODE": "true",
        "WANDB_SAVE_CODE": "false",
    }


def test_persistent_arm_session_initializes_once_and_finishes_once(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    first = _key()
    second = AttemptKey(
        first.study_id,
        first.hypothesis_id,
        first.arm_id,
        "F2",
        1,
    )
    store.write_sampling_receipt(first, {"raw_completion": "first"})
    store.write_sampling_receipt(second, {"raw_completion": "second"})
    fake = FakeWandb()
    mirror = WandbMetricsMirror(
        store=store,
        project="pixcell-baselines",
        source_git_sha=SOURCE_GIT_SHA,
        wandb_module=fake,
    )

    with mirror.session(first.run_key) as session:
        first_result = session.mirror_saved_metrics(
            key=first,
            source="sampling_receipt",
            metrics={"output_tokens": 10},
            step=0,
        )
        second_result = session.mirror_saved_metrics(
            key=second,
            source="sampling_receipt",
            metrics={"output_tokens": 20},
            step=1,
        )

    assert first_result.mirrored and second_result.mirrored
    assert len(fake.init_calls) == 1
    assert len(fake.logs) == 2
    assert fake.finished == 1


def test_tracking_failure_is_a_local_error_and_keeps_saved_sample(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    key = _key()
    saved = store.write_sampling_receipt(
        key,
        {
            "raw_completion": "durable sample",
            "output_tokens": 10,
        },
    )
    mirror = WandbMetricsMirror(
        store=store,
        project="pixcell-baselines",
        source_git_sha=SOURCE_GIT_SHA,
        wandb_module=FakeWandb(fail=True),
    )

    result = mirror.mirror_saved_metrics(
        key=key,
        source="sampling_receipt",
        metrics={"output_tokens": 10},
        step=0,
    )

    assert result.mirrored is False
    assert store.load_sampling_receipt(key) == saved
    errors = store.list_tracking_errors(key)
    assert len(errors) == 1
    assert result.tracking_error_relative_path == str(errors[0].relative_path)
    payload = errors[0].payload
    assert payload["error_type"] == "ConnectionError"
    assert payload["operation"] == "init"
    assert payload["source_record_sha256"] == saved.record_sha256
    assert payload["metrics_sha256"] == hashlib.sha256(
        b'{"output_tokens":10}'
    ).hexdigest()
    assert "durable sample" not in repr(payload)


@pytest.mark.parametrize(
    ("fake", "operation"),
    [
        (FakeWandb(fail_log=True), "log"),
        (FakeWandb(fail_finish=True), "finish"),
    ],
)
def test_log_and_finish_failures_each_create_local_error_records(
    tmp_path: Path,
    fake: FakeWandb,
    operation: str,
) -> None:
    store = _store(tmp_path)
    key = _key()
    saved = store.write_sampling_receipt(key, {"raw_completion": "durable"})
    mirror = WandbMetricsMirror(
        store=store,
        project="pixcell-baselines",
        source_git_sha=SOURCE_GIT_SHA,
        wandb_module=fake,
    )

    with mirror.session(key.run_key) as session:
        result = session.mirror_saved_metrics(
            key=key,
            source="sampling_receipt",
            metrics={"output_tokens": 10},
            step=0,
        )

    errors = store.list_tracking_errors(key)
    assert len(errors) == 1
    assert errors[0].payload["operation"] == operation
    assert store.load_sampling_receipt(key) == saved
    if operation == "log":
        assert result.mirrored is False
    else:
        # The metric reached W&B; only finalization failed afterward.
        assert result.mirrored is True


def test_tracking_contract_rejects_bad_metrics_and_repo_wandb_dir(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    with pytest.raises(TrackingContractError, match="outside"):
        WandbMetricsMirror(
            store=store,
            project="pixcell",
            source_git_sha=SOURCE_GIT_SHA,
            wandb_dir=store.repo_root / "wandb",
            wandb_module=FakeWandb(),
        )
    key = _key()
    store.write_sampling_receipt(key, {"raw_completion": "saved"})
    mirror = WandbMetricsMirror(
        store=store,
        project="pixcell",
        source_git_sha=SOURCE_GIT_SHA,
        wandb_module=FakeWandb(),
    )
    with pytest.raises(TrackingContractError):
        mirror.mirror_saved_metrics(
            key=key,
            source="sampling_receipt",
            metrics={"iou": float("inf")},
            step=0,
        )
