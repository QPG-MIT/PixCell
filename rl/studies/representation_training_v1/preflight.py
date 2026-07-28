"""Zero-spend validation for one sealed training stage."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from tinker import SamplingParams
from tinker_cookbook.renderers import Message, TextPart, TrainOnWhat

from homi.conductor.source_policy import strict_purity_violations

from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.isolation import require_execution_boundary
from rl.common.prompt import prompt_asset_hashes
from rl.common.runtime import validate_runtime_stack
from rl.track_a.tinker_data import _message, _renderer

from .dataset_binding import _dataset_binding
from .protocol import StageSpec, file_sha256, protocol_path
from .schedule import (
    stage_replay_tasks,
    stage_schedule_document,
    stage_tasks,
    verify_sft_step_count,
)


def _positive_target_text(model_input: Any, weights: Any, tokenizer: Any) -> str:
    offset = 0
    tokens: list[int] = []
    for chunk in model_input.chunks:
        length = int(chunk.length)
        chunk_weights = weights[offset : offset + length]
        chunk_tokens = getattr(chunk, "tokens", None)
        if chunk_tokens is not None:
            tokens.extend(
                int(token)
                for token, weight in zip(chunk_tokens, chunk_weights, strict=True)
                if float(weight) > 0
            )
        elif int((chunk_weights > 0).sum().item()) != 0:
            raise RuntimeError("an image token unexpectedly carries SFT loss")
        offset += length
    if offset != int(model_input.length) or not tokens:
        raise RuntimeError("SFT target mask is empty or misaligned")
    return str(tokenizer.decode(tokens))


def _audit_sft(
    dataset_root: Path,
    stage: StageSpec,
    model: dict[str, Any],
    recipe: dict[str, Any],
    *,
    max_steps: int,
) -> dict[str, Any]:
    verify_sft_step_count(dataset_root, stage, max_steps=max_steps)
    renderer = _renderer(
        model["model"],
        model["renderer"],
        effort=model.get("effort"),
    )
    lengths: list[int] = []
    trained: list[int] = []
    for task in stage_tasks(dataset_root, stage):
        assistant = Message(
            role="assistant",
            content=[TextPart(type="text", text=task.label)],
        )
        model_input, weights = renderer.build_supervised_example(
            [_message(task, max_image=int(model["max_image_long_edge"])), assistant],
            train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE,
        )
        length = int(model_input.length)
        positive = int((weights > 0).sum().item())
        if length > int(recipe["max_sequence_tokens"]):
            raise RuntimeError(
                f"{task.sampler.opaque_id} has {length} tokens, exceeding "
                f"{recipe['max_sequence_tokens']}"
            )
        target = _positive_target_text(model_input, weights, renderer.tokenizer)
        expected_target = task.label + "<|im_end|>"
        if target != expected_target:
            raise RuntimeError(
                f"{task.sampler.opaque_id} does not have an exact code-only SFT target"
            )
        lengths.append(length)
        trained.append(positive)
    return {
        "rows": len(lengths),
        "sequence_tokens": {
            "min": min(lengths),
            "max": max(lengths),
        },
        "trained_tokens": {
            "min": min(trained),
            "max": max(trained),
        },
        "target_policy": recipe["target"],
    }


def _audit_rl_context(
    dataset_root: Path,
    stage: StageSpec,
    model: dict[str, Any],
) -> dict[str, Any]:
    sampling_defaults = SamplingParams(
        max_tokens=int(model["max_output_tokens"]),
        temperature=1.0,
    )
    if float(sampling_defaults.top_p) != 1.0:
        raise RuntimeError("pinned Tinker top_p default is no longer 1.0")
    renderer = _renderer(
        model["model"],
        model["renderer"],
        effort=model.get("effort"),
    )
    lengths: list[int] = []
    tasks = stage_tasks(dataset_root, stage) + stage_replay_tasks(
        dataset_root,
        stage,
    )
    for task in tasks:
        prompt = renderer.build_generation_prompt(
            [_message(task, max_image=int(model["max_image_long_edge"]))]
        )
        length = int(prompt.length)
        if length + int(model["max_output_tokens"]) > int(model["context_tokens"]):
            raise RuntimeError(
                f"{task.sampler.opaque_id} leaves no room for the sealed output cap"
            )
        lengths.append(length)
    return {
        "rows": len(lengths),
        "prompt_tokens": {
            "min": min(lengths),
            "max": max(lengths),
        },
        "minimum_context_headroom": (
            int(model["context_tokens"])
            - int(model["max_output_tokens"])
            - max(lengths)
        ),
        "sampling_defaults": {
            "top_p": float(sampling_defaults.top_p),
        },
    }


def _source_and_reference_audit(
    dataset_root: Path,
    stage: StageSpec,
    *,
    execute_probe: bool,
) -> dict[str, Any]:
    tasks = stage_tasks(dataset_root, stage)
    if stage.kind == "rl":
        tasks.extend(stage_replay_tasks(dataset_root, stage))
    unique = {task.sampler.opaque_id: task for task in tasks}
    source_sha = hashlib.sha256()
    reference_sha = hashlib.sha256()
    with PixCellEvaluator(
        max_workers=1,
        evaluator_retries=1,
        require_isolation=execute_probe,
    ) as evaluator:
        for task_id, task in sorted(unique.items()):
            violations = strict_purity_violations(task.label)
            if violations:
                raise RuntimeError(
                    f"{task_id} violates the strict source policy: {violations}"
                )
            evidence = evaluator.validate_reference(task.reference)
            if (
                evidence["target_image_sha256"]
                != task.reference.target_image_sha256
            ):
                raise RuntimeError(f"{task_id} reference digest changed")
            source_sha.update(task_id.encode("utf-8"))
            source_sha.update(hashlib.sha256(task.label.encode("utf-8")).digest())
            reference_sha.update(task_id.encode("utf-8"))
            reference_sha.update(
                bytes.fromhex(task.reference.target_image_sha256)
            )
        probe: dict[str, Any] | None = None
        if execute_probe:
            first = unique[sorted(unique)[0]]
            result = evaluator.evaluate(first.reference, first.label)
            if (
                result.status is not EvaluationStatus.OK
                or result.attribution is not Attribution.MODEL
                or result.iou is None
                or result.iou < 0.99
            ):
                raise RuntimeError(
                    "isolated ground-truth probe failed: "
                    f"{result.status.value}/{result.attribution.value}/"
                    f"{result.iou}: {result.error}"
                )
            probe = {
                "task_id": first.sampler.opaque_id,
                "status": result.status.value,
                "iou": result.iou,
            }
    return {
        "rows": len(unique),
        "source_set_sha256": source_sha.hexdigest(),
        "reference_set_sha256": reference_sha.hexdigest(),
        "sandbox_probe": probe,
    }


def _cookbook_source_binding(runtime: dict[str, Any]) -> dict[str, Any]:
    expected = str(runtime["tinker_cookbook_commit"])
    distribution = importlib.metadata.distribution("tinker-cookbook")
    version = importlib.metadata.version("tinker-cookbook")
    direct = distribution.read_text("direct_url.json")
    if not direct:
        if f"g{expected[:10]}" not in version:
            raise RuntimeError(
                "installed Tinker Cookbook does not identify the pinned commit"
            )
        return {
            "kind": "installed-distribution",
            "version": version,
            "expected_commit": expected,
        }
    document = json.loads(direct)
    if document.get("dir_info", {}).get("editable") is not True:
        if f"g{expected[:10]}" not in version:
            raise RuntimeError(
                "direct Tinker Cookbook install does not identify the pinned commit"
            )
        return {
            "kind": "direct-install",
            "version": version,
            "expected_commit": expected,
            "direct_url_sha256": hashlib.sha256(direct.encode()).hexdigest(),
        }
    parsed = urlparse(str(document.get("url", "")))
    if parsed.scheme != "file":
        raise RuntimeError("editable Tinker Cookbook is not a local file checkout")
    checkout = Path(unquote(parsed.path)).resolve(strict=True)
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=checkout,
        text=True,
    ).strip()
    if head != expected or status:
        raise RuntimeError(
            "editable Tinker Cookbook differs from the pinned clean commit"
        )
    return {
        "kind": "clean-editable-checkout",
        "path": str(checkout),
        "git_sha": head,
    }


def _sandbox_binding() -> dict[str, Any]:
    boundary = require_execution_boundary()
    return {
        "runtime_path": str(boundary.runtime_path),
        "daemon_endpoint": boundary.daemon_endpoint,
        "image_ref": boundary.image_ref,
        "image_id": boundary.image_id,
        "workspace_root": str(boundary.workspace_root),
    }


def _benchmark_binding(repo_root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    manifest_path = (
        protocol_path(repo_root).parent / protocol["evaluation"]["task_manifest"]
    ).resolve(strict=True)
    if not manifest_path.is_relative_to(repo_root.resolve()):
        raise RuntimeError("benchmark manifest escaped the repository")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = protocol["evaluation"]["task_manifest_logical_sha256"]
    if document.get("logical_sha256") != expected:
        raise RuntimeError("benchmark task manifest differs from the protocol")
    unsigned = {key: value for key, value in document.items() if key != "logical_sha256"}
    logical = hashlib.sha256(
        json.dumps(
            unsigned,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if logical != expected:
        raise RuntimeError("benchmark task manifest has an invalid logical digest")
    task_set = document.get("task_sets", {}).get("f1_f8")
    if not isinstance(task_set, list) or len(task_set) != 8:
        raise RuntimeError("benchmark manifest does not contain exact F1-F8")
    return {
        "relative_path": str(manifest_path.relative_to(repo_root)),
        "file_sha256": file_sha256(manifest_path),
        "logical_sha256": logical,
        "task_ids": [item["task_id"] for item in task_set],
    }


def stage_preflight(
    *,
    repo_root: Path,
    protocol: dict[str, Any],
    stage: StageSpec,
    wave_name: str,
    require_sandbox: bool,
) -> dict[str, Any]:
    """Validate all deterministic launch inputs without creating a client."""

    dataset_root = repo_root / "dataset"
    wave = stage.wave(wave_name)
    model = dict(protocol["models"][stage.model_key])
    recipe = dict(protocol["recipes"][stage.recipe_key])
    schedule = stage_schedule_document(
        dataset_root,
        stage,
        groups_per_batch=(
            int(recipe["groups_per_batch"]) if stage.kind == "rl" else None
        ),
    )
    policy_audit = (
        _audit_sft(
            dataset_root,
            stage,
            model,
            recipe,
            max_steps=int(wave["max_steps"]),
        )
        if stage.kind == "sft"
        else _audit_rl_context(dataset_root, stage, model)
    )
    protocol_file = protocol_path(repo_root)
    runtime = validate_runtime_stack(repo_root)
    report = {
        "ok": True,
        "spend": False,
        "stage_id": stage.stage_id,
        "wave": wave_name,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "protocol_file_sha256": file_sha256(protocol_file),
        "prompt_assets": prompt_asset_hashes(),
        "benchmark": _benchmark_binding(repo_root, protocol),
        "dataset": _dataset_binding(dataset_root, protocol),
        "runtime": {
            **runtime,
            "cookbook_source": _cookbook_source_binding(runtime),
        },
        "schedule": schedule,
        "model": model,
        "recipe": recipe,
        "policy_audit": policy_audit,
        "source_and_reference_audit": _source_and_reference_audit(
            dataset_root,
            stage,
            execute_probe=require_sandbox,
        ),
        "sandbox": _sandbox_binding() if require_sandbox else None,
    }
    report["preflight_sha256"] = hashlib.sha256(
        json.dumps(
            report,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return report
