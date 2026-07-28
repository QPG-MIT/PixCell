from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from rl.common.contracts import ModelObservation, VerifierReference
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus
from rl.common.output import extract_code
from rl.evaluation.attempt_store import AttemptKey, AttemptStore, RunKey
from rl.evaluation.protocol import jobs_for_wave
from rl.evaluation.summarize import atomic_write_json, summarize_arm
from rl.evaluation.tasks import EvaluationTask, canonical_json_sha256
from rl.studies.representation_curriculum_v2 import freeze_phase1 as freezer


SOURCE_SHA = "a" * 40
PROMPT_SHA = "b" * 64
SANDBOX = ("sha256:" + "c" * 64, "sha256:" + "c" * 64)
RUNTIME = {
    "python": "3.13.14",
    "packages": {"tinker": "0.22.7"},
    "tinker_cookbook_commit": "f" * 40,
}


def _arm(
    *,
    model: str,
    renderer: str,
    effort: float | None,
) -> dict[str, Any]:
    return {
        "provider": "tinker",
        "model": model,
        "renderer": renderer,
        "thinking": True,
        "thinking_effort": effort,
        "max_output_tokens": 60000,
        "context_tokens": 65536,
        "max_image_long_edge": 1920,
    }


def _protocol() -> dict[str, Any]:
    hypotheses = {
        "RC-H05": {
            "name": "Qwen thinking-on 60k zero-shot F1-F8 baseline",
            "arm_ids": ["qwen-on-60000"],
            "attempts_per_task": 4,
            "task_set": "f1_f8",
            "status": "frozen",
            "waves": {
                "smoke": {"attempt_indices": [1], "task_count": 8},
                "complete": {
                    "attempt_indices": [1, 2, 3, 4],
                    "task_count": 8,
                },
            },
        },
        "RC-H06": {
            "name": "Inkling effort-0.9 60k zero-shot F1-F8 baseline",
            "arm_ids": ["inkling-e09-60000"],
            "attempts_per_task": 4,
            "task_set": "f1_f8",
            "status": "frozen",
            "waves": {
                "smoke": {"attempt_indices": [1], "task_count": 8},
                "complete": {
                    "attempt_indices": [1, 2, 3, 4],
                    "task_count": 8,
                },
            },
        },
    }
    return {
        "study_id": freezer.EXPECTED_STUDY,
        "contract_version": freezer.EXPECTED_CONTRACT,
        "logical_sha256": "d" * 64,
        "dataset": {
            "repository": "example/pixcell",
            "revision": "test",
            "configuration": "depth",
        },
        "arms": {
            "qwen-on-60000": _arm(
                model="Qwen/Qwen3.6-35B-A3B",
                renderer="qwen3_5",
                effort=None,
            ),
            "inkling-e09-60000": _arm(
                model="thinkingmachines/Inkling",
                renderer="tml_v0",
                effort=0.9,
            ),
        },
        "hypotheses": hypotheses,
        "sampling": {
            "temperature": 1.0,
            "top_p": 1.0,
            "seed_namespace": "phase1-v2-freezer-test",
        },
        "pricing": {
            "models": {
                "Qwen/Qwen3.6-35B-A3B": {
                    "prefill_cached": 0.1,
                    "prefill_uncached": 0.5,
                    "sample": 1.3,
                },
                "thinkingmachines/Inkling": {
                    "prefill_cached": 0.3,
                    "prefill_uncached": 1.8,
                    "sample": 4.6,
                },
            }
        },
        "tracking": {
            "provider": "wandb",
            "project": "pixcell-test",
            "entity": "test",
            "group": "phase1",
            "local_record_is_authoritative": True,
        },
    }


def _task(index: int) -> EvaluationTask:
    task_id = f"F{index}"
    image = f"image-{task_id}".encode()
    digest = hashlib.sha256(image).hexdigest()
    return EvaluationTask(
        task_id=task_id,
        level="BENCHMARK",
        representation_id=f"benchmark-f{index}",
        observation=ModelObservation(
            image_bytes=image,
            footprint_um=(10.0, 5.0),
            image_sha256=digest,
        ),
        reference=VerifierReference(
            target_image_bytes=image,
            footprint_um=(10.0, 5.0),
            target_image_sha256=digest,
        ),
    )


