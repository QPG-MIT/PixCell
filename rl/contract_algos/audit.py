"""Compare reward signals on identical artifacts; this is not a training run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
from importlib import import_module
import json
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

from rl.common.baselines import TaskBaseline, rect_baseline
from rl.common.contracts import TaskRecord
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus, PixCellEvaluator
from rl.track_a.reward import REWARD_POLICIES, reward_for_policy, shaped_components

from .splits import DATASET_ROOT, SPLITS, file_digest, load_release, verify_manifest, write_new_json


class MeasurementFault(RuntimeError):
    """Infrastructure/reference faults must never become policy zeros."""


def score_signals(result: EvaluationResult, baseline: TaskBaseline) -> dict:
    if result.attribution is not Attribution.MODEL:
        raise MeasurementFault(f"{result.attribution.value}/{result.status.value}: {result.error}")
    rewards: dict[str, float | None] = {}
    for policy in REWARD_POLICIES:
        if (
            policy == "rc01"
            and result.status is EvaluationStatus.OK
            and "rc01" not in result.metrics
            and "rc01_score" not in result.metrics
        ):
            continue
        rewards[policy] = reward_for_policy(result, policy=policy, baseline=baseline)
    return {
        "rewards": rewards,
        "shaped_components": shaped_components(result, baseline),
    }


def measurement_record(
    candidate: dict, task: TaskRecord, baseline: TaskBaseline, result: EvaluationResult
) -> dict:
    """Keep sampling metadata while replacing claimed metrics with measurements."""
    return {
        **candidate,
        "source_sha256": hashlib.sha256(candidate["completion"].encode()).hexdigest(),
        "level": task.sampler.level,
        "status": result.status.value,
        "attribution": result.attribution.value,
        "valid": result.status is EvaluationStatus.OK,
        "iou": result.iou,
        "dice": result.dice,
        "metrics": result.metrics,
        "violations": list(result.violations),
        "error": result.error,
        "evaluation_latency_seconds": result.latency_seconds,
        "baseline": asdict(baseline),
        **score_signals(result, baseline),
    }


def controls(task: TaskRecord) -> list[dict]:
    length, width = task.observation.footprint_um
    rectangle = f'''import gdsfactory as gf
length = {length!r}
width = {width!r}
@gf.cell
def device():
    c = gf.Component()
    c << gf.components.rectangle(size=(length, width), layer=(1, 0))
    return c
if __name__ == "__main__":
    device().write_gds("device.gds")
'''
    programs = {
        "ground_truth": task.label,
        "bbox_rectangle": rectangle,
        "syntax_failure": "def device(:\n",
        "impure_source": "import os\nos.system('true')\n",
    }
    return [
        {"task_id": task.sampler.opaque_id, "candidate_id": name, "completion": code}
        for name, code in programs.items()
    ]


def summarize(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["task_id"]].append(record)
    summary: dict = {
        "candidate_count": len(records),
        "task_count": len(groups),
        "status_counts": dict(Counter(row["status"] for row in records)),
        "validity_rate": statistics.mean(row["status"] == "ok" for row in records),
        "policies": {},
    }
    active_policies = (
        tuple(
            policy
            for policy in REWARD_POLICIES
            if all(policy in row["rewards"] for row in records)
        )
        if records
        else REWARD_POLICIES
    )
    for policy in active_policies:
        per_task = []
        for task_id, group in sorted(groups.items()):
            values = [row["rewards"][policy] for row in group]
            spread = max(values) - min(values)
            stdev = statistics.pstdev(values)
            center = statistics.mean(values)
            per_task.append({
                "task_id": task_id,
                "candidate_count": len(values),
                "spread": spread,
                "population_std": stdev,
                "nonconstant": spread > 1e-12,
                "descending_rank_ties_share_rank": {
                    row["candidate_id"]: 1 + sum(value > row["rewards"][policy] for value in values)
                    for row in group
                },
                "centered_advantage": {
                    row["candidate_id"]: row["rewards"][policy] - center for row in group
                },
                "std_normalized_advantage": {
                    row["candidate_id"]: (row["rewards"][policy] - center) / stdev if stdev > 1e-12 else 0.0
                    for row in group
                },
            })
        eligible = [group for group in per_task if group["candidate_count"] >= 2]
        summary["policies"][policy] = {
            "mean_reward": statistics.mean(row["rewards"][policy] for row in records),
            "eligible_group_count": len(eligible),
            "nonconstant_group_fraction": statistics.mean(group["nonconstant"] for group in eligible) if eligible else None,
            "groups": per_task,
        }
    summary["policy_pairs"] = {}
    for left, right in combinations(active_policies, 2):
        comparisons = []
        for task_id, group in sorted(groups.items()):
            if len(group) < 2:
                continue
            winners = {}
            for policy in (left, right):
                best = max(row["rewards"][policy] for row in group)
                winners[policy] = {
                    row["candidate_id"] for row in group
                    if abs(row["rewards"][policy] - best) <= 1e-12
                }
            disagreements = 0
            pairs = list(combinations(group, 2))
            for first, second in pairs:
                signs = []
                for policy in (left, right):
                    difference = first["rewards"][policy] - second["rewards"][policy]
                    signs.append(0 if abs(difference) <= 1e-12 else 1 if difference > 0 else -1)
                disagreements += signs[0] != signs[1]
            comparisons.append({
                "task_id": task_id,
                "top_choice_disagrees": winners[left] != winners[right],
                "pairwise_order_disagreement_fraction": disagreements / len(pairs),
            })
        summary["policy_pairs"][f"{left}:{right}"] = comparisons
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DATASET_ROOT)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--partition", choices=SPLITS, default="train")
    parser.add_argument("--per-level", type=int, default=1)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--execution-timeout", type=float, default=20.0)
    parser.add_argument("--level", choices=("L0", "L1", "L2", "L3", "L4"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--controls", action="store_true")
    source.add_argument("--candidates", type=Path, help="JSONL: task_id, candidate_id, completion")
    parser.add_argument("--controls-container", action="store_true", help="execute trusted controls in the same immutable container used for model programs")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output exists; use a new artifact path")
    if args.per_level < 1:
        parser.error("--per-level must be positive")
    if importlib.metadata.version("gdsfactory") != "9.20.7":
        raise RuntimeError("the evaluator requires gdsfactory==9.20.7")
    manifest = json.loads(args.manifest.read_text())
    verify_manifest(manifest, args.dataset_root)
    allowed = {row["task_id"] for row in manifest["rows"] if row["split"] == args.partition}
    tasks = {task.sampler.opaque_id: task for task in load_release(args.dataset_root)}
    if args.controls:
        chosen: list[TaskRecord] = []
        for level in ("L0", "L1", "L2", "L3", "L4"):
            if args.level and args.level != level:
                continue
            chosen.extend(sorted(
                (task for task_id, task in tasks.items() if task_id in allowed and task.sampler.level == level),
                key=lambda task: task.sampler.opaque_id,
            )[:args.per_level])
        candidates = [candidate for task in chosen for candidate in controls(task)]
    else:
        candidates = [json.loads(line) for line in args.candidates.read_text().splitlines() if line.strip()]
    if not candidates:
        raise ValueError("no candidates selected")
    identities = set()
    for candidate in candidates:
        task_id, candidate_id = candidate["task_id"], candidate["candidate_id"]
        if task_id not in allowed or task_id not in tasks:
            raise ValueError(f"candidate references task outside {args.partition}: {task_id}")
        if not isinstance(candidate_id, str) or not candidate_id or not isinstance(candidate["completion"], str):
            raise ValueError("candidate_id and completion must be strings; candidate_id must be nonempty")
        identity = (task_id, candidate_id)
        if identity in identities:
            raise ValueError(f"duplicate candidate: {identity}")
        identities.add(identity)
    # Only frozen, trusted labels and fixed controls run in local subprocesses.
    # Imported model programs must use the existing immutable Docker boundary.
    with PixCellEvaluator(
        require_isolation=not args.controls or args.controls_container,
        max_workers=args.workers,
        execution_timeout_seconds=args.execution_timeout,
    ) as evaluator:
        boundary = evaluator.execution_boundary
        sandbox = {"image_ref": boundary.image_ref, "image_id": boundary.image_id} if boundary else None
        results = evaluator.evaluate_batch([
            (tasks[candidate["task_id"]].reference, candidate["completion"])
            for candidate in candidates
        ])
    baselines = {task_id: rect_baseline(tasks[task_id].reference) for task_id, _ in identities}
    records = []
    for candidate, result in zip(candidates, results, strict=True):
        task = tasks[candidate["task_id"]]
        baseline = baselines[candidate["task_id"]]
        records.append(measurement_record(candidate, task, baseline, result))
    control_failures = []
    if args.controls:
        for record in records:
            expected = {
                "ground_truth": "ok", "bbox_rectangle": "ok",
                "syntax_failure": "syntax_error", "impure_source": "source_rejected",
            }[record["candidate_id"]]
            if record["status"] != expected or (
                record["candidate_id"] == "ground_truth"
                and (record["iou"] is None or record["iou"] < 0.97)
            ):
                control_failures.append({
                    "task_id": record["task_id"], "candidate_id": record["candidate_id"],
                    "expected_status": expected, "actual_status": record["status"],
                    "iou": record["iou"],
                })
    report = {
        "schema_version": "pixcell-contract-signal-audit-v1",
        "experiment_type": "offline_controls" if args.controls else "offline_rollout_rescore",
        "training_performed": False,
        "manifest_sha256": manifest["manifest_sha256"],
        "partition": args.partition,
        "execution_boundary": "isolated_container" if sandbox else "trusted_controls_subprocess",
        "sandbox": sandbox,
        "execution_workers": args.workers,
        "execution_timeout_seconds": args.execution_timeout,
        "control_checks": {"passed": not control_failures, "failures": control_failures} if args.controls else None,
        "runtime": {
            "python": sys.version,
            "packages": {name: importlib.metadata.version(name) for name in ("gdsfactory", "numpy", "scipy", "pillow", "pyarrow")},
        },
        "measurement_sources": {
            name: file_digest(Path(import_module(name).__file__))
            for name in (
                "rl.common.evaluator", "rl.common.baselines", "rl.common.geometry",
                "rl.track_a.reward", "homi.conductor.source_policy",
                "michaelangelo.core.compare_absolute", "michaelangelo.core.rc01",
            )
        },
        "limitations": [
            "Offline ranking is signal diagnosis; it does not establish which signal trains best.",
            "These are per-candidate scalar rewards, not per-token or per-primitive credit attribution.",
            "Normalized advantages are diagnostics, not a claim about a particular trainer's loss implementation.",
            "Final acceptance additionally requires the conductor verify_cell gate and relevant knob checks.",
        ],
        "summary": summarize(records),
        "records": records,
    }
    write_new_json(args.out, report)
    print(json.dumps({"out": str(args.out), "candidate_count": len(records), "statuses": report["summary"]["status_counts"]}))
    if control_failures:
        raise SystemExit("control audit failed; see artifact diagnostics before running model experiments")


if __name__ == "__main__":
    main()
