"""The Track A reward policies.

``shaped_v3b`` is the campaign policy: the private library's reward v3-b,
ported byte-for-byte in its constants. It pays only for structure beyond the
degenerate bbox-rectangle answer (``iou_n``/``dice_n`` — rectangle-baseline-
normalized excess IoU/Dice), adds a boundary-chamfer "teacher" term for
count/boundary progress IoU cannot see, keeps a 0.05 executable floor so a
valid-but-wrong program is distinguishable from a crash, and scores
rectangle-like targets raw (normalizing against a rectangle that IS the
answer would make every program look identical).

Purity stays pre-execution: the evaluator returns ``SOURCE_REJECTED`` as a
MODEL failure, so an impure program earns 0.0 — the old ship-mode semantics
(a floor for impure programs trains the violation).

``None`` means the rollout must be masked (or the run aborted for a broken
reference); it must never be converted to a policy reward of zero.
"""

from __future__ import annotations

from collections.abc import Mapping
import math

from rl.common.baselines import TaskBaseline
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus


VALID_PROGRAM_FLOOR = 0.05
IOU_WEIGHT = 0.95

SHAPED_FLOOR = 0.05
W_IOU3, W_DICE3, W_TEACHER = 0.40, 0.15, 0.40
TAU_FRAC = 0.05                 # tau = TAU_FRAC * diag_um (chamfer softness scale)
TEACHER_DENOM_FLOOR = 0.3       # floors the rect-subtraction denominator (1 - t2b_rect)
DEGENERATE_IOU_RECT = 0.95      # rect-like target: the rectangle already scores this IoU

REWARD_POLICIES = (
    "validity_floor",
    "validity_only",
    "raw_iou",
    "shaped_v3b",
    "rc01",
)


def reward_for(result: EvaluationResult) -> float | None:
    """Map measurement to reward without hiding evaluator failures."""

    if result.status is EvaluationStatus.OK:
        if result.iou is None:
            raise ValueError("successful evaluation has no IoU")
        return VALID_PROGRAM_FLOOR + IOU_WEIGHT * float(result.iou)
    if result.attribution is Attribution.MODEL:
        return 0.0
    return None


def norm_excess(x: float, base: float) -> float:
    """Excess over the rectangle baseline, as a fraction of the remaining
    headroom. 0 at (or below) the baseline, 1 at perfect."""

    if base >= 1.0:
        return 0.0
    return max(0.0, (x - base) / (1.0 - base))


def _t2b(chamfer_um: float | None, tau: float) -> float:
    """exp(-chamfer/tau) closeness-to-boundary score. None/inf chamfer (an
    empty mask, a failed render) scores 0 — worst case, never a crash."""

    if chamfer_um is None or chamfer_um == float("inf"):
        return 0.0
    return math.exp(-float(chamfer_um) / tau)


def _validated_scores(result: EvaluationResult) -> tuple[float, float]:
    if result.iou is None or result.dice is None:
        raise ValueError("successful evaluation has no IoU/Dice")
    iou = float(result.iou)
    dice = float(result.dice)
    for value in (iou, dice):
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("successful evaluation has an invalid measurement")
    return iou, dice


def shaped_components(
    result: EvaluationResult,
    baseline: TaskBaseline,
) -> dict[str, float]:
    """The logging breakdown of ``shaped_v3b``. Zeros for non-OK results."""

    if result.status is not EvaluationStatus.OK:
        return {
            "iou_n": 0.0,
            "dice_n": 0.0,
            "t2b": 0.0,
            "teacher_nb": 0.0,
            "degenerate": float(baseline.iou_rect >= DEGENERATE_IOU_RECT),
        }
    iou, dice = _validated_scores(result)
    diag = baseline.diag_um if baseline.diag_um > 0 else 1e-9
    tau = max(TAU_FRAC * diag, 1e-9)
    chamfer = result.metrics.get("chamfer_boundary_um")
    chamfer_rect = baseline.chamfer_rect_boundary_um
    t2b = _t2b(chamfer, tau)
    t2b_rect = _t2b(chamfer_rect if chamfer_rect is not None else diag, tau)
    teacher_nb = max(0.0, t2b - t2b_rect) / max(1.0 - t2b_rect, TEACHER_DENOM_FLOOR)
    return {
        "iou_n": norm_excess(iou, baseline.iou_rect),
        "dice_n": norm_excess(dice, baseline.dice_rect),
        "t2b": t2b,
        "teacher_nb": teacher_nb,
        "degenerate": float(baseline.iou_rect >= DEGENERATE_IOU_RECT),
    }


