"""Distance-transform geometry over boolean masks. Measure-only.

Ported verbatim from the private library's ``rl/reward/geometry.py`` — the
implementation behind the boundary-chamfer "teacher" term of the shaped
reward that produced the recorded learning runs.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt


def boundary_mask(mask: np.ndarray) -> np.ndarray:
    """1px outline of a boolean mask: ``mask & ~erode(mask)``.

    For a 1px-thin mask, erosion is all-False, so the boundary IS the mask;
    no special case needed.
    """

    return mask & ~binary_erosion(mask)


def chamfer_sym_um(
    mask_a: np.ndarray,
    mask_b: np.ndarray,
    um_per_px: float,
) -> tuple[float, float, float]:
    """Symmetric mean nearest-neighbor distance (µm) between two boolean masks.

    Returns ``(chamfer_um, a_to_b_um, b_to_a_um)``. An empty prediction or an
    empty target returns ``(inf, inf, inf)`` — callers treat that as worst
    case, never as an error.
    """

    if not mask_a.any() or not mask_b.any():
        infinite = float("inf")
        return infinite, infinite, infinite
    dist_to_b = distance_transform_edt(~mask_b)
    dist_to_a = distance_transform_edt(~mask_a)
    a_to_b = float(dist_to_b[mask_a].mean()) * um_per_px
    b_to_a = float(dist_to_a[mask_b].mean()) * um_per_px
    return 0.5 * (a_to_b + b_to_a), a_to_b, b_to_a
