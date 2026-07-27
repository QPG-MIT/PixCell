#!/usr/bin/env python3
"""Run the zero-spend audit required before a baseline launch is committed."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from rl.common.dataset_io import parquet_paths
from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.output import extract_code
from rl.common.runtime import validate_runtime_stack
from rl.evaluation.attempt_store import AttemptKey, AttemptStore, RunKey
from rl.evaluation.protocol import arm_spec, load_protocol, task_manifest_path
from rl.evaluation.runner import (
    _FORBIDDEN_PROMPT_FRAGMENTS,
    _preflight_references,
    _preflight_renderers,
)
from rl.evaluation.samplers import TinkerSampler
from rl.evaluation.tasks import (
    BENCHMARK_TASK_SET,
    OPERATING_POINT_TASK_SET,
    load_task_manifest,
    load_task_set,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_SCHEMA = "pixcell-representation-curriculum-phase0-audit-v1"


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


def _exact_code(dataset_root: Path, opaque_id: str) -> str:
    import pyarrow.parquet as pq

    matches: list[str] = []
    for path in parquet_paths(
        dataset_root,
        configuration="depth",
        split="validation",
    ):
        for row in pq.read_table(path, columns=["id", "code"]).to_pylist():
            row_id = str(row["id"])
            observed = hashlib.sha256(row_id.encode("utf-8")).hexdigest()[:20]
            if observed == opaque_id:
                matches.append(str(row["code"]))
    if len(matches) != 1 or not matches[0].strip():
        raise ValueError(
            f"expected one supervised label for audit task {opaque_id}; "
            f"found {len(matches)}"
        )
    return matches[0]


def _samplers(protocol: dict[str, Any]) -> dict[str, TinkerSampler]:
    def forbidden_client() -> Any:
        raise AssertionError("Phase 0 audit attempted to create a Tinker client")

    from rl.evaluation.runner import _sampler_target

    return {
        arm_id: TinkerSampler(
            _sampler_target(arm_spec(protocol, arm_id)),
            service_client_factory=forbidden_client,
        )
        for arm_id in protocol["arms"]
    }


def _schema_smoke(
    *,
    repo_root: Path,
    protocol: dict[str, Any],
    sandbox: Any,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="pixcell-phase0-audit-") as temporary:
        store = AttemptStore(
            repo_root=repo_root,
            external_root=Path(temporary) / "records",
        )
        run_key = RunKey(protocol["study_id"], "RC-H02", "inkling-e09-20000")
        manifest = {
            "source_git_sha": "0" * 40,
            "protocol_sha256": protocol["logical_sha256"],
            "task_set_sha256": "1" * 64,
            "prompt_sha256": "2" * 64,
            "sandbox_image_ref": sandbox.image_ref,
            "sandbox_image_id": sandbox.image_id,
            "runtime": validate_runtime_stack(repo_root),
            "model_binding": {"model": "thinkingmachines/Inkling"},
        }
        with store.acquire_run_lock(run_key):
            saved_manifest = store.create_or_verify_run_manifest(run_key, manifest)
            key = AttemptKey(
                protocol["study_id"],
                "RC-H02",
                "inkling-e09-20000",
                "F1",
                1,
            )
            completion = "```python\nprint('audit')\n```"
            receipt = store.write_sampling_receipt(
                key,
                {
                    "request": {
                        "max_tokens": 20000,
                        "temperature": 1.0,
                        "top_p": 1.0,
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
                    "sampling_seconds": 0.1,
                    "raw_completion_sha256": hashlib.sha256(
                        completion.encode("utf-8")
                    ).hexdigest(),
                    "completion_sha256": hashlib.sha256(
                        completion.encode("utf-8")
                    ).hexdigest(),
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
                    "program": "print('audit')",
                    "program_sha256": hashlib.sha256(
                        b"print('audit')"
                    ).hexdigest(),
                    "reference_sha256": "3" * 64,
                    "violations": [],
                    "error": "schema audit",
                    "retryable": False,
                    "evaluation_seconds": 0.1,
                    "diagnostics": {},
                },
            )
        if store.load_sampling_receipt(key) != receipt:
            raise AssertionError("sampling receipt did not round-trip")
        if store.load_evaluation(key) != evaluation:
            raise AssertionError("evaluation record did not round-trip")
        if store.load_run_manifest(run_key) != saved_manifest:
            raise AssertionError("run manifest did not round-trip")
        return {
            "run_manifest_record_sha256": saved_manifest.record_sha256,
            "sampling_record_sha256": receipt.record_sha256,
            "evaluation_record_sha256": evaluation.record_sha256,
        }


def run_audit(
    *,
    repo_root: Path,
    expected_source_sha: str | None = None,
) -> dict[str, Any]:
    root = repo_root.expanduser().resolve(strict=True)
    head, clean = _git_state(root)
    if expected_source_sha is not None:
        if head != expected_source_sha:
            raise ValueError(f"source SHA mismatch: {head} != {expected_source_sha}")
        if not clean:
            raise ValueError("source worktree must be clean for the sealed audit")

    protocol = load_protocol(root)
    manifest = load_task_manifest(task_manifest_path(root), repo_root=root)
    task_sets = {
        name: load_task_set(repo_root=root, manifest=manifest, task_set=name)
        for name in (OPERATING_POINT_TASK_SET, BENCHMARK_TASK_SET)
    }
    samplers = _samplers(protocol)
    dev_arm_ids = [
        arm_id for arm_id in protocol["arms"] if arm_id.startswith("qwen-")
    ]
    benchmark_arm_ids = list(protocol["arms"])
    renderer_cases = 0
    for task_set, arm_ids in (
        (task_sets[OPERATING_POINT_TASK_SET], dev_arm_ids),
        (task_sets[BENCHMARK_TASK_SET], benchmark_arm_ids),
    ):
        arms = {arm_id: arm_spec(protocol, arm_id) for arm_id in arm_ids}
        rendered = _preflight_renderers(
            tasks=task_set,
            arms=arms,
            samplers={arm_id: samplers[arm_id] for arm_id in arm_ids},
        )
        renderer_cases += len(rendered)
        for (arm_id, task_id), messages in rendered.items():
            visible = repr(messages)
            leaked = [
                fragment
                for fragment in _FORBIDDEN_PROMPT_FRAGMENTS
                if fragment in visible
            ]
            if leaked:
                raise ValueError(
                    f"{arm_id}/{task_id} leaked verifier-only prompt text: {leaked}"
                )

    from rl.common.isolation import require_execution_boundary

    sandbox = require_execution_boundary()
    all_tasks = [
        *task_sets[OPERATING_POINT_TASK_SET],
        *task_sets[BENCHMARK_TASK_SET],
    ]
    with PixCellEvaluator(
        max_workers=1,
        evaluator_retries=1,
        require_isolation=True,
    ) as evaluator:
        _preflight_references(all_tasks, evaluator)
        audit_task = task_sets[OPERATING_POINT_TASK_SET][0]
        exact_code = _exact_code(root / "dataset", audit_task.task_id)
        wrapped = f"<think>audit</think>\n```python\n{exact_code}\n```"
        if extract_code(wrapped) != exact_code.strip():
            raise ValueError("output extractor changed the known audit program")
        result = evaluator.evaluate(audit_task.reference, wrapped)
        if (
            result.status is not EvaluationStatus.OK
            or result.attribution is not Attribution.MODEL
            or result.iou is None
        ):
            raise ValueError(
                "isolated evaluator failed the accepted-program audit: "
                f"{result.status.value}/{result.attribution.value}: {result.error}"
            )

    runtime = validate_runtime_stack(root)

    report = {
        "schema_version": AUDIT_SCHEMA,
        "source_git_sha": head,
        "source_worktree_clean": clean,
        "protocol_sha256": protocol["logical_sha256"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "task_counts": {
            name: len(tasks) for name, tasks in sorted(task_sets.items())
        },
        "renderer_prompt_cases": renderer_cases,
        "model_client_created": False,
        "reference_count": len(all_tasks),
        "extractor_exact": True,
        "evaluator": {
            "status": result.status.value,
            "iou": result.iou,
            "sandbox_image_ref": sandbox.image_ref,
            "sandbox_image_id": sandbox.image_id,
        },
        "record_schema": _schema_smoke(
            repo_root=root,
            protocol=protocol,
            sandbox=sandbox,
        ),
        "runtime": runtime,
    }
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    result.add_argument("--expected-source-sha")
    return result


def main() -> None:
    args = parser().parse_args()
    report = run_audit(
        repo_root=args.repo_root,
        expected_source_sha=args.expected_source_sha,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
