from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from rl.common.contracts import ModelObservation, VerifierReference
from rl.common.output import extract_code
from rl.evaluation.attempt_store import AttemptKey, AttemptStore, RunKey
from rl.evaluation.protocol import jobs_for_wave, resolved_arm_ids
from rl.evaluation.summarize import (
    atomic_write_json,
    choose_operating_point,
    summarize_arm,
)
from rl.evaluation.tasks import EvaluationTask, canonical_json_sha256
from rl.studies.representation_curriculum_v1 import freeze_phase1 as freezer


SOURCE_SHA = "a" * 40
PROMPT_SHA = "b" * 64
SANDBOX = ("sha256:" + "c" * 64, "sha256:" + "c" * 64)
RUNTIME = {
    "python": "3.13.14",
    "packages": {"tinker": "0.22.7"},
    "tinker_cookbook_commit": "f" * 40,
}


def _arm(model: str, max_tokens: int) -> dict[str, Any]:
    return {
        "provider": "tinker",
        "model": model,
        "renderer": f"renderer-{model}",
        "thinking": False,
        "thinking_effort": None,
        "max_output_tokens": max_tokens,
        "context_tokens": 65536,
        "max_image_long_edge": 1440,
    }


def _protocol() -> dict[str, Any]:
    return {
        "study_id": "representation-curriculum-v1",
        "logical_sha256": "d" * 64,
        "dataset": {
            "repository": "example/pixcell",
            "revision": "test",
            "configuration": "depth",
        },
        "arms": {
            "q0": _arm("qwen", 4096),
            "q1": _arm("qwen", 16384),
            "qr": _arm("qwen", 32768),
            "ink": _arm("inkling", 20000),
        },
        "hypotheses": {
            "RC-H00": {
                "arm_ids": ["q0", "q1"],
                "attempts_per_task": 1,
                "task_set": "dev",
                "waves": {
                    "complete": {
                        "attempt_indices": [1],
                        "task_count": 1,
                    }
                },
            },
            "RC-H00R": {
                "arm_ids": ["qr"],
                "attempts_per_task": 1,
                "task_set": "dev",
                "trigger": {
                    "source_arm": "q1",
                    "metric": "cap_hit_rate",
                    "operator": ">",
                    "threshold": 0.05,
                },
                "waves": {
                    "complete": {
                        "attempt_indices": [1],
                        "task_count": 1,
                    }
                },
            },
            "RC-H01": {
                "arm_roles": {"incumbent": "q0", "selected": "RC-H00"},
                "attempts_per_task": 1,
                "task_set": "bench",
                "waves": {
                    "complete": {
                        "attempt_indices": [1],
                        "task_count": 1,
                    }
                },
            },
            "RC-H02": {
                "arm_ids": ["ink"],
                "attempts_per_task": 1,
                "task_set": "bench",
                "waves": {
                    "complete": {
                        "attempt_indices": [1],
                        "task_count": 1,
                    }
                },
            },
        },
        "sampling": {
            "temperature": 1.0,
            "top_p": 1.0,
            "seed_namespace": "phase1-freezer-test",
        },
        "pricing": {
            "models": {
                "qwen": {
                    "prefill_cached": 0.1,
                    "prefill_uncached": 0.5,
                    "sample": 1.3,
                },
                "inkling": {
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
        "operating_point_selection": {
            "primary_metric": "representation_macro_mean_iou",
            "metric_tie_band": 0.01,
            "tie_breakers": [
                "pure_executable_rate_desc",
                "estimated_uncached_cost_usd_asc",
                "completion_tokens_median_asc",
                "arm_id_asc",
            ],
        },
    }


def _task(task_id: str, level: str) -> EvaluationTask:
    image = f"image-{task_id}".encode()
    digest = hashlib.sha256(image).hexdigest()
    return EvaluationTask(
        task_id=task_id,
        level=level,
        representation_id=f"representation-{task_id}",
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


def _manifest(dev: EvaluationTask, bench: EvaluationTask) -> dict[str, Any]:
    value = {
        "task_sets": {
            "dev": [{"task_id": dev.task_id}],
            "bench": [{"task_id": bench.task_id}],
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
    score: float,
    cap_hit: bool,
) -> None:
    key = AttemptKey(
        protocol["study_id"],
        job.hypothesis_id,
        job.arm_id,
        job.task_id,
        job.attempt_index,
    )
    completion = f"```python\nprint('{job.hypothesis_id}-{job.arm_id}')\n```"
    program = extract_code(completion)
    raw = f"private reasoning\n{completion}"
    rates = protocol["pricing"]["models"][
        protocol["arms"][job.arm_id]["model"]
    ]
    prompt_tokens = 100
    completion_tokens = (
        protocol["arms"][job.arm_id]["max_output_tokens"]
        if cap_hit
        else 20
    )
    sample_cost = completion_tokens * rates["sample"] / 1_000_000
    store.write_sampling_receipt(
        key,
        {
            "request": {
                "max_tokens": protocol["arms"][job.arm_id][
                    "max_output_tokens"
                ],
                "temperature": 1.0,
                "top_p": 1.0,
                "seed": job.seed,
            },
            "sample": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "stop_reason": "length" if cap_hit else "stop",
                "cap_hit": cap_hit,
                "raw_text": raw,
                "completion_text": completion,
                "reasoning_text": "private reasoning",
                "answer_text": completion,
                "reasoning_tokens_exact": 2,
                "answer_tokens_exact": completion_tokens - 2,
                "reasoning_tokens_estimate": None,
                "answer_tokens_estimate": None,
                "channel_token_count_basis": "test",
                "channel_parse_complete": True,
            },
            "sampling_seconds": 0.5,
            "raw_completion_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "completion_sha256": hashlib.sha256(completion.encode()).hexdigest(),
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
            "measured_iou": score,
            "measured_dice": min(1.0, score + 0.1),
            "aggregation_iou": score,
            "program": program,
            "program_sha256": hashlib.sha256(program.encode()).hexdigest(),
            "reference_sha256": task.reference.target_image_sha256,
            "violations": [],
            "error": None,
            "retryable": False,
            "evaluation_seconds": 0.25,
            "diagnostics": {},
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
    jobs: list[Any],
    task_set_sha: str,
    score: float,
    cap_hit: bool = False,
) -> dict[str, Any]:
    run_key = RunKey(protocol["study_id"], hypothesis_id, arm_id)
    store.create_or_verify_run_manifest(
        run_key,
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
    task_by_id = {task.task_id: task for task in tasks}
    for job in jobs:
        if job.arm_id == arm_id:
            _write_attempt(
                store=store,
                protocol=protocol,
                task=task_by_id[job.task_id],
                job=job,
                score=score,
                cap_hit=cap_hit,
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
        store.external_root.joinpath(*store.run_relative_path(run_key).parts)
        / "summary.json"
    )
    atomic_write_json(path, summary)
    return summary


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    trigger_rescue: bool = False,
    include_rescue: bool = True,
) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    protocol = _protocol()
    dev = _task("D1", "L0")
    bench = _task("F1", "BENCHMARK")
    manifest = _manifest(dev, bench)

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
        lambda *, repo_root, manifest, task_set: (
            [dev] if task_set == "dev" else [bench]
        ),
    )
    monkeypatch.setattr(
        freezer,
        "_prompt_binding",
        lambda: ({"contract_version": "test"}, PROMPT_SHA),
    )

    store = AttemptStore(repo_root=repo, external_root=external)
    dev_sha = canonical_json_sha256(manifest["task_sets"]["dev"])
    bench_sha = canonical_json_sha256(manifest["task_sets"]["bench"])
    h00_jobs = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H00",
        wave_name="complete",
        task_ids=[dev.task_id],
    )
    h00 = {
        "q0": _write_run(
            store=store,
            protocol=protocol,
            hypothesis_id="RC-H00",
            arm_id="q0",
            tasks=[dev],
            jobs=h00_jobs,
            task_set_sha=dev_sha,
            score=0.2,
        ),
        "q1": _write_run(
            store=store,
            protocol=protocol,
            hypothesis_id="RC-H00",
            arm_id="q1",
            tasks=[dev],
            jobs=h00_jobs,
            task_set_sha=dev_sha,
            score=0.4,
            cap_hit=trigger_rescue,
        ),
    }
    preliminary = choose_operating_point(
        protocol=protocol,
        source_git_sha=SOURCE_SHA,
        source_summaries=h00,
    )
    selection_root = (
        external
        / "studies"
        / protocol["study_id"]
        / "selections"
    )
    atomic_write_json(
        selection_root / "operating_point.preliminary.json",
        preliminary,
    )
    final = preliminary
    if trigger_rescue and include_rescue:
        rescue_jobs = jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00R",
            wave_name="complete",
            task_ids=[dev.task_id],
            selection=preliminary,
        )
        rescue_summary = _write_run(
            store=store,
            protocol=protocol,
            hypothesis_id="RC-H00R",
            arm_id="qr",
            tasks=[dev],
            jobs=rescue_jobs,
            task_set_sha=dev_sha,
            score=0.5,
        )
        final = choose_operating_point(
            protocol=protocol,
            source_git_sha=SOURCE_SHA,
            source_summaries=h00,
            rescue_summary=rescue_summary,
        )
    atomic_write_json(selection_root / "operating_point.json", final)
    if trigger_rescue and not include_rescue:
        return repo, external

    for hypothesis_id in ("RC-H01", "RC-H02"):
        jobs = jobs_for_wave(
            protocol,
            hypothesis_id=hypothesis_id,
            wave_name="complete",
            task_ids=[bench.task_id],
            selection=final if hypothesis_id == "RC-H01" else None,
        )
        for arm_id in resolved_arm_ids(
            protocol,
            hypothesis_id,
            selection=final if hypothesis_id == "RC-H01" else None,
        ):
            _write_run(
                store=store,
                protocol=protocol,
                hypothesis_id=hypothesis_id,
                arm_id=arm_id,
                tasks=[bench],
                jobs=jobs,
                task_set_sha=bench_sha,
                score=0.3,
            )
    return repo, external


def test_freeze_is_deterministic_idempotent_and_excludes_raw_text(
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
    assert report["attempt_count"] == 5
    assert report["selected_qwen_arm"] == "q1"
    assert b"private reasoning" not in b"".join(first.values())
    assert not any(b"```python" in value for value in first.values())

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


def test_triggered_rescue_is_mandatory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(
        tmp_path,
        monkeypatch,
        trigger_rescue=True,
        include_rescue=False,
    )
    with pytest.raises(freezer.Phase1FreezeError, match="missing run manifest"):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
        )


def test_triggered_rescue_is_included_in_the_canonical_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(
        tmp_path,
        monkeypatch,
        trigger_rescue=True,
        include_rescue=True,
    )
    report = freezer.freeze_phase1(
        repo_root=repo,
        external_root=external,
        expected_source_sha=SOURCE_SHA,
    )
    assert report["selected_qwen_arm"] == "qr"
    assert report["attempt_count"] == 6
    assert any(
        run["hypothesis_id"] == "RC-H00R" for run in report["runs"]
    )


def test_output_location_is_fixed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, external = _prepare(tmp_path, monkeypatch)
    with pytest.raises(freezer.Phase1FreezeError, match="exactly"):
        freezer.freeze_phase1(
            repo_root=repo,
            external_root=external,
            expected_source_sha=SOURCE_SHA,
            output=repo / "somewhere-else",
        )


def test_source_drift_outside_the_release_directory_is_rejected(
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
