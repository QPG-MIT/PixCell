"""FINAL_8: multi-stripe coupler, attempt 2 (parametric tier).

Fixes vs attempt 1 (IoU 0.9606): corner curves rebuilt from measured midline
samples (slab-curve w 0.52, merged stripe-bundle curve w 0.55), straight
sections extended to the true transition x (10.2 / 109.8).
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

CENTER_STRIPES = [(0.160, 0.230), (0.060, 0.131), (-0.037, 0.023), (-0.137, -0.075), (-0.243, -0.173)]
TOP_STRIPES = [(0.768, 0.835), (0.868, 0.936), (0.969, 1.036), (1.068, 1.136), (1.167, 1.235)]

SLAB_CURVE = [(10.3, 0.504), (9.5, 0.523), (8.5, 0.634), (7.5, 0.856), (6.5, 1.174), (5.5, 1.52), (4.5, 2.05)]
BUNDLE_CURVE = [(10.45, 1.001), (9.5, 1.052), (8.5, 1.2785), (7.5, 1.61), (6.6, 2.05)]


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def rect(c, x1, y1, x2, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 4), round(y2 - y1, 4)), layer=LAYER)
    r.move((round(x1, 4), round(y1, 4)))
    return r


@gf.cell
def stripe_coupler_v2() -> gf.Component:
    c = gf.Component()

    for y1, y2 in CENTER_STRIPES:
        rect(c, 0.0, min(y1, y2), 120.0, max(y1, y2))

    for sgn in (1, -1):
        rect(c, 10.2, min(sgn * 0.267, sgn * 0.737), 109.8, max(sgn * 0.267, sgn * 0.737))
        for y1, y2 in TOP_STRIPES:
            rect(c, 10.45, min(sgn * y1, sgn * y2), 109.55, max(sgn * y1, sgn * y2))
        for pipe, w in ((SLAB_CURVE, 0.52), (BUNDLE_CURVE, 0.55)):
            left = [(x, sgn * y) for x, y in pipe]
            right = [(120.0 - x, sgn * y) for x, y in pipe]
            c << gf.path.extrude(gf.Path(left), cross_section=xs(w))
            c << gf.path.extrude(gf.Path(right), cross_section=xs(w))

    return c


if __name__ == "__main__":
    component = stripe_coupler_v2()
    out = Path(__file__).parent / "attempt2.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
