from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.evaluation.attempt_store import RunKey
from rl.evaluation.tracking import deterministic_wandb_run_id
from rl.studies.representation_curriculum_v1.extensions.qwen60 import freeze
from rl.studies.representation_curriculum_v1.freeze_phase1 import Phase1FreezeError


REPO_ROOT = Path(__file__).resolve().parents[5]


def test_collect_bundle_uses_distinct_canonical_wandb_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source_sha = "a" * 40
    protocol = {
        "study_id": "representation-curriculum-v1-qwen60",
        "logical_sha256": "b" * 64,
        "hypotheses": {
            "RC-H04": {
                "arm_ids": ["qwen-on-60000"],
                "task_set": "f1_f8",
            }
        },
        "base_study": {"study_id": "representation-curriculum-v1-qwen32"},
        "decision": {
            "policy": "quality_first_user_directed_near_context_limit_extension"
        },
        "dataset": {"revision": "v2.0.0"},
    }
    evidence = SimpleNamespace(
        summary={"complete": True},
        manifest=SimpleNamespace(record_sha256="c" * 64),
    )
    task = SimpleNamespace(task_id="F1")
    job = SimpleNamespace(task_id="F1", attempt_index=1)

    monkeypatch.setattr(freeze, "_git_head", lambda _root: source_sha)
    monkeypatch.setattr(
        freeze,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(freeze, "validate_runtime_stack", lambda _root: {})
    monkeypatch.setattr(
        freeze,
        "load_task_manifest",
        lambda *_args, **_kwargs: {"logical_sha256": "d" * 64},
    )
    monkeypatch.setattr(freeze, "_prompt_binding", lambda: ({}, "e" * 64))
    monkeypatch.setattr(
        freeze,
        "_task_set",
        lambda **_kwargs: ([task], "f" * 64),
    )
    monkeypatch.setattr(freeze, "jobs_for_wave", lambda *_args, **_kwargs: [job])
    monkeypatch.setattr(
        freeze,
        "_load_run",
        lambda **_kwargs: (evidence, ("sha256:image", "sha256:image")),
    )
    monkeypatch.setattr(
        freeze,
        "_collect_run_attempts",
        lambda **_kwargs: (
            [{"task_id": "F1", "attempt_index": 1}],
            {},
        ),
    )

    _files, manifest = freeze._collect_bundle(
        repo_root=REPO_ROOT,
        external_root=tmp_path,
        expected_source_sha=source_sha,
    )
    expected = deterministic_wandb_run_id(
        RunKey(
            "representation-curriculum-v1-qwen60",
            "RC-H04",
            "qwen-on-60000",
        ),
        source_git_sha=source_sha,
    )
    qwen32 = deterministic_wandb_run_id(
        RunKey(
            "representation-curriculum-v1-qwen32",
            "RC-H03",
            "qwen-on-32768",
        ),
        source_git_sha=source_sha,
    )
    assert manifest["run"]["wandb_run_id"] == expected
    assert manifest["run"]["wandb_run_id"] != qwen32


def test_output_root_rejects_symlink_escape(tmp_path: Path):
    repo = tmp_path / "repo"
    parent = repo / "data/training/representation-curriculum-v1"
    outside = tmp_path / "outside"
    parent.mkdir(parents=True)
    outside.mkdir()
    (parent / "phase1-qwen60").symlink_to(outside, target_is_directory=True)

    with pytest.raises(Phase1FreezeError, match="outside the source repository"):
        freeze._output_root(repo, None)


def test_output_root_is_fixed_and_cannot_overwrite_qwen32(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    qwen32 = repo / "data/training/representation-curriculum-v1/phase1-qwen32"
    with pytest.raises(Phase1FreezeError, match="must be written exactly"):
        freeze._output_root(repo, qwen32)
