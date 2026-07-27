"""Pair Track A checkpoint reports and apply the collapse veto."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rl.track_a.evaluation_contract import (
    CheckpointSelectionContract,
    validate_evaluation_report,
)


def _index_by_sampler(
    reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    expected_role: str,
    contract: CheckpointSelectionContract,
) -> dict[str, tuple[str, Mapping[str, Any]]]:
    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for path, report in reports:
        try:
            validate_evaluation_report(
                report,
                contract=contract,
                expected_role=expected_role,
            )
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        sampler_path = str(report.get("sampler_path", ""))
        if sampler_path in indexed:
            raise ValueError(
                f"duplicate {expected_role} report for sampler {sampler_path!r}"
            )
        indexed[sampler_path] = (path, report)
    return indexed


def select_sft_checkpoint(
    geometry_reports: Sequence[tuple[str, Mapping[str, Any]]],
    behavioral_reports: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    contract: CheckpointSelectionContract,
) -> dict[str, Any]:
    """Select by full k=1 geometry after applying a paired G4 collapse veto."""

    geometry = _index_by_sampler(
        geometry_reports,
        expected_role="checkpoint-geometry",
        contract=contract,
    )
    behavior = _index_by_sampler(
        behavioral_reports,
        expected_role="behavioral-collapse-probe",
        contract=contract,
    )
    missing = sorted(set(geometry) - set(behavior))
    extra = sorted(set(behavior) - set(geometry))
    if missing or extra:
        raise ValueError(
            "geometry/behavior sampler pairing mismatch: "
            f"missing_behavior={missing}, extra_behavior={extra}"
        )

    sandbox_identities = {
        (
            str(report["provenance"]["candidate_sandbox"]["image_ref"]),
            str(report["provenance"]["candidate_sandbox"]["image_id"]),
        )
        for _path, report in [*geometry.values(), *behavior.values()]
    }
    if len(sandbox_identities) != 1:
        raise ValueError(
            "checkpoint reports were measured with different candidate "
            "sandbox images"
        )
    sandbox_image_ref, sandbox_image_id = next(iter(sandbox_identities))

    candidates: list[dict[str, Any]] = []
    for sampler_path, (geometry_path, geometry_report) in geometry.items():
        behavior_path, behavior_report = behavior[sampler_path]
        probe = behavior_report.get("behavioral_probe")
        collapsed_value = probe.get("collapse_detected")
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
        "selection_provenance": {
            "source_git_sha": contract.source_git_sha,
            "depth_logical_release_sha256": (
                contract.depth_logical_release_sha256
            ),
            "model": contract.model,
            "renderer": contract.renderer,
            "candidate_sandbox": {
                "image_ref": sandbox_image_ref,
                "image_id": sandbox_image_id,
            },
        },
        "selected": eligible[0],
        "ranking": candidates,
    }
