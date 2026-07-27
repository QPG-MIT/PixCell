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
from rl.track_a.checkpoint_metrics import (
    behavioral_probe_summary,
    program_sha256,
)
from rl.track_a.curriculum import balanced_effective_pass
from rl.track_a.launch import run_launch_preflight
from rl.track_a.reward import reward_for
from rl.track_a.tinker_data import DEFAULT_MODEL, DEFAULT_RENDERER, _message, _renderer


REPO_ROOT = Path(__file__).resolve().parents[2]


def _filter_levels(tasks, levels: str):
    allowed = {item.strip().upper() for item in levels.split(",") if item.strip()}
    return [
        task for task in tasks if not allowed or task.sampler.level.upper() in allowed
    ]


async def run(args: argparse.Namespace) -> dict:
    if args.behavioral_probe:
        if args.k != 4:
            raise SystemExit("--behavioral-probe requires --k 4")
        if args.rows < 1:
            raise SystemExit("--behavioral-probe requires a bounded --rows value")
        if not args.levels.strip():
            raise SystemExit(
                "--behavioral-probe requires explicit --levels for the "
                "first unmastered curriculum level(s)"
            )
    elif args.k != 1:
        raise SystemExit(
            "checkpoint geometry evaluation is fixed at k=1; use "
            "--behavioral-probe --k 4 for the separate collapse diagnostic"
        )
    if args.confirm_spend != "TRACK_A_EVAL":
        raise SystemExit("paid evaluation blocked: pass --confirm-spend TRACK_A_EVAL")
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not present")
    if not args.sampler_path:
        raise SystemExit("--sampler-path is required")
    run_launch_preflight(REPO_ROOT)

    tasks = _filter_levels(
        load_tasks(
            args.dataset_root,
            configuration="depth",
            split="validation",
        ),
        args.levels,
    )
    if not tasks:
        raise SystemExit("no validation tasks matched --levels")
    if args.rows:
        tasks = balanced_effective_pass(
            tasks,
            seed=args.seed,
            draws=min(args.rows, len(tasks)),
        )
    renderer = _renderer(args.model_name, args.renderer_name)
    decode = getattr(renderer, "decode_action_text", None) or renderer.tokenizer.decode
    sampling = tinker.ServiceClient().create_sampling_client(
        model_path=args.sampler_path
    )
    semaphore = asyncio.Semaphore(args.concurrency)

    async def sample(task):
        prompt = renderer.build_generation_prompt([_message(task, max_image=1440)])
        stop = renderer.get_stop_sequences()
        async with semaphore:
            result = await sampling.sample_async(
                prompt=prompt,
                num_samples=args.k,
                sampling_params=tinker.SamplingParams(
                    stop=stop,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    top_p=1.0,
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

    with PixCellEvaluator(max_workers=args.evaluator_workers) as evaluator:
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
    report = {
        "schema_version": "pixcell-track-a-executable-eval-v1",
        "evaluation_role": (
            "behavioral-collapse-probe"
            if args.behavioral_probe
            else "checkpoint-geometry"
        ),
        "sampler_path": args.sampler_path,
        "model": args.model_name,
        "renderer": args.renderer_name,
        "split": "depth/validation",
        "levels": args.levels or "all",
        "k": args.k,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
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
            if args.behavioral_probe
            else None
        ),
        "records": records if args.include_records else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
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
