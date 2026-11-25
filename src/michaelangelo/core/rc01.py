"""RC-01: Deterministic Shape-Aware Visual Verification Metric for Calibrated Photonic Rasters.

Pure, symmetric, deterministic metric ``rc01_score(raster_a, raster_b) -> float`` in ``[0, 1]``
designed to satisfy PixCell Research Contract RC-01 (T1-T5) while serving both as an
evaluation verifier and as a dense, anti-shortcut RL/RFT reward signal.

Version ``1.2.0`` calibration refinements over ``1.1.0`` (all strictly symmetric in ``(A, B)``):
  (a) Decouple continuous 10% port-zone fill ratio ``r_fill`` from discrete ``s_port_topo``
      when side port counts match (``k_s(A) == k_s(B)``), keeping ``r_fill`` inside ``s_rim``
      and triggering ``s_topo`` only for catastrophic ``>4x`` arm/whisker collapse
      (``r_fill < 0.25``) or discrete port-count / bay mismatches.
  (b) Full-resolution narrow-band neck erosion on ``>1024px`` canvases (eliminating the
      2-px ``r_neck_phys`` downsampling skip for white-box thin interior whiskers).
  (c) Mild sublinear tempering (``s_cav ** 0.65``) when ``beta1(A) == beta1(B) >= 1`` so
      exact-count cavities with size scaling still degrade strongly without collapsing like
      missing or shifted non-overlapping cavities (``0 ** 0.65 == 0``).

Mathematical Pillars (all strictly symmetric in ``(A, B)``):
  1. Region Fidelity with 1-to-1 Topological Bijection: ``IoU_1to1(A, B)``
  2. Physical-Metric Scale-Normalized Boundary Alignment: arc-length-weighted local
     waveguide-scale F1 (``S_bnd``) + heavy-tailed global Cauchy proximity (``S_far``)
  3. Exact Full-Res Filtered 2D Homology + Uncapped Mass Distribution + Overlap-Gated
     Bijection & Nyquist-Tolerant Cavity Matching + Full-Res Neck & Port-Bay Topology
     (``S_topo``)
  4. Spur-Free Continuous Anisotropic Physical SDF Alignment with Dual-Target-Thickness
     FP Weighting (``S_sdf``) + Tight Inscribed-Radius Thickness Spectrum (``S_width``)
  5. Persistence-Cleaned Four-Side Bounding-Rim Exposure & Port-Zone Alignment (``S_rim``)

Anisotropy & Overflow Guards:
  - Supports arbitrary physical anisotropy via ``pixel_spacing=(dy_um, dx_um)`` or
    ``scale_px_per_um=(scale_x, scale_y)`` (default isotropic ``(1.0, 1.0)``).
  - Supports optional GDS canvas-overflow guard via ``gds_size_um`` / ``footprint_um`` /
    ``canvas_size_um`` and convenience wrapper ``evaluate_rc01_calibrated(...)``.

Dependencies: minimal stdlib + numpy + scipy only (zero learned weights).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy import ndimage
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------
# Frozen RC-01 v1.2.0 hyperparameters (pure constants, zero learned weights)
# ---------------------------------------------------------------------------

RC01_VERSION = "1.2.0"

# Nyquist rasterization jitter coefficient: 1.06066017 * hypot(1, 1) == 1.500 px
# on isotropic grids (covers sqrt(2) ~= 1.414 px 1-px diagonal subpixel uncertainty).
NYQUIST_DIAG_COEFF = 1.5 / math.sqrt(2.0)
NYQUIST_EPS_PX = 1.5

# Working-grid cap per axis for continuous Signed Distance Function (SDF) thickness field.
# Exact IoU, exact 1-px boundaries, exact 4-side rims/port zones, exact 2D homology, and
# narrow-band neck erosion ALWAYS run at full native pixel resolution (when r_neck <= 2.5 px).
SDF_MAX_DIM = 512

# Deterministic cap for boundary point sets passed to cKDTree (guards against
# adversarial 2496x2496 checkerboard DoS attacks while keeping <= 1 px spacing on
# normal photonic devices).
MAX_BOUNDARY_PTS = 32_000

# Hungarian matching cap (top-K largest components/holes matched 1-to-1; true Betti
# counts and mass distributions ALWAYS use the full uncapped filtered lists).
MAX_MATCH_COMPONENTS = 256

# 4-side bounding-rim strip width (pixels on isotropic grids; scaled physically under anisotropy)
# and intrinsic 4-side port-zone depth fraction of each mask's tight bounding box.
RIM_BAND_PX = 3
PORT_ZONE_FRAC = 0.10

# Catastrophic >4x arm/whisker collapse threshold for matching-count port zones in S_port_topo.
# Moderate geometric width differences (r_fill >= 0.25) with matching discrete port counts remain
# smoothly scored in S_rim without tripping the topological S_topo gate.
PORT_FILL_COLLAPSE_THRESHOLD = 0.25

# Mild sublinear tempering exponent on S_cav when beta1(A) == beta1(B) >= 1 so exact-count
# cavities with scale mismatches still degrade strongly while staying distinct from missing
# or non-overlapping shifted cavities (0 ** 0.65 == 0).
CAV_EXACT_BETA1_EXP = 0.65

# Topological Betti penalty parameters:
#   T_k = 1.0 if beta_k(A) == beta_k(B) else exp(-(GAMMA_STEP + GAMMA_REL * rel_diff))
GAMMA_STEP = 0.15
GAMMA_REL = 1.20
ALPHA_TOPO = 0.75

# Geometric-mean core exponents (strictly positive, sum to 1.0)
W_REG = 0.30
W_BND = 0.25
W_SDF = 0.30
W_RIM = 0.15

# Bounded far-field shaping ceiling (guarantees non-vanishing RL gradient at IoU=0
# without allowing any non-overlapping candidate to exceed ETA_SHAPING).
ETA_SHAPING = 0.15

# Global far-field distance scale fraction of physical union bounding-box diagonal
FAR_TAU_FRAC = 0.12

# Dual digital topology structuring elements (2D Jordan Curve Theorem pair:
# 8-connected foreground, 4-connected background), plus exact r=2 Euclidean disk
# (|dy|+|dx| <= 2 <=> dy^2+dx^2 <= 4 on Z^2, identical to two 4-connected erosions).
_STRUCT_4 = ndimage.generate_binary_structure(2, 1)
_STRUCT_8 = ndimage.generate_binary_structure(2, 2)
_DISK_R2 = np.array(
    [
        [False, False, True, False, False],
        [False, True, True, True, False],
        [True, True, True, True, True],
        [False, True, True, True, False],
        [False, False, True, False, False],
    ],
    dtype=np.bool_,
)


@dataclass(frozen=True)
class RC01Breakdown:
    """Full auditable diagnostic breakdown for a single RC-01 evaluation."""

    score: float
    iou_raw: float
    iou_1to1: float
    component_purity: float
    s_bnd: float
    bnd_precision: float
    bnd_recall: float
    s_far: float
    s_sdf: float
    sdf_precision: float
    sdf_recall: float
    s_width: float
    s_rim: float
    rim_sides: tuple[float, float, float, float]
    s_topo: float
    t_beta0: float
    t_beta1: float
    s_mass0: float
    s_bij0: float
    s_cav: float
    s_hole: float
    s_port_topo: float
    t_bay: float
    t_neck: float
    s_geom: float
    s_core: float
    s_shape_far: float
    beta0_a: int
    beta0_b: int
    beta1_a: int
    beta1_b: int
    port_counts_a: tuple[int, int, int, int]
    port_counts_b: tuple[int, int, int, int]
    bay_count_a: int
    bay_count_b: int
    width_a_px: float
    width_b_px: float
    width_star_px: float
    tau_loc_px: float
    tau_far_px: float
    mean_bnd_dist_px: float
    pixel_spacing: tuple[float, float] = (1.0, 1.0)
    overflow_factor: float = 1.0
    overflow_clipped: bool = False
    version: str = RC01_VERSION

    @property
    def s_mat(self) -> float:
        """Backward-compatible alias for continuous medial/SDF thickness fidelity."""
        return self.s_sdf

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _has_grayscale_hint(raster: Any) -> bool:
    """Return True if raster clearly uses 0..255 grayscale convention (PIL or max > 1)."""
    if hasattr(raster, "convert"):
        return True
    arr = np.asarray(raster)
    if arr.dtype == np.bool_:
        return False
    return bool(arr.size > 0 and float(arr.max()) > 1.0)


def _convert_single_mask(
    raster: Any,
    *,
    white_threshold: int,
    mask_mode: str,
    pair_grayscale_hint: bool,
) -> np.ndarray:
    if hasattr(raster, "convert"):
        arr = np.asarray(raster.convert("L"))
        if mask_mode == "bool":
            return arr > 0
        return arr < white_threshold

    arr = np.asarray(raster)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D raster mask, got shape {arr.shape}")
    if arr.dtype == np.bool_:
        return arr

    if mask_mode == "bool":
        return arr > 0
    if mask_mode == "grayscale":
        return arr < white_threshold
    # mask_mode == "auto": symmetric pair-level grayscale detection ensures an all-black
    # uint8 canvas (all 0s) paired with a white/grayscale canvas (max > 1) is properly
    # decoded as full ink rather than empty.
    if pair_grayscale_hint:
        return arr < white_threshold
    return arr > 0


def _as_bool_mask_pair(
    raster_a: Any,
    raster_b: Any,
    *,
    white_threshold: int = 245,
    mask_mode: str = "auto",
) -> tuple[np.ndarray, np.ndarray]:
    """Symmetrically normalize a pair of 2D masks (bool, {0,1}, uint8 grayscale, or PIL)."""
    if mask_mode not in ("auto", "bool", "grayscale"):
        raise ValueError(f"mask_mode must be 'auto', 'bool', or 'grayscale', got {mask_mode!r}")
    pair_gray = _has_grayscale_hint(raster_a) or _has_grayscale_hint(raster_b)
    a = _convert_single_mask(
        raster_a,
        white_threshold=white_threshold,
        mask_mode=mask_mode,
        pair_grayscale_hint=pair_gray,
    )
    b = _convert_single_mask(
        raster_b,
        white_threshold=white_threshold,
        mask_mode=mask_mode,
        pair_grayscale_hint=pair_gray,
    )
    return a, b


def _resolve_pixel_spacing(
    pixel_spacing: tuple[float, float] | None,
    scale_px_per_um: tuple[float, float] | None,
) -> tuple[float, float]:
    """Return physical ``(dy, dx)`` spacing per pixel row/column."""
    if pixel_spacing is not None and scale_px_per_um is not None:
        raise ValueError("Specify at most one of pixel_spacing or scale_px_per_um")
    if scale_px_per_um is not None:
        sx, sy = float(scale_px_per_um[0]), float(scale_px_per_um[1])
        if sx <= 0.0 or sy <= 0.0 or not (math.isfinite(sx) and math.isfinite(sy)):
            raise ValueError(f"scale_px_per_um must be positive finite, got {scale_px_per_um}")
        return (1.0 / sy, 1.0 / sx)
    if pixel_spacing is not None:
        dy, dx = float(pixel_spacing[0]), float(pixel_spacing[1])
        if dy <= 0.0 or dx <= 0.0 or not (math.isfinite(dy) and math.isfinite(dx)):
            raise ValueError(f"pixel_spacing must be positive finite, got {pixel_spacing}")
        return (dy, dx)
    return (1.0, 1.0)


def _compute_overflow_factor(
    *,
    gds_size_um: tuple[float, float] | None,
    footprint_um: tuple[float, float] | None,
    canvas_size_um: tuple[float, float] | None,
    shape_hw: tuple[int, int],
    pixel_spacing: tuple[float, float],
    has_physical_scale: bool,
) -> tuple[float, bool]:
    """Optional guard against silent canvas-frame clipping in ``compare_absolute.py``."""
    if gds_size_um is None:
        return 1.0, False
    gw, gh = float(gds_size_um[0]), float(gds_size_um[1])
    if math.isnan(gw) or math.isnan(gh):
        raise ValueError(f"gds_size_um must not be NaN, got {gds_size_um}")
    if gw <= 0.0 or gh <= 0.0:
        return 0.0, True

    if canvas_size_um is not None:
        aw, ah = float(canvas_size_um[0]), float(canvas_size_um[1])
    elif has_physical_scale:
        dy, dx = pixel_spacing
        aw, ah = shape_hw[1] * dx, shape_hw[0] * dy
    elif footprint_um is not None:
        aw, ah = float(footprint_um[0]), float(footprint_um[1])
    else:
        raise ValueError(
            "gds_size_um requires canvas_size_um, footprint_um, or physical "
            "scale_px_per_um/pixel_spacing"
        )
    if aw <= 0.0 or ah <= 0.0 or not (math.isfinite(aw) and math.isfinite(ah)):
        raise ValueError(f"canvas/footprint size must be positive finite, got {(aw, ah)}")

    tol_w = max(0.05, 0.01 * aw)
    tol_h = max(0.05, 0.01 * ah)
    rx = 1.0 if gw <= aw + tol_w else aw / gw
    ry = 1.0 if gh <= ah + tol_h else ah / gh
    factor = float(min(1.0, max(0.0, rx * ry)))
    return factor, factor < 1.0


def _crop_union(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Crop both masks tightly to the union bounding box with a 1-px empty border."""
    union = a | b
    ys = np.flatnonzero(union.any(axis=1))
    xs = np.flatnonzero(union.any(axis=0))
    y0, y1 = int(ys[0]), int(ys[-1]) + 1
    x0, x1 = int(xs[0]), int(xs[-1]) + 1
    ac = np.pad(a[y0:y1, x0:x1], 1, mode="constant", constant_values=False)
    bc = np.pad(b[y0:y1, x0:x1], 1, mode="constant", constant_values=False)
    return ac, bc


