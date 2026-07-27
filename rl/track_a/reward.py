"""The deliberately small Track A reward policy."""

from __future__ import annotations

from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus


VALID_PROGRAM_FLOOR = 0.05
IOU_WEIGHT = 0.95


def reward_for(result: EvaluationResult) -> float | None:
    """Map measurement to reward without hiding evaluator failures.

    ``None`` means the rollout must be masked (or the run aborted for a broken
    reference); it must never be converted to a policy reward of zero.
    """

    if result.status is EvaluationStatus.OK:
        if result.iou is None:
            raise ValueError("successful evaluation has no IoU")
        return VALID_PROGRAM_FLOOR + IOU_WEIGHT * float(result.iou)
    if result.attribution is Attribution.MODEL:
        return 0.0
    return None


def group_rewards(results: list[EvaluationResult]) -> list[float | None]:
    """Return ordered rewards; callers center advantages over non-``None`` items."""

    return [reward_for(item) for item in results]
