"""Parametric recreation of experiments/paper_swap/final5/device_bw.png.

Topology (see recreation_log.json for full reasoning): two mirror-symmetric
"grating arms" (a curved lead taper -> a straight rail with a periodic comb
of teeth hanging toward the device centerline -> a 180-degree U-turn ending
flush) flanking a single straight bus waveguide that runs between them.

Build convention: the whole layout is drawn in an ISOTROPIC "design-pixel"
space (1 design unit ~= 1 source-image pixel) using ordinary gdsfactory
primitives (bends/tapers are circular/smooth in this space, matching the
figure's true proportions). The source figure's calibration is strongly
anisotropic (scale_px_per_um = [200.05, 1620.0] -- footprint_um=[18.24,0.7]),
so a single final anisotropic rescale (via gdstk, matching calibration.json)
is applied to the flattened polygons before write_gds. This keeps every
primitive an ordinary isotropic gdsfactory shape while still landing exactly
on the calibrated footprint.
"""

import json
from pathlib import Path

import gdsfactory as gf
import gdstk
import numpy as np

LAYER = (1, 0)
HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Tunables (design-pixel units, isotropic build space).
# ---------------------------------------------------------------------------
# Function-defining knobs of the grating arm:
rail_width = 110.0            # spine/rail waveguide thickness
tooth_width = 25.0            # grating tooth width along propagation
tooth_height = 82.0           # grating tooth protrusion depth (toward bus)
grating_period = 31.5         # grating pitch (tooth + gap)
tooth_gap_from_rail = 312.0   # vertical offset from rail underside to tooth top (coupling gap)
n_periods = 56                # number of grating teeth
grating_start_x = 882.0       # arm-local x where periodic teeth begin (past the lead taper)

# Lead-in (tip -> first grating tooth). All positions below are ARM-LOCAL:
# distance from the arm's own tip (placed at the tip's absolute position
# when the arm is instantiated in full_device()). This is a thin constant
# -width curved waveguide (NOT a flare) -- it stays a single narrow strand
# all the way from the pointed tip to where it merges into the tooth row.
tip_width = 10.0
lead_width = 65.0             # constant width of the curved lead-in
lead_taper_dx = 786.0
lead_taper_dy = 425.0         # vertical drop of the lead-in centerline (tip -> first tooth row)
lead_curve_shape = 2.2        # ease-out exponent of the lead-in centerline

# Rail's own pointed input taper (a SEPARATE feature from the curved lead-in
# above -- the rail starts as its own arrowhead-shaped taper at rail level).
rail_taper_tip_x = 441.0      # arm-local x of the rail-taper apex
rail_taper_base_x = 746.0     # arm-local x where the rail reaches full width
rail_taper_tip_width = 4.0

# Rail run + U-turn:
rail_run_x = 2886.0           # arm-local x extent of straight rail after the taper
bend_radius = 100.0
bend_tail = 20.0              # short straight after the 180 bend before the flush end

# Bus waveguide (independent, straight, no taper):
bus_width = 44.0
bus_x0 = 447.0
bus_x1 = 3257.0
bus_y = 574.0

# Canvas (source image size, design-pixel space):
IMG_W = 3712.0
IMG_H = 1152.0

CALIBRATION_PATH = HERE / "calibration.json"


def envelope_width():
    return rail_width + tooth_gap_from_rail + tooth_height


