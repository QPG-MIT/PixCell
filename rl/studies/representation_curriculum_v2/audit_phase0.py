#!/usr/bin/env python3
"""Prove the v2 baseline launch boundary locally without making a model request."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.isolation import ExecutionBoundary, require_execution_boundary
from rl.common.output import extract_code
from rl.common.preprocess import IMAGE_PREPROCESS_VERSION
from rl.common.prompt import (
    CONTRACT_VERSION,
    build_prompt_text,
    prompt_asset_hashes,
)
from rl.common.runtime import validate_runtime_stack
from rl.evaluation.attempt_store import AttemptKey, AttemptStore, RunKey
from rl.evaluation.protocol import arm_spec, load_protocol
from rl.evaluation.runner import _messages, _preflight_references, _sampler_target
from rl.evaluation.samplers import TinkerSampler
from rl.evaluation.tasks import (
    BENCHMARK_TASK_SET,
    canonical_json_sha256,
    load_task_manifest,
    load_task_set,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_FILE = Path(__file__).with_name("protocol.json")
TASK_MANIFEST_FILE = Path(__file__).with_name("task_manifest.json")
AUDIT_SCHEMA = "pixcell-representation-curriculum-phase0-audit-v2"
EXPECTED_STUDY_ID = "representation-curriculum-v2"
EXPECTED_ARMS = ("inkling-e09-60000", "qwen-on-60000")
EXPECTED_IMAGE_LONG_EDGE = 1920
_AUDIT_PROBE_PROGRAM = """\
import gdsfactory as gf

length = 40.0
width = 1.7
layer = (1, 0)


@gf.cell
def device():
    component = gf.Component()
    component << gf.components.rectangle(
        size=(length, width),
        layer=layer,
        centered=True,
    )
    return component


if __name__ == "__main__":
    device().write_gds("device.gds")
