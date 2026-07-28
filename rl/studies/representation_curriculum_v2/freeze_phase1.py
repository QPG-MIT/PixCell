#!/usr/bin/env python3
"""Freeze or validate the compact Phase 1 evidence for the v2 baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from rl.common.evaluator import Attribution, EvaluationResult, PixCellEvaluator
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
    arm_spec,
    jobs_for_wave,
    load_protocol,
)
from rl.evaluation.runner import _messages, _sampler_target
from rl.evaluation.samplers import TinkerSampler
from rl.evaluation.summarize import summarize_arm
from rl.evaluation.tasks import (
    EvaluationTask,
    canonical_json_sha256,
    load_task_manifest,
    load_task_set,
)
from rl.evaluation.tracking import deterministic_wandb_run_id


REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_FILE = Path(__file__).with_name("protocol.json")
TASK_MANIFEST_FILE = Path(__file__).with_name("task_manifest.json")
PHASE1_RELATIVE_ROOT = Path(
    "data/training/representation-curriculum-v2/phase1"
)
RELEASE_SCHEMA = "pixcell-representation-curriculum-phase1-release-v2"
SUMMARIES_SCHEMA = "pixcell-representation-curriculum-phase1-summaries-v2"
ATTEMPT_INDEX_SCHEMA = "pixcell-representation-curriculum-attempt-v2"
PROGRAM_INDEX_SCHEMA = "pixcell-representation-curriculum-program-v2"
EXPECTED_CONTRACT = "pixcell-direct-reconstruction-v2"
EXPECTED_STUDY = "representation-curriculum-v2"
EXPECTED_HYPOTHESES = {
    "RC-H05": "qwen-on-60000",
    "RC-H06": "inkling-e09-60000",
}
EXPECTED_TASK_IDS = tuple(f"F{index}" for index in range(1, 9))
EXPECTED_ATTEMPTS = tuple(range(1, 5))
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Phase1FreezeError(RuntimeError):
    """The external ledger cannot certify the tracked v2 Phase 1 release."""


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
        release_path = PurePosixPath("release_manifest.json")
        release_bytes = _json_bytes(self.release_manifest)
        checksummed = {release_path: release_bytes, **self.files}
        checksums = b"".join(
            (
                f"{_sha256_bytes(content)}  {path.as_posix()}\n"
            ).encode("ascii")
            for path, content in sorted(
                checksummed.items(),
                key=lambda item: item[0],
            )
        )
        return {
            **checksummed,
            PurePosixPath("checksums.sha256"): checksums,
        }


@dataclass(frozen=True)
class _AttemptEvidence:
    row: dict[str, Any]
    program_row: dict[str, Any]
    task: EvaluationTask
    stored_evaluation: dict[str, Any]


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
        raise Phase1FreezeError(
            f"cannot read canonical JSON from {path}"
        ) from exc
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


def _require_launch_source_state(
    *,
    repo_root: Path,
    output_root: Path,
    expected_source_sha: str,
    validate_only: bool,
) -> None:
    """Bind source to launch SHA while allowing a later data-only commit."""

    head = _git_head(repo_root)
    if head == expected_source_sha:
        return
    if not validate_only:
        raise Phase1FreezeError("current source HEAD differs from the launch SHA")
    try:
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                expected_source_sha,
                head,
            ],
            cwd=repo_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        changed = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                "-z",
                f"{expected_source_sha}..{head}",
            ],
            cwd=repo_root,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Phase1FreezeError(
            "the launch SHA is not an ancestor of the evidence commit"
        ) from exc
    drift = []
    for raw in changed.split(b"\0"):
        if not raw:
            continue
        path = (repo_root / os.fsdecode(raw)).resolve(strict=False)
        if path != output_root and not path.is_relative_to(output_root):
            drift.append(str(path.relative_to(repo_root)))
    if drift:
        raise Phase1FreezeError(
            "the evidence commit changes source beyond the frozen Phase 1 "
            f"record: {sorted(drift)}"
        )


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
            raise Phase1FreezeError(
                "repository worktree cannot be inspected"
            ) from exc
        for raw in output.split(b"\0"):
            if raw:
                result.add(
                    (repo_root / os.fsdecode(raw)).resolve(strict=False)
                )
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
            f"tracked v2 Phase 1 output: {drift}"
        )


def _phase1_output_root(repo_root: Path, requested: Path | None) -> Path:
    root = repo_root.expanduser().resolve(strict=True)
    expected = (root / PHASE1_RELATIVE_ROOT).resolve(strict=False)
    if expected == root or not expected.is_relative_to(root):
        raise Phase1FreezeError(
            "the tracked v2 Phase 1 path resolves outside the repository"
        )
    observed = (
        expected
        if requested is None
        else requested.expanduser().resolve(strict=False)
    )
    if observed != expected:
        raise Phase1FreezeError(
            f"v2 Phase 1 evidence must be written exactly to {expected}"
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
            "the mutable attempt ledger must remain outside the repository"
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
    if binding["contract_version"] != EXPECTED_CONTRACT:
        raise Phase1FreezeError(
            "the active prompt is not the direct reconstruction v2 contract"
        )
    return binding, canonical_json_sha256(binding)


@contextmanager
def _offline_model_assets() -> Iterator[None]:
    """Prevent prompt certification from consulting mutable remote assets."""

    names = (
        "HF_DATASETS_OFFLINE",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
    )
    previous = {name: os.environ.get(name) for name in names}
    os.environ.update({name: "1" for name in names})
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _expected_prompt_lengths(
    protocol: dict[str, Any],
    tasks: list[EvaluationTask],
) -> dict[tuple[str, str], int]:
    """Re-render every bound input without allowing a remote model client."""

    def forbidden_remote_client() -> Any:
        raise Phase1FreezeError(
            "prompt certification must not create a remote model client"
        )

    result: dict[tuple[str, str], int] = {}
    with _offline_model_assets():
        for arm_id in EXPECTED_HYPOTHESES.values():
            arm = protocol["arms"][arm_id]
            resolved_arm = arm_spec(protocol, arm_id)
            sampler = TinkerSampler(
                _sampler_target(resolved_arm),
                service_client_factory=forbidden_remote_client,
            )
            for task in tasks:
                prompt = sampler.build_prompt(_messages(task, resolved_arm))
                prompt_tokens = int(prompt.length)
                if (
                    prompt_tokens + int(arm["max_output_tokens"])
                    > int(arm["context_tokens"])
                ):
                    raise Phase1FreezeError(
                        f"{arm_id}/{task.task_id} no longer fits its context"
                    )
                result[(arm_id, task.task_id)] = prompt_tokens
    expected_count = len(EXPECTED_HYPOTHESES) * len(tasks)
    if len(result) != expected_count:
        raise Phase1FreezeError(
            "prompt certification did not cover every arm/task input"
        )
    return result


def _validate_protocol_shape(protocol: dict[str, Any]) -> None:
    if protocol.get("study_id") != EXPECTED_STUDY:
        raise Phase1FreezeError("the protocol is not representation-curriculum-v2")
    if protocol.get("contract_version") != EXPECTED_CONTRACT:
        raise Phase1FreezeError("the protocol does not bind the v2 prompt")
    if set(protocol.get("hypotheses", {})) != set(EXPECTED_HYPOTHESES):
        raise Phase1FreezeError("the v2 Phase 1 hypothesis registry changed")
    if set(protocol.get("arms", {})) != set(EXPECTED_HYPOTHESES.values()):
        raise Phase1FreezeError("the v2 Phase 1 arm registry changed")
    if protocol.get("sampling", {}).get("temperature") != 1.0:
        raise Phase1FreezeError("v2 Phase 1 requires temperature 1.0")
    if protocol.get("sampling", {}).get("top_p") != 1.0:
        raise Phase1FreezeError("v2 Phase 1 requires top-p 1.0")

    qwen = protocol["arms"]["qwen-on-60000"]
    if {
        "model": qwen.get("model"),
        "renderer": qwen.get("renderer"),
        "thinking": qwen.get("thinking"),
        "thinking_effort": qwen.get("thinking_effort"),
        "max_output_tokens": qwen.get("max_output_tokens"),
        "context_tokens": qwen.get("context_tokens"),
        "max_image_long_edge": qwen.get("max_image_long_edge"),
    } != {
        "model": "Qwen/Qwen3.6-35B-A3B",
        "renderer": "qwen3_5",
        "thinking": True,
        "thinking_effort": None,
        "max_output_tokens": 60000,
        "context_tokens": 65536,
        "max_image_long_edge": 1920,
    }:
        raise Phase1FreezeError("the Qwen 60k arm changed")

    inkling = protocol["arms"]["inkling-e09-60000"]
    if {
        "model": inkling.get("model"),
        "renderer": inkling.get("renderer"),
        "thinking": inkling.get("thinking"),
        "thinking_effort": inkling.get("thinking_effort"),
        "max_output_tokens": inkling.get("max_output_tokens"),
        "context_tokens": inkling.get("context_tokens"),
        "max_image_long_edge": inkling.get("max_image_long_edge"),
    } != {
        "model": "thinkingmachines/Inkling",
        "renderer": "tml_v0",
        "thinking": True,
        "thinking_effort": 0.9,
        "max_output_tokens": 60000,
        "context_tokens": 65536,
        "max_image_long_edge": 1920,
    }:
        raise Phase1FreezeError("the Inkling 60k arm changed")

    for hypothesis_id, arm_id in EXPECTED_HYPOTHESES.items():
        hypothesis = protocol["hypotheses"][hypothesis_id]
        expected_waves = {
            "smoke": {"attempt_indices": [1], "task_count": 8},
            "complete": {
                "attempt_indices": list(EXPECTED_ATTEMPTS),
                "task_count": 8,
            },
        }
        if (
            hypothesis.get("arm_ids") != [arm_id]
            or hypothesis.get("attempts_per_task") != 4
            or hypothesis.get("task_set") != "f1_f8"
            or hypothesis.get("status") != "frozen"
            or hypothesis.get("waves") != expected_waves
        ):
            raise Phase1FreezeError(f"{hypothesis_id} changed")


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
    if EXPECTED_HYPOTHESES.get(hypothesis_id) != arm_id:
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} is not a registered v2 Phase 1 run"
        )
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
        raise Phase1FreezeError(
            f"missing run manifest for {hypothesis_id}/{arm_id}"
        )
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
            f"{hypothesis_id}/{arm_id} run manifest does not match its launch"
        )

    run_jobs = tuple(
        job
        for job in jobs
        if job.hypothesis_id == hypothesis_id and job.arm_id == arm_id
    )
    if len(run_jobs) != 32:
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} does not resolve to exactly 32 attempts"
        )
    summary = summarize_arm(
        store=store,
        study_id=protocol["study_id"],
        hypothesis_id=hypothesis_id,
        arm_id=arm_id,
        jobs=jobs,
        tasks=tasks,
    )
    if (
        not summary["complete"]
        or summary["expected_attempts"] != 32
        or summary["attempts"] != 32
        or summary["tasks"] != 8
        or summary["missing"]
    ):
        raise Phase1FreezeError(
            f"{hypothesis_id}/{arm_id} is not a complete F1-F8 G4 run"
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
            jobs=run_jobs,
            manifest=manifest,
            summary=summary,
        ),
        observed_sandbox,
    )


def _finite_unit_interval(
    value: Any,
    *,
    key: AttemptKey,
    field: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Phase1FreezeError(f"{key} has invalid {field}")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise Phase1FreezeError(f"{key} has invalid {field}")
    return result


def _validate_receipt_and_evaluation(
    *,
    protocol: dict[str, Any],
    store: AttemptStore,
    task: EvaluationTask,
    job: JobSpec,
    expected_prompt_tokens: int,
    run_manifest_record_sha256: str,
) -> tuple[StoredRecord, StoredRecord]:
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

    required_receipt = {
        "request",
        "sample",
        "sampling_seconds",
        "raw_completion_sha256",
        "completion_sha256",
        "cost_estimate_usd",
        "run_manifest_record_sha256",
    }
    if set(receipt.payload) != required_receipt:
        raise Phase1FreezeError(
            f"{key} sampling receipt fields differ from the frozen schema"
        )
    if (
        receipt.payload["run_manifest_record_sha256"]
        != run_manifest_record_sha256
    ):
        raise Phase1FreezeError(
            f"{key} sampling receipt belongs to another run manifest"
        )
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
        raise Phase1FreezeError(
            f"{key} sample fields differ from the frozen schema"
        )
    prompt_tokens = sample["prompt_tokens"]
    completion_tokens = sample["completion_tokens"]
    if (
        isinstance(prompt_tokens, bool)
        or not isinstance(prompt_tokens, int)
        or prompt_tokens != expected_prompt_tokens
        or isinstance(completion_tokens, bool)
        or not isinstance(completion_tokens, int)
        or completion_tokens < 0
        or completion_tokens > int(request["max_tokens"])
        or prompt_tokens + int(request["max_tokens"])
        > int(arm["context_tokens"])
    ):
        raise Phase1FreezeError(
            f"{key} has invalid or non-reproducible token accounting"
        )
    if not isinstance(sample["cap_hit"], bool):
        raise Phase1FreezeError(f"{key} has a non-boolean cap-hit flag")
    if sample["cap_hit"] != (sample["stop_reason"] == "length"):
        raise Phase1FreezeError(
            f"{key} cap-hit flag differs from its stop reason"
        )
    if sample["cap_hit"] and completion_tokens != int(request["max_tokens"]):
        raise Phase1FreezeError(
            f"{key} length stop did not reach the output cap"
        )

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
        raise Phase1FreezeError(
            f"{key} exact channel tokens do not partition output"
        )
    for field in ("reasoning_tokens_estimate", "answer_tokens_estimate"):
        value = sample[field]
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise Phase1FreezeError(f"{key} has invalid {field}")
    if not isinstance(sample["channel_parse_complete"], bool):
        raise Phase1FreezeError(f"{key} has invalid channel parse state")

    raw_text = str(sample["raw_text"])
    completion = str(sample["completion_text"])
    if receipt.payload.get("raw_completion_sha256") != _sha256_bytes(
        raw_text.encode("utf-8")
    ):
        raise Phase1FreezeError(f"{key} raw completion digest mismatch")
    if receipt.payload.get("completion_sha256") != _sha256_bytes(
        completion.encode("utf-8")
    ):
        raise Phase1FreezeError(f"{key} completion digest mismatch")
    sampling_seconds = receipt.payload.get("sampling_seconds")
    if (
        isinstance(sampling_seconds, bool)
        or not isinstance(sampling_seconds, (int, float))
        or not math.isfinite(float(sampling_seconds))
        or float(sampling_seconds) < 0
    ):
        raise Phase1FreezeError(f"{key} has invalid sampling duration")
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
        raise Phase1FreezeError(
            f"{key} stored program does not match deterministic extraction"
        )
    if measured["program_sha256"] != _sha256_bytes(
        program.encode("utf-8")
    ):
        raise Phase1FreezeError(f"{key} program digest mismatch")
    if measured["reference_sha256"] != task.reference.target_image_sha256:
        raise Phase1FreezeError(f"{key} reference digest mismatch")
    if not _SHA256.fullmatch(str(measured["program_sha256"])):
        raise Phase1FreezeError(f"{key} has invalid program digest")

    aggregation_iou = _finite_unit_interval(
        measured["aggregation_iou"],
        key=key,
        field="aggregation_iou",
    )
    measured_iou = measured["measured_iou"]
    measured_dice = measured["measured_dice"]
    if (measured_iou is None) != (measured_dice is None):
        raise Phase1FreezeError(f"{key} has partial geometry metrics")
    expected_iou = 0.0
    if measured_iou is not None:
        expected_iou = _finite_unit_interval(
            measured_iou,
            key=key,
            field="measured_iou",
        )
        _finite_unit_interval(
            measured_dice,
            key=key,
            field="measured_dice",
        )
    if aggregation_iou != expected_iou:
        raise Phase1FreezeError(
            f"{key} aggregation IoU is not the raw model IoU"
        )
    if (
        not isinstance(measured["measurement_available"], bool)
        or measured["measurement_available"] != (measured_iou is not None)
    ):
        raise Phase1FreezeError(
            f"{key} measurement-availability flag is inconsistent"
        )
    if measured["measurement_available"] != (measured["status"] == "ok"):
        raise Phase1FreezeError(
            f"{key} successful execution and geometry measurement disagree"
        )
    if not isinstance(measured["diagnostics"], dict):
        raise Phase1FreezeError(f"{key} has invalid evaluator diagnostics")
    if measured_iou is not None:
        render_sha = measured.get("render_sha256")
        if not isinstance(render_sha, str) or not _SHA256.fullmatch(render_sha):
            raise Phase1FreezeError(
                f"{key} measured geometry has no valid render digest"
            )
        if measured["diagnostics"].get("render_sha256") != render_sha:
            raise Phase1FreezeError(
                f"{key} render digest differs from evaluator diagnostics"
            )
        if (
            measured["diagnostics"].get("reference_sha256")
            != task.reference.target_image_sha256
        ):
            raise Phase1FreezeError(
                f"{key} diagnostics belong to another reference"
            )
    if (
        not isinstance(measured["pure_executable"], bool)
        or measured["pure_executable"] != (measured["status"] == "ok")
    ):
        raise Phase1FreezeError(
            f"{key} executable flag is inconsistent with status"
        )
    if measured["retryable"] is not False:
        raise Phase1FreezeError(
            f"{key} model-attributed evaluation cannot be retryable"
        )
    evaluation_seconds = measured["evaluation_seconds"]
    if (
        isinstance(evaluation_seconds, bool)
        or not isinstance(evaluation_seconds, (int, float))
        or not math.isfinite(float(evaluation_seconds))
        or float(evaluation_seconds) < 0
    ):
        raise Phase1FreezeError(f"{key} has invalid evaluation duration")
    return receipt, evaluation


def _attempt_row(
    *,
    protocol: dict[str, Any],
    store: AttemptStore,
    evidence: _RunEvidence,
    job: JobSpec,
    expected_prompt_tokens: int,
) -> _AttemptEvidence:
    tasks = {task.task_id: task for task in evidence.tasks}
    task = tasks[job.task_id]
    receipt, evaluation = _validate_receipt_and_evaluation(
        protocol=protocol,
        store=store,
        task=task,
        job=job,
        expected_prompt_tokens=expected_prompt_tokens,
        run_manifest_record_sha256=evidence.manifest.record_sha256,
    )
    sample = receipt.payload["sample"]
    measured = evaluation.payload
    row = {
        "schema_version": ATTEMPT_INDEX_SCHEMA,
        "study_id": protocol["study_id"],
        "hypothesis_id": job.hypothesis_id,
        "arm_id": job.arm_id,
        "task_id": job.task_id,
        "attempt_index": job.attempt_index,
        "seed": job.seed,
        "status": measured["status"],
        "pure_executable": measured["pure_executable"],
        "measurement_available": measured["measurement_available"],
        "aggregation_iou": measured["aggregation_iou"],
        "measured_iou": measured["measured_iou"],
        "measured_dice": measured["measured_dice"],
        "violations": measured["violations"],
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
        "channel_token_count_basis": sample["channel_token_count_basis"],
        "channel_parse_complete": sample["channel_parse_complete"],
        "estimated_cost_usd": receipt.payload["cost_estimate_usd"],
        "sampling_seconds": receipt.payload["sampling_seconds"],
        "evaluation_seconds": measured["evaluation_seconds"],
        "raw_completion_sha256": receipt.payload[
            "raw_completion_sha256"
        ],
        "completion_sha256": receipt.payload["completion_sha256"],
        "program_sha256": measured["program_sha256"],
        "reference_sha256": measured["reference_sha256"],
        "render_sha256": measured.get("render_sha256"),
        "sampling_record_sha256": receipt.record_sha256,
        "evaluation_record_sha256": evaluation.record_sha256,
    }
    program = str(measured["program"])
    return _AttemptEvidence(
        row=row,
        program_row={
            "schema_version": PROGRAM_INDEX_SCHEMA,
            "study_id": protocol["study_id"],
            "hypothesis_id": job.hypothesis_id,
            "arm_id": job.arm_id,
            "task_id": job.task_id,
            "attempt_index": job.attempt_index,
            "program": program,
            "program_sha256": measured["program_sha256"],
            "reference_sha256": measured["reference_sha256"],
        },
        task=task,
        stored_evaluation=measured,
    )


def _same_optional_metric(observed: float | None, expected: Any) -> bool:
    if observed is None or expected is None:
        return observed is None and expected is None
    return math.isclose(
        float(observed),
        float(expected),
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def _compare_replayed_evaluation(
    evidence: _AttemptEvidence,
    replayed: EvaluationResult,
) -> None:
    """Require deterministic recomputation to reproduce the stored verdict."""

    row = evidence.row
    stored = evidence.stored_evaluation
    identity = (
        f"{row['hypothesis_id']}/{row['arm_id']}/"
        f"{row['task_id']}/attempt-{row['attempt_index']}"
    )
    if replayed.attribution is not Attribution.MODEL:
        raise Phase1FreezeError(
            f"{identity} replay produced an evaluator/reference failure: "
            f"{replayed.attribution.value}/{replayed.status.value}"
        )
    if replayed.status.value != stored["status"]:
        raise Phase1FreezeError(
            f"{identity} replay status differs: "
            f"{replayed.status.value} != {stored['status']}"
        )
    if tuple(replayed.violations) != tuple(stored["violations"]):
        raise Phase1FreezeError(f"{identity} replay purity verdict differs")
    if not _same_optional_metric(replayed.iou, stored["measured_iou"]):
        raise Phase1FreezeError(f"{identity} replay IoU differs")
    if not _same_optional_metric(replayed.dice, stored["measured_dice"]):
        raise Phase1FreezeError(f"{identity} replay Dice differs")

    replay_measurement = replayed.iou is not None
    replay_iou = float(replayed.iou) if replayed.iou is not None else 0.0
    if replay_measurement != stored["measurement_available"]:
        raise Phase1FreezeError(
            f"{identity} replay measurement availability differs"
        )
    if not math.isclose(
        replay_iou,
        float(stored["aggregation_iou"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise Phase1FreezeError(f"{identity} replay aggregation IoU differs")
    if (replayed.status.value == "ok") != stored["pure_executable"]:
        raise Phase1FreezeError(f"{identity} replay executable verdict differs")

    replay_render = replayed.metrics.get("render_sha256")
    if replay_render != stored.get("render_sha256"):
        raise Phase1FreezeError(f"{identity} replay render digest differs")
    replay_reference = replayed.metrics.get("reference_sha256")
    if replay_measurement and (
        replay_reference != evidence.task.reference.target_image_sha256
    ):
        raise Phase1FreezeError(f"{identity} replay reference digest differs")


def _replay_attempts(
    attempts: list[_AttemptEvidence],
    *,
    expected_sandbox: tuple[str, str],
) -> None:
    """Re-execute all recorded programs inside the immutable sandbox."""

    requests = [
        (evidence.task.reference, evidence.program_row["program"])
        for evidence in attempts
    ]
    with PixCellEvaluator(
        max_workers=8,
        evaluator_retries=1,
        require_isolation=True,
    ) as evaluator:
        boundary = evaluator.execution_boundary
        if boundary is None or (
            boundary.image_ref,
            boundary.image_id,
        ) != expected_sandbox:
            raise Phase1FreezeError(
                "certification sandbox differs from the paid launch sandbox"
            )
        replayed = evaluator.evaluate_batch(requests)
    if len(replayed) != len(attempts):
        raise Phase1FreezeError("evaluator replay returned the wrong row count")
    for evidence, result in zip(attempts, replayed, strict=True):
        _compare_replayed_evaluation(evidence, result)


def _published_program_rows(
    attempts: list[_AttemptEvidence],
) -> list[dict[str, Any]]:
    """Publish executable code, never raw fallback text from failed outputs."""

    return [
        evidence.program_row
        for evidence in attempts
        if evidence.row["status"] == "ok"
    ]


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
    protocol = load_protocol(repo_root, protocol_file=PROTOCOL_FILE)
    _validate_protocol_shape(protocol)
    manifest = load_task_manifest(TASK_MANIFEST_FILE, repo_root=repo_root)
    prompt_binding, prompt_sha = _prompt_binding()
    runtime = validate_runtime_stack(repo_root)
    store = AttemptStore(repo_root=repo_root, external_root=external_root)

    tasks = load_task_set(
        repo_root=repo_root,
        manifest=manifest,
        task_set="f1_f8",
    )
    task_ids = tuple(task.task_id for task in tasks)
    if task_ids != EXPECTED_TASK_IDS:
        raise Phase1FreezeError(
            f"the benchmark is not ordered exactly F1-F8: {task_ids}"
        )
    task_set_sha = canonical_json_sha256(manifest["task_sets"]["f1_f8"])
    prompt_lengths = _expected_prompt_lengths(protocol, tasks)

    sandbox: tuple[str, str] | None = None
    runs: list[_RunEvidence] = []
    for hypothesis_id, arm_id in EXPECTED_HYPOTHESES.items():
        jobs = jobs_for_wave(
            protocol,
            hypothesis_id=hypothesis_id,
            wave_name="complete",
            task_ids=list(task_ids),
        )
        evidence, sandbox = _load_run(
            store=store,
            protocol=protocol,
            hypothesis_id=hypothesis_id,
            arm_id=arm_id,
            source_git_sha=expected_source_sha,
            tasks=tasks,
            jobs=jobs,
            task_set_sha256=task_set_sha,
            prompt_sha256=prompt_sha,
            sandbox=sandbox,
            runtime=runtime,
        )
        runs.append(evidence)

    attempt_evidence = [
        _attempt_row(
            protocol=protocol,
            store=store,
            evidence=run,
            job=job,
            expected_prompt_tokens=prompt_lengths[
                (job.arm_id, job.task_id)
            ],
        )
        for run in runs
        for job in run.jobs
    ]
    attempt_evidence.sort(
        key=lambda value: (
            value.row["hypothesis_id"],
            value.row["task_id"],
            value.row["attempt_index"],
        )
    )
    if len(attempt_evidence) != 64:
        raise Phase1FreezeError("v2 Phase 1 must contain exactly 64 attempts")
    if sandbox is None:
        raise Phase1FreezeError("v2 Phase 1 has no bound evaluator sandbox")
    _replay_attempts(
        attempt_evidence,
        expected_sandbox=sandbox,
    )
    attempts = [evidence.row for evidence in attempt_evidence]
    programs = _published_program_rows(attempt_evidence)

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
        PurePosixPath("attempts.jsonl"): _jsonl_bytes(attempts),
        PurePosixPath("programs.jsonl"): _jsonl_bytes(programs),
        PurePosixPath("summaries.json"): _json_bytes(summaries_document),
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
        "source_git_sha": expected_source_sha,
        "protocol_sha256": protocol["logical_sha256"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "task_set_sha256": task_set_sha,
        "task_ids": list(task_ids),
        "prompt": prompt_binding,
        "prompt_sha256": prompt_sha,
        "runtime": runtime,
        "sandbox": {
            "image_ref": sandbox[0] if sandbox is not None else "",
            "image_id": sandbox[1] if sandbox is not None else "",
        },
        "attempt_count": len(attempts),
        "program_count": len(programs),
        "certification": {
            "prompt_token_counts_recomputed_offline": True,
            "programs_reexecuted_in_bound_sandbox": len(attempts),
            "stored_and_replayed_metrics_must_match": True,
            "published_programs_are_successful_executables_only": True,
        },
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
                    ),
                    source_git_sha=expected_source_sha,
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
            "completion_text",
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


def _assert_exact_output(
    output_root: Path,
    expected: dict[PurePosixPath, bytes],
) -> None:
    if not output_root.is_dir():
        raise Phase1FreezeError(
            f"tracked v2 Phase 1 release is missing: {output_root}"
        )
    observed_paths = {
        PurePosixPath(path.relative_to(output_root).as_posix())
        for path in output_root.rglob("*")
        if path.is_file()
    }
    expected_paths = set(expected)
    if observed_paths != expected_paths:
        raise Phase1FreezeError(
            "tracked v2 Phase 1 file inventory differs: "
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
        path
        for path in output_root.rglob("*")
        if path.is_file() or path.is_symlink()
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
            "refusing to overwrite a non-canonical v2 Phase 1 directory: "
            f"{extras}"
        )
    for path, content in expected_paths.items():
        if path.exists() or path.is_symlink():
            if path.is_symlink() or path.read_bytes() != content:
                raise Phase1FreezeError(
                    f"refusing to replace existing evidence at {path}"
                )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = (
            path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        )
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
    if not _SOURCE_SHA.fullmatch(expected_source_sha):
        raise Phase1FreezeError(
            "expected source SHA must be a full lowercase Git commit SHA"
        )
    _require_launch_source_state(
        repo_root=source,
        output_root=output_root,
        expected_source_sha=expected_source_sha,
        validate_only=validate_only,
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
