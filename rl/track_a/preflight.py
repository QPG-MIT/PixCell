#!/usr/bin/env python3
"""Zero-spend Track A dataset, prompt, source-policy, and evaluator preflight."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import importlib.metadata
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from homi.conductor.source_policy import ALLOWED_COMPONENTS, purity_violations
from rl.common.contracts import (
    observation_from_row,
    reference_from_row,
    task_from_row,
)
from rl.common.dataset_io import load_rows
from rl.common.evaluator import EvaluationStatus, PixCellEvaluator
from rl.track_a.curriculum import (
    hierarchical_sft_weights,
    stratified_physical_pass,
)
from rl.track_a.prompt import (
    CONTRACT_VERSION,
    build_prompt_text,
    catalog_text,
    prompt_asset_hashes,
)
from rl.track_a.reward import reward_for
from rl.track_a.recipe import (
    canonical_config_path,
    canonical_dataset_root,
    canonical_json_sha256,
    validate_resolved_binding,
)


def _dataset_allowed_components(dataset_root: Path) -> frozenset[str]:
    path = dataset_root / "scripts" / "_shared.py"
    spec = importlib.util.spec_from_file_location("pixcell_dataset_shared", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return frozenset(module.ALLOWED_COMPONENTS)


def _selected_ground_truth(rows: list[dict], count: int) -> list[dict]:
    if count <= 0:
        return []
    by_level: dict[str, list[dict]] = {}
    for row in rows:
        by_level.setdefault(str(row["level"]), []).append(row)
    selected: list[dict] = []
    levels = sorted(by_level)
    cursor = {level: 0 for level in levels}
    while len(selected) < min(count, len(rows)):
        for level in levels:
            values = by_level[level]
            index = cursor[level]
            if index < len(values):
                selected.append(values[index])
                cursor[level] += 1
                if len(selected) >= count:
                    break
        else:
            if all(cursor[level] >= len(by_level[level]) for level in levels):
                break
    return selected


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_frozen_release(dataset_root: Path) -> dict:
    freeze_path = dataset_root / "depth-v1" / "factory" / "freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for relative, expected in freeze["reference_artifacts"].items():
        if not relative.startswith("data/"):
            continue
        path = dataset_root / "depth-v1" / relative
        observed = _sha256_file(path)
        if observed != expected:
            raise RuntimeError(f"frozen shard mismatch: {relative}")
    return {
        "depth_logical_release_sha256": freeze["logical_release_sha256"],
        "core_logical_release_sha256": freeze["parent_core_digest_sha256"],
    }


def _git_state(repo_root: Path, *, require_clean: bool) -> dict:
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
    if require_clean and status:
        raise RuntimeError(
            "worktree changes remain, including untracked files; "
            "commit before paid launch"
        )
    return {"head": head, "clean": not bool(status)}


def _runtime_stack(repo_root: Path) -> dict:
    expected = json.loads(
        (repo_root / "rl" / "stack.json").read_text(encoding="utf-8")
    )
    observed_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if observed_python != expected["python_major_minor"]:
        raise RuntimeError(
            f"Python {observed_python}, expected {expected['python_major_minor']}"
        )
    observed: dict[str, str] = {}
    for package, version in expected["packages"].items():
        actual = importlib.metadata.version(package)
        observed[package] = actual
        if actual != version:
            raise RuntimeError(f"{package}=={actual}, expected {version}")
    return {
        "python": sys.version.split()[0],
        "packages": observed,
        "tinker_cookbook_commit": expected["tinker_cookbook_commit"],
    }


def _token_audit(
    tasks,
    *,
    model_name: str,
    renderer_name: str,
    max_length: int,
    max_image: int,
) -> dict:
    from tinker_cookbook.renderers import Message, TextPart, TrainOnWhat

    from rl.track_a.tinker_data import _message, _renderer

    renderer = _renderer(model_name, renderer_name)
    lengths: list[int] = []
    assistant_tokens: list[int] = []
    for task in tasks:
        assistant = Message(
            role="assistant",
            content=[TextPart(type="text", text=task.label)],
        )
        model_input, weights = renderer.build_supervised_example(
            [_message(task, max_image=max_image), assistant],
            train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE,
        )
        length = int(model_input.length)
        trained = int((weights > 0).sum().item())
        if length > max_length:
            raise RuntimeError(
                f"{task.sampler.opaque_id}: {length} tokens exceeds {max_length}"
            )
        if trained <= 0 or trained >= length:
            raise RuntimeError(
                f"{task.sampler.opaque_id}: invalid assistant-only weight mask"
            )
        lengths.append(length)
        assistant_tokens.append(trained)
    values = np.asarray(lengths)
    trained_values = np.asarray(assistant_tokens)
    return {
        "rows": len(lengths),
        "max_length": max_length,
        "sequence_tokens": {
            "min": int(values.min()),
            "p50": int(np.percentile(values, 50)),
            "p95": int(np.percentile(values, 95)),
            "p99": int(np.percentile(values, 99)),
            "max": int(values.max()),
        },
        "assistant_tokens": {
            "min": int(trained_values.min()),
            "p50": int(np.percentile(trained_values, 50)),
            "p95": int(np.percentile(trained_values, 95)),
            "p99": int(np.percentile(trained_values, 99)),
            "max": int(trained_values.max()),
        },
    }


def run(args: argparse.Namespace) -> dict:
    dataset_root = args.dataset_root.resolve()
    repo_root = dataset_root.parent
    config_path = args.config.resolve()
    if dataset_root != canonical_dataset_root(repo_root):
        raise RuntimeError("preflight dataset_root is not repo_root/dataset")
    if config_path != canonical_config_path(repo_root):
        raise RuntimeError("preflight config is not the committed Track A config")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if args.audit_only:
        if args.resolved_launch_json is not None:
            raise RuntimeError("audit-only preflight does not accept a launch binding")
        resolved_launch = {
            "kind": "audit-only",
            "dataset_root": str(dataset_root),
            "config_path": str(config_path),
            "model_name": config["model"]["name"],
            "renderer_name": config["model"]["renderer"],
            "lora_rank": config["model"]["lora_rank"],
        }
    else:
        if args.resolved_launch_json is None:
            raise RuntimeError(
                "paid-launch preflight requires the exact resolved launch binding"
            )
        try:
            resolved_launch = json.loads(args.resolved_launch_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("resolved launch binding is not valid JSON") from exc
        if not isinstance(resolved_launch, dict):
            raise RuntimeError("resolved launch binding must be a JSON object")
        try:
            validate_resolved_binding(repo_root, resolved_launch)
        except ValueError as exc:
            raise RuntimeError(f"resolved launch binding failed: {exc}") from exc
    if config["contract_version"] != CONTRACT_VERSION:
        raise RuntimeError("config and prompt contract versions differ")
    if config["launch"]["paid_launch_enabled"] is not False:
        raise RuntimeError("committed config must remain spend-locked")
    release = _verify_frozen_release(dataset_root)
    git = _git_state(repo_root, require_clean=args.require_clean)
    runtime = _runtime_stack(repo_root)

    train = load_rows(
        dataset_root,
        configuration="depth",
        split="train",
    )
    validation = load_rows(
        dataset_root,
        configuration="depth",
        split="validation",
    )
    if len(train) != 3468 or len(validation) != 1092:
        raise RuntimeError(
            f"unexpected depth rows: train={len(train)}, validation={len(validation)}"
        )
    train_tasks = [task_from_row(row) for row in train]
    physical_pass = stratified_physical_pass(train_tasks, seed=0)
    if len({task.sampler.opaque_id for task in physical_pass}) != len(train_tasks):
        raise RuntimeError("SFT physical pass omits or duplicates a row")
    sft_weights = hierarchical_sft_weights(train_tasks)

    dataset_allowed = _dataset_allowed_components(dataset_root)
    catalog_allowed = frozenset(
        re.findall(r"\bgf\.components\.([A-Za-z_]\w*)", catalog_text())
    )
    if dataset_allowed != ALLOWED_COMPONENTS or catalog_allowed != ALLOWED_COMPONENTS:
        raise RuntimeError(
            "catalog, dataset admission, and conductor source whitelists differ"
        )

    source_failures: list[str] = []
    reference_failures: list[str] = []
    level_counts: Counter[str] = Counter()
    representation_ids: set[str] = set()
    evaluator = PixCellEvaluator(max_workers=args.workers)
    for row in [*train, *validation]:
        level_counts[str(row["level"])] += 1
        representation_ids.add(str(row["representation_id"]))
        violations = purity_violations(str(row["code"]))
        if violations:
            source_failures.append(f"{row['id']}: {violations[0]}")
        try:
            evaluator.validate_reference(reference_from_row(row))
        except Exception as exc:
            reference_failures.append(f"{row['id']}: {exc}")
    if source_failures:
        raise RuntimeError(f"ground-truth source failures: {source_failures[:5]}")
    if reference_failures:
        raise RuntimeError(f"reference failures: {reference_failures[:5]}")

    sample = train[0]
    observation = observation_from_row(sample)
    prompt = build_prompt_text(observation)
    forbidden = (
        "DISPLAY NOTE",
        "magnification x:y",
        "px/um",
        "target_image",
        str(sample["id"]),
        str(sample["representation_id"]),
    )
    leaked = [item for item in forbidden if item and item in prompt]
    if leaked:
        raise RuntimeError(f"policy prompt leaked hidden row state: {leaked}")

    sandbox: dict | None = None
    if resolved_launch["kind"] in {"rl", "evaluation"}:
        with PixCellEvaluator(
            max_workers=1,
            evaluator_retries=0,
            require_isolation=True,
        ) as sandbox_evaluator:
            row = train[0]
            result = sandbox_evaluator.evaluate(
                reference_from_row(row),
                str(row["code"]),
            )
            if result.status is not EvaluationStatus.OK or result.iou is None:
                raise RuntimeError(
                    "candidate sandbox self-test failed: "
                    f"{result.status.value}: {result.error}"
                )
            if result.iou < args.minimum_self_iou:
                raise RuntimeError(
                    "candidate sandbox changed ground-truth geometry: "
                    f"{result.iou:.6f} < {args.minimum_self_iou}"
                )
            boundary = sandbox_evaluator.execution_boundary
            assert boundary is not None
            sandbox = {
                "runtime": str(boundary.runtime_path),
                "image_ref": boundary.image_ref,
                "image_id": boundary.image_id,
                "self_iou": result.iou,
            }

    executed: list[dict] = []
    for row in _selected_ground_truth(train, args.execute_ground_truth):
        result = evaluator.evaluate(
            reference_from_row(row),
            str(row["code"]),
        )
        if result.status is not EvaluationStatus.OK or result.iou is None:
            raise RuntimeError(
                f"{row['id']}: ground truth failed with {result.status.value}: {result.error}"
            )
        if result.iou < args.minimum_self_iou:
            raise RuntimeError(
                f"{row['id']}: self IoU {result.iou:.6f} < {args.minimum_self_iou}"
            )
        executed.append(
            {
                "opaque_index": len(executed),
                "level": row["level"],
                "iou": result.iou,
                "reward": reward_for(result),
            }
        )

    return {
        "ok": True,
        "spend": False,
        "contract_version": CONTRACT_VERSION,
        "prompt_assets": prompt_asset_hashes(),
        "resolved_launch_sha256": canonical_json_sha256(resolved_launch),
        "resolved_launch": resolved_launch,
        "release": release,
        "git": git,
        "dataset": {
            "train_rows": len(train),
            "validation_rows": len(validation),
            "representations": len(representation_ids),
            "rows_by_level": dict(sorted(level_counts.items())),
        },
        "catalog_components": sorted(ALLOWED_COMPONENTS),
        "reference_rows_validated": len(train) + len(validation),
        "source_rows_validated": len(train) + len(validation),
        "ground_truth_execution": executed,
        "candidate_sandbox": sandbox,
        "sft_schedule": {
            "rows_visited_once": len(physical_pass),
            "mean_loss_multiplier": (
                sum(sft_weights.values()) / len(sft_weights)
            ),
            "minimum_loss_multiplier": min(sft_weights.values()),
            "maximum_loss_multiplier": max(sft_weights.values()),
        },
        "token_audit": (
            _token_audit(
                train_tasks,
                model_name=str(resolved_launch["model_name"]),
                renderer_name=str(resolved_launch["renderer_name"]),
                max_length=int(config["sft"]["max_sequence_tokens"]),
                max_image=int(config["model"]["max_image_long_edge"]),
            )
            if args.tokenize_sft
            else None
        ),
        "runtime": runtime,
    }


def parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[2]
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--dataset-root", type=Path, default=repo_root / "dataset")
    result.add_argument(
        "--config",
        type=Path,
        default=repo_root / "rl" / "track_a" / "config.json",
    )
    result.add_argument("--execute-ground-truth", type=int, default=5)
    result.add_argument("--minimum-self-iou", type=float, default=0.97)
    result.add_argument("--workers", type=int, default=8)
    result.add_argument("--tokenize-sft", action="store_true")
    result.add_argument("--require-clean", action="store_true")
    result.add_argument(
        "--audit-only",
        action="store_true",
        help="run the zero-spend repository audit without authorizing a launch",
    )
    result.add_argument("--resolved-launch-json")
    return result


if __name__ == "__main__":
    print(json.dumps(run(parser().parse_args()), indent=2, sort_keys=True))
