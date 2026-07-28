"""Per-task rectangle baselines: the zero point of the shaped reward.

``iou_rect``/``dice_rect`` are what a solid rectangle filling the target's
calibrated ink bounding box would score — the degenerate answer the old
campaign's policy demonstrably discovered. The shaped reward normalizes
against these so area-filling earns nothing and one reward scale means the
same thing on every task. The dataset is frozen, so a baseline is a constant
of the release; it is computed once per ``target_image_sha256`` and cached.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rl.common.contracts import VerifierReference
from rl.common.geometry import boundary_mask, chamfer_sym_um


@dataclass(frozen=True)
class TaskBaseline:
    iou_rect: float
    dice_rect: float
    chamfer_rect_boundary_um: float | None
    diag_um: float


def rect_baseline(reference: VerifierReference) -> TaskBaseline:
    """Score the bbox-rectangle fill against the target, on the evaluator's
    own calibration (one geometry for baseline and score)."""

    from rl.common.evaluator import _prepare_reference

    prepared = _prepare_reference(reference)
    array = np.asarray(prepared.target)
    threshold = prepared.calibration["white_threshold"]
    x0, y0, x1, y1 = prepared.calibration["bbox"]
    target = array < threshold
    rectangle = np.zeros_like(target)
    rectangle[y0:y1, x0:x1] = True
    intersection = float(np.logical_and(target, rectangle).sum())
    union = float(np.logical_or(target, rectangle).sum())
    denominator = float(target.sum() + rectangle.sum())
    scale_x, scale_y = prepared.calibration["scale_px_per_um"]
    um_per_px = 2.0 / (scale_x + scale_y)
    chamfer_b, _, _ = chamfer_sym_um(
        boundary_mask(rectangle),
        boundary_mask(target),
        um_per_px,
    )
    length_um, width_um = prepared.calibration["footprint_um"]
    return TaskBaseline(
        iou_rect=intersection / union if union else 0.0,
        dice_rect=2.0 * intersection / denominator if denominator else 0.0,
        chamfer_rect_boundary_um=(
            None if chamfer_b == float("inf") else float(chamfer_b)
        ),
        diag_um=float((length_um * length_um + width_um * width_um) ** 0.5),
    )


_CACHE: dict[str, TaskBaseline] = {}


def cached_rect_baseline(reference: VerifierReference) -> TaskBaseline:
    key = reference.target_image_sha256
    if key not in _CACHE:
        _CACHE[key] = rect_baseline(reference)
    return _CACHE[key]
