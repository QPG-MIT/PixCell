"""FINAL_8: multi-stripe coupler (120 x 4 um), attempt 1 (parametric tier).

- 5 center stripes spanning the full length (pitch ~0.10, w ~0.065)
- top/bottom: solid slab [0.267, 0.737] + 5 stripes at pitch 0.100 above it
- at all four corners the slab and the stripe bundle sweep up/down out of frame
  (modelled as 0.5-wide paths along measured centerlines)
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

CENTER_STRIPES = [(0.160, 0.230), (0.060, 0.131), (-0.037, 0.023), (-0.137, -0.075), (-0.243, -0.173)]
TOP_STRIPES = [(0.768, 0.835), (0.868, 0.936), (0.969, 1.036), (1.068, 1.136), (1.167, 1.235)]

PIPE_A = [(9.5, 0.45), (7.05, 1.00), (5.75, 1.50), (4.90, 1.95), (4.55, 2.10)]
PIPE_B = [(10.2, 0.95), (8.85, 1.20), (7.95, 1.50), (7.15, 1.95), (6.85, 2.10)]


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def rect(c, x1, y1, x2, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 4), round(y2 - y1, 4)), layer=LAYER)
    r.move((round(x1, 4), round(y1, 4)))
    return r


@gf.cell
def stripe_coupler_v1() -> gf.Component:
    c = gf.Component()

    for y1, y2 in CENTER_STRIPES:
        rect(c, 0.0, min(y1, y2), 120.0, max(y1, y2))

    for sgn in (1, -1):
        rect(c, 9.0, min(sgn * 0.267, sgn * 0.737), 111.0, max(sgn * 0.267, sgn * 0.737))
        for y1, y2 in TOP_STRIPES:
            rect(c, 8.7, min(sgn * y1, sgn * y2), 111.3, max(sgn * y1, sgn * y2))
        for pipe in (PIPE_A, PIPE_B):
            left = [(x, sgn * y) for x, y in pipe]
            right = [(120.0 - x, sgn * y) for x, y in pipe]
            c << gf.path.extrude(gf.Path(left), cross_section=xs(0.5))
            c << gf.path.extrude(gf.Path(right), cross_section=xs(0.5))

    return c


if __name__ == "__main__":
    component = stripe_coupler_v1()
    out = Path(__file__).parent / "attempt1.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
