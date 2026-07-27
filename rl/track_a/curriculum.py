"""Deterministic scheduling and loss weighting for Track A."""

from __future__ import annotations

import math
import random
from collections import defaultdict, deque

from rl.common.contracts import TaskRecord


def balanced_effective_pass(
    tasks: list[TaskRecord],
    *,
    seed: int,
    draws: int | None = None,
) -> list[TaskRecord]:
    """Level-then-representation balanced deterministic task schedule."""

    if not tasks:
        return []
    target = draws if draws is not None else len(tasks)
    if target < 1:
        raise ValueError("draws must be positive")

    by_level: dict[str, dict[str, list[TaskRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for task in tasks:
        by_level[task.sampler.level][task.sampler.representation_id].append(task)

    rng = random.Random(seed)
    level_names = sorted(by_level)
    representation_orders: dict[str, deque[str]] = {}
    row_orders: dict[tuple[str, str], deque[TaskRecord]] = {}
    for level in level_names:
        representations = sorted(by_level[level])
        rng.shuffle(representations)
        representation_orders[level] = deque(representations)
        for representation in representations:
            values = list(by_level[level][representation])
            rng.shuffle(values)
            row_orders[(level, representation)] = deque(values)

    scheduled: list[TaskRecord] = []
    for index in range(target):
        level = level_names[index % len(level_names)]
        representations = representation_orders[level]
        representation = representations[0]
        representations.rotate(-1)
        rows = row_orders[(level, representation)]
        task = rows[0]
        rows.rotate(-1)
        scheduled.append(task)
    return scheduled


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
