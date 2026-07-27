"""Deterministic aggregation and Qwen operating-point selection."""

from __future__ import annotations

import json
import math
import os
import statistics
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rl.evaluation.attempt_store import AttemptKey, AttemptStore
from rl.evaluation.protocol import JobSpec
from rl.evaluation.tasks import EvaluationTask, canonical_json_sha256


SUMMARY_SCHEMA = "pixcell-baseline-summary-v1"
SELECTION_SCHEMA = "pixcell-operating-point-selection-v1"


def _percentile(values: list[int | float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _attempt_key(study_id: str, job: JobSpec) -> AttemptKey:
    return AttemptKey(
        study_id=study_id,
        hypothesis_id=job.hypothesis_id,
        arm_id=job.arm_id,
        task_id=job.task_id,
        attempt_index=job.attempt_index,
    )


def summarize_arm(
    *,
    store: AttemptStore,
    study_id: str,
    hypothesis_id: str,
    arm_id: str,
    jobs: list[JobSpec],
    tasks: list[EvaluationTask],
) -> dict[str, Any]:
    relevant = [
        job
        for job in jobs
        if job.hypothesis_id == hypothesis_id and job.arm_id == arm_id
    ]
    task_by_id = {task.task_id: task for task in tasks}
    attempts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for job in relevant:
        key = _attempt_key(study_id, job)
        receipt = store.load_sampling_receipt(key)
        evaluation = store.load_evaluation(key)
        if receipt is None or evaluation is None:
            missing.append(key.as_dict())
            continue
        if evaluation.payload.get("attribution") != "model":
            raise ValueError(
                f"{key} is not a model-attributed result and cannot be summarized"
            )
        task = task_by_id[job.task_id]
        attempts.append(
            {
                "task_id": job.task_id,
                "level": task.level,
                "representation_id": task.representation_id,
                "attempt_index": job.attempt_index,
                "receipt": receipt.payload,
                "evaluation": evaluation.payload,
            }
        )

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_representation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in attempts:
        by_task[attempt["task_id"]].append(attempt)
        by_representation[attempt["representation_id"]].append(attempt)
        by_level[attempt["level"]].append(attempt)

    def score(value: dict[str, Any]) -> float:
        return float(value["evaluation"]["aggregation_iou"])

    task_means = [
        statistics.fmean(score(value) for value in values)
        for values in by_task.values()
    ]
    task_bests = [
        max(score(value) for value in values)
        for values in by_task.values()
    ]
    representation_means = [
        statistics.fmean(score(value) for value in values)
        for values in by_representation.values()
    ]
    completion_tokens = [
        int(value["receipt"]["sample"]["completion_tokens"]) for value in attempts
    ]
    prompt_tokens = [
        int(value["receipt"]["sample"]["prompt_tokens"]) for value in attempts
    ]
    sampling_seconds = [
        float(value["receipt"]["sampling_seconds"]) for value in attempts
    ]
    evaluation_seconds = [
        float(value["evaluation"]["evaluation_seconds"]) for value in attempts
    ]
    pure_count = sum(
        bool(value["evaluation"]["pure_executable"]) for value in attempts
    )
    cap_count = sum(bool(value["receipt"]["sample"]["cap_hit"]) for value in attempts)
    cached_cost = sum(
        float(value["receipt"]["cost_estimate_usd"]["cached_prefill"])
        for value in attempts
    )
    uncached_cost = sum(
        float(value["receipt"]["cost_estimate_usd"]["uncached_prefill"])
        for value in attempts
    )
    statuses = Counter(
        str(value["evaluation"]["status"]) for value in attempts
    )
    levels: dict[str, Any] = {}
    for level, values in sorted(by_level.items()):
        level_tasks: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for value in values:
            level_tasks[value["task_id"]].append(value)
        levels[level] = {
            "attempts": len(values),
            "tasks": len(level_tasks),
            "mean_iou_at_1": statistics.fmean(
                statistics.fmean(score(item) for item in task_values)
                for task_values in level_tasks.values()
            ),
            "pure_executable_rate": (
                sum(bool(value["evaluation"]["pure_executable"]) for value in values)
                / len(values)
            ),
        }

    count = len(attempts)
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "study_id": study_id,
        "hypothesis_id": hypothesis_id,
        "arm_id": arm_id,
        "complete": not missing and len(attempts) == len(relevant),
        "expected_attempts": len(relevant),
        "attempts": count,
        "tasks": len(by_task),
        "representations": len(by_representation),
        "mean_iou_at_1": statistics.fmean(task_means) if task_means else 0.0,
        "mean_best_at_k_iou": statistics.fmean(task_bests) if task_bests else 0.0,
        "representation_macro_mean_iou": (
            statistics.fmean(representation_means)
            if representation_means
            else 0.0
        ),
        "pure_executable_rate": pure_count / count if count else 0.0,
        "cap_hit_rate": cap_count / count if count else 0.0,
        "completion_tokens_total": sum(completion_tokens),
        "completion_tokens_median": (
            statistics.median(completion_tokens) if completion_tokens else 0.0
        ),
        "completion_tokens_p95": _percentile(completion_tokens, 0.95),
        "prompt_tokens_total": sum(prompt_tokens),
        "sampling_seconds_total": sum(sampling_seconds),
        "evaluation_seconds_total": sum(evaluation_seconds),
        "estimated_cached_cost_usd": cached_cost,
        "estimated_uncached_cost_usd": uncached_cost,
        "statuses": dict(sorted(statuses.items())),
        "levels": levels,
        "missing": missing,
    }
    summary["logical_sha256"] = canonical_json_sha256(summary)
    return summary


def choose_operating_point(
    *,
    protocol: dict[str, Any],
    source_git_sha: str,
    source_summaries: dict[str, dict[str, Any]],
    rescue_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected = set(protocol["hypotheses"]["RC-H00"]["arm_ids"])
    if set(source_summaries) != expected:
        raise ValueError("operating-point selection requires every RC-H00 arm")
    if not all(value["complete"] for value in source_summaries.values()):
        raise ValueError("operating-point selection requires complete RC-H00 summaries")
    trigger = protocol["hypotheses"]["RC-H00R"]["trigger"]
    source_arm = str(trigger["source_arm"])
    rescue_required = (
        float(source_summaries[source_arm][trigger["metric"]])
        > float(trigger["threshold"])
    )
    candidates = dict(source_summaries)
    rescue_run = rescue_summary is not None
    if rescue_summary is not None:
        if not rescue_summary["complete"]:
            raise ValueError("rescue summary is incomplete")
        candidates[str(rescue_summary["arm_id"])] = rescue_summary
    complete = not rescue_required or rescue_run
    selected: str | None = None
    if complete:
        primary = protocol["operating_point_selection"]["primary_metric"]
        best = max(float(value[primary]) for value in candidates.values())
        tie_band = float(protocol["operating_point_selection"]["metric_tie_band"])
        eligible = [
            (arm_id, value)
            for arm_id, value in candidates.items()
            if float(value[primary]) >= best - tie_band
        ]
        eligible.sort(
            key=lambda item: (
                -float(item[1]["pure_executable_rate"]),
                float(item[1]["estimated_uncached_cost_usd"]),
                float(item[1]["completion_tokens_median"]),
                item[0],
            )
        )
        selected = eligible[0][0]
    document = {
        "schema_version": SELECTION_SCHEMA,
        "study_id": protocol["study_id"],
        "protocol_sha256": protocol["logical_sha256"],
        "source_git_sha": source_git_sha,
        "source_hypothesis": "RC-H00",
        "complete": complete,
        "rescue_required": rescue_required,
        "rescue_run": rescue_run,
        "selected_arm": selected,
        "selection_rule": protocol["operating_point_selection"],
        "arm_summaries": candidates,
    }
    document["logical_sha256"] = canonical_json_sha256(document)
    return document


def atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document, indent=2, sort_keys=True) + "\n"
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
