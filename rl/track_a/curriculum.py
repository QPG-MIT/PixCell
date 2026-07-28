"""Deterministic scheduling and loss weighting for Track A."""

from __future__ import annotations

import math
import random
from collections import defaultdict, deque
from collections.abc import Sequence

from rl.common.contracts import TaskRecord


def balanced_effective_pass(
    tasks: list[TaskRecord],
    *,
    seed: int,
    draws: int | None = None,
) -> list[TaskRecord]:
    """Return a balanced deterministic subset without replacement."""

    if not tasks:
        return []
    target = draws if draws is not None else len(tasks)
    if target < 1:
        raise ValueError("draws must be positive")
    if target > len(tasks):
        raise ValueError(
            f"draws={target} exceeds the {len(tasks)} unique available tasks"
        )
    return stratified_physical_pass(tasks, seed=seed)[:target]


def stratified_physical_pass(
    tasks: list[TaskRecord],
    *,
    seed: int,
) -> list[TaskRecord]:
    """Interleave levels and representations while visiting every row once."""

    if not tasks:
        return []
    rng = random.Random(seed)
    grouped: dict[str, dict[str, deque[TaskRecord]]] = defaultdict(
        lambda: defaultdict(deque)
    )
    for task in tasks:
        grouped[task.sampler.level][task.sampler.representation_id].append(task)

    representation_orders: dict[str, deque[str]] = {}
    for level, representations in grouped.items():
        names = sorted(representations)
        rng.shuffle(names)
        representation_orders[level] = deque(names)
        for name in names:
            values = list(representations[name])
            rng.shuffle(values)
            representations[name] = deque(values)

    output: list[TaskRecord] = []
    levels = sorted(grouped)
    while len(output) < len(tasks):
        progress = False
        for level in levels:
            names = representation_orders[level]
            for _ in range(len(names)):
                name = names[0]
                names.rotate(-1)
                rows = grouped[level][name]
                if rows:
                    output.append(rows.popleft())
                    progress = True
                    break
        if not progress:
            break
    if len(output) != len(tasks) or len({id(item) for item in output}) != len(tasks):
        raise RuntimeError("stratified pass did not visit every task exactly once")
    return output


def hierarchical_sft_weights(tasks: list[TaskRecord]) -> dict[str, float]:
    """Equalize total SFT loss mass by level, then representation."""

    if not tasks:
        return {}
    grouped: dict[str, dict[str, list[TaskRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for task in tasks:
        grouped[task.sampler.level][task.sampler.representation_id].append(task)
    level_count = len(grouped)
    total = len(tasks)
    weights: dict[str, float] = {}
    for representations in grouped.values():
        representation_count = len(representations)
        for rows in representations.values():
            multiplier = total / (
                level_count * representation_count * len(rows)
            )
            for task in rows:
                weights[task.sampler.opaque_id] = multiplier
    mean = sum(weights[task.sampler.opaque_id] for task in tasks) / total
    if not math.isclose(mean, 1.0, rel_tol=1e-12, abs_tol=1e-12):
        raise RuntimeError(f"SFT weight mean is {mean}, expected 1")
    return weights


def deterministic_rl_batch(
    current_tasks: Sequence[TaskRecord],
    replay_tasks: Sequence[TaskRecord],
    *,
    step: int,
    groups_per_batch: int,
    schedule_seed: int,
    shuffle: bool = True,
) -> list[tuple[str, TaskRecord]]:
    """Select one exact current/replay batch shared by launch and preflight."""

    current = list(current_tasks)
    replay = list(replay_tasks)
    if not current:
        raise ValueError("RL current-task pool is empty")
    if step < 0 or groups_per_batch < 1:
        raise ValueError("RL step and groups_per_batch must be nonnegative/positive")
    count = min(groups_per_batch, len(current))
    if shuffle and replay:
        def replay_groups(index: int) -> int:
            proposed = (
                (2, 2, 2, 1, 1)[index % 5]
                if groups_per_batch == 8
                else max(1, round(0.2 * groups_per_batch))
            )
            return min(proposed, count, len(replay))

        replay_count = replay_groups(step)
        current_count = count - replay_count
        current_order = stratified_physical_pass(
            current,
            seed=schedule_seed + step // max(1, len(current)),
        )
        replay_order = stratified_physical_pass(
            replay,
            seed=schedule_seed + 100_000 + step // max(1, len(replay)),
        )
        replay_start = sum(replay_groups(index) for index in range(step))
        current_start = step * count - replay_start
        current_start %= len(current_order)
        replay_start %= len(replay_order)
        selected = [
            (
                "current",
                current_order[(current_start + offset) % len(current_order)],
            )
            for offset in range(current_count)
        ]
        selected.extend(
            (
                "replay",
                replay_order[(replay_start + offset) % len(replay_order)],
            )
            for offset in range(replay_count)
        )
        random.Random(schedule_seed + 200_000 + step).shuffle(selected)
        return selected
    if shuffle:
        order = stratified_physical_pass(
            current,
            seed=schedule_seed + step // max(1, len(current)),
        )
        start = (step * count) % len(order)
        return [
            ("current", order[(start + offset) % len(order)])
            for offset in range(count)
        ]
    return [("current", task) for task in current[:count]]