def _manifest(tasks: list[EvaluationTask]) -> dict[str, Any]:
    value = {
        "task_sets": {
            "f1_f8": [{"task_id": task.task_id} for task in tasks],
        }
    }
    value["logical_sha256"] = canonical_json_sha256(value)
    return value


def _write_attempt(
    *,
    store: AttemptStore,
    protocol: dict[str, Any],
    task: EvaluationTask,
    job: Any,
    manifest_sha: str,
    bad_program_hash: bool = False,
) -> None:
    key = AttemptKey(
        protocol["study_id"],
        job.hypothesis_id,
        job.arm_id,
        job.task_id,
        job.attempt_index,
    )
    completion = (
        "```python\n"
        f"print('{job.hypothesis_id}-{job.arm_id}-{job.task_id}')\n"
        "```"
    )
    program = extract_code(completion)
    raw = f"secret raw reasoning\n{completion}"
    rates = protocol["pricing"]["models"][
        protocol["arms"][job.arm_id]["model"]
    ]
    prompt_tokens = 100
    completion_tokens = 20
    sample_cost = completion_tokens * rates["sample"] / 1_000_000
    store.write_sampling_receipt(
        key,
        {
            "request": {
                "max_tokens": 60000,
                "temperature": 1.0,
                "top_p": 1.0,
                "seed": job.seed,
            },
            "sample": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "stop_reason": "stop",
                "cap_hit": False,
                "raw_text": raw,
                "completion_text": completion,
                "reasoning_text": "secret raw reasoning",
                "answer_text": completion,
                "reasoning_tokens_exact": 2,
                "answer_tokens_exact": 18,
                "reasoning_tokens_estimate": None,
                "answer_tokens_estimate": None,
                "channel_token_count_basis": "test",
                "channel_parse_complete": True,
            },
            "sampling_seconds": 0.5,
            "raw_completion_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "completion_sha256": hashlib.sha256(
                completion.encode()
            ).hexdigest(),
            "run_manifest_record_sha256": manifest_sha,
            "cost_estimate_usd": {
                "cached_prefill": (
                    prompt_tokens * rates["prefill_cached"] / 1_000_000
                    + sample_cost
                ),
                "uncached_prefill": (
                    prompt_tokens * rates["prefill_uncached"] / 1_000_000
                    + sample_cost
                ),
            },
        },
    )
    store.write_evaluation(
        key,
        {
            "status": "ok",
            "attribution": "model",
            "pure_executable": True,
            "measurement_available": True,
            "measured_iou": 0.25,
            "measured_dice": 0.4,
            "aggregation_iou": 0.25,
            "program": program,
            "program_sha256": (
                "0" * 64
                if bad_program_hash
                else hashlib.sha256(program.encode()).hexdigest()
            ),
            "reference_sha256": task.reference.target_image_sha256,
            "violations": [],
            "error": None,
            "retryable": False,
            "evaluation_seconds": 0.25,
            "diagnostics": {
                "render_sha256": "e" * 64,
                "reference_sha256": task.reference.target_image_sha256,
            },
            "render_sha256": "e" * 64,
        },
    )