def _shaped_v3b(result: EvaluationResult, baseline: TaskBaseline) -> float:
    iou, dice = _validated_scores(result)
    parts = shaped_components(result, baseline)
    if baseline.iou_rect >= DEGENERATE_IOU_RECT:
        return (
            SHAPED_FLOOR
            + W_IOU3 * iou
            + W_DICE3 * dice
            + W_TEACHER * parts["t2b"]
        )
    return (
        SHAPED_FLOOR
        + W_IOU3 * parts["iou_n"]
        + W_DICE3 * parts["dice_n"]
        + W_TEACHER * parts["teacher_nb"]
    )


def _validated_unit_float(value: object, *, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"successful evaluation has no {label}")
    numeric = float(value)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError(f"successful evaluation has an invalid {label}")
    return numeric


def _rc01_reward(result: EvaluationResult) -> float:
    """Compute the frozen RC-01 v1.2.0 policy reward:
    ``0.05 * overflow_factor + 0.95 * score`` on non-empty OK renders, ``0.0`` on empty renders.
    """
    rc01_info = result.metrics.get("rc01")
    if isinstance(rc01_info, Mapping):
        raw_score = rc01_info.get("score")
        raw_overflow = rc01_info.get("overflow_factor", 1.0)
        beta0_a = rc01_info.get("beta0_a")
    elif rc01_info is not None and hasattr(rc01_info, "score"):
        raw_score = getattr(rc01_info, "score")
        raw_overflow = getattr(rc01_info, "overflow_factor", 1.0)
        beta0_a = getattr(rc01_info, "beta0_a", None)
    else:
        raw_score = result.metrics.get("rc01_score")
        raw_overflow = result.metrics.get("rc01_overflow_factor", 1.0)
        beta0_a = None

    score = _validated_unit_float(raw_score, label="RC-01 score")
    overflow_factor = _validated_unit_float(raw_overflow, label="RC-01 overflow_factor")

    if "rc01_empty" in result.metrics:
        is_empty = bool(result.metrics["rc01_empty"])
    elif beta0_a is not None:
        is_empty = int(beta0_a) == 0
    else:
        is_empty = False
    if is_empty:
        return 0.0
    return float(VALID_PROGRAM_FLOOR * overflow_factor + IOU_WEIGHT * score)


def reward_for_policy(
    result: EvaluationResult,
    *,
    policy: str,
    baseline: TaskBaseline | None = None,
) -> float | None:
    """Apply one explicit reward policy while preserving fault attribution."""

    if policy == "validity_floor":
        return reward_for(result)
    if policy == "validity_only":
        if result.status is EvaluationStatus.OK:
            return 1.0
        if result.attribution is Attribution.MODEL:
            return 0.0
        return None
    if policy == "raw_iou":
        if result.status is EvaluationStatus.OK:
            if result.iou is None:
                raise ValueError("successful evaluation has no IoU")
            iou = float(result.iou)
            if not math.isfinite(iou) or not 0.0 <= iou <= 1.0:
                raise ValueError("successful evaluation has an invalid IoU")
            return iou
        if result.attribution is Attribution.MODEL:
            return 0.0
        return None
    if policy == "shaped_v3b":
        if result.status is EvaluationStatus.OK:
            if baseline is None:
                raise ValueError("shaped_v3b requires a per-task baseline")
            return float(_shaped_v3b(result, baseline))
        if result.attribution is Attribution.MODEL:
            return 0.0
        return None
    if policy == "rc01":
        if result.status is EvaluationStatus.OK:
            return _rc01_reward(result)
        if result.attribution is Attribution.MODEL:
            return 0.0
        return None
    raise ValueError(f"unknown reward policy: {policy!r}")


def group_rewards(results: list[EvaluationResult]) -> list[float | None]:
    """Return ordered rewards; callers center advantages over non-``None`` items."""

    return [reward_for(item) for item in results]