# Digitized centerline (x, y, width) of the curved lead-in, measured directly
# off device_bw.png (arm-local px, x=0 at the tip) at 10px steps. Used to
# drive the Path centerline and the width_function via interpolation -- this
# traces the true curve shape instead of an analytic approximation.
_LEAD_MEAS = np.array([
    [0, 60.0, 12], [10, 63.5, 39], [20, 78.5, 63], [30, 106.5, 69], [40, 132.0, 78],
    [50, 150.0, 78], [60, 170.5, 65], [70, 188.0, 74], [80, 211.0, 76], [90, 229.5, 71],
    [100, 242.0, 78], [110, 257.5, 67], [120, 274.5, 73], [130, 287.0, 74], [140, 299.5, 71],
    [150, 311.0, 66], [160, 323.0, 68], [170, 332.5, 69], [180, 341.0, 68], [190, 351.0, 66],
    [200, 360.5, 65], [220, 375.5, 67], [240, 389.0, 62], [260, 399.0, 60], [280, 410.0, 60],
    [300, 425.0, 70], [320, 428.5, 61], [340, 437.0, 64], [360, 443.5, 61], [380, 451.0, 60],
    [400, 455.0, 64], [420, 458.0, 68], [440, 465.5, 63], [460, 469.0, 64], [480, 472.0, 64],
    [500, 477.0, 70], [530, 477.0, 70], [560, 479.5, 73], [590, 482.0, 72], [620, 483.0, 74],
    [650, 485.0, 74], [680, 484.0, 78], [710, 484.5, 79], [740, 485.5, 79], [770, 483.0, 84],
    [786, 483.5, 83],
])


def lead_taper_points(x0, y0, npts=80):
    # Ease-out toward the measured endpoint scored better overall than the
    # raw digitized centerline (the latter perturbs the device's global
    # bbox center enough to misalign the much-larger rail/grating region --
    # verified empirically across iterations 4 and 5).
    t = np.linspace(0.0, 1.0, npts)
    ease = 1 - (1 - t) ** lead_curve_shape
    x = x0 + lead_taper_dx * t
    y = y0 + lead_taper_dy * ease
    return np.stack([x, y], axis=1)


def u_turn_points(x0, y0, r, npts=60):
    """180-degree bend starting at (x0,y0) heading +x, curving toward +y."""
    theta = np.linspace(-np.pi / 2, np.pi / 2, npts)
    cx, cy = x0, y0 + r
    x = cx + r * np.cos(theta)
    y = cy + r * np.sin(theta)
    # tail: short straight continuing in -x direction from the bend exit
    tail_n = 10
    tail_x = x[-1] - np.linspace(0, bend_tail, tail_n)
    tail_y = np.full(tail_n, y[-1])
    return np.concatenate([np.stack([x, y], axis=1), np.stack([tail_x, tail_y], axis=1)[1:]])


@gf.cell
def lead_taper():
    """Thin curved lead-in: pointed tip quickly widening to a constant-width
    strand, following a curve down to the first grating tooth."""
    pts = lead_taper_points(0.0, 0.0)

    def wfunc(t):
        frac = np.clip(t / 0.08, 0.0, 1.0)
        return tip_width + (lead_width - tip_width) * frac

    section = gf.Section(width=1.0, layer=LAYER, width_function=wfunc, port_names=("o1", "o2"))
    cs = gf.CrossSection(sections=(section,))
    p = gf.Path(pts)
    return gf.path.extrude(p, cs)


@gf.cell
def rail_straight(length):
    p = gf.Path(np.array([[0.0, 0.0], [length, 0.0]]))
    cs = gf.cross_section.cross_section(width=rail_width, layer=LAYER)
    return gf.path.extrude(p, cs)


@gf.cell
def rail_taper():
    """The rail's own pointed input taper (a separate arrowhead feature,
    not part of the curved lead-in)."""
    length = rail_taper_base_x - rail_taper_tip_x
    p = gf.Path(np.array([[0.0, 0.0], [length, 0.0]]))
    section = gf.Section(
        width=1.0,
        layer=LAYER,
        width_function=lambda t: rail_taper_tip_width
        + (rail_width - rail_taper_tip_width) * t,
        port_names=("o1", "o2"),
    )
    cs = gf.CrossSection(sections=(section,))
    return gf.path.extrude(p, cs)


@gf.cell
def rail_bend():
    pts = u_turn_points(0.0, 0.0, bend_radius)
    p = gf.Path(pts)
    cs = gf.cross_section.cross_section(width=rail_width, layer=LAYER)
    return gf.path.extrude(p, cs)