def _write_run(
    *,
    store: AttemptStore,
    protocol: dict[str, Any],
    hypothesis_id: str,
    arm_id: str,
    tasks: list[EvaluationTask],
    task_set_sha: str,
    omit_last: bool = False,
    bad_program_hash: bool = False,
) -> None:
    jobs = jobs_for_wave(
        protocol,
        hypothesis_id=hypothesis_id,
        wave_name="complete",
        task_ids=[task.task_id for task in tasks],
    )
    manifest = store.create_or_verify_run_manifest(
        RunKey(protocol["study_id"], hypothesis_id, arm_id),
        freezer._expected_run_manifest(
            protocol=protocol,
            hypothesis_id=hypothesis_id,
            arm_id=arm_id,
            source_git_sha=SOURCE_SHA,
            task_set_sha256=task_set_sha,
            prompt_sha256=PROMPT_SHA,
            sandbox_image_ref=SANDBOX[0],
            sandbox_image_id=SANDBOX[1],
            runtime=RUNTIME,
        ),
    )
    tasks_by_id = {task.task_id: task for task in tasks}
    selected = jobs[:-1] if omit_last else jobs
    for index, job in enumerate(selected):
        _write_attempt(
            store=store,
            protocol=protocol,
            task=tasks_by_id[job.task_id],
            job=job,
            manifest_sha=manifest.record_sha256,
            bad_program_hash=bad_program_hash and index == 0,
        )
    summary = summarize_arm(
        store=store,
        study_id=protocol["study_id"],
        hypothesis_id=hypothesis_id,
        arm_id=arm_id,
        jobs=jobs,
        tasks=tasks,
    )
    path = (
        store.external_root.joinpath(
            *store.run_relative_path(
                RunKey(protocol["study_id"], hypothesis_id, arm_id)
            ).parts
        )
        / "summary.json"
    )
    atomic_write_json(path, summary)


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    omit_last: bool = False,
    bad_program_hash: bool = False,
) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    protocol = _protocol()
    tasks = [_task(index) for index in range(1, 9)]
    manifest = _manifest(tasks)

    monkeypatch.setattr(freezer, "_git_head", lambda _root: SOURCE_SHA)
    monkeypatch.setattr(freezer, "_changed_paths", lambda _root: set())
    monkeypatch.setattr(
        freezer,
        "validate_runtime_stack",
        lambda _root: RUNTIME,
    )
    monkeypatch.setattr(
        freezer,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(
        freezer,
        "load_task_manifest",
        lambda _path, *, repo_root: manifest,
    )
    monkeypatch.setattr(
        freezer,
        "load_task_set",
        lambda *, repo_root, manifest, task_set: tasks,
    )
    monkeypatch.setattr(
        freezer,
        "_prompt_binding",
        lambda: (
            {
                "contract_version": freezer.EXPECTED_CONTRACT,
                "preprocess_version": "test",
            },
            PROMPT_SHA,
        ),
    )
    monkeypatch.setattr(
        freezer,
        "_expected_prompt_lengths",
        lambda _protocol, tasks: {
            (arm_id, task.task_id): 100
            for arm_id in freezer.EXPECTED_HYPOTHESES.values()
            for task in tasks
        },
    )
    monkeypatch.setattr(
        freezer,
        "_replay_attempts",
        lambda _attempts, *, expected_sandbox: None,
    )

    store = AttemptStore(repo_root=repo, external_root=external)
    task_set_sha = canonical_json_sha256(manifest["task_sets"]["f1_f8"])
    for index, (hypothesis_id, arm_id) in enumerate(
        freezer.EXPECTED_HYPOTHESES.items()
    ):
        _write_run(
            store=store,
            protocol=protocol,
            hypothesis_id=hypothesis_id,
            arm_id=arm_id,
            tasks=tasks,
            task_set_sha=task_set_sha,
            omit_last=omit_last and index == 0,
            bad_program_hash=bad_program_hash and index == 0,
        )
    return repo, external


def test_freeze_is_exact_idempotent_and_excludes_private_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    report = freezer.freeze_phase1(
        repo_root=repo,
        external_root=external,
        expected_source_sha=SOURCE_SHA,
    )
    output = repo / freezer.PHASE1_RELATIVE_ROOT
    first = {
        path.relative_to(output): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert report["attempt_count"] == 64
    assert report["program_count"] == 64
    assert set(first) == {
        Path("attempts.jsonl"),
        Path("programs.jsonl"),
        Path("summaries.json"),
        Path("release_manifest.json"),
        Path("checksums.sha256"),
    }
    combined = b"".join(first.values())
    assert b"secret raw reasoning" not in combined
    assert b"```python" not in combined
    programs = [
        json.loads(line)
        for line in first[Path("programs.jsonl")].decode().splitlines()
    ]
    assert len(programs) == 64
    assert all("program" in row for row in programs)
    assert all(
        hashlib.sha256(row["program"].encode()).hexdigest()
        == row["program_sha256"]
        for row in programs
    )

    checksums = first[Path("checksums.sha256")].decode().splitlines()
    assert len(checksums) == 4
    for line in checksums:
        digest, relative = line.split("  ", 1)
        assert digest == hashlib.sha256(
            first[Path(relative)]
        ).hexdigest()

    repeated = freezer.freeze_phase1(
        repo_root=repo,
        external_root=external,
        expected_source_sha=SOURCE_SHA,
    )
    assert repeated == report
    freezer.freeze_phase1(
        repo_root=repo,
        external_root=external,
        expected_source_sha=SOURCE_SHA,
        validate_only=True,
    )
    assert first == {
        path.relative_to(output): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }


def test_freeze_rejects_an_incomplete_32_attempt_arm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(
        tmp_path,
        monkeypatch,
        omit_last=True,
    )
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="not a complete F1-F8 G4 run",
    ):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_freeze_rejects_a_program_digest_that_does_not_match_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(
        tmp_path,
        monkeypatch,
        bad_program_hash=True,
    )
    with pytest.raises(freezer.Phase1FreezeError, match="program digest mismatch"):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_validate_rejects_tampered_tracked_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    freezer.freeze_phase1(
        repo_root=repo,
        external_root=external,
        expected_source_sha=SOURCE_SHA,
    )
    attempts = repo / freezer.PHASE1_RELATIVE_ROOT / "attempts.jsonl"
    attempts.write_bytes(attempts.read_bytes() + b"{}\n")
    with pytest.raises(freezer.Phase1FreezeError, match="differs"):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
            validate_only=True,
        )


