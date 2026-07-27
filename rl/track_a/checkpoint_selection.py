"""Pair Track A checkpoint reports and apply the collapse veto."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _index_by_sampler(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    expected_role: str,
) -> dict[str, tuple[str, Mapping[str, Any]]]:
    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for path, report in reports:
        role = report.get("evaluation_role")
        if role != expected_role:
            raise ValueError(
                f"{path} has evaluation_role={role!r}; expected {expected_role!r}"
            )
        sampler_path = str(report.get("sampler_path", ""))
        if not sampler_path:
            raise ValueError(f"{path} does not declare sampler_path")
        if sampler_path in indexed:
            raise ValueError(
                f"duplicate {expected_role} report for sampler {sampler_path!r}"
            )
        indexed[sampler_path] = (path, report)
    return indexed


def select_sft_checkpoint(
    geometry_reports: Sequence[tuple[str, Mapping[str, Any]]],
    behavioral_reports: Sequence[tuple[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    """Select by full k=1 geometry after applying a paired G4 collapse veto."""

    geometry = _index_by_sampler(
        geometry_reports,
        expected_role="checkpoint-geometry",
    )
    behavior = _index_by_sampler(
        behavioral_reports,
        expected_role="behavioral-collapse-probe",
    )
    missing = sorted(set(geometry) - set(behavior))
    extra = sorted(set(behavior) - set(geometry))
    if missing or extra:
        raise ValueError(
            "geometry/behavior sampler pairing mismatch: "
            f"missing_behavior={missing}, extra_behavior={extra}"
        )

    candidates: list[dict[str, Any]] = []
    for sampler_path, (geometry_path, geometry_report) in geometry.items():
        behavior_path, behavior_report = behavior[sampler_path]
        if int(geometry_report.get("k", 0)) != 1:
            raise ValueError(f"{geometry_path} is not a k=1 geometry report")
        if int(behavior_report.get("k", 0)) != 4:
            raise ValueError(f"{behavior_path} is not a k=4 behavioral report")
        probe = behavior_report.get("behavioral_probe")
        if not isinstance(probe, Mapping):
            raise ValueError(f"{behavior_path} has no behavioral_probe")
        collapsed_value = probe.get("collapse_detected")
        if not isinstance(collapsed_value, bool):
            raise ValueError(
                f"{behavior_path} has no boolean collapse_detected verdict"
            )
        collapsed = collapsed_value
        candidates.append(
            {
                "sampler_path": sampler_path,
                "geometry_report": geometry_path,
                "behavioral_report": behavior_path,
                "eligible": not collapsed,
                "veto_reason": (
                    "G4 behavioral probe detected sampling collapse"
                    if collapsed
                    else None
                ),
                "representation_macro_mean_iou": float(
                    geometry_report["representation_macro_mean_iou"]
                ),
                "pure_executable_rate": float(
                    geometry_report["summary"]["pure_executable_rate"]
                ),
                "behavioral_probe": {
                    "nonconstant_reward_group_fraction": probe[
                        "nonconstant_reward_group_fraction"
                    ],
                    "mean_within_group_reward_std": probe[
                        "mean_within_group_reward_std"
                    ],
                    "mean_distinct_programs_per_prompt": probe[
                        "mean_distinct_programs_per_prompt"
                    ],
                    "mean_distinct_successful_renders_per_prompt": probe[
                        "mean_distinct_successful_renders_per_prompt"
                    ],
                    "collapse_detected": collapsed,
                    "collapse_signals": probe.get("collapse_signals", {}),
                },
            }
        )

    candidates.sort(
        key=lambda item: (
            item["eligible"],
            item["representation_macro_mean_iou"],
            item["pure_executable_rate"],
        ),
        reverse=True,
    )
    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    if not eligible:
        raise ValueError("every checkpoint was vetoed by its paired G4 probe")

    return {
        "selection_rule": (
            "veto only explicit G4 sampling collapse; among eligible checkpoints, "
            "maximize full-validation k=1 representation-macro raw IoU; "
            "pure-executable rate breaks ties"
        ),
        "behavioral_metrics_are_ranking_features": False,
        "selected": eligible[0],
        "ranking": candidates,
    }
