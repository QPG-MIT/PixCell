from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rl.evaluation.attempt_store import (
    AttemptKey,
    AttemptStore,
    ImmutableRecordError,
    InvalidRecordError,
    ManifestDriftError,
    RunKey,
    RunLockedError,
    RunLockRequiredError,
    UnsafeStoreRootError,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _manifest(**updates: object) -> dict:
    value = {
        "source_git_sha": "a" * 40,
        "protocol_sha256": _digest("protocol"),
        "task_set_sha256": _digest("tasks"),
        "prompt_sha256": _digest("prompt"),
        "sandbox_image_ref": "sha256:" + "b" * 64,
        "sandbox_image_id": "sha256:" + "b" * 64,
        "runtime": {
            "python": "3.13.14",
            "packages": {"tinker": "0.22.7"},
            "tinker_cookbook_commit": "c" * 40,
        },
        "model_binding": {
            "provider": "tinker",
            "model": "Qwen/Qwen3.6-35B-A3B",
            "renderer": "qwen3_5_disable_thinking",
            "temperature": 1.0,
            "top_p": 1.0,
            "max_output_tokens": 4096,
        },
    }
    value.update(updates)
    return value


@pytest.fixture
def roots(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo, tmp_path / "external-record"


def test_store_rejects_repository_output_and_unsafe_keys(
    roots: tuple[Path, Path],
) -> None:
    repo, _ = roots
    with pytest.raises(UnsafeStoreRootError):
        AttemptStore(repo_root=repo, external_root=repo / "runs")
    with pytest.raises(UnsafeStoreRootError):
        AttemptStore(repo_root=repo, external_root=repo.parent)
    with pytest.raises(ValueError):
        AttemptKey("study", "hypothesis", "arm", "../escape", 1)
    with pytest.raises(ValueError):
        AttemptKey("study", "hypothesis", "arm", "task", 0)


def test_manifest_is_create_or_verify_and_paths_are_stable(
    roots: tuple[Path, Path],
) -> None:
    repo, external = roots
    store = AttemptStore(repo_root=repo, external_root=external)
    run_key = RunKey("study-v1", "H-QWEN-ZERO", "off-4k")
    first = store.create_or_verify_run_manifest(run_key, _manifest())
    second = store.create_or_verify_run_manifest(run_key, _manifest())

    assert first == second
    assert str(first.relative_path) == (
        "studies/study-v1/hypotheses/H-QWEN-ZERO/"
        "arms/off-4k/run_manifest.json"
    )
    with pytest.raises(ManifestDriftError):
        store.create_or_verify_run_manifest(
            run_key,
            _manifest(prompt_sha256=_digest("changed prompt")),
        )
    assert store.load_run_manifest(run_key) == first


def test_resume_uses_receipt_without_calling_sampler_and_records_evaluation(
    roots: tuple[Path, Path],
) -> None:
    repo, external = roots
    store = AttemptStore(repo_root=repo, external_root=external)
    key = AttemptKey("study-v1", "H-QWEN-ZERO", "off-4k", "F1", 1)
    store.create_or_verify_run_manifest(key.run_key, _manifest())
    calls = 0

    def sample() -> dict:
        nonlocal calls
        calls += 1
        return {
            "raw_completion": "print('first')",
            "completion_sha256": _digest("print('first')"),
            "finish_reason": "stop",
            "output_tokens": 7,
            "latency_seconds": 0.25,
        }

    with pytest.raises(RunLockRequiredError):
        store.resume_or_sample(key, sample)
    with store.acquire_run_lock(key.run_key):
        created = store.resume_or_sample(key, sample)
        resumed = store.resume_or_sample(
            key,
            lambda: pytest.fail("a saved receipt must never be resampled"),
        )

    assert calls == 1
    assert created.resumed is False
    assert resumed.resumed is True
    assert resumed.record == created.record
    assert str(created.record.relative_path).endswith(
        "tasks/F1/attempts/000001/sampling_receipt.json"
    )

    evaluation = store.write_evaluation(
        key,
        {
            "extracted_code": "print('first')",
            "raw_iou": 0.75,
            "measured_dice": None,
            "render_sha256": None,
            "pure_executable_rate": 1.0,
        },
    )
    assert store.load_evaluation(key) == evaluation
    with pytest.raises(ImmutableRecordError):
        store.write_evaluation(
            key,
            {
                "extracted_code": "print('different')",
                "raw_iou": 0.8,
                "pure_executable_rate": 1.0,
            },
        )


def test_run_lock_is_nonblocking_across_store_instances(
    roots: tuple[Path, Path],
) -> None:
    repo, external = roots
    first = AttemptStore(repo_root=repo, external_root=external)
    second = AttemptStore(repo_root=repo, external_root=external)
    run_key = RunKey("study-v1", "H-QWEN-ZERO", "off-4k")

    with first.acquire_run_lock(run_key):
        with pytest.raises(RunLockedError):
            with second.acquire_run_lock(run_key):
                pass
    with second.acquire_run_lock(run_key):
        pass


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_completion": "x", "raw_iou": float("nan")},
        {"raw_completion": "x", "raw_iou": 1.01},
        {"raw_completion": "x", "completion_sha256": "not-a-hash"},
        {"raw_completion": "x", "output_tokens": -1},
        {"raw_completion": "x", "temperature": 2.01},
    ],
)
def test_receipts_reject_nonfinite_out_of_range_and_bad_hashes(
    roots: tuple[Path, Path],
    payload: dict,
) -> None:
    repo, external = roots
    store = AttemptStore(repo_root=repo, external_root=external)
    key = AttemptKey("study-v1", "H-QWEN-ZERO", "off-4k", "F1", 1)
    with pytest.raises(InvalidRecordError):
        store.write_sampling_receipt(key, payload)


def test_read_detects_tampering_through_record_hash(
    roots: tuple[Path, Path],
) -> None:
    repo, external = roots
    store = AttemptStore(repo_root=repo, external_root=external)
    key = AttemptKey("study-v1", "H-QWEN-ZERO", "off-4k", "F1", 1)
    stored = store.write_sampling_receipt(key, {"raw_completion": "original"})
    path = external / Path(*stored.relative_path.parts)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["payload"]["raw_completion"] = "tampered"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(InvalidRecordError, match="payload hash mismatch"):
        store.load_sampling_receipt(key)
