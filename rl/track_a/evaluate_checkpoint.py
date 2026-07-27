#!/usr/bin/env python3
"""Spend-locked Track A evaluation for a Tinker sampler checkpoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import tinker

from rl.common.dataset_io import load_tasks
from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.isolation import IsolationError
from rl.track_a.checkpoint_metrics import (
    behavioral_probe_summary,
    program_sha256,
)
from rl.track_a.curriculum import balanced_effective_pass
from rl.track_a.evaluation_contract import (
    BEHAVIORAL_PROBE_TASKS,
    FULL_GEOMETRY_REPRESENTATIONS,
    FULL_GEOMETRY_TASKS,
    REPORT_SCHEMA_VERSION,
    build_checkpoint_selection_contract,
    report_provenance,
    validate_evaluation_report,
)
from rl.track_a.launch import bind_execution_boundary, run_launch_preflight
from rl.track_a.recipe import validate_evaluation_cli
from rl.track_a.reward import reward_for
from rl.track_a.tinker_data import DEFAULT_MODEL, DEFAULT_RENDERER, _message, _renderer


REPO_ROOT = Path(__file__).resolve().parents[2]


def _filter_levels(tasks, levels: str):
    allowed = {item.strip().upper() for item in levels.split(",") if item.strip()}
    return [
        task for task in tasks if not allowed or task.sampler.level.upper() in allowed
    ]


async def run(args: argparse.Namespace) -> dict:
    try:
        resolved_launch = validate_evaluation_cli(REPO_ROOT, args)
        resolved_launch = bind_execution_boundary(resolved_launch)
    except (ValueError, IsolationError) as exc:
        raise SystemExit(f"paid evaluation blocked: {exc}") from exc
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not present")
    run_launch_preflight(REPO_ROOT, resolved_launch=resolved_launch)
    dataset_root = Path(str(resolved_launch["dataset_root"]))
    sampler_path = str(resolved_launch["sampler_path"])
    output_path = Path(str(resolved_launch["output"]))
    levels = str(resolved_launch["levels"])
    rows = int(resolved_launch["rows"])
    k = int(resolved_launch["k"])
    temperature = float(resolved_launch["temperature"])
    max_tokens = int(resolved_launch["max_tokens"])
    max_image = int(resolved_launch["max_image"])
    top_p = float(resolved_launch["top_p"])
    seed = int(resolved_launch["seed"])
    concurrency = int(resolved_launch["concurrency"])
    evaluator_workers = int(resolved_launch["evaluator_workers"])
    include_records = bool(resolved_launch["include_records"])
    behavioral_probe = (
        resolved_launch["role"] == "behavioral-collapse-probe"
    )
    contract = build_checkpoint_selection_contract(
        REPO_ROOT,
        dataset_root,
    )

    tasks = _filter_levels(
        load_tasks(
            dataset_root,
            configuration="depth",
            split="validation",
        ),
        levels,
    )
    if not tasks:
        raise SystemExit("no validation tasks matched --levels")
    if rows:
        tasks = balanced_effective_pass(
            tasks,
            seed=seed,
            draws=rows,
        )
    task_ids = [task.sampler.opaque_id for task in tasks]
    if len(set(task_ids)) != len(task_ids):
        raise RuntimeError("checkpoint evaluation selected duplicate tasks")
    expected_tasks = (
        BEHAVIORAL_PROBE_TASKS
        if behavioral_probe
        else FULL_GEOMETRY_TASKS
    )
    if len(tasks) != expected_tasks:
        raise RuntimeError(
            f"checkpoint evaluation selected {len(tasks)} tasks; "
            f"expected {expected_tasks}"
        )
    representation_count = len(
        {task.sampler.representation_id for task in tasks}
    )
    if (
        not behavioral_probe
        and representation_count != FULL_GEOMETRY_REPRESENTATIONS
    ):
        raise RuntimeError(
            "checkpoint geometry evaluation selected "
            f"{representation_count} representations; expected "
            f"{FULL_GEOMETRY_REPRESENTATIONS}"
        )
    evaluator = PixCellEvaluator(
        max_workers=evaluator_workers,
        require_isolation=True,
    )
    renderer = _renderer(
        str(resolved_launch["model_name"]),
        str(resolved_launch["renderer_name"]),
    )
    decode = getattr(renderer, "decode_action_text", None) or renderer.tokenizer.decode
    sampling = tinker.ServiceClient().create_sampling_client(
        model_path=sampler_path
    )
    semaphore = asyncio.Semaphore(concurrency)

    async def sample(task):
        prompt = renderer.build_generation_prompt(
            [_message(task, max_image=max_image)]
        )
        stop = renderer.get_stop_sequences()
        async with semaphore:
            result = await sampling.sample_async(
                prompt=prompt,
                num_samples=k,
                sampling_params=tinker.SamplingParams(
                    stop=stop,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                ),
            )
        return [
            {
                "completion": decode(sequence.tokens),
                "completion_tokens": len(sequence.tokens),
            }
            for sequence in result.sequences
        ]

    sampled = await asyncio.gather(*(sample(task) for task in tasks))
    requests = []
    owners = []
    token_counts = []
    program_hashes = []
    for task, completions in zip(tasks, sampled, strict=True):
        for completion in completions:
            requests.append((task.reference, completion["completion"]))
            owners.append(task)
            token_counts.append(completion["completion_tokens"])
            program_hashes.append(program_sha256(completion["completion"]))

    with evaluator:
        results = evaluator.evaluate_batch(requests)
    masked = [
        result for result in results if result.attribution is not Attribution.MODEL
    ]
    if masked:
        first = masked[0]
        raise RuntimeError(
            f"evaluation aborted on {first.attribution.value} failure: "
            f"{first.status.value}: {first.error}"
        )

    records = []
    for task, result, completion_tokens, program_hash in zip(
        owners,
        results,
        token_counts,
        program_hashes,
        strict=True,
    ):
        records.append(
            {
                "opaque_id": task.sampler.opaque_id,
                "level": task.sampler.level,
                "representation_id": task.sampler.representation_id,
                "status": result.status.value,
                "pure_executable": result.status is EvaluationStatus.OK,
                "iou": float(result.iou or 0.0),
                "reward": float(reward_for(result) or 0.0),
                "completion_tokens": completion_tokens,
                "program_sha256": program_hash,
                "render_sha256": result.metrics.get("render_sha256"),
            }
        )

    by_representation = defaultdict(list)
    by_level = defaultdict(list)
    for record in records:
        by_representation[record["representation_id"]].append(record)
        by_level[record["level"]].append(record)

    def aggregate(values):
        per_task = defaultdict(list)
        for value in values:
            per_task[value["opaque_id"]].append(value)
        task_means = [
            sum(item["iou"] for item in attempts) / len(attempts)
            for attempts in per_task.values()
        ]
        task_bests = [
            max(item["iou"] for item in attempts) for attempts in per_task.values()
        ]
        return {
            "attempts": len(values),
            "tasks": len(per_task),
            "pure_executable_rate": (
                sum(item["pure_executable"] for item in values) / len(values)
            ),
            "mean_iou_at_1": sum(task_means) / len(task_means),
            "mean_best_at_k_iou": sum(task_bests) / len(task_bests),
        }

    representation_means = [
        sum(record["iou"] for record in values) / len(values)
        for values in by_representation.values()
    ]
    role = (
        "behavioral-collapse-probe"
        if behavioral_probe
        else "checkpoint-geometry"
    )
    actual_levels = sorted(
        {task.sampler.level.upper() for task in tasks}
    )
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evaluation_role": role,
        "sampler_path": sampler_path,
        "model": resolved_launch["model_name"],
        "renderer": resolved_launch["renderer_name"],
        "split": "depth/validation",
        "levels": actual_levels[0] if behavioral_probe else "all",
        "k": k,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "summary": aggregate(records),
        "representation_macro_mean_iou": (
            sum(representation_means) / len(representation_means)
        ),
        "statuses": dict(sorted(Counter(item["status"] for item in records).items())),
        "levels_summary": {
            level: aggregate(values) for level, values in sorted(by_level.items())
        },
        "mean_completion_tokens": sum(token_counts) / len(token_counts),
        "behavioral_probe": (
            behavioral_probe_summary(records, expected_group_size=4)
            if behavioral_probe
            else None
        ),
        "records": records if include_records else None,
    }
    boundary = evaluator.execution_boundary
    assert boundary is not None
    report["provenance"] = report_provenance(
        contract=contract,
        sampler_path=sampler_path,
        role=role,
        levels=actual_levels,
        task_ids=task_ids,
        representation_count=representation_count,
        requested_rows=rows if behavioral_probe else None,
        k=k,
        attempt_count=len(records),
        sandbox_image_ref=boundary.image_ref,
        sandbox_image_id=boundary.image_id,
    )
    validate_evaluation_report(
        report,
        contract=contract,
        expected_role=role,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--confirm-spend", default="")
    result.add_argument("--sampler-path", required=True)
    result.add_argument("--dataset-root", type=Path, default=REPO_ROOT / "dataset")
    result.add_argument("--model-name", default=DEFAULT_MODEL)
    result.add_argument("--renderer-name", default=DEFAULT_RENDERER)
    result.add_argument("--levels", default="")
    result.add_argument(
        "--rows", type=int, default=0, help="0 evaluates the full split"
    )
    result.add_argument("--k", type=int, default=1)
    result.add_argument("--temperature", type=float, default=1.0)
    result.add_argument("--max-tokens", type=int, default=4096)
    result.add_argument("--concurrency", type=int, default=16)
    result.add_argument("--evaluator-workers", type=int, default=8)
    result.add_argument("--seed", type=int, default=7)
    result.add_argument("--include-records", action="store_true")
    result.add_argument(
        "--behavioral-probe",
        action="store_true",
        help=(
            "run the separate bounded G4 collapse probe; requires --k 4, "
            "--rows, and explicit --levels"
        ),
    )
    result.add_argument("--output", type=Path, required=True)
    return result


if __name__ == "__main__":
    report = asyncio.run(run(parser().parse_args()))
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "records"}, indent=2
        )
    )
