"""Ring resonator with coupling pads - parametric device (primitives + extrude)."""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

# === TOP-LEVEL TUNABLES ===
ring_ax = 1.35  # Ring semi-major axis (half-width)
ring_ay = 2.70  # Ring semi-minor axis (half-height)
ring_n = 2.0  # Superellipse exponent (2=ellipse)
ring_width = 0.34  # Ring material thickness

pad_width = 1.00  # Pad outer width
pad_height = 1.17  # Pad outer height
pad_border = 0.22  # Border thickness around windows
pad_offset_y = 0.91  # Vertical offset of pad center

window_width = 0.30  # Window cutout width
window_height = 0.54  # Window cutout height
divider_width = 0.11  # Divider bar width

arm_width = 0.44  # Arm width at pad side
arm_flare_width = 1.05  # Arm width at ring side - iter5: 1.00->1.05
arm_length = 0.90  # Taper length

# Layer definition
LAYER = (1, 0)


def _ellipse_ring(ax, ay, width, exponent=2.0, n=240):
    """Create elliptical ring using path + extrude."""
    theta = np.linspace(0, 2 * np.pi, n)
    c, s = np.cos(theta), np.sin(theta)
    x = ax * np.sign(c) * np.abs(c) ** (2.0 / exponent)
    y = ay * np.sign(s) * np.abs(s) ** (2.0 / exponent)
    pts = np.column_stack([x, y])
    path = gf.Path(pts)
    xs = gf.cross_section.cross_section(width=width, layer=LAYER)
    return path.extrude(xs)


def _pad():
    """Create a rectangular pad with two window cutouts."""
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


def _arm():
    """Create a tapered arm."""
    return gf.components.taper(
        length=arm_length, width1=arm_width, width2=arm_flare_width, layer=LAYER
    )


@gf.cell
def ring_resonator_coupler():
    """Build the device."""
    c = gf.Component("ring_resonator_coupler")

    # Create and add ring
    ring = _ellipse_ring(ring_ax, ring_ay, ring_width, exponent=ring_n)
    c << ring

    # Create top and bottom pads with arms
    for sign in (+1, -1):
        # Pad
        pad = _pad()
        pad_ref = c << pad
        pad_ref.move((0, sign * pad_offset_y))

        # Left arm
        arm_l = _arm()
        arm_l_ref = c << arm_l
        arm_l_ref.mirror_x(x=0)
        arm_l_ref.move((-pad_width / 2, sign * pad_offset_y - arm_width / 2))

        # Right arm
        arm_r = _arm()
        arm_r_ref = c << arm_r
        arm_r_ref.move((pad_width / 2, sign * pad_offset_y - arm_width / 2))

    return c


if __name__ == "__main__":
    # Build device
    device = ring_resonator_coupler()

    # Write GDS
    gds_path = Path(__file__).parent / "device.gds"
    device.write_gds(str(gds_path))

    # Export lengths.json
    lengths_data = {
        "delta_length_um": 2 * arm_length,
        "pad_count": 2,
    }
    lengths_path = Path(__file__).parent / "lengths.json"
    with open(lengths_path, "w") as f:
        json.dump(lengths_data, f, indent=2)

    print(f"Device written to {gds_path}")
    print(f"Lengths written to {lengths_path}")
