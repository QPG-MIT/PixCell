#!/usr/bin/env python3
"""
Footprint penalty calculation for GDS optimization.

Penalizes GDS designs that exceed the target footprint dimensions.
The penalty is computed in pixel-squared units for commensurability with SSE.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple

import numpy as np

try:
    import gdstk
except ImportError:
    gdstk = None


def compute_gds_bbox_um(
    gds_path: Path,
    layer: int,
    datatype: int,
) -> Tuple[float, float, float, float]:
    """
    Extract bounding box from GDS file in microns.

    Args:
        gds_path: Path to GDS file
        layer: Layer number to extract
        datatype: Datatype to extract

    Returns:
        (x_min, y_min, x_max, y_max) in microns
    """
    if gdstk is None:
        raise ImportError("gdstk is required")

    lib = gdstk.read_gds(str(gds_path))
    top = lib.top_level()
    if not top:
        raise ValueError("No top-level cell found")

    cell = top[0]
    # Flatten to get all polygons including references
    try:
        tmp = cell.copy("__TMP__")
        tmp.flatten()
    except Exception:
        tmp = cell

    all_points = []
    for poly in getattr(tmp, "polygons", []) or []:
        if int(poly.layer) == layer and int(poly.datatype) == datatype:
            all_points.append(np.asarray(poly.points))

    if not all_points:
        raise ValueError(f"No polygons found on layer {layer}:{datatype}")

    pts = np.concatenate(all_points)
    return (
        float(pts[:, 0].min()),
        float(pts[:, 1].min()),
        float(pts[:, 0].max()),
        float(pts[:, 1].max()),
    )


def compute_footprint_penalty(
    gds_bbox_um: Tuple[float, float, float, float],
    target_footprint_um: Tuple[float, float],
    scale_px_per_um: Tuple[float, float],
    mode: str = "exceed",
) -> dict:
    """
    Compute footprint penalty in pixel-squared units.

    The penalty is designed to be commensurable with SSE (pixel-based).

    Args:
        gds_bbox_um: (x_min, y_min, x_max, y_max) of GDS in microns
        target_footprint_um: (length, width) target footprint in microns
        scale_px_per_um: (sx, sy) pixels per micron from calibration
        mode: Penalty mode:
            - "exceed": Only penalize if GDS exceeds target (default)
            - "match": Penalize any deviation from target (too big OR too small)

    Returns:
        dict with:
        - penalty: The penalty value (pixel-squared units)
        - gds_length_um, gds_width_um: Actual GDS dimensions
        - diff_length_um, diff_width_um: Difference from target (signed)
        - diff_length_px, diff_width_px: Difference in pixels (absolute)
        - within_bounds: True if GDS fits within target footprint
        - exact_match: True if GDS matches target exactly (within tolerance)
    """
    x_min, y_min, x_max, y_max = gds_bbox_um
    gds_length_um = x_max - x_min
    gds_width_um = y_max - y_min

    target_length_um, target_width_um = target_footprint_um
    sx, sy = scale_px_per_um

    # Compute difference from target (signed: positive = too big, negative = too small)
    diff_length_um = gds_length_um - target_length_um
    diff_width_um = gds_width_um - target_width_um

    # Target dimensions in pixels (for area calculation)
    target_length_px = target_length_um * sx
    target_width_px = target_width_um * sy

    if mode == "match":
        # Penalize ANY deviation from target (too big OR too small)
        abs_diff_length_px = abs(diff_length_um) * sx
        abs_diff_width_px = abs(diff_width_um) * sy

        # Penalty = area of the "missing" or "extra" region
        if abs_diff_length_px > 0 and abs_diff_width_px > 0:
            penalty = (
                abs_diff_length_px * abs_diff_width_px
                + abs_diff_length_px * target_width_px
                + abs_diff_width_px * target_length_px
            )
        elif abs_diff_length_px > 0:
            penalty = abs_diff_length_px * target_width_px
        elif abs_diff_width_px > 0:
            penalty = abs_diff_width_px * target_length_px
        else:
            penalty = 0.0

        diff_length_px = abs_diff_length_px
        diff_width_px = abs_diff_width_px

    else:  # mode == "exceed"
        # Only penalize if GDS exceeds target
        excess_length_um = max(0.0, diff_length_um)
        excess_width_um = max(0.0, diff_width_um)

        excess_length_px = excess_length_um * sx
        excess_width_px = excess_width_um * sy

        if excess_length_px > 0 and excess_width_px > 0:
            penalty = (
                excess_length_px * excess_width_px
                + excess_length_px * target_width_px
                + excess_width_px * target_length_px
            )
        elif excess_length_px > 0:
            penalty = excess_length_px * target_width_px
        elif excess_width_px > 0:
            penalty = excess_width_px * target_length_px
        else:
            penalty = 0.0

        diff_length_px = excess_length_px
        diff_width_px = excess_width_px

    within_bounds = diff_length_um <= 0 and diff_width_um <= 0
    # Consider "exact match" if within 1% of target
    tolerance = 0.01
    exact_match = (
        abs(diff_length_um) <= target_length_um * tolerance
        and abs(diff_width_um) <= target_width_um * tolerance
    )

    return {
        "penalty": float(penalty),
        "gds_length_um": gds_length_um,
        "gds_width_um": gds_width_um,
        "target_length_um": target_length_um,
        "target_width_um": target_width_um,
        "diff_length_um": diff_length_um,
        "diff_width_um": diff_width_um,
        "diff_length_px": diff_length_px,
        "diff_width_px": diff_width_px,
        "within_bounds": within_bounds,
        "exact_match": exact_match,
        "mode": mode,
    }


def compute_footprint_penalty_from_polygons(
    polygons: Sequence[np.ndarray],
    target_footprint_um: Tuple[float, float],
    scale_px_per_um: Tuple[float, float],
    mode: str = "exceed",
) -> dict:
    """
    Compute footprint penalty directly from polygon arrays.

    This is more efficient when polygons are already extracted.

    Args:
        polygons: List of polygon point arrays (Nx2, in microns)
        target_footprint_um: (length, width) target footprint in microns
        scale_px_per_um: (sx, sy) pixels per micron from calibration
        mode: Penalty mode - "exceed" (default) or "match"

    Returns:
        Same dict as compute_footprint_penalty()
    """
    if not polygons:
        return {
            "penalty": 0.0,
            "error": "No polygons provided",
            "within_bounds": True,
            "exact_match": False,
        }

    xs = np.concatenate([p[:, 0] for p in polygons])
    ys = np.concatenate([p[:, 1] for p in polygons])
    gds_bbox_um = (
        float(xs.min()),
        float(ys.min()),
        float(xs.max()),
        float(ys.max()),
    )

    return compute_footprint_penalty(gds_bbox_um, target_footprint_um, scale_px_per_um, mode)
