"""Primitives-only recreation of experiments/paper_swap/final8/device_bw.png.

Topology (see recreation_log.json): calibration shows image-X = 120um LENGTH,
image-Y = 4um WIDTH. Scanning across width reveals 3 finger arrays (5 fingers
each, comb_top / comb_mid / comb_bot) bridged by 2 solid pads. Each finger's
LENGTH extent is a smoothly varying "inset" from the two length edges:
mid-array fingers span the full 120um (inset~0); pad-adjacent fingers are
shortest; the outermost finger of each outer array is itself a smooth taper
continuing all the way to the width edge (y=0 / y=total_width), which is why
the raw image shows a curved (not sharp) silhouette there. Each tapered
outer finger is built as a stack of thin rectangles (primitive composition,
approximating the measured smooth curve) rather than a raw polygon.
"""

import gdsfactory as gf

LAYER = (1, 0)

# ---- Tunables (top-level, JEE-substitutable) ---------------------------
total_length_um = 120.0
total_width_um = 4.0

# transverse (width) band edges, measured from the image (um)
comb_top_teeth_y = [
    (0.7656, 0.8315),
    (0.8650, 0.9319),
    (0.9654, 1.0313),
    (1.0658, 1.1317),
    (1.1663, 1.2321),
]
pad1_y = (1.2645, 1.7332)
comb_mid_teeth_y = [
    (1.7712, 1.8404),
    (1.8712, 1.9386),
    (1.9777, 2.0369),
    (2.0759, 2.1373),
    (2.1741, 2.2422),
]
pad2_y = (2.2690, 2.7355)
comb_bot_teeth_y = [
    (2.7712, 2.8371),
    (2.8705, 2.9375),
    (2.9710, 3.0368),
    (3.0714, 3.1384),
    (3.1719, 3.2377),
]

# length (x) insets from each end, um -- the function-defining knobs: they
# set the coupling/grating aperture length available to each finger.
inset_pad1_um = 7.61
inset_pad2_um = 8.05
inset_comb_top_flat_um = [5.676, 5.908, 6.139, 6.398, 6.687]
inset_comb_mid_um = 0.03
inset_comb_bot_flat_um = [6.687, 6.398, 6.109, 5.879, 5.65]


def _add_rect(c, x0, x1, y0, y1):
    w = x1 - x0
    h = y1 - y0
    if w <= 0 or h <= 0:
        return
    r = c.add_ref(gf.components.rectangle(size=(w, h), layer=LAYER))
    r.move((x0, y0))


def _add_flat_finger(c, y_range, inset):
    y0, y1 = y_range
    _add_rect(c, inset, total_length_um - inset, y0, y1)


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    for y_range, inset in zip(comb_top_teeth_y, inset_comb_top_flat_um):
        _add_flat_finger(c, y_range, inset)

    _add_flat_finger(c, pad1_y, inset_pad1_um)

    for y_range in comb_mid_teeth_y:
        _add_flat_finger(c, y_range, inset_comb_mid_um)

    _add_flat_finger(c, pad2_y, inset_pad2_um)

    for y_range, inset in zip(comb_bot_teeth_y, inset_comb_bot_flat_um):
        _add_flat_finger(c, y_range, inset)

    return c


if __name__ == "__main__":
    comp = device()
    gds_path = "device.gds"
    comp.write_gds(gds_path)
    print(f"wrote {gds_path}, bbox={comp.bbox()}")
