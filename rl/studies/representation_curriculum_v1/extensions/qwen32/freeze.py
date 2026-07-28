#!/usr/bin/env python3
"""Freeze or validate the tracked Qwen 32k F1-F8 baseline addendum."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from rl.common.runtime import validate_runtime_stack
from rl.evaluation.attempt_store import AttemptStore, RunKey
from rl.evaluation.protocol import jobs_for_wave, load_protocol, task_manifest_path
from rl.evaluation.tasks import canonical_json_sha256, load_task_manifest
from rl.evaluation.tracking import deterministic_wandb_run_id
from rl.studies.representation_curriculum_v1.freeze_phase1 import (
    Phase1FreezeError,
    _assert_exact_output,
    _collect_run_attempts,
    _git_head,
    _json_bytes,
    _jsonl_bytes,
    _load_run,
    _prompt_binding,
    _require_source_clean_except_output,
    _sha256_bytes,
    _task_set,
    _validate_roots,
    _write_create_or_verify,
)


REPO_ROOT = Path(__file__).resolve().parents[5]
PROTOCOL_FILE = Path(__file__).with_name("protocol.json")
OUTPUT_RELATIVE_ROOT = Path(
    "data/training/representation-curriculum-v1/phase1-qwen32"
)
RELEASE_SCHEMA = "pixcell-representation-curriculum-qwen32-release-v1"
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")


def _output_root(repo_root: Path, requested: Path | None) -> Path:
    root = repo_root.expanduser().resolve(strict=True)
    expected = (root / OUTPUT_RELATIVE_ROOT).resolve(strict=False)
    if expected == root or not expected.is_relative_to(root):
        raise Phase1FreezeError(
            "the tracked Qwen 32k path resolves outside the source repository"
        )
    observed = (
        expected
        if requested is None
        else requested.expanduser().resolve(strict=False)
    )
    if observed != expected:
        raise Phase1FreezeError(
            f"Qwen 32k evidence must be written exactly to {expected}"
        )
    return expected


def _collect_bundle(
    *,
    repo_root: Path,
    external_root: Path,
    expected_source_sha: str,
) -> tuple[dict[PurePosixPath, bytes], dict[str, Any]]:
    if not _SOURCE_SHA.fullmatch(expected_source_sha):
        raise Phase1FreezeError(
            "expected_source_sha must be a full lowercase Git SHA"
        )
    if _git_head(repo_root) != expected_source_sha:
        raise Phase1FreezeError("source HEAD differs from the paid-launch commit")

    protocol = load_protocol(repo_root, protocol_file=PROTOCOL_FILE)
    runtime = validate_runtime_stack(repo_root)
    manifest = load_task_manifest(
        task_manifest_path(repo_root),
        repo_root=repo_root,
    )
    prompt_binding, prompt_sha = _prompt_binding()
    tasks, task_set_sha = _task_set(
        repo_root=repo_root,
        protocol=protocol,
        manifest=manifest,
        hypothesis_id="RC-H03",
    )
    jobs = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H03",
        wave_name="complete",
        task_ids=[task.task_id for task in tasks],
    )
    arm_id = str(protocol["hypotheses"]["RC-H03"]["arm_ids"][0])
    store = AttemptStore(repo_root=repo_root, external_root=external_root)
    evidence, sandbox = _load_run(
        store=store,
        protocol=protocol,
        hypothesis_id="RC-H03",
        arm_id=arm_id,
        source_git_sha=expected_source_sha,
        tasks=tasks,
        jobs=jobs,
        task_set_sha256=task_set_sha,
        prompt_sha256=prompt_sha,
        sandbox=None,
        runtime=runtime,
    )
    attempts, programs = _collect_run_attempts(
        protocol=protocol,
        store=store,
        evidence=evidence,
    )
    attempts.sort(key=lambda row: (row["task_id"], row["attempt_index"]))

    summary_document = {
        "schema_version": "pixcell-representation-curriculum-qwen32-summary-v1",
        "study_id": protocol["study_id"],
        "hypothesis_id": "RC-H03",
        "arm_id": arm_id,
        "summary": evidence.summary,
    }
    summary_document["logical_sha256"] = canonical_json_sha256(summary_document)
    files: dict[PurePosixPath, bytes] = {
        PurePosixPath("summary.json"): _json_bytes(summary_document),
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
        "phase": "phase1-quality-first-qwen32-addendum",
        "source_git_sha": expected_source_sha,
        "protocol_path": str(PROTOCOL_FILE.relative_to(repo_root)),
        "protocol_sha256": protocol["logical_sha256"],
        "base_study": protocol["base_study"],
        "decision": protocol["decision"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "dataset": protocol["dataset"],
        "prompt": prompt_binding,
        "prompt_sha256": prompt_sha,
        "sandbox": {
            "image_ref": sandbox[0],
            "image_id": sandbox[1],
        },
        "runtime": runtime,
        "run": {
            "hypothesis_id": "RC-H03",
            "arm_id": arm_id,
            "attempts": len(attempts),
            "run_manifest_record_sha256": evidence.manifest.record_sha256,
            "wandb_run_id": deterministic_wandb_run_id(
                RunKey(protocol["study_id"], "RC-H03", arm_id),
                source_git_sha=expected_source_sha,
            ),
        },
        "files": file_inventory,
    }
    release_manifest["logical_sha256"] = canonical_json_sha256(release_manifest)
    return files, release_manifest


def freeze(
    *,
    repo_root: Path,
    external_root: Path,
    expected_source_sha: str,
    output: Path | None = None,
    validate_only: bool = False,
) -> dict[str, Any]:
    output_root = _output_root(repo_root, output)
    source, external = _validate_roots(
        repo_root=repo_root,
        external_root=external_root,
        output_root=output_root,
    )
    _require_source_clean_except_output(
        repo_root=source,
        output_root=output_root,
    )
    files, manifest = _collect_bundle(
        repo_root=source,
        external_root=external,
        expected_source_sha=expected_source_sha,
    )
    expected = {
        PurePosixPath("release_manifest.json"): _json_bytes(manifest),
        **files,
    }
    if validate_only:
        _assert_exact_output(output_root, expected)
    else:
        _write_create_or_verify(output_root, expected)
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    result.add_argument("--external-root", type=Path, required=True)
    result.add_argument("--expected-source-sha", required=True)
    result.add_argument("--output", type=Path)
    result.add_argument("--validate", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    report = freeze(
        repo_root=args.repo_root,
        external_root=args.external_root,
        expected_source_sha=args.expected_source_sha,
        output=args.output,
        validate_only=args.validate,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
