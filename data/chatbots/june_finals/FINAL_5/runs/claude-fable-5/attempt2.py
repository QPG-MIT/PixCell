"""FINAL_5: contra-directional grating-assisted coupler, attempt 2 — extent anchoring + hairpin/teeth tuning.

Measured from device_bw.png (3712x1152, 200.05 px/um x, 1620 px/um y, 18.24 x 0.7 um):
- two grating rows (period 0.1593, tooth 0.12, 54 teeth, bands [+0.0364,+0.0870] / [-0.0741,-0.0235])
  with solid bus sections at both ends
- continuous center wire x [1.94, 15.97], w 0.027, c +0.0065
- top dead-end waveguide (c +0.314, w 0.068) with left taper tip; bottom mirror (c -0.299)
  with right taper tip
- hairpin turns drawn as solid teardrops: filled circle r 0.155 + flaring arms
- entry diagonal (top-left) and exit diagonal (bottom-right), w 0.040
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def band_rect(c, x1, x2, y1, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 3), round(y2 - y1, 3)), layer=LAYER)
    r.move((x1, y1))
    return r


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

N_TEETH = 54
PERIOD = 0.1590
TOOTH = 0.12
UP_BAND = (0.0364, 0.0870)
LO_BAND = (-0.0741, -0.0235)


@gf.cell
def contra_dc() -> gf.Component:
    c = gf.Component()

    # --- entry / exit diagonals ---
    c << gf.path.extrude(gf.Path(ENTRY), cross_section=xs(0.040))
    c << gf.path.extrude(gf.Path(EXIT), cross_section=xs(0.040))

    # --- center wire ---
    band_rect(c, 1.94, 15.97, -0.0071, 0.0201)

    # --- grating rows: solid bus ends + teeth ---
    band_rect(c, 2.30, 4.41, *UP_BAND)
    band_rect(c, 13.156, 14.79, *UP_BAND)
    band_rect(c, 3.16, 4.41, *LO_BAND)
    band_rect(c, 13.156, 15.83, *LO_BAND)
    tooth_up = gf.components.rectangle(size=(TOOTH, round(UP_BAND[1] - UP_BAND[0], 4)), layer=LAYER)
    tooth_lo = gf.components.rectangle(size=(TOOTH, round(LO_BAND[1] - LO_BAND[0], 4)), layer=LAYER)
    for i in range(N_TEETH):
        x = 4.609 + i * PERIOD
        (c << tooth_up).move((x, UP_BAND[0]))
        (c << tooth_lo).move((x, LO_BAND[0]))

    # --- top dead-end waveguide: left taper tip + straight ---
    t = c << gf.components.taper(length=1.75, width1=0.010, width2=0.068, layer=LAYER)
    t.move((2.25, 0.3140))
    s = c << gf.components.straight(length=10.55, cross_section=xs(0.068))
    s.move((4.0, 0.3140))

    # --- bottom dead-end waveguide: left flare + straight + right taper tip ---
    sb = c << gf.components.straight(length=10.0, cross_section=xs(0.066))
    sb.move((4.2, -0.2988))
    fl = c << gf.path.extrude(gf.Path([(2.78, -0.2870), (3.30, -0.2960), (4.20, -0.2988)]), cross_section=xs(0.056))
    tb = c << gf.components.taper(length=1.48, width1=0.066, width2=0.006, layer=LAYER)
    tb.move((14.2, -0.2988))

    # --- right hairpin: solid teardrop ---
    circ_r = c << gf.components.circle(radius=0.160, layer=LAYER)
    circ_r.move((15.32, 0.187))
    c << gf.path.extrude(gf.Path([(14.55, 0.3120), (14.95, 0.2980), (15.22, 0.2680)]), cross_section=xs(0.070))
    c << gf.path.extrude(gf.Path([(14.79, 0.0617), (15.05, 0.0780), (15.25, 0.1150)]), cross_section=xs(0.056))

    # --- left hairpin: solid teardrop ---
    circ_l = c << gf.components.circle(radius=0.160, layer=LAYER)
    circ_l.move((2.66, -0.172))
    c << gf.path.extrude(gf.Path([(3.16, -0.0490), (2.92, -0.0620), (2.72, -0.0950)]), cross_section=xs(0.050))

    # extent anchors: pin bbox to exactly y in [-0.350, +0.350] so renderer centering is identity
    band_rect(c, 8.0, 8.06, 0.3475, 0.3500)
    band_rect(c, 17.55, 17.61, -0.3500, -0.3460)

    return c


if __name__ == "__main__":
    component = contra_dc()
    out = Path(__file__).parent / "attempt2.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