def test_freeze_rejects_prompt_binding_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        freezer,
        "_prompt_binding",
        lambda: (
            {"contract_version": freezer.EXPECTED_CONTRACT},
            "9" * 64,
        ),
    )
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="run manifest does not match its launch",
    ):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_freeze_rejects_runtime_binding_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        freezer,
        "validate_runtime_stack",
        lambda _root: {
            **RUNTIME,
            "python": "3.13.15",
        },
    )
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="run manifest does not match its launch",
    ):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_freeze_rejects_a_summary_not_reproduced_from_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    path = (
        external
        / "studies"
        / freezer.EXPECTED_STUDY
        / "hypotheses"
        / "RC-H05"
        / "arms"
        / "qwen-on-60000"
        / "summary.json"
    )
    summary = json.loads(path.read_text())
    summary["attempts"] = 31
    path.write_text(json.dumps(summary))
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="summary does not reproduce",
    ):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_source_drift_outside_release_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        freezer,
        "_changed_paths",
        lambda _root: {repo / "rl" / "unexpected.py"},
    )
    with pytest.raises(freezer.Phase1FreezeError, match="source worktree differs"):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_protocol_shape_rejects_a_non_60k_arm() -> None:
    protocol = _protocol()
    protocol["arms"]["qwen-on-60000"]["max_output_tokens"] = 59999
    with pytest.raises(freezer.Phase1FreezeError, match="Qwen 60k arm changed"):
        freezer._validate_protocol_shape(protocol)


def test_release_manifest_is_finite_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    freezer.freeze_phase1(
        repo_root=repo,
        external_root=external,
        expected_source_sha=SOURCE_SHA,
    )
    release = json.loads(
        (
            repo
            / freezer.PHASE1_RELATIVE_ROOT
            / "release_manifest.json"
        ).read_text()
    )
    assert release["runtime"] == RUNTIME
    assert release["task_ids"] == list(freezer.EXPECTED_TASK_IDS)
    assert [run["expected_attempts"] for run in release["runs"]] == [32, 32]
    assert release["certification"] == {
        "programs_reexecuted_in_bound_sandbox": 64,
        "prompt_token_counts_recomputed_offline": True,
        "published_programs_are_successful_executables_only": True,
        "stored_and_replayed_metrics_must_match": True,
    }


