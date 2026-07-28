"""Rectangle-baseline computation: the zero point of the shaped reward."""

from __future__ import annotations

import hashlib
import io
import math

import numpy as np
import pytest
from PIL import Image

from rl.common.baselines import cached_rect_baseline, rect_baseline
from rl.common.contracts import VerifierReference
from rl.common.geometry import boundary_mask, chamfer_sym_um


def _reference(mask: np.ndarray, footprint_um: tuple[float, float]) -> VerifierReference:
    """PNG-encode a boolean ink mask (True = black material) as a target reference."""

    array = np.where(mask, 0, 255).astype(np.uint8)
    image = Image.fromarray(array, mode="L")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    return VerifierReference(
        target_image_bytes=payload,
        footprint_um=footprint_um,
        target_image_sha256=hashlib.sha256(payload).hexdigest(),
    )


def test_solid_rectangle_target_is_degenerate() -> None:
    mask = np.zeros((80, 100), dtype=bool)
    mask[20:60, 20:80] = True
    baseline = rect_baseline(_reference(mask, (30.0, 20.0)))
    assert baseline.iou_rect == pytest.approx(1.0)
    assert baseline.dice_rect == pytest.approx(1.0)
    assert baseline.diag_um == pytest.approx(math.hypot(30.0, 20.0))


def test_l_shape_baseline_matches_hand_computation() -> None:
    mask = np.zeros((80, 100), dtype=bool)
    mask[20:60, 20:40] = True   # vertical bar: 40 x 20
    mask[40:60, 20:80] = True   # horizontal bar: 20 x 60, overlap 20 x 20
    ink = float(mask.sum())
    bbox_area = float(40 * 60)  # ink bbox: rows 20:60, cols 20:80
    baseline = rect_baseline(_reference(mask, (30.0, 20.0)))
    assert baseline.iou_rect == pytest.approx(ink / bbox_area)
    assert baseline.dice_rect == pytest.approx(2.0 * ink / (ink + bbox_area))
    assert baseline.chamfer_rect_boundary_um is not None
    assert baseline.chamfer_rect_boundary_um > 0.0
    assert baseline.diag_um == pytest.approx(math.hypot(30.0, 20.0))


def test_cache_returns_identical_object_per_sha() -> None:
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:30, 5:35] = True
    reference = _reference(mask, (10.0, 5.0))
    first = cached_rect_baseline(reference)
    second = cached_rect_baseline(reference)
    assert first is second


def test_chamfer_of_shifted_row_is_exact() -> None:
    a = np.zeros((5, 5), dtype=bool)
    b = np.zeros((5, 5), dtype=bool)
    a[2, 1:4] = True
    b[3, 1:4] = True
    chamfer, a_to_b, b_to_a = chamfer_sym_um(a, b, um_per_px=2.0)
    assert a_to_b == pytest.approx(2.0)
    assert b_to_a == pytest.approx(2.0)
    assert chamfer == pytest.approx(2.0)


def test_chamfer_empty_mask_is_infinite() -> None:
    empty = np.zeros((4, 4), dtype=bool)
    full = np.ones((4, 4), dtype=bool)
    chamfer, a_to_b, b_to_a = chamfer_sym_um(empty, full, um_per_px=1.0)
    assert chamfer == float("inf") and a_to_b == float("inf") and b_to_a == float("inf")


def test_boundary_mask_of_solid_block_is_its_outline() -> None:
    mask = np.zeros((6, 6), dtype=bool)
    mask[1:5, 1:5] = True
    outline = boundary_mask(mask)
    assert outline[1, 1] and outline[1, 4] and outline[4, 1] and outline[4, 4]
    assert not outline[2, 2] and not outline[3, 3]
    assert outline.sum() == 12
