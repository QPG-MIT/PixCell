"""Deterministic & adversarial unit test suite for RC-01 v1.2.0 (`michaelangelo.core.rc01`).

Covers all Research Contract RC-01 gates (T1-T5), adversarial exploits, mathematical
cross-audit stress-tests, and regression tests for all three RC-01 v1.2.0 calibration
refinements (matching-port r_fill decoupling, full-res narrow-band neck erosion on
>1024px canvases, and exact-beta1 sublinear s_cav tempering).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from PIL import Image, ImageDraw
from scipy import ndimage

from michaelangelo.core import rc01 as m


def _ring_mask(
    size: int = 256,
    r_out: float = 90.0,
    r_in: float = 55.0,
    cy: int | None = None,
    cx: int | None = None,
) -> np.ndarray:
    yy, xx = np.ogrid[:size, :size]
    cy = size // 2 if cy is None else cy
    cx = size // 2 if cx is None else cx
    d2 = (yy - cy) ** 2 + (xx - cx) ** 2
    return (d2 <= r_out**2) & (d2 >= r_in**2)


def _coupler_mask(size: int = 256, wg_w: int = 16, gap: int = 10) -> np.ndarray:
    mask = np.zeros((size, size), dtype=bool)
    cy = size // 2
    y1a = cy - gap // 2 - wg_w
    y1b = cy - gap // 2
    y2a = cy + gap // 2
    y2b = cy + gap // 2 + wg_w
    mask[y1a:y1b, 20 : size - 20] = True
    mask[y2a:y2b, 20 : size - 20] = True
    return mask


def _mmi_1x4(
    h: int = 300,
    w: int = 500,
    n_right: int = 4,
    fuse_right: bool = False,
    has_left: bool = True,
) -> np.ndarray:
    img = np.zeros((h, w), dtype=bool)
    cy = h // 2
    img[cy - 60 : cy + 60, 140:340] = True
    if has_left:
        img[cy - 8 : cy + 8, 20:140] = True
    if fuse_right:
        img[cy - 50 : cy + 50, 340:480] = True
    elif n_right > 0:
        ys = np.linspace(cy - 42, cy + 42, n_right).astype(int)
        for y in ys:
            img[y - 7 : y + 7, 340:480] = True
    return img


def _polygon_mask(shape: tuple[int, int], vertices: list[tuple[float, float]]) -> np.ndarray:
    h, w = shape
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).polygon(vertices, fill=255)
    return np.asarray(img) > 0


def test_version_is_frozen_v1_2_0() -> None:
    ring = _ring_mask(128, 45.0, 25.0)
    assert m.RC01_VERSION == "1.2.0"
    assert m.evaluate_rc01(ring, ring).version == "1.2.0"


def test_t1_determinism_symmetry_identity_and_bounds() -> None:
    ring = _ring_mask()
    shifted = np.roll(ring, shift=12, axis=1)

    assert m.rc01_score(ring, ring) == 1.0
    s1 = m.rc01_score(ring, shifted)
    s2 = m.rc01_score(ring, shifted)
    s_rev = m.rc01_score(shifted, ring)

    assert 0.0 < s1 < 1.0
    assert s1 == s2  # bit-identical determinism
    assert s1 == s_rev  # exact symmetry


def test_empty_and_shape_mismatch_edge_cases() -> None:
    empty = np.zeros((64, 64), dtype=bool)
    dot = np.zeros((64, 64), dtype=bool)
    dot[30:35, 30:35] = True

    assert m.rc01_score(empty, empty) == 1.0
    assert m.rc01_score(empty, dot) == 0.0
    assert m.rc01_score(dot, empty) == 0.0

    with pytest.raises(ValueError, match="exact canvas shape"):
        m.rc01_score(empty, np.zeros((64, 65), dtype=bool))


def test_grayscale_pixcell_convention_and_all_black_uint8() -> None:
    """All-0 uint8 vs all-255 uint8 must decode symmetrically and score 0.0."""
    ring = _ring_mask(128, 45.0, 25.0)
    shifted = np.roll(ring, 5, axis=0)
    gray_a = np.where(ring, 0, 255).astype(np.uint8)
    gray_b = np.where(shifted, 0, 255).astype(np.uint8)
    assert m.rc01_score(ring, shifted) == m.rc01_score(gray_a, gray_b)

    all_black = np.zeros((64, 64), dtype=np.uint8)
    all_white = np.full((64, 64), 255, dtype=np.uint8)
    all_ones = np.ones((64, 64), dtype=np.uint8)
    assert m.rc01_score(all_black, all_white) == 0.0
    assert m.rc01_score(all_white, all_black) == 0.0
    assert m.rc01_score(all_black, all_ones) == 0.0
    assert m.rc01_score(all_black, all_white, mask_mode="grayscale") == 0.0
    assert m.rc01_score(all_black, all_black) == 1.0


def test_uncapped_betti_counts_above_256() -> None:
    """True Betti counts beta0/beta1 must never silently cap at 256."""

    def grid_dots(n: int, shape: tuple[int, int] = (400, 400)) -> np.ndarray:
        arr = np.zeros(shape, dtype=bool)
        k = 0
        for r in range(5, shape[0] - 5, 16):
            for c in range(5, shape[1] - 5, 16):
                if k < n:
                    arr[r : r + 6, c : c + 6] = True
                    k += 1
        return arr

    g260, g350 = grid_dots(260), grid_dots(350)
    bd_fg = m.evaluate_rc01(g260, g350)
    assert bd_fg.beta0_a == 260 and bd_fg.beta0_b == 350
    assert bd_fg.t_beta0 < 0.70

    h260 = np.ones((400, 400), dtype=bool)
    h260[g260] = False
    h350 = np.ones((400, 400), dtype=bool)
    h350[g350] = False
    bd_h = m.evaluate_rc01(h260, h350)
    assert bd_h.beta1_a == 260 and bd_h.beta1_b == 350
    assert bd_h.t_beta1 < 0.70


def test_isolated_exterior_dust_speck_does_not_crash_gt_rim() -> None:
    """1-px aliasing speck outside the device keeps GT >= 0.99."""
    ring = _ring_mask(256, 70.0, 45.0)
    specked = ring.copy()
    specked[2, 2] = True  # isolated 1-px speck far outside the ring
    bd = m.evaluate_rc01(specked, ring)
    assert bd.beta0_a == 1 and bd.beta0_b == 1
    assert bd.s_rim > 0.99
    assert bd.score > 0.99


def test_one_pixel_waveguide_cut_severely_penalized() -> None:
    wg = np.zeros((128, 512), dtype=bool)
    wg[54:74, 20:492] = True
    cut = wg.copy()
    cut[:, 256] = False  # 1-px vertical break

    raw_iou = (wg & cut).sum() / (wg | cut).sum()
    bd = m.evaluate_rc01(cut, wg)
    assert raw_iou > 0.995
    assert bd.beta0_a == 2 and bd.beta0_b == 1
    assert bd.score < 0.35


def test_one_pixel_coupler_bridge_and_dust_speck_spoof_penalized() -> None:
    dc = _coupler_mask(256, wg_w=16, gap=10)
    bridged = dc.copy()
    bridged[110:146, 128] = True  # 1-px short across coupling gap

    bd_bridge = m.evaluate_rc01(bridged, dc)
    assert bd_bridge.iou_raw > 0.995
    assert bd_bridge.beta0_a == 1 and bd_bridge.beta0_b == 2
    assert bd_bridge.score < 0.35

    # Red-team spoof: attempt to spoof beta0=2 via a detached corner speck
    for sz in (2, 10):
        spoof = bridged.copy()
        spoof[5 : 5 + sz, 5 : 5 + sz] = True
        bd_spoof = m.evaluate_rc01(spoof, dc)
        assert bd_spoof.score < 0.30


def test_filled_ring_swiss_cheese_and_shifted_fake_hole_penalized() -> None:
    """Covers filled ring, 2-px pinhole, Swiss-cheese (off- & on-center), and V7 shifted hole."""
    ring = _ring_mask(256, 90.0, 55.0)
    disk = _ring_mask(256, 90.0, 0.0)

    bd_fill = m.evaluate_rc01(disk, ring)
    assert bd_fill.iou_raw > 0.60
    assert bd_fill.beta1_a == 0 and bd_fill.beta1_b == 1
    assert bd_fill.score < 0.05

    # 2-px pinhole in filled disk (filtered by existence-side area persistence)
    pin2 = disk.copy()
    pin2[127:129, 127:129] = False
    assert m.rc01_score(pin2, ring) < 0.05

    # Red-team Attack A (off-center): 10x10 fake hole in filled disk
    swiss = disk.copy()
    swiss[60:70, 123:133] = False
    bd_swiss = m.evaluate_rc01(swiss, ring)
    assert bd_swiss.beta1_a == 1 and bd_swiss.beta1_b == 1
    assert bd_swiss.score < 0.05

    # Red-team Attack A (centered inside ring cavity): still crushed even with v1.2 tempering,
    # while staying strictly above the completely filled disk for monotone RL gradient.
    swiss_center = disk.copy()
    swiss_center[123:133, 123:133] = False
    bd_swiss_c = m.evaluate_rc01(swiss_center, ring)
    assert bd_swiss_c.beta1_a == 1 and bd_swiss_c.beta1_b == 1
    assert bd_swiss_c.s_topo < 0.15
    assert bd_fill.score < bd_swiss_c.score < 0.10

    # V7: fill real hole in large slab, carve same-area fake hole elsewhere (IoU > 0.95)
    slab = np.zeros((256, 256), dtype=bool)
    slab[20:236, 20:236] = True
    gt_hole = slab.copy()
    gt_hole[110:140, 110:140] = False  # 30x30 hole at center
    fake_hole = slab.copy()
    fake_hole[40:70, 40:70] = False  # same-area 30x30 hole shifted with 0% overlap
    bd_v7 = m.evaluate_rc01(fake_hole, gt_hole)
    assert bd_v7.iou_raw > 0.95
    assert bd_v7.s_hole == 0.0
    assert bd_v7.s_cav == 0.0
    assert bd_v7.score < 0.05


def test_deletion_bonus_paradox_and_hollow_slit_frame() -> None:
    """Thin ring vs solid disk at matched IoU, plus contractible hollow slit-frame."""
    thin_ring = _ring_mask(256, 90.0, 62.0)
    solid_disk = _ring_mask(256, 90.0, 0.0)
    shifted_ring = _ring_mask(256, 90.0, 62.0, cy=128, cx=142)

    bd_disk = m.evaluate_rc01(solid_disk, thin_ring)
    bd_shift = m.evaluate_rc01(shifted_ring, thin_ring)
    assert abs(bd_disk.iou_raw - bd_shift.iou_raw) < 0.02
    assert bd_shift.score > 10.0 * bd_disk.score

    # Hollow-slit-frame on 1x4 MMI: contractible (1, 0) wireframe matching outer boundary
    mmi5 = _mmi_1x4(n_right=4)
    wf1 = mmi5 & ~ndimage.binary_erosion(mmi5, iterations=1)
    wf1[148:152, 20:25] = False  # 1-px slit makes beta1=0
    wf3 = mmi5 & ~ndimage.binary_erosion(mmi5, iterations=3)
    wf3[148:152, 20:30] = False
    assert m.rc01_score(wf1, mmi5) < 0.10
    assert m.rc01_score(wf3, mmi5) < 0.12


def test_parallel_walled_mmi_bays_whisker_and_ect_cancellation() -> None:
    """MMI bay destruction, whisker+end-cap exploit, and Euler-characteristic cancellation."""
    mmi5 = _mmi_1x4(n_right=4)
    bd_3p = m.evaluate_rc01(_mmi_1x4(n_right=2), mmi5)
    bd_2p = m.evaluate_rc01(_mmi_1x4(n_right=1), mmi5)
    bd_0p = m.evaluate_rc01(_mmi_1x4(n_right=0, has_left=False), mmi5)
    bd_fuse = m.evaluate_rc01(_mmi_1x4(fuse_right=True), mmi5)

    assert bd_3p.score < 0.52 and bd_3p.s_topo < 0.50
    assert bd_2p.score < 0.35 and bd_2p.s_topo < 0.30
    assert bd_0p.score < 0.10
    assert bd_fuse.score < 0.35 and bd_fuse.s_topo < 0.35

    # Whisker exploit (delete 95% of left input arm behind 3-px end-cap + 1-px whisker)
    whisk = mmi5.copy()
    whisk[:, 23:140] = False
    whisk[150, 20:142] = True
    bd_w = m.evaluate_rc01(whisk, mmi5)
    assert bd_w.iou_raw > 0.92
    assert bd_w.s_topo < 0.65  # decisively blocked by s_topo >= 0.80 RFT gate
    assert bd_w.score < 0.70

    # ECT cancellation (1-px cut + extra hole keeps chi constant on 25-hole beam)
    nb = np.zeros((200, 800), dtype=bool)
    nb[60:140, 20:780] = True
    for i in range(25):
        cx = 60 + i * 28
        nb[88:112, cx - 7 : cx + 7] = False
    nb_cut = nb.copy()
    nb_cut[:, 400] = False
    nb_ect = nb_cut.copy()
    nb_ect[65:75, 420:430] = False
    bd_cut = m.evaluate_rc01(nb_cut, nb)
    bd_ect = m.evaluate_rc01(nb_ect, nb)
    assert bd_cut.t_beta0 < 0.50 and bd_cut.score < 0.30
    assert bd_ect.t_beta0 < 0.50 and bd_ect.score < 0.30


def test_severe_anisotropy_10x_and_25x_physical_equivalence() -> None:
    """Equal physical X- vs Y-shifts must score equivalently at 10:1 and 25:1."""
    for ratio in (10, 25):
        sx, sy = 20.0, 20.0 * ratio
        w_px, h_px = int(6 * sx), int(6 * sy)
        yy = (np.arange(h_px)[:, None] + 0.5) / sy
        xx = (np.arange(w_px)[None, :] + 0.5) / sx
        gt = (
            (np.abs(xx - 3.0) <= 1.2)
            & (np.abs(yy - 3.0) <= 1.2)
            & ~((np.abs(xx - 3.0) <= 0.6) & (np.abs(yy - 3.0) <= 0.6))
        )
        sh_x = np.roll(gt, int(round(0.5 * sx)), axis=1)
        sh_y = np.roll(gt, int(round(0.5 * sy)), axis=0)
        bx = m.evaluate_rc01(sh_x, gt, scale_px_per_um=(sx, sy))
        by = m.evaluate_rc01(sh_y, gt, scale_px_per_um=(sx, sy))
        assert abs(bx.score - by.score) < 0.035
        assert bx.score == m.rc01_score(sh_x, gt, pixel_spacing=(1.0 / sy, 1.0 / sx))


def test_canvas_overflow_clipping_guard_and_calibrated_wrapper() -> None:
    """Oversized GDS exceeding canvas frame is explicitly penalized."""
    ring = _ring_mask(256, 80.0, 50.0)
    calib = {
        "bbox": [20, 20, 236, 236],
        "scale_px_per_um": [10.0, 10.0],
        "footprint_um": [21.6, 21.6],
        "image_size_px": [256, 256],
        "white_threshold": 245,
    }
    bd_ok = m.evaluate_rc01_calibrated(ring, ring, calib, gds_size_um=(21.6, 21.6))
    bd_ov = m.evaluate_rc01_calibrated(ring, ring, calib, gds_size_um=(100.0, 50.0))
    assert bd_ok.score == 1.0 and not bd_ok.overflow_clipped
    assert bd_ov.overflow_clipped and bd_ov.overflow_factor < 0.20
    assert bd_ov.score == pytest.approx(bd_ov.overflow_factor, rel=1e-6)


def test_persistence_filters_single_pixel_pinhole_aliasing() -> None:
    ring = _ring_mask(256, 90.0, 55.0)
    noisy = ring.copy()
    noisy[128, 55] = False
    noisy[128, 200] = False
    noisy[55, 128] = False

    bd = m.evaluate_rc01(noisy, ring)
    assert bd.beta1_a == 1 and bd.beta1_b == 1
    assert bd.s_topo == 1.0
    assert bd.score > 0.98


def test_zero_overlap_translation_preserves_monotone_dense_rl_gradient() -> None:
    wg = np.zeros((256, 256), dtype=bool)
    wg[30:42, 40:216] = True

    shifts = [20, 40, 80, 140]  # ALL strictly > width=12 -> IoU == 0.0
    scores = []
    for dy in shifts:
        shifted = np.zeros_like(wg)
        shifted[30 + dy : 42 + dy, 40:216] = True
        assert (wg & shifted).sum() == 0
        s = m.rc01_score(shifted, wg)
        assert 0.0 < s <= m.ETA_SHAPING
        scores.append(s)

    for s_near, s_far in zip(scores, scores[1:], strict=False):
        assert s_near > s_far


def test_stick_figure_and_checkerboard_shortcuts_crushed() -> None:
    ring = _ring_mask(256, 90.0, 55.0)
    yy, xx = np.ogrid[:256, :256]
    r = np.hypot(yy - 128, xx - 128)
    stick = np.abs(r - 72.5) <= 0.6
    assert m.rc01_score(stick, ring) < 0.05

    cb = np.zeros_like(ring)
    cb[38:218, 38:218] = ((yy[38:218, :] // 2 + xx[:, 38:218] // 2) % 2) == 0
    assert m.rc01_score(cb, ring) < 0.05


def test_edge_touching_narrow_bar_preserves_exact_thickness() -> None:
    """EDT border padding preserves thickness on edge-touching high-aspect bars."""
    bar = np.zeros((100, 1000), dtype=bool)
    bar[20:80, 10:500] = True
    bar[10:90, 500:990] = True
    jitter = bar.copy()
    jitter[19, 10:500] = True
    jitter[90, 500:990] = True

    bd = m.evaluate_rc01(jitter, bar)
    assert bd.score > 0.99
    assert math.isclose(bd.width_a_px, bd.width_b_px, rel_tol=0.05)


# ---------------------------------------------------------------------------
# RC-01 v1.2.0 Calibration Regression Tests (Refinements a, b, c)
# ---------------------------------------------------------------------------


def test_v12_refinement_a_l0_taper_passes_topo_gate_while_preserving_rim_and_flip_penalties() -> None:
    """v1.2 (a): single-piece L0 tapers (matching port counts, r_fill >= 0.25) pass s_topo >= 0.80,
    while continuous r_fill stays active inside s_rim and >4x collapse / 180-deg flips still fail.
    """
    # Single-piece left-to-right linear taper matching the 1d4432f7 / 0b6771b2 failure mode:
    # narrow left end 62 px vs 40 px (ratio ~0.65), identical right end 160 px, length 360 px.
    cy = 256
    taper_gt = _polygon_mask(
        (512, 512),
        [(76, cy - 31), (436, cy - 80), (436, cy + 80), (76, cy + 31)],
    )
    taper_pred = _polygon_mask(
        (512, 512),
        [(76, cy - 20), (436, cy - 80), (436, cy + 80), (76, cy + 20)],
    )

    bd_taper = m.evaluate_rc01(taper_pred, taper_gt)
    assert bd_taper.beta0_a == 1 and bd_taper.beta0_b == 1
    assert bd_taper.beta1_a == 0 and bd_taper.beta1_b == 0
    assert bd_taper.port_counts_a == bd_taper.port_counts_b == (1, 1, 1, 1)
    assert bd_taper.s_port_topo == 1.0
    assert bd_taper.s_topo >= 0.80
    assert bd_taper.s_rim < 1.0  # r_fill still reflected smoothly in s_rim
    assert 0.55 < bd_taper.score < 0.92
    assert bd_taper.score == m.rc01_score(taper_gt, taper_pred)

    # Catastrophic >4x collapse (1-px whisker replacing the left MMI arm without end-cap)
    mmi5 = _mmi_1x4(n_right=4)
    whisk_nocap = mmi5.copy()
    whisk_nocap[:, 20:140] = False
    whisk_nocap[150, 20:142] = True
    bd_wn = m.evaluate_rc01(whisk_nocap, mmi5)
    assert bd_wn.s_port_topo < 0.50
    assert bd_wn.s_topo < 0.50

    # 180-deg upside-down regular pentagon (flat top vs pointed bottom: r_fill ~0.20 < 0.25)
    radius = 180.0
    angles_up = [math.radians(-90 + 72 * k) for k in range(5)]  # point at top, flat at bottom
    angles_dn = [math.radians(90 + 72 * k) for k in range(5)]  # flat at top, point at bottom
    pent_up = _polygon_mask(
        (512, 512),
        [(256 + radius * math.cos(a), 256 + radius * math.sin(a)) for a in angles_up],
    )
    pent_dn = _polygon_mask(
        (512, 512),
        [(256 + radius * math.cos(a), 256 + radius * math.sin(a)) for a in angles_dn],
    )
    bd_pent = m.evaluate_rc01(pent_up, pent_dn)
    assert bd_pent.iou_raw > 0.78
    assert bd_pent.s_port_topo < 0.50
    assert bd_pent.s_topo < 0.50
    assert bd_pent.score < 0.45


def test_v12_refinement_b_fullres_narrow_band_neck_erosion_on_large_canvas() -> None:
    """v1.2 (b): on >1024px canvases (where SDF stride >= 3), full-res narrow-band neck erosion
    catches white-box thin interior whiskers (1-4 px) without false alarms on clean GT jitter.
    """
    gt = np.zeros((1600, 1600), dtype=bool)
    gt[740:860, 100:1500] = True  # 120 px thick, 1400 px long (stride_x = 3)

    # White-box interior thin whisker bridging an interior cut far from outer 10% port zones
    for whisker_w in (1, 2, 4):
        attack = gt.copy()
        attack[:, 780:820] = False
        y0 = 800 - whisker_w // 2
        attack[y0 : y0 + whisker_w, 778:822] = True

        bd = m.evaluate_rc01(attack, gt)
        assert bd.beta0_a == 1 and bd.beta0_b == 1  # raw homology is fooled
        assert bd.t_neck < 0.50, f"whisker_w={whisker_w} escaped full-res neck erosion"
        assert bd.s_topo < 0.50
        assert bd.score < 0.60
        assert bd.score == m.rc01_score(gt, attack)  # exact symmetry

    # 1-px Nyquist jitter on the same >1024px canvas stays exact on t_neck and >= 0.99 overall
    jitter = gt.copy()
    jitter[739, 100:1500] = True
    bd_jit = m.evaluate_rc01(jitter, gt)
    assert bd_jit.t_neck == 1.0
    assert bd_jit.s_topo == 1.0
    assert bd_jit.score > 0.99

    # Mild-to-moderate anisotropy on a full 2496x2496 canvas (sy_s=5, sx_s=5) must NOT fall
    # into a dead zone between full-res and SDF neck erosion (1.26:1-1.8:1 + 1.005:1 rounding).
    sq = np.zeros((2496, 2496), dtype=bool)
    sq[100:2400, 100:220] = True
    sq[1180:1300, 100:2400] = True
    sq[100:2400, 2280:2400] = True
    sq_atk = sq.copy()
    sq_atk[:, 1230:1270] = False
    sq_atk[1239:1241, 1228:1272] = True  # 2-px interior whisker

    for spacing in ((1.0, 1.005), (1.0, 1.3), (1.0, 1.5), (1.0, 1.8)):
        bd_aniso = m.evaluate_rc01(sq_atk, sq, pixel_spacing=spacing)
        assert bd_aniso.t_neck < 0.50, f"spacing={spacing} escaped neck erosion dead zone"
        assert bd_aniso.s_topo < 0.50
        assert bd_aniso.score == m.rc01_score(sq, sq_atk, pixel_spacing=spacing)


def test_overflow_guard_rejects_nan_and_nonpositive_canvas_bounds() -> None:
    ring = _ring_mask(64, 24.0, 14.0)
    with pytest.raises(ValueError, match="NaN"):
        m.evaluate_rc01(ring, ring, scale_px_per_um=(1.0, 1.0), gds_size_um=(float("nan"), 10.0))
    with pytest.raises(ValueError, match="positive finite"):
        m.evaluate_rc01(ring, ring, gds_size_um=(10.0, 10.0), canvas_size_um=(0.0, 10.0))
    with pytest.raises(ValueError, match="positive finite"):
        m.evaluate_rc01(ring, ring, gds_size_um=(10.0, 10.0), footprint_um=(10.0, float("nan")))


def test_v12_refinement_c_exact_beta1_cavity_tempering_preserves_missing_cavity_collapse() -> None:
    """v1.2 (c): exact-count cavities (beta1_a == beta1_b >= 1) with size scaling are mildly
    sublinearly tempered while still strongly penalized and distinct from missing/shifted holes.
    """
    slab = np.zeros((400, 400), dtype=bool)
    slab[20:380, 20:380] = True

    # Two real 20x20 holes (400 px each) vs two 70x70 oversized holes (~12.25x area, overlapping)
    gt = slab.copy()
    gt[110:130, 110:130] = False
    gt[270:290, 270:290] = False

    oversized = slab.copy()
    oversized[85:155, 85:155] = False
    oversized[245:315, 245:315] = False

    bd_scaled = m.evaluate_rc01(oversized, gt)
    bd_missing = m.evaluate_rc01(slab, gt)

    assert bd_scaled.beta1_a == 2 and bd_scaled.beta1_b == 2
    assert bd_scaled.s_hole > 0.0
    assert bd_scaled.s_cav == pytest.approx(bd_scaled.s_hole ** m.CAV_EXACT_BETA1_EXP, rel=1e-6)
    assert bd_scaled.s_cav > bd_scaled.s_hole  # sublinear tempering lifts exact-count scaling
    assert bd_scaled.s_topo < 0.50  # still strongly penalized below 0.80 RFT gate
    assert bd_scaled.score < 0.55
    assert bd_scaled.score == m.rc01_score(gt, oversized)

    # Missing cavities (beta1=0 vs 2) must still collapse completely
    assert bd_missing.s_cav == 0.0
    assert bd_missing.score < 0.05
    assert bd_scaled.score > 5.0 * bd_missing.score
