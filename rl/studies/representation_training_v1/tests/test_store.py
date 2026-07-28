from __future__ import annotations

from pathlib import Path

import pytest

from rl.studies.representation_training_v1.store import (
    ImmutableTrainingRecordError,
    StageKey,
    TrainingStore,
    TrainingStoreError,
    UnsafeTrainingRootError,
)


def test_store_rejects_repository_overlap(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(UnsafeTrainingRootError):
        TrainingStore(repo_root=repo, external_root=repo / "runs")


def test_records_require_lock_and_are_immutable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    external = tmp_path / "external"
    repo.mkdir()
    store = TrainingStore(repo_root=repo, external_root=external)
    key = StageKey("study", "stage", "r0")
    with pytest.raises(TrainingStoreError):
        store.create_or_verify_manifest(key, {"value": 1})
    with store.acquire_stage_lock(key):
        first = store.create_or_verify_manifest(key, {"value": 1})
        assert store.create_or_verify_manifest(key, {"value": 1}) == first
        with pytest.raises(ImmutableTrainingRecordError):
            store.create_or_verify_manifest(key, {"value": 2})


def test_crash_retry_invocations_never_collide_candidates(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    external = tmp_path / "external"
    repo.mkdir()
    store = TrainingStore(repo_root=repo, external_root=external)
    key = StageKey("study", "stage", "r0")
    with store.acquire_stage_lock(key):
        store.create_or_verify_manifest(key, {"value": 1})
        for invocation, score in (("smoke-first", 0.1), ("smoke-retry", 0.2)):
            store.begin_invocation(
                key,
                invocation_id=invocation,
                payload={"invocation_id": invocation},
            )
            store.write_candidate(
                key,
                invocation_id=invocation,
                step=0,
                task_id="abc123",
                attempt=1,
                payload={"iou": score},
            )
            store.write_candidate_sample(
                key,
                invocation_id=invocation,
                step=0,
                task_id="abc123",
                attempt=1,
                payload={"tokens": [1, 2, 3]},
            )
    candidates = sorted(store.candidate_root(key).rglob("evaluation.json"))
    samples = sorted(store.candidate_root(key).rglob("sample.json"))
    assert len(candidates) == 2
    assert len(samples) == 2
    assert {path.parts[-5] for path in candidates} == {
        "smoke-first",
        "smoke-retry",
    }


def test_invocation_tracking_is_create_only_and_requires_start(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    external = tmp_path / "external"
    repo.mkdir()
    store = TrainingStore(repo_root=repo, external_root=external)
    key = StageKey("study", "stage", "r0")
    payload = {
        "expected": {"run_id": "pxct-expected"},
        "observed": {"run_id": "pxct-expected"},
    }
    with store.acquire_stage_lock(key):
        store.create_or_verify_manifest(key, {"value": 1})
        with pytest.raises(TrainingStoreError, match="cannot precede"):
            store.write_invocation_tracking(
                key,
                invocation_id="complete-unit",
                payload=payload,
            )
        invocation = store.begin_invocation(
            key,
            invocation_id="complete-unit",
            payload={"invocation_id": "complete-unit"},
        )
        assert (
            store.load_invocation(
                key,
                invocation_id="complete-unit",
            )
            == invocation
        )
        tracking = store.write_invocation_tracking(
            key,
            invocation_id="complete-unit",
            payload=payload,
        )
        assert (
            store.load_invocation_tracking(
                key,
                invocation_id="complete-unit",
            )
            == tracking
        )
        assert (
            store.write_invocation_tracking(
                key,
                invocation_id="complete-unit",
                payload=payload,
            )
            == tracking
        )
        with pytest.raises(ImmutableTrainingRecordError):
            store.write_invocation_tracking(
                key,
                invocation_id="complete-unit",
                payload={
                    **payload,
                    "observed": {"run_id": "random"},
                },
            )