def _min_topo_area(fg_area: int) -> int:
    """Self-relative persistence area threshold filtering 1-px aliasing debris."""
    if fg_area <= 0:
        return 1
    return min(max(9, fg_area // 10_000), max(1, fg_area // 100))


def _analyze_topology(
    mask: np.ndarray,
) -> tuple[
    np.ndarray,
    int,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    int,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Fast full-res filtered 2D homology with UNCAPPED true Betti counts & mass vectors.

    Returns:
      ``(raw_fg, raw_n_fg, fg_all_ids, fg_match_ids, fg_all_areas,
         raw_bg, raw_n_bg, hole_all_ids, hole_match_ids, hole_all_areas)``
    """
    fg_area = int(np.count_nonzero(mask))
    a_min = _min_topo_area(fg_area)

    # Foreground: 8-connectivity
    raw_fg, raw_n_fg = ndimage.label(mask, structure=_STRUCT_8)
    if raw_n_fg == 0:
        fg_all_ids = np.empty(0, dtype=np.int32)
        fg_all_areas = np.empty(0, dtype=np.int64)
    elif raw_n_fg == 1:
        fg_all_ids = np.array([1], dtype=np.int32)
        fg_all_areas = np.array([fg_area], dtype=np.int64)
    else:
        counts = np.bincount(raw_fg.ravel(), minlength=raw_n_fg + 1)
        keep = np.flatnonzero(counts[1:] >= a_min) + 1
        if keep.size == 0:
            keep = np.array([int(np.argmax(counts[1:])) + 1], dtype=np.int64)
        areas = counts[keep]
        order = np.argsort(-areas, kind="mergesort")
        fg_all_ids = keep[order].astype(np.int32)
        fg_all_areas = areas[order].astype(np.int64)
    fg_match_ids = fg_all_ids[:MAX_MATCH_COMPONENTS]

    # Bounded holes: 4-connectivity on complement (1-px False border guarantees 1 exterior)
    raw_bg, raw_n_bg = ndimage.label(~mask, structure=_STRUCT_4)
    if raw_n_bg <= 1:
        hole_all_ids = np.empty(0, dtype=np.int32)
        hole_all_areas = np.empty(0, dtype=np.int64)
    else:
        ext_label = int(raw_bg[0, 0])
        bg_counts = np.bincount(raw_bg.ravel(), minlength=raw_n_bg + 1)
        bg_counts[0] = 0
        bg_counts[ext_label] = 0
        keep_h = np.flatnonzero(bg_counts >= a_min)
        if keep_h.size == 0:
            hole_all_ids = np.empty(0, dtype=np.int32)
            hole_all_areas = np.empty(0, dtype=np.int64)
        else:
            h_areas = bg_counts[keep_h]
            order_h = np.argsort(-h_areas, kind="mergesort")
            hole_all_ids = keep_h[order_h].astype(np.int32)
            hole_all_areas = h_areas[order_h].astype(np.int64)
    hole_match_ids = hole_all_ids[:MAX_MATCH_COMPONENTS]

    return (
        raw_fg,
        int(raw_n_fg),
        fg_all_ids,
        fg_match_ids,
        fg_all_areas,
        raw_bg,
        int(raw_n_bg),
        hole_all_ids,
        hole_match_ids,
        hole_all_areas,
    )


def _filtered_fg_mask(
    mask: np.ndarray,
    raw_fg: np.ndarray,
    raw_n_fg: int,
    fg_all_ids: np.ndarray,
) -> np.ndarray:
    """Return persistence-filtered foreground mask (zero copy when no debris was dropped)."""
    if raw_n_fg == int(fg_all_ids.size):
        return mask
    keep_lut = np.zeros(raw_n_fg + 1, dtype=np.bool_)
    keep_lut[fg_all_ids] = True
    return keep_lut[raw_fg]


def _fast_dilate_8(mask: np.ndarray) -> np.ndarray:
    """1-pixel 8-connected dilation (Nyquist tolerance band) via fast numpy slicing."""
    out = mask.copy()
    out[1:-1, 1:-1] |= (
        mask[:-2, :-2]
        | mask[:-2, 1:-1]
        | mask[:-2, 2:]
        | mask[1:-1, :-2]
        | mask[1:-1, 2:]
        | mask[2:, :-2]
        | mask[2:, 1:-1]
        | mask[2:, 2:]
    )
    return out


def _fast_erode_4(mask: np.ndarray) -> np.ndarray:
    """Exact 1-pixel 4-connected erosion (Euclidean disk d <= 1) via fast numpy slicing."""
    out = np.zeros_like(mask)
    out[1:-1, 1:-1] = (
        mask[1:-1, 1:-1]
        & mask[:-2, 1:-1]
        & mask[2:, 1:-1]
        & mask[1:-1, :-2]
        & mask[1:-1, 2:]
    )
    return out


def _fast_erode_8(mask: np.ndarray) -> np.ndarray:
    """Exact 1-pixel 8-connected erosion (Euclidean disk d <= sqrt(2)) via fast numpy slicing."""
    out = np.zeros_like(mask)
    out[1:-1, 1:-1] = (
        mask[1:-1, 1:-1]
        & mask[:-2, :-2]
        & mask[:-2, 1:-1]
        & mask[:-2, 2:]
        & mask[1:-1, :-2]
        & mask[1:-1, 2:]
        & mask[2:, :-2]
        & mask[2:, 1:-1]
        & mask[2:, 2:]
    )
    return out


def _matched_fg_overlap(
    raw_a: np.ndarray,
    raw_na: int,
    match_a: np.ndarray,
    raw_b: np.ndarray,
    raw_nb: int,
    match_b: np.ndarray,
    overlap_mask: np.ndarray,
    inter: int,
) -> int:
    """Exact 1-to-1 maximum-weight bipartite overlap between top-K filtered components."""
    na, nb = int(match_a.size), int(match_b.size)
    if na == 0 or nb == 0 or inter == 0:
        return 0
    if na == 1 and nb == 1 and raw_na == 1 and raw_nb == 1:
        return inter

    remap_a = np.zeros(raw_na + 1, dtype=np.int32)
    remap_a[match_a] = np.arange(1, na + 1, dtype=np.int32)
    remap_b = np.zeros(raw_nb + 1, dtype=np.int32)
    remap_b[match_b] = np.arange(1, nb + 1, dtype=np.int32)

    la = remap_a[raw_a[overlap_mask]]
    lb = remap_b[raw_b[overlap_mask]]
    valid = (la > 0) & (lb > 0)
    if not valid.any():
        return 0
    la = la[valid].astype(np.int64, copy=False)
    lb = lb[valid].astype(np.int64, copy=False)

    stride = nb + 1
    hist = np.bincount(la * stride + lb, minlength=(na + 1) * stride)
    mat = hist.reshape(na + 1, stride)[1:, 1:]
    if na == 1 and nb == 1:
        return int(mat[0, 0])
    row_ind, col_ind = linear_sum_assignment(-mat)
    return int(mat[row_ind, col_ind].sum())


def _nyquist_hole_agreement(
    raw_bg_a: np.ndarray,
    raw_nba: int,
    match_a: np.ndarray,
    all_areas_a: np.ndarray,
    raw_bg_b: np.ndarray,
    raw_nbb: int,
    match_b: np.ndarray,
    all_areas_b: np.ndarray,
) -> float:
    """Symmetric 1-to-1 Nyquist-tolerant (1-px) hole agreement in [0, 1]."""
    na, nb = int(match_a.size), int(match_b.size)
    tot_a = float(all_areas_a.sum())
    tot_b = float(all_areas_b.sum())
    if all_areas_a.size == 0 and all_areas_b.size == 0:
        return 1.0
    if all_areas_a.size == 0 or all_areas_b.size == 0 or tot_a <= 0.0 or tot_b <= 0.0:
        return 0.0

    # Fast exact path for single-hole devices (rings, scaffolds, slot crossings)
    if all_areas_a.size == 1 and all_areas_b.size == 1:
        ha = raw_bg_a == match_a[0]
        hb = raw_bg_b == match_b[0]
        inter_exact = int(np.count_nonzero(ha & hb))
        if inter_exact == 0:
            return 0.0
        a_in_b1 = int(np.count_nonzero(ha & _fast_dilate_8(hb)))
        b_in_a1 = int(np.count_nonzero(hb & _fast_dilate_8(ha)))
        return _harmonic_mean(a_in_b1 / tot_a, b_in_a1 / tot_b)

    lut_a = np.zeros(raw_nba + 1, dtype=np.int32)
    lut_a[match_a] = np.arange(1, na + 1, dtype=np.int32)
    lut_b = np.zeros(raw_nbb + 1, dtype=np.int32)
    lut_b[match_b] = np.arange(1, nb + 1, dtype=np.int32)

    ma = lut_a[raw_bg_a]
    mb = lut_b[raw_bg_b]
    both = (ma > 0) & (mb > 0)
    if not both.any():
        return 0.0

    la = ma[both].astype(np.int64, copy=False)
    lb = mb[both].astype(np.int64, copy=False)
    stride = nb + 1
    hist = np.bincount(la * stride + lb, minlength=(na + 1) * stride)
    mat = hist.reshape(na + 1, stride)[1:, 1:]
    row_ind, col_ind = linear_sum_assignment(-mat)

    pair_b_for_a = np.zeros(na + 1, dtype=np.int32)
    pair_a_for_b = np.zeros(nb + 1, dtype=np.int32)
    for r, c in zip(row_ind, col_ind, strict=True):
        if mat[r, c] > 0:
            pair_b_for_a[r + 1] = c + 1
            pair_a_for_b[c + 1] = r + 1

    target_b = pair_b_for_a[ma]
    hit_a = (target_b > 0) & (
        (mb == target_b)
        | (np.roll(mb, 1, axis=0) == target_b)
        | (np.roll(mb, -1, axis=0) == target_b)
        | (np.roll(mb, 1, axis=1) == target_b)
        | (np.roll(mb, -1, axis=1) == target_b)
        | (np.roll(np.roll(mb, 1, axis=0), 1, axis=1) == target_b)
        | (np.roll(np.roll(mb, 1, axis=0), -1, axis=1) == target_b)
        | (np.roll(np.roll(mb, -1, axis=0), 1, axis=1) == target_b)
        | (np.roll(np.roll(mb, -1, axis=0), -1, axis=1) == target_b)
    )
    target_a = pair_a_for_b[mb]
    hit_b = (target_a > 0) & (
        (ma == target_a)
        | (np.roll(ma, 1, axis=0) == target_a)
        | (np.roll(ma, -1, axis=0) == target_a)
        | (np.roll(ma, 1, axis=1) == target_a)
        | (np.roll(ma, -1, axis=1) == target_a)
        | (np.roll(np.roll(ma, 1, axis=0), 1, axis=1) == target_a)
        | (np.roll(np.roll(ma, 1, axis=0), -1, axis=1) == target_a)
        | (np.roll(np.roll(ma, -1, axis=0), 1, axis=1) == target_a)
        | (np.roll(np.roll(ma, -1, axis=0), -1, axis=1) == target_a)
    )

    prec = int(np.count_nonzero(hit_a)) / tot_a
    rec = int(np.count_nonzero(hit_b)) / tot_b
    return _harmonic_mean(prec, rec)


def _mass_distribution_similarity(areas_a: np.ndarray, areas_b: np.ndarray) -> float:
    """1 - TV distance between sorted normalized component/hole mass distributions."""
    if areas_a.size == 0 and areas_b.size == 0:
        return 1.0
    if areas_a.size == 0 or areas_b.size == 0:
        return 0.0
    pa = areas_a.astype(np.float64) / float(areas_a.sum())
    pb = areas_b.astype(np.float64) / float(areas_b.sum())
    k = max(pa.size, pb.size)
    va = np.zeros(k, dtype=np.float64)
    vb = np.zeros(k, dtype=np.float64)
    va[: pa.size] = pa
    vb[: pb.size] = pb
    return float(max(0.0, 1.0 - 0.5 * np.abs(va - vb).sum()))


def _betti_score(b_a: int, b_b: int) -> float:
    if b_a == b_b:
        return 1.0
    rel = abs(b_a - b_b) / max(b_a, b_b, 1)
    return float(math.exp(-(GAMMA_STEP + GAMMA_REL * rel)))


def _boundary_points_and_arc_weights(
    mask: np.ndarray,
    dy: float,
    dx: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact 1-px inner boundary coordinates in physical units + physical arc-length weights.

    A horizontal exposed face contributes physical length ``dx`` and a vertical exposed face
    contributes ``dy``, yielding ``w = hypot(n_tb * dx, n_lr * dy)`` so anisotropic grids
    (up to 25.94x on PixCell benchmarks F1-F8) weight boundary length in true physical um.
    """
    inner = mask[1:-1, 1:-1]
    eroded = (
        inner
        & mask[:-2, 1:-1]
        & mask[2:, 1:-1]
        & mask[1:-1, :-2]
        & mask[1:-1, 2:]
    )
    iy, ix = np.nonzero(inner & ~eroded)
    y = iy + 1
    x = ix + 1
    pts = np.empty((iy.size, 2), dtype=np.float64)
    pts[:, 0] = y * dy
    pts[:, 1] = x * dx
    # Evaluate 4-neighbor exposure ONLY at boundary coordinates (~0.5% of canvas pixels).
    n_tb = (~mask[y - 1, x]).astype(np.float64) + (~mask[y + 1, x]).astype(np.float64)
    n_lr = (~mask[y, x - 1]).astype(np.float64) + (~mask[y, x + 1]).astype(np.float64)
    w_arc = np.hypot(n_tb * dx, n_lr * dy)
    return pts, w_arc


def _count_bbox_bays(ds_mask: np.ndarray) -> int:
    """Fast 2D tight-bbox void/bay count inside ``BBox(M) \\ M`` on the SDF working grid.

    Applies a 1-cell 4-connected morphological opening to ``~sub`` so 1-cell grazing
    corridors along the tight bounding-box edge cannot randomly merge adjacent corner
    bays under 1-px GT rasterization jitter, while preserving all real >=2-cell bays.
    """
    ys = np.flatnonzero(ds_mask.any(axis=1))
    xs = np.flatnonzero(ds_mask.any(axis=0))
    if ys.size == 0 or xs.size == 0:
        return 0
    sub = ds_mask[int(ys[0]) : int(ys[-1]) + 1, int(xs[0]) : int(xs[-1]) + 1]
    fg_cells = int(np.count_nonzero(sub))
    a_min_bay = max(4, fg_cells // 2000)
    void = ndimage.binary_opening(~sub, structure=_STRUCT_4)
    lbl_v, n_v = ndimage.label(void, structure=_STRUCT_4)
    if n_v == 0:
        return 0
    v_cnts = np.bincount(lbl_v.ravel(), minlength=n_v + 1)[1:]
    return int(np.count_nonzero(v_cnts >= a_min_bay))


def _analyze_ports(
    mask_clean: np.ndarray,
    dy: float,
    dx: float,
) -> tuple[
    tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    tuple[int, int, int, int],
    tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]:
    """Extract persistence-cleaned 4-side bounding-rim points, intrinsic 10% port-zone
    component signatures, and normalized port-zone fill fractions.

    All intrinsic signatures are strictly translation-invariant and scale/anisotropy-invariant.
    """
    ys = np.flatnonzero(mask_clean.any(axis=1))
    xs = np.flatnonzero(mask_clean.any(axis=0))
    y0, y1 = int(ys[0]), int(ys[-1]) + 1
    x0, x1 = int(xs[0]), int(xs[-1]) + 1
    sub = mask_clean[y0:y1, x0:x1]
    sh, sw = sub.shape

    band_phys = RIM_BAND_PX * max(dx, dy)
    bx = min(max(RIM_BAND_PX, int(round(band_phys / dx))), max(RIM_BAND_PX, sw // 20), sw)
    by = min(max(RIM_BAND_PX, int(round(band_phys / dy))), max(RIM_BAND_PX, sh // 20), sh)

    def _rim_phys(region: np.ndarray, oy: int, ox: int) -> np.ndarray:
        iy, ix = np.nonzero(region)
        pts = np.empty((iy.size, 2), dtype=np.float64)
        pts[:, 0] = (iy + oy) * dy
        pts[:, 1] = (ix + ox) * dx
        return pts

    rim_pts = (
        _rim_phys(sub[:, :bx], y0, x0),
        _rim_phys(sub[:, sw - bx :], y0, x0 + sw - bx),
        _rim_phys(sub[:by, :], y0, x0),
        _rim_phys(sub[sh - by :, :], y0 + sh - by, x0),
    )

    zx = max(bx, int(round(PORT_ZONE_FRAC * sw)))
    zy = max(by, int(round(PORT_ZONE_FRAC * sh)))
    zones = (sub[:, :zx], sub[:, sw - zx :], sub[:zy, :], sub[sh - zy :, :])
    rim_projs = (
        (sub[:, :bx].any(axis=1), dy),
        (sub[:, sw - bx :].any(axis=1), dy),
        (sub[:by, :].any(axis=0), dx),
        (sub[sh - by :, :].any(axis=0), dx),
    )

    port_counts_list: list[int] = []
    port_areas_list: list[np.ndarray] = []
    zone_fills_list: list[float] = []
    zone_tols_list: list[float] = []

    close_phys = 2.0 * max(dx, dy)
    for (proj, step_axis), zone in zip(rim_projs, zones, strict=True):
        close_rad = max(1, min(4, int(round(close_phys / step_axis)), max(1, proj.size // 40)))
        if proj.size > 2 * close_rad + 1:
            proj_c = ndimage.binary_closing(
                proj, structure=np.ones(2 * close_rad + 1, dtype=bool)
            )
        else:
            proj_c = proj
        lbl1d, n1d = ndimage.label(proj_c)
        if n1d > 0:
            cnts1d = np.bincount(lbl1d)[1:]
            min_seg = max(2, int(0.005 * proj.size))
            keep1d = cnts1d[cnts1d >= min_seg]
            if keep1d.size == 0:
                keep1d = np.array([int(cnts1d.max())], dtype=np.int64)
            keep1d = np.sort(keep1d)[::-1].astype(np.int64)
            port_counts_list.append(int(keep1d.size))
            port_areas_list.append(keep1d)
        else:
            port_counts_list.append(0)
            port_areas_list.append(np.empty(0, dtype=np.int64))

        z_fg = int(np.count_nonzero(zone))
        z_tot = max(1, zone.size)
        zone_fills_list.append(z_fg / float(z_tot))
        zp = np.pad(zone, 1, mode="constant", constant_values=False)
        z_perim = int(
            np.count_nonzero(
                zone
                & (
                    ~zp[:-2, 1:-1]
                    | ~zp[2:, 1:-1]
                    | ~zp[1:-1, :-2]
                    | ~zp[1:-1, 2:]
                )
            )
        )
        # 1-px Nyquist perimeter band (covers >=1.9x worst-case GT rasterization jitter
        # without inflating collapsed 1-px whiskers above the 0.25 catastrophic threshold).
        zone_tols_list.append(float(z_perim) / float(z_tot))

    return (
        rim_pts,
        (port_counts_list[0], port_counts_list[1], port_counts_list[2], port_counts_list[3]),
        (port_areas_list[0], port_areas_list[1], port_areas_list[2], port_areas_list[3]),
        (zone_fills_list[0], zone_fills_list[1], zone_fills_list[2], zone_fills_list[3]),
        (zone_tols_list[0], zone_tols_list[1], zone_tols_list[2], zone_tols_list[3]),
    )


def _neck_eroded_beta0_from_sdf(
    r_in: np.ndarray,
    r_neck_phys: float,
) -> int:
    """Fast filtered connected-component count of the core ``r_in > r_neck_phys`` on the SDF grid.

    Snaps thin whisker/hairline bridges in ~1.5 ms while leaving real photonic waveguides invariant.
    """
    core = r_in > r_neck_phys
    if not core.any():
        return 0
    fg_cells = int(np.count_nonzero(core))
    a_min = min(max(3, fg_cells // 2000), max(1, fg_cells // 100))
    lbl, n = ndimage.label(core, structure=_STRUCT_8)
    if n <= 1:
        return int(n)
    cnts = np.bincount(lbl.ravel(), minlength=n + 1)[1:]
    keep = int(np.count_nonzero(cnts >= a_min))
    return max(1, keep)


def _neck_eroded_beta0_fullres(
    mask_clean: np.ndarray,
    r_neck_phys: float,
    dy: float,
    dx: float,
) -> int:
    """Exact full-resolution narrow-band neck erosion.

    Removes the ``>1024px`` downsampling skip so white-box thin interior whiskers (1-4 px)
    on ``1440px`` / ``2496px`` canvases (including mildly anisotropic calibrated grids) are
    snapped cleanly at native resolution. Because ``mask_clean`` carries a 1-px False border
    from ``_crop_union``, exact lattice matches to ``_STRUCT_4`` (``d^2 <= 1``), ``_STRUCT_8``
    (``d^2 <= 2``), and ``_DISK_R2`` (``d^2 <= 4``, ``2x _fast_erode_4``) dispatch to fast
    vectorized slicing even when integer pixel-bbox calibration introduces tiny ``dx != dy``
    rounding differences.
    """
    ry = int(math.floor(r_neck_phys / dy + 1e-12))
    rx = int(math.floor(r_neck_phys / dx + 1e-12))
    if ry == 0 and rx == 0:
        return 0

    oy = np.arange(-ry, ry + 1, dtype=np.float64)[:, None] * dy
    ox = np.arange(-rx, rx + 1, dtype=np.float64)[None, :] * dx
    struct = np.hypot(oy, ox) <= (r_neck_phys + 1e-12)

    if struct.shape == (5, 5) and np.array_equal(struct, _DISK_R2):
        core = _fast_erode_4(_fast_erode_4(mask_clean))
    elif struct.shape == (3, 3) and np.array_equal(struct, _STRUCT_8):
        core = _fast_erode_8(mask_clean)
    elif struct.shape == (3, 3) and np.array_equal(struct, _STRUCT_4):
        core = _fast_erode_4(mask_clean)
    else:
        core = ndimage.binary_erosion(mask_clean, structure=struct, border_value=0)

    if not core.any():
        return 0
    fg = int(np.count_nonzero(core))
    a_min = _min_topo_area(fg)
    lbl, n = ndimage.label(core, structure=_STRUCT_8)
    if n <= 1:
        return int(n)
    cnts = np.bincount(lbl.ravel(), minlength=n + 1)[1:]
    keep = int(np.count_nonzero(cnts >= a_min))
    return max(1, keep)


def _compute_neck_score(
    a_clean: np.ndarray,
    b_clean: np.ndarray,
    r_in_a: np.ndarray,
    r_in_b: np.ndarray,
    *,
    width_star: float,
    sy_s: int,
    sx_s: int,
    dy: float,
    dx: float,
) -> float:
    """Compute structural neck connectivity ``t_neck`` without skipping ``>1024px`` canvases."""
    r_neck_phys = min(0.12 * width_star, 2.0 * max(dy, dx))
    if r_neck_phys < min(dy, dx) - 1e-12:
        return 1.0

    min_sdf_cell = min(sy_s * dy, sx_s * dx)
    max_px_radius = max(r_neck_phys / dy, r_neck_phys / dx)

    # Exact full-resolution narrow-band erosion covers all isotropic canvases of arbitrary
    # size AND closes the mild-to-moderate anisotropy dead zone where the SDF grid is too
    # coarse to resolve r_neck_phys (e.g., 1.25:1-1.87:1 on 2496px canvases).
    if max_px_radius <= 2.5 + 1e-9 or (
        r_neck_phys < 0.75 * min_sdf_cell and max_px_radius <= 8.0 + 1e-9
    ):
        bn_a = _neck_eroded_beta0_fullres(a_clean, r_neck_phys, dy, dx)
        bn_b = _neck_eroded_beta0_fullres(b_clean, r_neck_phys, dy, dx)
        return _betti_score(bn_a, bn_b)

    # Severe physical anisotropy (e.g., 10:1 or 25:1) where the fine axis spans >2.5 px:
    # the physical-sampling SDF working grid already resolves r_neck_phys cleanly.
    if r_neck_phys >= 0.75 * min_sdf_cell:
        bn_a = _neck_eroded_beta0_from_sdf(r_in_a, r_neck_phys)
        bn_b = _neck_eroded_beta0_from_sdf(r_in_b, r_neck_phys)
        return _betti_score(bn_a, bn_b)
    return 1.0


def _downsample_for_sdf(
    mask: np.ndarray,
    stride_y: int,
    stride_x: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic anisotropic block downsampling returning ``(binary_core, cell_density)``."""
    if stride_y <= 1 and stride_x <= 1:
        return mask, mask.astype(np.float32)
    h, w = mask.shape
    pad_h = (-h) % stride_y
    pad_w = (-w) % stride_x
    if pad_h or pad_w:
        m = np.pad(mask, ((0, pad_h), (0, pad_w)), mode="constant", constant_values=False)
    else:
        m = mask
    nh, nw = m.shape[0] // stride_y, m.shape[1] // stride_x
    density = m.reshape(nh, stride_y, nw, stride_x).mean(axis=(1, 3), dtype=np.float32)
    ds = density >= 0.5
    if not ds.any():
        ds = density > 0.0
    return ds, density


def _compute_sdf_and_width(
    mask: np.ndarray,
    stride_y: int,
    stride_x: int,
    dy: float,
    dx: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, np.ndarray]:
    """Compute physical 1-Lipschitz continuous Signed Distance Function and thickness spectrum.

    Supports arbitrary physical anisotropy via ``sampling=(stride_y * dy, stride_x * dx)``,
    and preserves isolated thin sub-stride filaments (e.g., 1-px whiskers) in ``ds_eval``
    so sub-stride exploits can never hide beneath ``density >= 0.5``.
    """
    ds_core, density = _downsample_for_sdf(mask, stride_y, stride_x)
    sy_ds = stride_y * dy
    sx_ds = stride_x * dx
    min_cell = min(sy_ds, sx_ds)

    # Pad ds_core with 1-cell False border so EDT measures true boundary distance even on
    # edge-touching high-aspect bars (e.g., L1 06b88ff9).
    edt_in = ndimage.distance_transform_edt(
        np.pad(ds_core, 1, mode="constant", constant_values=False),
        sampling=(sy_ds, sx_ds),
    )[1:-1, 1:-1]
    edt_out = ndimage.distance_transform_edt(~ds_core, sampling=(sy_ds, sx_ds))

    # Sub-cell density attenuation on thin 1-cell boundary/stick features
    r_in = np.where(
        (edt_in > 0.0) & (edt_in <= 1.05 * max(sy_ds, sx_ds)),
        edt_in * np.minimum(density.astype(np.float64), 1.0),
        edt_in,
    )

    # Preserve isolated sub-stride thin filaments (density > 0 detached from ds_core)
    if stride_y > 1 or stride_x > 1:
        core_dil = _fast_dilate_8(
            np.pad(ds_core, 1, mode="constant", constant_values=False)
        )[1:-1, 1:-1]
        ds_thin = (density > 0.0) & ~core_dil
        ds_eval = ds_core | ds_thin
        if ds_thin.any():
            r_in = np.where(ds_thin, density.astype(np.float64) * min_cell, r_in)
            r_out = np.where(ds_thin, 0.0, edt_out)
        else:
            r_out = edt_out
    else:
        ds_eval = ds_core
        r_out = edt_out

    sdf = r_in - r_out

    fg_r = r_in[ds_eval]
    if fg_r.size > 0:
        qs = np.percentile(fg_r, [25, 35, 50, 75, 90])
        char_width = float(4.0 * qs[1])
        width_quantiles = np.maximum(0.5 * min(dy, dx), 2.0 * qs[[0, 2, 3, 4]])
    else:
        char_width = min(dy, dx)
        width_quantiles = np.full(4, min(dy, dx), dtype=np.float64)
    return ds_eval, r_in, sdf, max(min(dy, dx), char_width), width_quantiles


def _width_spectrum_similarity(
    wq_a: np.ndarray, wq_b: np.ndarray, eps_phys: float
) -> float:
    """Symmetric rigid-motion-invariant thickness-spectrum similarity in (0, 1]."""
    lo = np.minimum(wq_a, wq_b)
    hi = np.maximum(wq_a, wq_b)
    adj_lo = np.minimum(hi, lo + eps_phys)
    ratios = adj_lo / np.maximum(hi, 1e-12)
    return float(np.prod(ratios) ** (1.0 / ratios.size))


def _directed_sdf_alignment(
    src_mask: np.ndarray,
    src_r_in: np.ndarray,
    src_sdf: np.ndarray,
    dst_r_in: np.ndarray,
    dst_sdf: np.ndarray,
    width_star: float,
    eps_sdf: float,
    min_sigma: float,
) -> float:
    """Symmetric, un-inflatable continuous SDF alignment with Dual-Target-Thickness FP weighting.

    Properties:
      1. 1-Lipschitz continuous under Hausdorff boundary jitter (ZERO skeleton spurs).
      2. Dual-Target-Thickness FP weighting: false-positive pixels (``dst_r_in == 0``) are
         weighted by the *target's void distance* ``|dst_sdf|`` (capped at ``0.5 * width_star``),
         NEVER by the candidate's own thickness ``src_r_in`` — preventing fat solid blobs
         from discounting their own false-positive interior while heavily penalizing FPs
         inside narrow coupling gaps and ring cavities.
      3. Gentle bounded thickness-weight dynamic range ``[0.25, 0.75] * width_star`` avoids
         giving the outer 2-px skin of a giant solid disk a 6x bonus over its FP core.
    """
    r_src = src_r_in[src_mask]
    r_dst = dst_r_in[src_mask]
    sdf_d = dst_sdf[src_mask]
    diff = np.abs(src_sdf[src_mask] - sdf_d)
    err = np.maximum(0.0, diff - eps_sdf)

    # Local tolerance scale: never inflated by a fat FP blob's own r_src
    r_eff = np.where(
        r_dst > 0.0,
        np.minimum(r_src, r_dst),
        np.minimum(np.abs(sdf_d), 0.50 * width_star),
    )
    local_scale = np.maximum(min_sigma, 0.50 * r_eff)
    match = np.exp(-err / local_scale)

    # Dual-target-thickness weight: TPs use min(r_src, r_dst); FPs use target void |dst_sdf|
    w_lo = max(min_sigma, 0.25 * width_star)
    w_hi = max(w_lo, 0.75 * width_star)
    r_weight = np.where(
        r_dst > 0.0,
        np.minimum(r_src, r_dst),
        np.minimum(np.abs(sdf_d), 0.50 * width_star),
    )
    weights = 1.0 / np.clip(r_weight, w_lo, w_hi)
    return float(np.dot(match, weights) / weights.sum())


def _subsample_pts_and_weights(
    pts: np.ndarray,
    weights: np.ndarray | None = None,
    cap: int = MAX_BOUNDARY_PTS,
) -> tuple[np.ndarray, np.ndarray | None]:
    if pts.shape[0] <= cap:
        return pts, weights
    step = int(math.ceil(pts.shape[0] / cap))
    return pts[::step], (weights[::step] if weights is not None else None)


def _bidirectional_point_distances(
    pts_a: np.ndarray,
    pts_b: np.ndarray,
    w_a: np.ndarray | None = None,
    w_b: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    pa, wa = _subsample_pts_and_weights(pts_a, w_a)
    pb, wb = _subsample_pts_and_weights(pts_b, w_b)
    d_a2b, _ = cKDTree(pb).query(pa, workers=1)
    d_b2a, _ = cKDTree(pa).query(pb, workers=1)
    return d_a2b, d_b2a, wa, wb


def _weighted_mean(values: np.ndarray, weights: np.ndarray | None) -> float:
    if weights is None:
        return float(values.mean())
    w_sum = float(weights.sum())
    if w_sum <= 1e-15:
        return float(values.mean())
    return float(np.dot(values, weights) / w_sum)


def _harmonic_mean(a: float, b: float) -> float:
    denom = a + b
    return (2.0 * a * b / denom) if denom > 1e-15 else 0.0


def evaluate_rc01(
    raster_a: Any,
    raster_b: Any,
    *,
    white_threshold: int = 245,
    mask_mode: str = "auto",
    pixel_spacing: tuple[float, float] | None = None,
    scale_px_per_um: tuple[float, float] | None = None,
    gds_size_um: tuple[float, float] | None = None,
    footprint_um: tuple[float, float] | None = None,
    canvas_size_um: tuple[float, float] | None = None,
) -> RC01Breakdown:
    """Compute RC-01 v1.2.0 score and full diagnostic breakdown for two calibrated rasters."""
    a_full, b_full = _as_bool_mask_pair(
        raster_a, raster_b, white_threshold=white_threshold, mask_mode=mask_mode
    )
    if a_full.shape != b_full.shape:
        raise ValueError(
            f"Calibrated rasters must share exact canvas shape: {a_full.shape} != {b_full.shape}"
        )

    has_phys_scale = (pixel_spacing is not None) or (scale_px_per_um is not None)
    dy, dx = _resolve_pixel_spacing(pixel_spacing, scale_px_per_um)
    min_step = min(dy, dx)
    nyq_phys = NYQUIST_DIAG_COEFF * math.hypot(dy, dx)

    overflow_factor, overflow_clipped = _compute_overflow_factor(
        gds_size_um=gds_size_um,
        footprint_um=footprint_um,
        canvas_size_um=canvas_size_um,
        shape_hw=(int(a_full.shape[0]), int(a_full.shape[1])),
        pixel_spacing=(dy, dx),
        has_physical_scale=has_phys_scale,
    )

    a_any = bool(a_full.any())
    b_any = bool(b_full.any())
    if not a_any and not b_any:
        s_out = float(overflow_factor)
        return RC01Breakdown(
            score=s_out, iou_raw=1.0, iou_1to1=1.0, component_purity=1.0,
            s_bnd=1.0, bnd_precision=1.0, bnd_recall=1.0, s_far=1.0,
            s_sdf=1.0, sdf_precision=1.0, sdf_recall=1.0, s_width=1.0,
            s_rim=1.0, rim_sides=(1.0, 1.0, 1.0, 1.0),
            s_topo=1.0, t_beta0=1.0, t_beta1=1.0, s_mass0=1.0, s_bij0=1.0,
            s_cav=1.0, s_hole=1.0, s_port_topo=1.0, t_bay=1.0, t_neck=1.0,
            s_geom=1.0, s_core=s_out, s_shape_far=s_out,
            beta0_a=0, beta0_b=0, beta1_a=0, beta1_b=0,
            port_counts_a=(0, 0, 0, 0), port_counts_b=(0, 0, 0, 0),
            bay_count_a=0, bay_count_b=0,
            width_a_px=0.0, width_b_px=0.0, width_star_px=0.0,
            tau_loc_px=0.0, tau_far_px=0.0, mean_bnd_dist_px=0.0,
            pixel_spacing=(dy, dx), overflow_factor=overflow_factor,
            overflow_clipped=overflow_clipped,
        )
    if a_any != b_any:
        return RC01Breakdown(
            score=0.0, iou_raw=0.0, iou_1to1=0.0, component_purity=0.0,
            s_bnd=0.0, bnd_precision=0.0, bnd_recall=0.0, s_far=0.0,
            s_sdf=0.0, sdf_precision=0.0, sdf_recall=0.0, s_width=0.0,
            s_rim=0.0, rim_sides=(0.0, 0.0, 0.0, 0.0),
            s_topo=0.0, t_beta0=0.0, t_beta1=0.0, s_mass0=0.0, s_bij0=0.0,
            s_cav=0.0, s_hole=0.0, s_port_topo=0.0, t_bay=0.0, t_neck=0.0,
            s_geom=0.0, s_core=0.0, s_shape_far=0.0,
            beta0_a=int(a_any), beta0_b=int(b_any), beta1_a=0, beta1_b=0,
            port_counts_a=(0, 0, 0, 0), port_counts_b=(0, 0, 0, 0),
            bay_count_a=0, bay_count_b=0,
            width_a_px=0.0, width_b_px=0.0, width_star_px=0.0,
            tau_loc_px=0.0, tau_far_px=0.0, mean_bnd_dist_px=float("inf"),
            pixel_spacing=(dy, dx), overflow_factor=overflow_factor,
            overflow_clipped=overflow_clipped,
        )

    # Lossless tight crop to union bounding box + 1-px empty border
    a, b = _crop_union(a_full, b_full)
    h, w = a.shape
    diag_union = math.hypot((h - 2) * dy, (w - 2) * dx)

    # Exact region overlap (full resolution; area ratios are anisotropy-invariant)
    overlap_mask = a & b
    inter = int(np.count_nonzero(overlap_mask))
    union = int(np.count_nonzero(a | b))
    iou_raw = inter / union if union > 0 else 1.0

    # Fast exact identity path
    if inter == union:
        (
            raw_fg_a, raw_na, fg_all_a, _, fg_areas_a,
            _, _, _, _, h_areas_a,
        ) = _analyze_topology(a)
        a_clean = _filtered_fg_mask(a, raw_fg_a, raw_na, fg_all_a)
        _, p_cnt_a, _, _, _ = _analyze_ports(a_clean, dy, dx)
        sy_s = max(1, int(math.ceil(h / SDF_MAX_DIM)))
        sx_s = max(1, int(math.ceil(w / SDF_MAX_DIM)))
        ds_a, _, _, width_a, _ = _compute_sdf_and_width(a_clean, sy_s, sx_s, dy, dx)
        bay_a = _count_bbox_bays(ds_a)
        tau_loc = max(2.5 * min_step, 0.50 * width_a)
        tau_far = max(8.0 * min_step, FAR_TAU_FRAC * diag_union)
        s_out = float(overflow_factor)
        return RC01Breakdown(
            score=s_out, iou_raw=1.0, iou_1to1=1.0, component_purity=1.0,
            s_bnd=1.0, bnd_precision=1.0, bnd_recall=1.0, s_far=1.0,
            s_sdf=1.0, sdf_precision=1.0, sdf_recall=1.0, s_width=1.0,
            s_rim=1.0, rim_sides=(1.0, 1.0, 1.0, 1.0),
            s_topo=1.0, t_beta0=1.0, t_beta1=1.0, s_mass0=1.0, s_bij0=1.0,
            s_cav=1.0, s_hole=1.0, s_port_topo=1.0, t_bay=1.0, t_neck=1.0,
            s_geom=1.0, s_core=s_out, s_shape_far=s_out,
            beta0_a=int(fg_areas_a.size), beta0_b=int(fg_areas_a.size),
            beta1_a=int(h_areas_a.size), beta1_b=int(h_areas_a.size),
            port_counts_a=p_cnt_a, port_counts_b=p_cnt_a,
            bay_count_a=bay_a, bay_count_b=bay_a,
            width_a_px=width_a, width_b_px=width_a, width_star_px=width_a,
            tau_loc_px=tau_loc, tau_far_px=tau_far, mean_bnd_dist_px=0.0,
            pixel_spacing=(dy, dx), overflow_factor=overflow_factor,
            overflow_clipped=overflow_clipped,
        )

    # Pillar 1 & 3: Full-resolution uncapped filtered 2D homology + mass & bijection fidelity
    (
        raw_fg_a, raw_na, fg_all_a, fg_match_a, fg_areas_a,
        raw_bg_a, raw_nba, _, h_match_a, h_areas_a,
    ) = _analyze_topology(a)
    (
        raw_fg_b, raw_nb, fg_all_b, fg_match_b, fg_areas_b,
        raw_bg_b, raw_nbb, _, h_match_b, h_areas_b,
    ) = _analyze_topology(b)

    beta0_a, beta0_b = int(fg_areas_a.size), int(fg_areas_b.size)
    beta1_a, beta1_b = int(h_areas_a.size), int(h_areas_b.size)

    a_clean = _filtered_fg_mask(a, raw_fg_a, raw_na, fg_all_a)
    b_clean = _filtered_fg_mask(b, raw_fg_b, raw_nb, fg_all_b)

    matched_fg = _matched_fg_overlap(
        raw_fg_a, raw_na, fg_match_a, raw_fg_b, raw_nb, fg_match_b, overlap_mask, inter
    )
    iou_1to1 = min(iou_raw, matched_fg / union) if union > 0 else 0.0
    comp_purity = (matched_fg / inter) if inter > 0 else 1.0

    # Foreground topological consistency: uncapped Betti + uncapped mass + smooth bijection
    t_beta0 = _betti_score(beta0_a, beta0_b)
    s_mass0 = _mass_distribution_similarity(fg_areas_a, fg_areas_b)
    omega = min(1.0, 5.0 * iou_raw)
    s_bij0 = 1.0 - omega * (1.0 - comp_purity)

    # Cavity / hole topological consistency: overlap-gated fallback crushes shifted same-area
    # fake holes (V7) at high IoU while preserving translated-ring RL shaping at IoU -> 0.
    # v1.2.0 refinement (c): mildly temper s_cav sublinearly when beta1(A) == beta1(B) >= 1
    # so exact-count cavities with size scaling degrade strongly without collapsing like missing
    # cavities (while keeping 0 ** 0.65 == 0 for non-overlapping shifted fake holes).
    t_beta1 = _betti_score(beta1_a, beta1_b)
    if beta1_a == 0 and beta1_b == 0:
        s_hole = 1.0
        s_cav = 1.0
    else:
        s_hole = _nyquist_hole_agreement(
            raw_bg_a, raw_nba, h_match_a, h_areas_a,
            raw_bg_b, raw_nbb, h_match_b, h_areas_b,
        )
        tot_ha = float(h_areas_a.sum())
        tot_hb = float(h_areas_b.sum())
        hole_vol_ratio = (
            (min(tot_ha, tot_hb) / max(tot_ha, tot_hb)) if max(tot_ha, tot_hb) > 0 else 0.0
        )
        s_mass1 = _mass_distribution_similarity(h_areas_a, h_areas_b)
        s_cav_raw = (1.0 - omega) * (hole_vol_ratio * s_mass1) + omega * s_hole
        if beta1_a == beta1_b and beta1_a >= 1 and s_cav_raw > 0.0:
            s_cav = float(s_cav_raw ** CAV_EXACT_BETA1_EXP)
        else:
            s_cav = float(s_cav_raw)

    # Pillar 4: Continuous Physical 1-Lipschitz SDF Field & Tight Width Spectrum
    sy_s = max(1, int(math.ceil(h / SDF_MAX_DIM)))
    sx_s = max(1, int(math.ceil(w / SDF_MAX_DIM)))
    ds_a, r_in_a, sdf_a, width_a, wq_a = _compute_sdf_and_width(a_clean, sy_s, sx_s, dy, dx)
    ds_b, r_in_b, sdf_b, width_b, wq_b = _compute_sdf_and_width(b_clean, sy_s, sx_s, dy, dx)
    width_star = min(width_a, width_b)

    stride_eff = math.hypot(sy_s * dy, sx_s * dx) / math.sqrt(2.0)
    eps_sdf = max(nyq_phys, 0.75 * stride_eff)
    eps_w = max(2.0 * nyq_phys, 1.0 * stride_eff)
    min_sigma_sdf = max(2.5 * min_step, stride_eff + 1.5 * min_step)

    sdf_prec = _directed_sdf_alignment(
        ds_a, r_in_a, sdf_a, r_in_b, sdf_b, width_star, eps_sdf, min_sigma_sdf
    )
    sdf_rec = _directed_sdf_alignment(
        ds_b, r_in_b, sdf_b, r_in_a, sdf_a, width_star, eps_sdf, min_sigma_sdf
    )
    s_sdf = _harmonic_mean(sdf_prec, sdf_rec)
    s_width = _width_spectrum_similarity(wq_a, wq_b, eps_phys=eps_w)

    # v1.2.0 refinement (b): full-res narrow-band neck erosion on >1024px canvases
    t_neck = _compute_neck_score(
        a_clean, b_clean, r_in_a, r_in_b,
        width_star=width_star, sy_s=sy_s, sx_s=sx_s, dy=dy, dx=dx,
    )

    # Pillar 5: Persistence-cleaned 4-side bounding-rim exposure + port-zone & bay topology
    rims_a, p_cnt_a, p_areas_a, z_fills_a, z_tols_a = _analyze_ports(a_clean, dy, dx)
    rims_b, p_cnt_b, p_areas_b, z_fills_b, z_tols_b = _analyze_ports(b_clean, dy, dx)
    bay_a = _count_bbox_bays(ds_a)
    bay_b = _count_bbox_bays(ds_b)

    tau_loc = max(2.5 * min_step, 0.50 * width_star)
    tau_far = max(8.0 * min_step, FAR_TAU_FRAC * diag_union)

    side_dist_scores: list[float] = []
    side_rim_port_scores: list[float] = []
    side_topo_port_scores: list[float] = []
    for idx in range(4):
        dr1, dr2, _, _ = _bidirectional_point_distances(rims_a[idx], rims_b[idx])
        er1 = np.maximum(0.0, dr1 - nyq_phys)
        er2 = np.maximum(0.0, dr2 - nyq_phys)
        rp = float(np.exp(-er1 / tau_loc).mean())
        rr = float(np.exp(-er2 / tau_loc).mean())
        d_s = _harmonic_mean(rp, rr)
        side_dist_scores.append(d_s)

        # Intrinsic side port-topology & port-zone fill consistency (translation-invariant)
        t_p = _betti_score(p_cnt_a[idx], p_cnt_b[idx])
        m_p = _mass_distribution_similarity(p_areas_a[idx], p_areas_b[idx])
        fa, fb = z_fills_a[idx], z_fills_b[idx]
        lo_f, hi_f = min(fa, fb), max(fa, fb)
        tol_f = min(z_tols_a[idx], z_tols_b[idx])
        r_fill = (min(hi_f, lo_f + tol_f) / hi_f) if hi_f > 1e-12 else 1.0

        # Continuous r_fill ALWAYS remains inside s_rim for smooth geometric credit.
        side_rim_port_scores.append(t_p * (m_p ** 0.5) * r_fill)

        # v1.2.0 refinement (a): decouple moderate geometric r_fill from discrete s_port_topo
        # when side port counts match (k_s(A) == k_s(B)), triggering s_topo only for
        # catastrophic >4x arm/whisker collapse (r_fill < 0.25) or discrete count mismatches.
        if p_cnt_a[idx] == p_cnt_b[idx]:
            r_fill_topo = 1.0 if r_fill >= PORT_FILL_COLLAPSE_THRESHOLD else r_fill
            side_topo_port_scores.append((m_p ** 0.5) * r_fill_topo)
        else:
            side_topo_port_scores.append(t_p * (m_p ** 0.5) * r_fill)

    rim_sides = (
        side_dist_scores[0] * (side_rim_port_scores[0] ** 0.5),
        side_dist_scores[1] * (side_rim_port_scores[1] ** 0.5),
        side_dist_scores[2] * (side_rim_port_scores[2] ** 0.5),
        side_dist_scores[3] * (side_rim_port_scores[3] ** 0.5),
    )
    s_rim = float((rim_sides[0] * rim_sides[1] * rim_sides[2] * rim_sides[3]) ** 0.25)

    t_bay = _betti_score(bay_a, bay_b)
    port_prod = (
        side_topo_port_scores[0]
        * side_topo_port_scores[1]
        * side_topo_port_scores[2]
        * side_topo_port_scores[3]
    )
    s_port_topo = float((port_prod ** 0.5) * (t_bay ** 0.5))

    s_topo = t_beta0 * s_mass0 * s_bij0 * t_beta1 * s_cav * t_neck * s_port_topo

    # Pillar 2: Exact full-resolution physical arc-length-weighted bidirectional boundary alignment
    pts_a, wa = _boundary_points_and_arc_weights(a, dy, dx)
    pts_b, wb = _boundary_points_and_arc_weights(b, dy, dx)
    d_a2b, d_b2a, wa_s, wb_s = _bidirectional_point_distances(pts_a, pts_b, wa, wb)
    mean_bnd_dist = 0.5 * (_weighted_mean(d_a2b, wa_s) + _weighted_mean(d_b2a, wb_s))

    e_a2b = np.maximum(0.0, d_a2b - nyq_phys)
    e_b2a = np.maximum(0.0, d_b2a - nyq_phys)

    bnd_prec = _weighted_mean(np.exp(-e_a2b / tau_loc), wa_s)
    bnd_rec = _weighted_mean(np.exp(-e_b2a / tau_loc), wb_s)
    s_bnd = _harmonic_mean(bnd_prec, bnd_rec)

    far_prec = 1.0 / (1.0 + _weighted_mean(e_a2b, wa_s) / tau_far)
    far_rec = 1.0 / (1.0 + _weighted_mean(e_b2a, wb_s) / tau_far)
    s_far = _harmonic_mean(far_prec, far_rec)

    # Coupled gated-geometric core + bounded far-field shaping bridge
    if iou_1to1 > 0.0 and s_bnd > 0.0 and s_sdf > 0.0 and s_rim > 0.0:
        s_geom = (
            (iou_1to1 ** W_REG)
            * (s_bnd ** W_BND)
            * (s_sdf ** W_SDF)
            * (s_rim ** W_RIM)
        )
    else:
        s_geom = 0.0

    g_topo = s_topo ** ALPHA_TOPO
    s_core = g_topo * s_width * s_geom * overflow_factor
    g_far = 0.20 + 0.80 * (g_topo ** 0.5)
    s_shape_far = (
        g_far
        * (s_width ** 0.5)
        * (0.5 * s_far + 0.5 * ((max(0.0, s_bnd * s_sdf * s_rim)) ** (1.0 / 3.0)))
        * overflow_factor
    )

    score = (1.0 - ETA_SHAPING) * s_core + ETA_SHAPING * s_shape_far
    score = float(min(1.0 - 1e-12, max(0.0, score)))

    return RC01Breakdown(
        score=score,
        iou_raw=float(iou_raw),
        iou_1to1=float(iou_1to1),
        component_purity=float(comp_purity),
        s_bnd=float(s_bnd),
        bnd_precision=float(bnd_prec),
        bnd_recall=float(bnd_rec),
        s_far=float(s_far),
        s_sdf=float(s_sdf),
        sdf_precision=float(sdf_prec),
        sdf_recall=float(sdf_rec),
        s_width=float(s_width),
        s_rim=float(s_rim),
        rim_sides=rim_sides,
        s_topo=float(s_topo),
        t_beta0=float(t_beta0),
        t_beta1=float(t_beta1),
        s_mass0=float(s_mass0),
        s_bij0=float(s_bij0),
        s_cav=float(s_cav),
        s_hole=float(s_hole),
        s_port_topo=float(s_port_topo),
        t_bay=float(t_bay),
        t_neck=float(t_neck),
        s_geom=float(s_geom),
        s_core=float(s_core),
        s_shape_far=float(s_shape_far),
        beta0_a=beta0_a,
        beta0_b=beta0_b,
        beta1_a=beta1_a,
        beta1_b=beta1_b,
        port_counts_a=p_cnt_a,
        port_counts_b=p_cnt_b,
        bay_count_a=bay_a,
        bay_count_b=bay_b,
        width_a_px=float(width_a),
        width_b_px=float(width_b),
        width_star_px=float(width_star),
        tau_loc_px=float(tau_loc),
        tau_far_px=float(tau_far),
        mean_bnd_dist_px=float(mean_bnd_dist),
        pixel_spacing=(dy, dx),
        overflow_factor=overflow_factor,
        overflow_clipped=overflow_clipped,
    )


def evaluate_rc01_calibrated(
    pred_raster: Any,
    target_raster: Any,
    calibration: dict[str, Any],
    *,
    gds_size_um: tuple[float, float] | None = None,
    mask_mode: str = "auto",
) -> RC01Breakdown:
    """Convenience wrapper extracting physical scale, threshold, and canvas span from
    PixCell's ``calibration.json`` (including exact ``compare_absolute.py`` frame-clipping bounds).
    """
    sx, sy = float(calibration["scale_px_per_um"][0]), float(calibration["scale_px_per_um"][1])
    white_threshold = int(calibration.get("white_threshold", 245))
    fp = calibration.get("footprint_um")
    footprint_um = (float(fp[0]), float(fp[1])) if fp is not None else None

    canvas_size_um: tuple[float, float] | None = None
    if "image_size_px" in calibration and "bbox" in calibration:
        img_w = float(calibration["image_size_px"][0])
        img_h = float(calibration["image_size_px"][1])
        x0, y0, _x1, y1 = [float(v) for v in calibration["bbox"]]
        # compare_absolute.py left-aligns X at x0 and vertically centers Y at (y0 + y1)/2
        avail_w_um = max(1e-6, (img_w - x0) / sx)
        cy_px = 0.5 * (y0 + y1)
        avail_h_um = max(1e-6, 2.0 * min(cy_px, img_h - cy_px) / sy)
        canvas_size_um = (avail_w_um, avail_h_um)

    return evaluate_rc01(
        pred_raster,
        target_raster,
        white_threshold=white_threshold,
        mask_mode=mask_mode,
        scale_px_per_um=(sx, sy),
        gds_size_um=gds_size_um,
        footprint_um=footprint_um,
        canvas_size_um=canvas_size_um,
    )


def rc01_score(
    raster_a: Any,
    raster_b: Any,
    *,
    white_threshold: int = 245,
    mask_mode: str = "auto",
    pixel_spacing: tuple[float, float] | None = None,
    scale_px_per_um: tuple[float, float] | None = None,
    gds_size_um: tuple[float, float] | None = None,
    footprint_um: tuple[float, float] | None = None,
    canvas_size_um: tuple[float, float] | None = None,
) -> float:
    """Pure, deterministic, symmetric RC-01 v1.2.0 similarity score in ``[0.0, 1.0]``."""
    return evaluate_rc01(
        raster_a,
        raster_b,
        white_threshold=white_threshold,
        mask_mode=mask_mode,
        pixel_spacing=pixel_spacing,
        scale_px_per_um=scale_px_per_um,
        gds_size_um=gds_size_um,
        footprint_um=footprint_um,
        canvas_size_um=canvas_size_um,
    ).score
