"""Parametric primitives-only recreation of experiments/paper_swap/final7 device_bw.png.

Elliptical ring loop with two symmetric internal loading pads (each a
frame with two window cutouts) fed by tapered arms. See recreation_log.json
for the topology reasoning.
"""
import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# ---- footprint reference (from footprint.json, not itself a tunable) ----
FOOTPRINT_X = 3.0
FOOTPRINT_Y = 5.497

# ---- tunables (function-defining knobs) ----
ring_ax = 1.35           # ring superellipse centerline semi-axis, x
ring_ay = 2.70           # ring superellipse centerline semi-axis, y
ring_n = 2.0             # superellipse exponent (2=ellipse, larger=flatter poles/fuller sides)
ring_width = 0.34        # ring rail (waveguide) width
pad_width = 1.00         # pad outer width (x)
pad_height = 1.17        # pad outer height (y)
pad_border = 0.22        # solid frame thickness around each window
window_width = 0.30      # window cutout width
window_height = 0.54     # window cutout height
divider_width = 0.11     # central bar width between the two windows
pad_offset_y = 0.91      # pad center distance from device vertical center
arm_width = 0.44         # straight arm width at the pad side
arm_flare_width = 1.00   # arm width at the flared (ring-side) end
arm_length = 0.85        # taper length of each arm


def _ellipse_ring(ax: float, ay: float, width: float, exponent: float = 2.0, n: int = 240) -> gf.Component:
    """Superelliptical annulus built via gf.Path (sampled centerline) + extrude.

    exponent=2 gives a true ellipse; larger exponent flattens the poles and
    fills out the sides (approaching a rounded rectangle).
    """
    theta = np.linspace(0, 2 * np.pi, n)
    c, s = np.cos(theta), np.sin(theta)
    x = ax * np.sign(c) * np.abs(c) ** (2.0 / exponent)
    y = ay * np.sign(s) * np.abs(s) ** (2.0 / exponent)
    pts = np.column_stack([x, y])
    path = gf.Path(pts)
    xs = gf.cross_section.cross_section(width=width, layer=LAYER)
    return path.extrude(xs)


def _pad() -> gf.Component:
    """Rectangular loading pad: solid frame with two window cutouts."""
    x0 = -pad_width / 2 + pad_border

    solid = gf.Component()
    s = solid << gf.components.rectangle(size=(pad_width, pad_height), layer=LAYER)
    s.move((-pad_width / 2, -pad_height / 2))

    windows_only = gf.Component()
    w1 = windows_only << gf.components.rectangle(size=(window_width, window_height), layer=LAYER)
    w1.move((x0, -window_height / 2))
    w2 = windows_only << gf.components.rectangle(size=(window_width, window_height), layer=LAYER)
    w2.move((x0 + window_width + divider_width, -window_height / 2))

    framed = gf.boolean(A=solid, B=windows_only, operation="not", layer=LAYER)
    return framed


def _arm() -> gf.Component:
    return gf.components.taper(
        length=arm_length, width1=arm_width, width2=arm_flare_width, layer=LAYER
    )


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    ring = _ellipse_ring(ring_ax, ring_ay, ring_width, exponent=ring_n)
    c << ring

    for sign in (+1, -1):
        pad = _pad()
        pad_ref = c << pad
        pad_ref.move((0, sign * pad_offset_y))

        arm_l = _arm()
        arm_l_ref = c << arm_l
        arm_l_ref.mirror_x(x=0)
        arm_l_ref.move((-pad_width / 2, sign * pad_offset_y - arm_width / 2))

        arm_r = _arm()
        arm_r_ref = c << arm_r
        arm_r_ref.move((pad_width / 2, sign * pad_offset_y - arm_width / 2))

    return c


if __name__ == "__main__":
    import pathlib

    out = pathlib.Path(__file__).parent / "device.gds"
    comp = device()
    comp.write_gds(str(out))
    print("wrote", out, "bbox:", comp.bbox())
