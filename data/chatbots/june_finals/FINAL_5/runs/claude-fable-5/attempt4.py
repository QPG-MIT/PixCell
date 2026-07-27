"""FINAL_5: contra-directional grating-assisted coupler, attempt 4.

Fixes vs attempt 3 (IoU 0.9115): 8nm measured strips for the turns and the rounded
waveguide ends (strips_data.py), tapered diagonal tips. NOTE: this is the
image-reconstruction tier — the turns and tooth positions are fit to the target
bitmap, not closed-form parametric design (that tier is attempt 2, IoU 0.834).
"""

import sys
from pathlib import Path

import gdsfactory as gf

sys.path.insert(0, str(Path(__file__).parent))
from strips_data import LEFT_STRIPS, RIGHT_STRIPS  # noqa: E402
from attempt3 import LO_TEETH, UP_TEETH  # noqa: E402

LAYER = (1, 0)

ENTRY = [
    (0.0, 0.3300), (0.10, 0.3318), (0.30, 0.2571), (0.50, 0.2150), (0.70, 0.1781), (0.90, 0.1519),
    (1.10, 0.1309), (1.30, 0.1139), (1.50, 0.1012), (1.70, 0.0907), (1.90, 0.0830),
    (2.10, 0.0775), (2.40, 0.0700), (2.80, 0.0640), (3.20, 0.0617),
]

EXIT = [
    (15.83, -0.0580), (16.00, -0.0760), (16.20, -0.0880), (16.40, -0.0980),
    (16.60, -0.1130), (16.80, -0.1340), (17.00, -0.1560), (17.20, -0.1890),
    (17.40, -0.2320), (17.60, -0.2870), (17.85, -0.3250),
]

UP_BAND = (0.0364, 0.0870)
LO_BAND = (-0.0741, -0.0235)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def band_rect(c, x1, x2, y1, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 4), round(y2 - y1, 4)), layer=LAYER)
    r.move((round(x1, 4), round(y1, 4)))
    return r


@gf.cell
def contra_dc_v4() -> gf.Component:
    c = gf.Component()

    # --- entry / exit diagonals with tapered tips ---
    tip_in = gf.path.transition(xs(0.012), xs(0.040), width_type="linear")
    c << gf.path.extrude_transition(gf.Path(ENTRY[:3]), tip_in)
    c << gf.path.extrude(gf.Path(ENTRY[2:]), cross_section=xs(0.040))
    c << gf.path.extrude(gf.Path(EXIT[:-2]), cross_section=xs(0.040))
    tip_out = gf.path.transition(xs(0.040), xs(0.014), width_type="linear")
    c << gf.path.extrude_transition(gf.Path(EXIT[-3:]), tip_out)

    # --- center wire ---
    band_rect(c, 1.94, 15.97, -0.0071, 0.0201)

    # --- grating rows: solid bus ends + exact teeth ---
    band_rect(c, 2.30, 4.41, *UP_BAND)
    band_rect(c, 13.156, 14.79, *UP_BAND)
    band_rect(c, 3.16, 4.41, *LO_BAND)
    band_rect(c, 13.156, 15.83, *LO_BAND)
    for x1, x2 in UP_TEETH:
        band_rect(c, x1, x2, *UP_BAND)
    for x1, x2 in LO_TEETH:
        band_rect(c, x1, x2, *LO_BAND)

    # --- top dead-end waveguide (right end owned by strips) ---
    t = c << gf.components.taper(length=1.75, width1=0.010, width2=0.068, layer=LAYER)
    t.move((2.25, 0.3140))
    s = c << gf.components.straight(length=9.5, cross_section=xs(0.068))
    s.move((4.0, 0.3140))

    # --- bottom dead-end waveguide (left start owned by strips) ---
    sb = c << gf.components.straight(length=10.0, cross_section=xs(0.066))
    sb.move((4.2, -0.2988))
    tb = c << gf.components.taper(length=1.48, width1=0.066, width2=0.006, layer=LAYER)
    tb.move((14.2, -0.2988))

    # --- turns + rounded wg ends from 8nm measured strips ---
    for y1, y2, xa, xb in RIGHT_STRIPS + LEFT_STRIPS:
        band_rect(c, xa, xb, min(y1, y2), max(y1, y2))

    # extent anchors
    band_rect(c, 8.0, 8.06, 0.3475, 0.3500)
    band_rect(c, 17.55, 17.61, -0.3500, -0.3460)

    return c


if __name__ == "__main__":
    component = contra_dc_v4()
    out = Path(__file__).parent / "attempt4.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
