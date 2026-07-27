#!/usr/bin/env python3
"""Freeze or validate the compact, tracked Phase 1 baseline evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from rl.common.output import extract_code
from rl.common.preprocess import IMAGE_PREPROCESS_VERSION
from rl.common.prompt import CONTRACT_VERSION, prompt_asset_hashes
from rl.common.runtime import validate_runtime_stack
from rl.evaluation.attempt_store import (
    AttemptKey,
    AttemptStore,
    RunKey,
    StoredRecord,
)
from rl.evaluation.protocol import (
    JobSpec,
    jobs_for_wave,
    load_protocol,
    resolved_arm_ids,
    task_manifest_path,
)
from rl.evaluation.summarize import choose_operating_point, summarize_arm
from rl.evaluation.tasks import (
    EvaluationTask,
    canonical_json_sha256,
    load_task_manifest,
    load_task_set,
)
from rl.evaluation.tracking import deterministic_wandb_run_id


REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE1_RELATIVE_ROOT = Path(
    "data/training/representation-curriculum-v1/phase1"
)
RELEASE_SCHEMA = "pixcell-representation-curriculum-phase1-release-v1"
SUMMARIES_SCHEMA = "pixcell-representation-curriculum-phase1-summaries-v1"
ATTEMPT_INDEX_SCHEMA = "pixcell-representation-curriculum-attempt-v1"
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
_HYPOTHESIS_ORDER = ("RC-H00", "RC-H00R", "RC-H01", "RC-H02")


class Phase1FreezeError(RuntimeError):
    """The external ledger cannot certify the tracked Phase 1 release."""


@dataclass(frozen=True)
class _RunEvidence:
    hypothesis_id: str
    arm_id: str
    tasks: tuple[EvaluationTask, ...]
    jobs: tuple[JobSpec, ...]
    manifest: StoredRecord
    summary: dict[str, Any]


@dataclass(frozen=True)
class _Bundle:
    files: dict[PurePosixPath, bytes]
    release_manifest: dict[str, Any]

    @property
    def all_files(self) -> dict[PurePosixPath, bytes]:
        return {
            PurePosixPath("release_manifest.json"): _json_bytes(
                self.release_manifest
            ),
            **self.files,
        }


def _json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise Phase1FreezeError("release evidence is not finite JSON") from exc


def _jsonl_bytes(values: list[dict[str, Any]]) -> bytes:
    try:
        return b"".join(
            (
                json.dumps(
                    value,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            for value in values
        )
    except (TypeError, ValueError) as exc:
        raise Phase1FreezeError("attempt index is not finite JSON") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> Any:
        raise Phase1FreezeError(f"{path} contains non-finite number {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise Phase1FreezeError(
                    f"{path} contains duplicate key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_bytes(),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Phase1FreezeError(f"cannot read canonical JSON from {path}") from exc
    if not isinstance(value, dict):
        raise Phase1FreezeError(f"{path} must contain a JSON object")
    return value


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Phase1FreezeError("repository HEAD cannot be resolved") from exc


def _changed_paths(repo_root: Path) -> set[Path]:
    commands = (
        ["git", "diff", "--name-only", "-z"],
        ["git", "diff", "--cached", "--name-only", "-z"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    result: set[Path] = set()
    for command in commands:
        try:
            output = subprocess.check_output(command, cwd=repo_root)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise Phase1FreezeError("repository worktree cannot be inspected") from exc
        for raw in output.split(b"\0"):
            if raw:
                result.add((repo_root / os.fsdecode(raw)).resolve(strict=False))
    return result


def _require_source_clean_except_output(
    *,
    repo_root: Path,
    output_root: Path,
) -> None:
    drift = sorted(
        str(path.relative_to(repo_root))
        for path in _changed_paths(repo_root)
        if path != output_root and not path.is_relative_to(output_root)
    )
    if drift:
        raise Phase1FreezeError(
            "source worktree differs from the paid-launch commit outside the "
            f"tracked Phase 1 output: {drift}"
        )


def _phase1_output_root(repo_root: Path, requested: Path | None) -> Path:
    root = repo_root.expanduser().resolve(strict=True)
    expected = (root / PHASE1_RELATIVE_ROOT).resolve(strict=False)
    if expected == root or not expected.is_relative_to(root):
        raise Phase1FreezeError(
            "the tracked Phase 1 path resolves outside the source repository"
        )
    observed = (
        expected
        if requested is None
        else requested.expanduser().resolve(strict=False)
    )
    if observed != expected:
        raise Phase1FreezeError(
            f"Phase 1 evidence must be written exactly to {expected}"
        )
    return expected


def _validate_roots(
    *,
    repo_root: Path,
    external_root: Path,
    output_root: Path,
) -> tuple[Path, Path]:
    source = repo_root.expanduser().resolve(strict=True)
    external = external_root.expanduser().resolve(strict=True)
    if external == source or external.is_relative_to(source):
        raise Phase1FreezeError(
            "the mutable attempt ledger must remain outside the source repository"
        )
    if (
        output_root == external
        or output_root.is_relative_to(external)
        or external.is_relative_to(output_root)
    ):
        raise Phase1FreezeError("source ledger and tracked output overlap")
    return source, external


def _prompt_binding() -> tuple[dict[str, str], str]:
    binding = {
        "contract_version": CONTRACT_VERSION,
        "preprocess_version": IMAGE_PREPROCESS_VERSION,
        **prompt_asset_hashes(),
    }
    return binding, canonical_json_sha256(binding)


def _task_set(
    *,
    repo_root: Path,
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    hypothesis_id: str,
) -> tuple[list[EvaluationTask], str]:
    task_set_name = str(protocol["hypotheses"][hypothesis_id]["task_set"])
    tasks = load_task_set(
        repo_root=repo_root,
        manifest=manifest,
        task_set=task_set_name,
    )
    task_set_sha = canonical_json_sha256(manifest["task_sets"][task_set_name])
    return tasks, task_set_sha


def _expected_run_manifest(
    *,
    protocol: dict[str, Any],
    hypothesis_id: str,
    arm_id: str,
    source_git_sha: str,
    task_set_sha256: str,
    prompt_sha256: str,
    sandbox_image_ref: str,
    sandbox_image_id: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    if hypothesis_id != "RC-H01":
        allowed = resolved_arm_ids(
            protocol,
            hypothesis_id,
            selection=(
                {"rescue_required": True}
                if hypothesis_id == "RC-H00R"
                else None
            ),
        )
        if arm_id not in allowed:
            raise Phase1FreezeError(f"{hypothesis_id} does not register {arm_id}")
    return {
        "source_git_sha": source_git_sha,
        "protocol_sha256": protocol["logical_sha256"],
        "task_set_sha256": task_set_sha256,
        "prompt_sha256": prompt_sha256,
        "sandbox_image_ref": sandbox_image_ref,
        "sandbox_image_id": sandbox_image_id,
        "runtime": runtime,
        "model_binding": {
            "arm_id": arm_id,
            **protocol["arms"][arm_id],
            "temperature": protocol["sampling"]["temperature"],
            "top_p": protocol["sampling"]["top_p"],
        },
    }


def _load_run(
    *,
    store: AttemptStore,
    protocol: dict[str, Any],
    hypothesis_id: str,
    arm_id: str,
    source_git_sha: str,
    tasks: list[EvaluationTask],
    jobs: list[JobSpec],
    task_set_sha256: str,
    prompt_sha256: str,
    sandbox: tuple[str, str] | None,
    runtime: dict[str, Any],
) -> tuple[_RunEvidence, tuple[str, str]]:
    run_key = RunKey(protocol["study_id"], hypothesis_id, arm_id)
    manifest = store.load_run_manifest(run_key)
    if manifest is None:
        raise Phase1FreezeError(f"missing run manifest for {hypothesis_id}/{arm_id}")
    observed_sandbox = (
        str(manifest.payload.get("sandbox_image_ref", "")),
        str(manifest.payload.get("sandbox_image_id", "")),
    )
    if sandbox is not None and observed_sandbox != sandbox:
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} used a different evaluator sandbox"
        )
    expected = _expected_run_manifest(
        protocol=protocol,
        hypothesis_id=hypothesis_id,
        arm_id=arm_id,
        source_git_sha=source_git_sha,
        task_set_sha256=task_set_sha256,
        prompt_sha256=prompt_sha256,
        sandbox_image_ref=observed_sandbox[0],
        sandbox_image_id=observed_sandbox[1],
        runtime=runtime,
    )
    if manifest.payload != expected:
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} run manifest does not match the frozen launch"
        )
    summary = summarize_arm(
        store=store,
        study_id=protocol["study_id"],
        hypothesis_id=hypothesis_id,
        arm_id=arm_id,
        jobs=jobs,
        tasks=tasks,
    )
    if not summary["complete"]:
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} is incomplete: {summary['missing']}"
        )
    external_summary = (
        store.external_root.joinpath(*store.run_relative_path(run_key).parts)
        / "summary.json"
    )
    if not external_summary.is_file():
        raise Phase1FreezeError(
            f"missing canonical summary for {hypothesis_id}/{arm_id}"
        )
    if _load_json(external_summary) != summary:
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} summary does not reproduce from attempts"
        )
    return (
        _RunEvidence(
            hypothesis_id=hypothesis_id,
            arm_id=arm_id,
            tasks=tuple(tasks),
            jobs=tuple(
                job
                for job in jobs
                if job.hypothesis_id == hypothesis_id and job.arm_id == arm_id
            ),
            manifest=manifest,
            summary=summary,
        ),
        observed_sandbox,
    )


def _validate_receipt_and_evaluation(
    *,
    protocol: dict[str, Any],
    store: AttemptStore,
    task: EvaluationTask,
    job: JobSpec,
) -> tuple[StoredRecord, StoredRecord, str]:
    key = AttemptKey(
        protocol["study_id"],
        job.hypothesis_id,
        job.arm_id,
        job.task_id,
        job.attempt_index,
    )
    receipt = store.load_sampling_receipt(key)
    evaluation = store.load_evaluation(key)
    if receipt is None or evaluation is None:
        raise Phase1FreezeError(f"missing immutable attempt record for {key}")

    request = receipt.payload.get("request")
    sample = receipt.payload.get("sample")
    if not isinstance(request, dict) or not isinstance(sample, dict):
        raise Phase1FreezeError(f"{key} has an invalid sampling payload")
    arm = protocol["arms"][job.arm_id]
    expected_request = {
        "max_tokens": int(arm["max_output_tokens"]),
        "temperature": protocol["sampling"]["temperature"],
        "top_p": protocol["sampling"]["top_p"],
        "seed": job.seed,
    }
    if request != expected_request:
        raise Phase1FreezeError(f"{key} sampling request differs from protocol")
    required_sample = {
        "prompt_tokens",
        "completion_tokens",
        "stop_reason",
        "cap_hit",
        "raw_text",
        "completion_text",
        "reasoning_text",
        "answer_text",
        "reasoning_tokens_exact",
        "answer_tokens_exact",
        "reasoning_tokens_estimate",
        "answer_tokens_estimate",
        "channel_token_count_basis",
        "channel_parse_complete",
    }
    if set(sample) != required_sample:
        raise Phase1FreezeError(f"{key} sample fields differ from the frozen schema")
    prompt_tokens = sample["prompt_tokens"]
    completion_tokens = sample["completion_tokens"]
    if (
        isinstance(prompt_tokens, bool)
        or not isinstance(prompt_tokens, int)
        or prompt_tokens < 1
        or isinstance(completion_tokens, bool)
        or not isinstance(completion_tokens, int)
        or completion_tokens < 0
        or completion_tokens > int(request["max_tokens"])
    ):
        raise Phase1FreezeError(f"{key} has invalid token accounting")
    if bool(sample["cap_hit"]) != (sample["stop_reason"] == "length"):
        raise Phase1FreezeError(f"{key} cap-hit flag differs from its stop reason")
    if sample["cap_hit"] and completion_tokens != int(request["max_tokens"]):
        raise Phase1FreezeError(f"{key} length stop did not reach the output cap")
    reasoning_exact = sample["reasoning_tokens_exact"]
    answer_exact = sample["answer_tokens_exact"]
    if (reasoning_exact is None) != (answer_exact is None):
        raise Phase1FreezeError(f"{key} has a partial exact channel partition")
    if reasoning_exact is not None and (
        isinstance(reasoning_exact, bool)
        or not isinstance(reasoning_exact, int)
        or reasoning_exact < 0
        or isinstance(answer_exact, bool)
        or not isinstance(answer_exact, int)
        or answer_exact < 0
        or reasoning_exact + answer_exact != completion_tokens
    ):
        raise Phase1FreezeError(f"{key} exact channel tokens do not partition output")
    raw_text = str(sample["raw_text"])
    completion = str(sample["completion_text"])
    if receipt.payload.get("raw_completion_sha256") != hashlib.sha256(
        raw_text.encode("utf-8")
    ).hexdigest():
        raise Phase1FreezeError(f"{key} raw completion digest mismatch")
    if receipt.payload.get("completion_sha256") != hashlib.sha256(
        completion.encode("utf-8")
    ).hexdigest():
        raise Phase1FreezeError(f"{key} completion digest mismatch")
    if not math.isfinite(float(receipt.payload.get("sampling_seconds", -1))):
        raise Phase1FreezeError(f"{key} has non-finite sampling duration")
    costs = receipt.payload.get("cost_estimate_usd")
    if not isinstance(costs, dict) or set(costs) != {
        "cached_prefill",
        "uncached_prefill",
    }:
        raise Phase1FreezeError(f"{key} has invalid cost evidence")
    rates = protocol["pricing"]["models"][arm["model"]]
    sample_cost = completion_tokens * float(rates["sample"]) / 1_000_000
    expected_costs = {
        "cached_prefill": (
            prompt_tokens * float(rates["prefill_cached"]) / 1_000_000
            + sample_cost
        ),
        "uncached_prefill": (
            prompt_tokens * float(rates["prefill_uncached"]) / 1_000_000
            + sample_cost
        ),
    }
    if costs != expected_costs:
        raise Phase1FreezeError(f"{key} cost evidence does not reproduce")

    measured = evaluation.payload
    required_evaluation = {
        "status",
        "attribution",
        "pure_executable",
        "measurement_available",
        "measured_iou",
        "measured_dice",
        "aggregation_iou",
        "program",
        "program_sha256",
        "reference_sha256",
        "violations",
        "error",
        "retryable",
        "evaluation_seconds",
        "diagnostics",
    }
    allowed_evaluation = required_evaluation | {"render_sha256"}
    if not required_evaluation.issubset(measured) or not set(measured).issubset(
        allowed_evaluation
    ):
        raise Phase1FreezeError(
            f"{key} evaluation fields differ from the frozen schema"
        )
    if measured["attribution"] != "model":
        raise Phase1FreezeError(
            f"{key} is an evaluator/reference failure, not a model result"
        )
    program = str(measured["program"])
    if program != extract_code(completion):
        raise Phase1FreezeError(f"{key} stored program does not match extraction")
    if measured["program_sha256"] != hashlib.sha256(
        program.encode("utf-8")
    ).hexdigest():
        raise Phase1FreezeError(f"{key} program digest mismatch")
    if measured["reference_sha256"] != task.reference.target_image_sha256:
        raise Phase1FreezeError(f"{key} reference digest mismatch")
    aggregation_iou = float(measured["aggregation_iou"])
    if not math.isfinite(aggregation_iou) or not 0 <= aggregation_iou <= 1:
        raise Phase1FreezeError(f"{key} has invalid aggregation IoU")
    measured_iou = measured["measured_iou"]
    expected_iou = 0.0 if measured_iou is None else float(measured_iou)
    if aggregation_iou != expected_iou:
        raise Phase1FreezeError(f"{key} aggregation IoU is not the raw model IoU")
    if bool(measured["measurement_available"]) != (measured_iou is not None):
        raise Phase1FreezeError(f"{key} measurement-availability flag is inconsistent")
    if measured_iou is not None and "render_sha256" not in measured:
        raise Phase1FreezeError(f"{key} measured geometry has no render digest")
    if bool(measured["pure_executable"]) != (measured["status"] == "ok"):
        raise Phase1FreezeError(f"{key} executable flag is inconsistent with status")
    return receipt, evaluation, program


def _collect_run_attempts(
    *,
    protocol: dict[str, Any],
    store: AttemptStore,
    evidence: _RunEvidence,
) -> tuple[list[dict[str, Any]], dict[PurePosixPath, bytes]]:
    tasks = {task.task_id: task for task in evidence.tasks}
    rows: list[dict[str, Any]] = []
    programs: dict[PurePosixPath, bytes] = {}
    for job in evidence.jobs:
        task = tasks[job.task_id]
        receipt, evaluation, program = _validate_receipt_and_evaluation(
            protocol=protocol,
            store=store,
            task=task,
            job=job,
        )
        program_path = PurePosixPath(
            "programs",
            job.hypothesis_id,
            job.arm_id,
            job.task_id,
            f"attempt_{job.attempt_index:02d}.py",
        )
        program_bytes = program.encode("utf-8")
        if program_path in programs and programs[program_path] != program_bytes:
            raise Phase1FreezeError(f"program-path collision at {program_path}")
        programs[program_path] = program_bytes
        sample = receipt.payload["sample"]
        measured = evaluation.payload
        rows.append(
            {
                "schema_version": ATTEMPT_INDEX_SCHEMA,
                "study_id": protocol["study_id"],
                "hypothesis_id": job.hypothesis_id,
                "arm_id": job.arm_id,
                "task_id": job.task_id,
                "level": task.level,
                "representation_id": task.representation_id,
                "attempt_index": job.attempt_index,
                "seed": job.seed,
                "status": measured["status"],
                "violations": measured["violations"],
                "error": measured["error"],
                "retryable": measured["retryable"],
                "pure_executable": measured["pure_executable"],
                "measurement_available": measured["measurement_available"],
                "aggregation_iou": measured["aggregation_iou"],
                "measured_iou": measured["measured_iou"],
                "measured_dice": measured["measured_dice"],
                "cap_hit": sample["cap_hit"],
                "stop_reason": sample["stop_reason"],
                "prompt_tokens": sample["prompt_tokens"],
                "completion_tokens": sample["completion_tokens"],
                "reasoning_tokens_exact": sample["reasoning_tokens_exact"],
                "answer_tokens_exact": sample["answer_tokens_exact"],
                "reasoning_tokens_estimate": sample[
                    "reasoning_tokens_estimate"
                ],
                "answer_tokens_estimate": sample["answer_tokens_estimate"],
                "channel_token_count_basis": sample[
                    "channel_token_count_basis"
                ],
                "channel_parse_complete": sample["channel_parse_complete"],
                "estimated_cost_usd": receipt.payload["cost_estimate_usd"],
                "sampling_seconds": receipt.payload["sampling_seconds"],
                "evaluation_seconds": measured["evaluation_seconds"],
                "diagnostics": measured["diagnostics"],
                "raw_completion_sha256": receipt.payload[
                    "raw_completion_sha256"
                ],
                "completion_sha256": receipt.payload["completion_sha256"],
                "sampling_record_sha256": receipt.record_sha256,
                "evaluation_record_sha256": evaluation.record_sha256,
                "program_path": program_path.as_posix(),
                "program_sha256": measured["program_sha256"],
                "reference_sha256": measured["reference_sha256"],
                **(
                    {"render_sha256": measured["render_sha256"]}
                    if measured.get("render_sha256") is not None
                    else {}
                ),
            }
        )
    return rows, programs


def _selection_path(store: AttemptStore, name: str) -> Path:
    return (
        store.external_root
        / "studies"
        / "representation-curriculum-v1"
        / "selections"
        / name
    )


def _require_selection(path: Path, expected: dict[str, Any]) -> None:
    if not path.is_file():
        raise Phase1FreezeError(f"missing canonical selection receipt: {path}")
    if _load_json(path) != expected:
        raise Phase1FreezeError(
            f"{path.name} does not reproduce from immutable attempts"
        )


def _collect_bundle(
    *,
    repo_root: Path,
    external_root: Path,
    expected_source_sha: str,
) -> _Bundle:
    if not _SOURCE_SHA.fullmatch(expected_source_sha):
        raise Phase1FreezeError(
            "expected source SHA must be a full lowercase Git commit SHA"
        )
    if _git_head(repo_root) != expected_source_sha:
        raise Phase1FreezeError("current source HEAD differs from the launch SHA")
    protocol = load_protocol(repo_root)
    manifest = load_task_manifest(task_manifest_path(repo_root), repo_root=repo_root)
    prompt_binding, prompt_sha = _prompt_binding()
    runtime = validate_runtime_stack(repo_root)
    store = AttemptStore(repo_root=repo_root, external_root=external_root)
    source_git_sha = expected_source_sha
    sandbox: tuple[str, str] | None = None
    runs: list[_RunEvidence] = []

    dev_tasks, dev_task_sha = _task_set(
        repo_root=repo_root,
        protocol=protocol,
        manifest=manifest,
        hypothesis_id="RC-H00",
    )
    dev_ids = [task.task_id for task in dev_tasks]
    h00_jobs = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H00",
        wave_name="complete",
        task_ids=dev_ids,
    )
    h00_summaries: dict[str, dict[str, Any]] = {}
    for arm_id in protocol["hypotheses"]["RC-H00"]["arm_ids"]:
        evidence, sandbox = _load_run(
            store=store,
            protocol=protocol,
            hypothesis_id="RC-H00",
            arm_id=str(arm_id),
            source_git_sha=source_git_sha,
            tasks=dev_tasks,
            jobs=h00_jobs,
            task_set_sha256=dev_task_sha,
            prompt_sha256=prompt_sha,
            sandbox=sandbox,
            runtime=runtime,
        )
        runs.append(evidence)
        h00_summaries[str(arm_id)] = evidence.summary

    preliminary = choose_operating_point(
        protocol=protocol,
        source_git_sha=source_git_sha,
        source_summaries=h00_summaries,
    )
    _require_selection(
        _selection_path(store, "operating_point.preliminary.json"),
        preliminary,
    )
    final_selection = preliminary
    if preliminary["rescue_required"]:
        rescue_arm = str(protocol["hypotheses"]["RC-H00R"]["arm_ids"][0])
        h00r_jobs = jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00R",
            wave_name="complete",
            task_ids=dev_ids,
            selection=preliminary,
        )
        rescue, sandbox = _load_run(
            store=store,
            protocol=protocol,
            hypothesis_id="RC-H00R",
            arm_id=rescue_arm,
            source_git_sha=source_git_sha,
            tasks=dev_tasks,
            jobs=h00r_jobs,
            task_set_sha256=dev_task_sha,
            prompt_sha256=prompt_sha,
            sandbox=sandbox,
            runtime=runtime,
        )
        runs.append(rescue)
        final_selection = choose_operating_point(
            protocol=protocol,
            source_git_sha=source_git_sha,
            source_summaries=h00_summaries,
            rescue_summary=rescue.summary,
        )
    if not final_selection["complete"]:
        raise Phase1FreezeError("operating-point selection is not complete")
    _require_selection(
        _selection_path(store, "operating_point.json"),
        final_selection,
    )

    benchmark_tasks, benchmark_task_sha = _task_set(
        repo_root=repo_root,
        protocol=protocol,
        manifest=manifest,
        hypothesis_id="RC-H01",
    )
    benchmark_ids = [task.task_id for task in benchmark_tasks]
    for hypothesis_id in ("RC-H01", "RC-H02"):
        jobs = jobs_for_wave(
            protocol,
            hypothesis_id=hypothesis_id,
            wave_name="complete",
            task_ids=benchmark_ids,
            selection=final_selection if hypothesis_id == "RC-H01" else None,
        )
        for arm_id in resolved_arm_ids(
            protocol,
            hypothesis_id,
            selection=final_selection if hypothesis_id == "RC-H01" else None,
        ):
            evidence, sandbox = _load_run(
                store=store,
                protocol=protocol,
                hypothesis_id=hypothesis_id,
                arm_id=arm_id,
                source_git_sha=source_git_sha,
                tasks=benchmark_tasks,
                jobs=jobs,
                task_set_sha256=benchmark_task_sha,
                prompt_sha256=prompt_sha,
                sandbox=sandbox,
                runtime=runtime,
            )
            runs.append(evidence)

    attempts: list[dict[str, Any]] = []
    programs: dict[PurePosixPath, bytes] = {}
    for evidence in runs:
        run_attempts, run_programs = _collect_run_attempts(
            protocol=protocol,
            store=store,
            evidence=evidence,
        )
        attempts.extend(run_attempts)
        for path, content in run_programs.items():
            if path in programs and programs[path] != content:
                raise Phase1FreezeError(f"duplicate program evidence at {path}")
            programs[path] = content
    attempts.sort(
        key=lambda value: (
            _HYPOTHESIS_ORDER.index(value["hypothesis_id"]),
            value["arm_id"],
            value["task_id"],
            value["attempt_index"],
        )
    )

    summaries_document = {
        "schema_version": SUMMARIES_SCHEMA,
        "study_id": protocol["study_id"],
        "summaries": {
            f"{run.hypothesis_id}/{run.arm_id}": run.summary for run in runs
        },
    }
    summaries_document["logical_sha256"] = canonical_json_sha256(
        summaries_document
    )
    files: dict[PurePosixPath, bytes] = {
        PurePosixPath("operating_point_selection.json"): _json_bytes(
            final_selection
        ),
        PurePosixPath("summaries.json"): _json_bytes(summaries_document),
        PurePosixPath("attempts.jsonl"): _jsonl_bytes(attempts),
        **programs,
    }
    file_inventory = [
        {
            "path": path.as_posix(),
            "sha256": _sha256_bytes(content),
            "bytes": len(content),
        }
        for path, content in sorted(files.items(), key=lambda item: item[0])
    ]
    release_manifest: dict[str, Any] = {
        "schema_version": RELEASE_SCHEMA,
        "study_id": protocol["study_id"],
        "phase": "phase1-zero-shot-baselines",
        "source_git_sha": source_git_sha,
        "protocol_sha256": protocol["logical_sha256"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "dataset": protocol["dataset"],
        "prompt": prompt_binding,
        "prompt_sha256": prompt_sha,
        "sandbox": {
            "image_ref": sandbox[0] if sandbox is not None else "",
            "image_id": sandbox[1] if sandbox is not None else "",
        },
        "selection_sha256": final_selection["logical_sha256"],
        "selected_qwen_arm": final_selection["selected_arm"],
        "attempt_count": len(attempts),
        "program_count": len(programs),
        "runs": [
            {
                "hypothesis_id": run.hypothesis_id,
                "arm_id": run.arm_id,
                "expected_attempts": len(run.jobs),
                "run_manifest_payload": run.manifest.payload,
                "run_manifest_payload_sha256": run.manifest.payload_sha256,
                "run_manifest_record_sha256": run.manifest.record_sha256,
                "summary_sha256": run.summary["logical_sha256"],
                "wandb_run_id": deterministic_wandb_run_id(
                    RunKey(
                        protocol["study_id"],
                        run.hypothesis_id,
                        run.arm_id,
                    )
                ),
            }
            for run in runs
        ],
        "tracking": {
            "provider": protocol["tracking"]["provider"],
            "project": protocol["tracking"]["project"],
            "entity": protocol["tracking"].get("entity"),
            "group": protocol["tracking"].get("group"),
            "local_record_is_authoritative": protocol["tracking"][
                "local_record_is_authoritative"
            ],
        },
        "files": file_inventory,
        "excluded_external_state": [
            "raw_completion_text",
            "reasoning_text",
            "answer_text",
            "wandb_state",
            "tracking_errors",
        ],
    }
    release_manifest["logical_sha256"] = canonical_json_sha256(
        release_manifest
    )
    return _Bundle(files=files, release_manifest=release_manifest)


def _assert_exact_output(output_root: Path, expected: dict[PurePosixPath, bytes]) -> None:
    if not output_root.is_dir():
        raise Phase1FreezeError(f"tracked Phase 1 release is missing: {output_root}")
    observed_paths = {
        PurePosixPath(path.relative_to(output_root).as_posix())
        for path in output_root.rglob("*")
        if path.is_file()
    }
    expected_paths = set(expected)
    if observed_paths != expected_paths:
        raise Phase1FreezeError(
            "tracked Phase 1 file inventory differs: "
            f"missing={sorted(str(value) for value in expected_paths - observed_paths)}, "
            f"extra={sorted(str(value) for value in observed_paths - expected_paths)}"
        )
    for relative, content in expected.items():
        path = output_root.joinpath(*relative.parts)
        if path.is_symlink() or path.read_bytes() != content:
            raise Phase1FreezeError(f"tracked evidence differs at {relative}")


def _write_create_or_verify(
    output_root: Path,
    expected: dict[PurePosixPath, bytes],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    observed_files = [
        path for path in output_root.rglob("*") if path.is_file() or path.is_symlink()
    ]
    expected_paths = {
        output_root.joinpath(*relative.parts): content
        for relative, content in expected.items()
    }
    extras = sorted(
        str(path.relative_to(output_root))
        for path in observed_files
        if path not in expected_paths
    )
    if extras:
        raise Phase1FreezeError(
            f"refusing to overwrite a non-canonical Phase 1 directory: {extras}"
        )
    for path, content in expected_paths.items():
        if path.exists() or path.is_symlink():
            if path.is_symlink() or path.read_bytes() != content:
                raise Phase1FreezeError(
                    f"refusing to replace existing evidence at {path}"
                )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        try:
            with temporary.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    _assert_exact_output(output_root, expected)


def freeze_phase1(
    *,
    repo_root: Path,
    external_root: Path,
    expected_source_sha: str,
    output: Path | None = None,
    validate_only: bool = False,
) -> dict[str, Any]:
    """Recompute the canonical record, then write or validate exact bytes."""

    output_root = _phase1_output_root(repo_root, output)
    source, external = _validate_roots(
        repo_root=repo_root,
        external_root=external_root,
        output_root=output_root,
    )
    _require_source_clean_except_output(
        repo_root=source,
        output_root=output_root,
    )
    bundle = _collect_bundle(
        repo_root=source,
        external_root=external,
        expected_source_sha=expected_source_sha,
    )
    expected = bundle.all_files
    if validate_only:
        _assert_exact_output(output_root, expected)
    else:
        _write_create_or_verify(output_root, expected)
    return bundle.release_manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    result.add_argument("--external-root", type=Path, required=True)
    result.add_argument("--expected-source-sha", required=True)
    result.add_argument("--output", type=Path)
    result.add_argument(
        "--validate",
        action="store_true",
        help="validate an existing tracked release without writing",
    )
    return result


def main() -> None:
    args = parser().parse_args()
    report = freeze_phase1(
        repo_root=args.repo_root,
        external_root=args.external_root,
        expected_source_sha=args.expected_source_sha,
        output=args.output,
        validate_only=args.validate,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