def test_freeze_rejects_prompt_token_count_that_does_not_reproduce(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        freezer,
        "_expected_prompt_lengths",
        lambda _protocol, tasks: {
            (arm_id, task.task_id): 101
            for arm_id in freezer.EXPECTED_HYPOTHESES.values()
            for task in tasks
        },
    )
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="non-reproducible token accounting",
    ):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_replay_comparison_rejects_metric_drift() -> None:
    task = _task(1)
    evidence = freezer._AttemptEvidence(
        row={
            "hypothesis_id": "RC-H05",
            "arm_id": "qwen-on-60000",
            "task_id": "F1",
            "attempt_index": 1,
        },
        program_row={
            "program": "print('test')",
            "program_sha256": hashlib.sha256(
                b"print('test')"
            ).hexdigest(),
            "reference_sha256": task.reference.target_image_sha256,
        },
        task=task,
        stored_evaluation={
            "status": "ok",
            "attribution": "model",
            "pure_executable": True,
            "measurement_available": True,
            "measured_iou": 0.25,
            "measured_dice": 0.4,
            "aggregation_iou": 0.25,
            "violations": [],
            "render_sha256": "e" * 64,
        },
    )
    replayed = EvaluationResult(
        status=EvaluationStatus.OK,
        attribution=Attribution.MODEL,
        iou=0.26,
        dice=0.4,
        metrics={
            "render_sha256": "e" * 64,
            "reference_sha256": task.reference.target_image_sha256,
        },
    )
    with pytest.raises(freezer.Phase1FreezeError, match="replay IoU differs"):
        freezer._compare_replayed_evaluation(evidence, replayed)


def test_failed_fallback_text_is_not_published_as_program_source() -> None:
    task = _task(1)
    private_fallback = "<think>private reasoning without an answer"
    evidence = freezer._AttemptEvidence(
        row={
            "hypothesis_id": "RC-H05",
            "arm_id": "qwen-on-60000",
            "task_id": "F1",
            "attempt_index": 1,
            "status": "syntax_error",
        },
        program_row={
            "program": private_fallback,
            "program_sha256": hashlib.sha256(
                private_fallback.encode()
            ).hexdigest(),
            "reference_sha256": task.reference.target_image_sha256,
        },
        task=task,
        stored_evaluation={},
    )
    assert freezer._published_program_rows([evidence]) == []


def test_validation_allows_a_descendant_commit_containing_only_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    output = repo / freezer.PHASE1_RELATIVE_ROOT
    output.mkdir(parents=True)
    monkeypatch.setattr(freezer, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(
        freezer.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        freezer.subprocess,
        "check_output",
        lambda *_args, **_kwargs: (
            b"data/training/representation-curriculum-v2/"
            b"phase1/attempts.jsonl\0"
        ),
    )
    freezer._require_launch_source_state(
        repo_root=repo,
        output_root=output,
        expected_source_sha=SOURCE_SHA,
        validate_only=True,
    )


def test_validation_rejects_source_drift_after_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    output = repo / freezer.PHASE1_RELATIVE_ROOT
    output.mkdir(parents=True)
    monkeypatch.setattr(freezer, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(
        freezer.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        freezer.subprocess,
        "check_output",
        lambda *_args, **_kwargs: b"rl/common/prompt.py\0",
    )
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="changes source beyond",
    ):
        freezer._require_launch_source_state(
            repo_root=repo,
            output_root=output,
            expected_source_sha=SOURCE_SHA,
            validate_only=True,
        )


def test_replay_rejects_a_different_immutable_sandbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class WrongSandboxEvaluator:
        def __init__(self, **_kwargs: Any) -> None:
            self.execution_boundary = SimpleNamespace(
                image_ref="sha256:" + "1" * 64,
                image_id="sha256:" + "1" * 64,
            )

        def __enter__(self) -> WrongSandboxEvaluator:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def evaluate_batch(self, _requests: Any) -> Any:
            raise AssertionError("sandbox mismatch must precede evaluation")

    monkeypatch.setattr(
        freezer,
        "PixCellEvaluator",
        WrongSandboxEvaluator,
    )
    with pytest.raises(
        freezer.Phase1FreezeError,
        match="certification sandbox differs",
    ):
        freezer._replay_attempts(
            [],
            expected_sandbox=SANDBOX,
        )
