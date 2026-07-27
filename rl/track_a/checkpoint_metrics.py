"""Track A behavioral diagnostics for executable checkpoint evaluation."""

from __future__ import annotations

import hashlib
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from rl.common.output import extract_code


def program_sha256(completion: str) -> str:
    """Hash normalized extracted source rather than chat or fence formatting."""

    source = extract_code(completion).replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in source.splitlines()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def behavioral_probe_summary(
    records: Sequence[Mapping[str, Any]],
    *,
    expected_group_size: int = 4,
) -> dict[str, Any]:
    """Summarize within-prompt diversity for a small independent G4 probe.

    This is deliberately not a quality score. It detects only the strongest
    collapse signatures and leaves checkpoint ordering to the full k=1
    executable-geometry report.
    """

    if expected_group_size < 2:
        raise ValueError("behavioral probes require a group size of at least 2")
    if not records:
        raise ValueError("behavioral probe has no records")

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["opaque_id"])].append(record)

    groups: list[dict[str, Any]] = []
    for opaque_id, attempts in sorted(grouped.items()):
        if len(attempts) != expected_group_size:
            raise ValueError(
                f"prompt {opaque_id!r} has {len(attempts)} attempts; "
                f"expected {expected_group_size}"
            )
        program_hashes = sorted(
            {str(attempt["program_sha256"]) for attempt in attempts}
        )
        render_hashes = sorted(
            {
                str(attempt["render_sha256"])
                for attempt in attempts
                if attempt.get("pure_executable") and attempt.get("render_sha256")
            }
        )
        rewards = [float(attempt["reward"]) for attempt in attempts]
        reward_std = statistics.pstdev(rewards)
        reward_range = max(rewards) - min(rewards)
        groups.append(
            {
                "opaque_id": opaque_id,
                "distinct_program_count": len(program_hashes),
                "distinct_program_sha256": program_hashes,
                "successful_render_attempts": sum(
                    bool(attempt.get("pure_executable")) for attempt in attempts
                ),
                "distinct_successful_render_count": len(render_hashes),
                "distinct_successful_render_sha256": render_hashes,
                "reward_std": reward_std,
                "reward_range": reward_range,
                "nonconstant_reward": reward_range > 1e-12,
            }
        )

    group_count = len(groups)
    nonconstant_fraction = (
        sum(group["nonconstant_reward"] for group in groups) / group_count
    )
    mean_reward_std = statistics.fmean(group["reward_std"] for group in groups)
    mean_programs = statistics.fmean(
        group["distinct_program_count"] for group in groups
    )
    mean_renders = statistics.fmean(
        group["distinct_successful_render_count"] for group in groups
    )

    identical_program_every_group = all(
        group["distinct_program_count"] == 1 for group in groups
    )
    constant_render_and_reward_every_group = all(
        group["distinct_successful_render_count"] <= 1
        and not group["nonconstant_reward"]
        for group in groups
    )
    collapse_detected = (
        identical_program_every_group or constant_render_and_reward_every_group
    )

    if not all(
        math.isfinite(value)
        for value in (
            nonconstant_fraction,
            mean_reward_std,
            mean_programs,
            mean_renders,
        )
    ):
        raise ValueError("behavioral probe produced a non-finite metric")

    return {
        "probe_kind": "small-balanced-unmastered-g4",
        "group_size": expected_group_size,
        "prompt_groups": group_count,
        "nonconstant_reward_group_fraction": nonconstant_fraction,
        "mean_within_group_reward_std": mean_reward_std,
        "mean_distinct_programs_per_prompt": mean_programs,
        "mean_distinct_successful_renders_per_prompt": mean_renders,
        "collapse_detected": collapse_detected,
        "collapse_signals": {
            "identical_program_every_group": identical_program_every_group,
            "constant_render_and_reward_every_group": (
                constant_render_and_reward_every_group
            ),
        },
        "groups": groups,
    }