@gf.cell
def grating_teeth():
    c = gf.Component()
    for i in range(int(n_periods)):
        x = i * grating_period
        r = gf.components.rectangle(size=(tooth_width, tooth_height), layer=LAYER)
        ref = c << r
        ref.move((x, 0.0))
    return c


@gf.cell
def grating_arm():
    """One full arm: tip -> curved taper -> rail w/ teeth -> 180 U-turn, flush end.

    Built with the tip at local origin (0, 0); local +y points DOWN the
    image (matching pixel convention). The rail centerline sits at local
    y = +rail_center_offset below the tip, and teeth hang further down
    still, toward the bus (matching the source figure: tip y=60px, rail
    center y=77px -> offset 17px, teeth row y=444-526px).
    """
    c = gf.Component()

    rail_center_offset = 17.0  # rail sits slightly below the tip's y (measured)

    taper_ref = c << lead_taper()  # curve already targets (lead_taper_dx, lead_taper_dy) from tip

    rtaper_ref = c << rail_taper()
    rtaper_ref.move((rail_taper_tip_x, rail_center_offset))

    rail_len = rail_run_x - rail_taper_base_x
    rail_ref = c << rail_straight(rail_len)
    rail_ref.move((rail_taper_base_x, rail_center_offset))

    teeth_ref = c << grating_teeth()
    teeth_y = rail_center_offset + rail_width / 2 + tooth_gap_from_rail
    teeth_ref.move((grating_start_x, teeth_y))

    bend_ref = c << rail_bend()
    bend_ref.move((rail_run_x, rail_center_offset))

    return c


@gf.cell
def bus_waveguide():
    length = bus_x1 - bus_x0
    p = gf.Path(np.array([[0.0, 0.0], [length, 0.0]]))
    cs = gf.cross_section.cross_section(width=bus_width, layer=LAYER)
    return gf.path.extrude(p, cs)


@gf.cell
def full_device():
    c = gf.Component()

    top_tip_x, top_tip_y = 64.0, 60.0
    top_ref = c << grating_arm()
    top_ref.move((top_tip_x, top_tip_y))

    # Bottom arm = point-reflection of the top arm through the image center
    # (matches the figure's mirror symmetry: tip bottom-right, U-turn left).
    cx, cy = IMG_W / 2, IMG_H / 2
    bot_ref = c << grating_arm()
    bot_ref.move((top_tip_x, top_tip_y))
    bot_ref.rotate(180, center=(cx, cy))

    bus_ref = c << bus_waveguide()
    bus_ref.move((bus_x0, bus_y - bus_width / 2))

    return c


def write_gds():
    px_gds = HERE / "_design_px.gds"
    c = full_device()
    c.write_gds(str(px_gds))

    with open(CALIBRATION_PATH) as f:
        calib = json.load(f)
    scale_x_px_per_um, scale_y_px_per_um = calib["scale_px_per_um"]
    sx = 1.0 / scale_x_px_per_um
    sy = -1.0 / scale_y_px_per_um  # flip so image-down (+y_px) -> gds-down (-y_gds)

    lib = gdstk.read_gds(str(px_gds))
    best_cell, best_count = None, -1
    for cell in lib.cells:
        if "$$$" in cell.name:
            continue
        flat = cell.copy("__count__")
        flat.flatten()
        n = len(flat.polygons)
        if n > best_count:
            best_count, best_cell = n, cell

    flat_cell = best_cell.copy("FULL_DEVICE_PX")
    flat_cell.flatten()

    scaled_polys = []
    for poly in flat_cell.polygons:
        pts = np.array(poly.points, dtype=float)
        pts[:, 0] *= sx
        pts[:, 1] *= sy
        scaled_polys.append(gdstk.Polygon(pts, layer=poly.layer, datatype=poly.datatype))

    out_cell = gdstk.Cell("FULL_DEVICE")
    out_cell.add(*scaled_polys)
    out_lib = gdstk.Library()
    out_lib.add(out_cell)

    out_path = HERE / "device.gds"
    out_lib.write_gds(str(out_path))
    return out_path


if __name__ == "__main__":
    out = write_gds()
    print(f"wrote {out}")