"""
_FORBIDDEN_MODEL_TEXT = (
    "calibration",
    "display note",
    "ground truth",
    "iou",
    "leakage_group_id",
    "magnification",
    "px/um",
    "realization_slot",
    "reference code",
    "representation_id",
    "scale_px_per_um",
    "split_role",
    "target raster",
    "target_image",
)


def _git_state(repo_root: Path) -> tuple[str, bool]:
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        text=True,
    ).strip()
    return head, not bool(status)


def _assert_prompt_is_model_safe(text: str, *, case_id: str) -> None:
    normalized = text.casefold()
    leaked = [
        fragment
        for fragment in _FORBIDDEN_MODEL_TEXT
        if fragment.casefold() in normalized
    ]
    if leaked:
        raise ValueError(
            f"{case_id} leaked verifier/answer-only prompt fields: {leaked}"
        )


@contextmanager
def _offline_model_assets() -> Iterator[None]:
    """Forbid tokenizer/image-processor cache misses from reaching the network."""

    names = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
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


def _renderer_audit(
    *,
    protocol: dict[str, Any],
    tasks: list[Any],
) -> dict[str, Any]:
    remote_client_calls = 0

    def forbidden_remote_client() -> Any:
        nonlocal remote_client_calls
        remote_client_calls += 1
        raise AssertionError("Phase 0 audit attempted to create a Tinker client")

    rows: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, int]] = {}
    with _offline_model_assets():
        for arm_id in EXPECTED_ARMS:
            arm = arm_spec(protocol, arm_id)
            if arm.max_image_long_edge != EXPECTED_IMAGE_LONG_EDGE:
                raise ValueError(
                    f"{arm_id} must use the frozen "
                    f"{EXPECTED_IMAGE_LONG_EDGE}px image policy"
                )
            sampler = TinkerSampler(
                _sampler_target(arm),
                service_client_factory=forbidden_remote_client,
            )
            arm_rows: list[dict[str, Any]] = []
            for task in tasks:
                text = build_prompt_text(task.observation)
                _assert_prompt_is_model_safe(
                    text,
                    case_id=f"{arm_id}/{task.task_id}",
                )
                prompt = sampler.build_prompt(_messages(task, arm))
                prompt_tokens = int(prompt.length)
                headroom = (
                    arm.context_tokens
                    - arm.max_output_tokens
                    - prompt_tokens
                )
                if headroom < 0:
                    raise ValueError(
                        f"{arm_id}/{task.task_id} exceeds context: "
                        f"{prompt_tokens}+{arm.max_output_tokens}>"
                        f"{arm.context_tokens}"
                    )
                arm_rows.append(
                    {
                        "arm_id": arm_id,
                        "task_id": task.task_id,
                        "prompt_tokens": prompt_tokens,
                        "headroom_tokens": headroom,
                    }
                )
            rows.extend(arm_rows)
            summaries[arm_id] = {
                "prompt_cases": len(arm_rows),
                "prompt_tokens_min": min(
                    row["prompt_tokens"] for row in arm_rows
                ),
                "prompt_tokens_max": max(
                    row["prompt_tokens"] for row in arm_rows
                ),
                "minimum_headroom_tokens": min(
                    row["headroom_tokens"] for row in arm_rows
                ),
            }

    expected_cases = len(EXPECTED_ARMS) * len(tasks)
    if len(rows) != expected_cases or expected_cases != 16:
        raise ValueError(
            f"expected exactly 16 arm/task prompt cases, observed {len(rows)}"
        )
    if remote_client_calls:
        raise AssertionError("renderer audit created a remote model client")
    return {
        "model_client_created": False,
        "prompt_cases": len(rows),
        "arms": summaries,
        "rows": rows,
    }


def _run_manifest(
    *,
    protocol: dict[str, Any],
    arm_id: str,
    source_git_sha: str,
    task_set_sha256: str,
    prompt_sha256: str,
    runtime: dict[str, Any],
    boundary: ExecutionBoundary,
) -> dict[str, Any]:
    return {
        "source_git_sha": source_git_sha,
        "protocol_sha256": protocol["logical_sha256"],
        "task_set_sha256": task_set_sha256,
        "prompt_sha256": prompt_sha256,
        "sandbox_image_ref": boundary.image_ref,
        "sandbox_image_id": boundary.image_id,
        "runtime": runtime,
        "model_binding": {
            "arm_id": arm_id,
            **protocol["arms"][arm_id],
            "temperature": protocol["sampling"]["temperature"],
            "top_p": protocol["sampling"]["top_p"],
        },
    }


def _schema_smoke(
    *,
    repo_root: Path,
    protocol: dict[str, Any],
    source_git_sha: str,
    task_set_sha256: str,
    prompt_sha256: str,
    runtime: dict[str, Any],
    boundary: ExecutionBoundary,
) -> dict[str, dict[str, str]]:
    hypothesis_by_arm = {
        hypothesis["arm_ids"][0]: hypothesis_id
        for hypothesis_id, hypothesis in protocol["hypotheses"].items()
    }
    records: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="pixcell-phase0-v2-") as temporary:
        store = AttemptStore(
            repo_root=repo_root,
            external_root=Path(temporary) / "records",
        )
        for arm_id in EXPECTED_ARMS:
            hypothesis_id = hypothesis_by_arm[arm_id]
            run_key = RunKey(protocol["study_id"], hypothesis_id, arm_id)
            key = AttemptKey(
                protocol["study_id"],
                hypothesis_id,
                arm_id,
                "F1",
                1,
            )
            completion = "```python\nprint('phase0 schema audit')\n```"
            with store.acquire_run_lock(run_key):
                run = store.create_or_verify_run_manifest(
                    run_key,
                    _run_manifest(
                        protocol=protocol,
                        arm_id=arm_id,
                        source_git_sha=source_git_sha,
                        task_set_sha256=task_set_sha256,
                        prompt_sha256=prompt_sha256,
                        runtime=runtime,
                        boundary=boundary,
                    ),
                )
                receipt = store.write_sampling_receipt(
                    key,
                    {
                        "request": {
                            "max_tokens": protocol["arms"][arm_id][
                                "max_output_tokens"
                            ],
                            "temperature": protocol["sampling"]["temperature"],
                            "top_p": protocol["sampling"]["top_p"],
                            "seed": 1,
                        },
                        "sample": {
                            "prompt_tokens": 100,
                            "completion_tokens": 10,
                            "stop_reason": "stop",
                            "cap_hit": False,
                            "raw_text": completion,
                            "completion_text": completion,
                            "reasoning_text": "",
                            "answer_text": completion,
                            "reasoning_tokens_exact": 0,
                            "answer_tokens_exact": 10,
                            "reasoning_tokens_estimate": None,
                            "answer_tokens_estimate": None,
                            "channel_token_count_basis": "phase0_schema_audit",
                            "channel_parse_complete": True,
                        },
                        "sampling_seconds": 0.0,
                        "raw_completion_sha256": hashlib.sha256(
                            completion.encode("utf-8")
                        ).hexdigest(),
                        "completion_sha256": hashlib.sha256(
                            completion.encode("utf-8")
                        ).hexdigest(),
                        "run_manifest_record_sha256": run.record_sha256,
                        "cost_estimate_usd": {
                            "cached_prefill": 0.0,
                            "uncached_prefill": 0.0,
                        },
                    },
                )
                evaluation = store.write_evaluation(
                    key,
                    {
                        "status": EvaluationStatus.SYNTAX_ERROR.value,
                        "attribution": Attribution.MODEL.value,
                        "pure_executable": False,
                        "measurement_available": False,
                        "measured_iou": None,
                        "measured_dice": None,
                        "aggregation_iou": 0.0,
                        "program": "print('phase0 schema audit')",
                        "program_sha256": hashlib.sha256(
                            b"print('phase0 schema audit')"
                        ).hexdigest(),
                        "reference_sha256": "3" * 64,
                        "violations": [],
                        "error": "schema audit",
                        "retryable": False,
                        "evaluation_seconds": 0.0,
                        "diagnostics": {},
                    },
                )
            if store.load_run_manifest(run_key) != run:
                raise AssertionError("run manifest did not round-trip")
            if store.load_sampling_receipt(key) != receipt:
                raise AssertionError("sampling receipt did not round-trip")
            if store.load_evaluation(key) != evaluation:
                raise AssertionError("evaluation record did not round-trip")
            records[arm_id] = {
                "run_manifest_record_sha256": run.record_sha256,
                "sampling_record_sha256": receipt.record_sha256,
                "evaluation_record_sha256": evaluation.record_sha256,
            }
    return records


def run_audit(
    *,
    repo_root: Path,
    expected_source_sha: str | None = None,
) -> dict[str, Any]:
    root = repo_root.expanduser().resolve(strict=True)
    head, clean = _git_state(root)
    if expected_source_sha is not None:
        if head != expected_source_sha:
            raise ValueError(
                f"source SHA mismatch: {head} != {expected_source_sha}"
            )
        if not clean:
            raise ValueError("source worktree must be clean for the sealed audit")

    protocol_file = root / PROTOCOL_FILE.relative_to(REPO_ROOT)
    manifest_file = root / TASK_MANIFEST_FILE.relative_to(REPO_ROOT)
    protocol = load_protocol(root, protocol_file=protocol_file)
    if protocol["study_id"] != EXPECTED_STUDY_ID:
        raise ValueError("Phase 0 loaded the wrong study")
    if tuple(sorted(protocol["arms"])) != EXPECTED_ARMS:
        raise ValueError("Phase 0 loaded an unexpected baseline arm set")
    manifest = load_task_manifest(manifest_file, repo_root=root)
    tasks = load_task_set(
        repo_root=root,
        manifest=manifest,
        task_set=BENCHMARK_TASK_SET,
    )
    if [task.task_id for task in tasks] != [
        f"F{index}" for index in range(1, 9)
    ]:
        raise ValueError("Phase 0 did not resolve exact F1-F8 order")

    runtime = validate_runtime_stack(root)
    renderer = _renderer_audit(protocol=protocol, tasks=tasks)
    boundary = require_execution_boundary()
    with PixCellEvaluator(
        max_workers=1,
        evaluator_retries=1,
        require_isolation=True,
    ) as evaluator:
        if evaluator.execution_boundary is None:
            raise AssertionError("accepted-program audit is not isolated")
        if evaluator.execution_boundary.image_id != boundary.image_id:
            raise ValueError("sandbox identity changed during Phase 0")
        _preflight_references(tasks, evaluator)
        probe = _AUDIT_PROBE_PROGRAM.strip()
        wrapped = f"```python\n{probe}\n```"
        if extract_code(wrapped) != probe:
            raise ValueError("output extractor changed the fixed audit probe")
        result = evaluator.evaluate(tasks[0].reference, wrapped)
        if (
            result.status is not EvaluationStatus.OK
            or result.attribution is not Attribution.MODEL
            or result.iou is None
        ):
            raise ValueError(
                "isolated evaluator rejected the fixed primitive-only probe: "
                f"{result.status.value}/{result.attribution.value}: {result.error}"
            )

    prompt_binding = {
        "contract_version": CONTRACT_VERSION,
        "preprocess_version": IMAGE_PREPROCESS_VERSION,
        **prompt_asset_hashes(),
    }
    prompt_sha256 = canonical_json_sha256(prompt_binding)
    task_set_sha256 = canonical_json_sha256(
        manifest["task_sets"][BENCHMARK_TASK_SET]
    )
    return {
        "schema_version": AUDIT_SCHEMA,
        "study_id": protocol["study_id"],
        "source_git_sha": head,
        "source_worktree_clean": clean,
        "protocol_sha256": protocol["logical_sha256"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "task_set_sha256": task_set_sha256,
        "prompt": prompt_binding,
        "prompt_sha256": prompt_sha256,
        "renderer": renderer,
        "reference_count": len(tasks),
        "runtime": runtime,
        "sandbox": {
            "image_ref": boundary.image_ref,
            "image_id": boundary.image_id,
        },
        "evaluator_probe": {
            "task_id": tasks[0].task_id,
            "program_sha256": hashlib.sha256(
                probe.encode("utf-8")
            ).hexdigest(),
            "status": result.status.value,
            "iou": result.iou,
        },
        "record_schema": _schema_smoke(
            repo_root=root,
            protocol=protocol,
            source_git_sha=head,
            task_set_sha256=task_set_sha256,
            prompt_sha256=prompt_sha256,
            runtime=runtime,
            boundary=boundary,
        ),
        "model_client_created": False,
        "network_required": False,
        "credentials_required": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    result.add_argument("--expected-source-sha")
    return result


def main() -> None:
    args = parser().parse_args()
    print(
        json.dumps(
            run_audit(
                repo_root=args.repo_root,
                expected_source_sha=args.expected_source_sha,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
