"""
Adiabatic Four-Port Splitter (Cross/Plus Topology)
Parametric GDSFactory implementation using primitives only.
"""

import gdsfactory as gf
import numpy as np
from gdsfactory.typings import Float2, Callable


# ============ TUNABLE PARAMETERS ============
petal_width_um = 1.2
petal_length_um = 1.38
junction_width_um = 0.42
stem_width_um = 0.52
stem_length_um = 0.58
port_length_um = 0.33
taper_smoothness = 0.62  # 0 = sharp, 1 = very smooth (lower = sharper petal tips)
layer = (1, 0)


@gf.cell
def adiabatic_four_port_splitter(
    petal_width: float = petal_width_um,
    petal_length: float = petal_length_um,
    junction_width: float = junction_width_um,
    stem_width: float = stem_width_um,
    stem_length: float = stem_length_um,
    port_length: float = port_length_um,
    taper_smoothness: float = taper_smoothness,
) -> gf.Component:
    """
    Creates a symmetric four-port adiabatic splitter with extended ports.

    The device is built using four-fold rotational symmetry:
    1. Define one arm from port entry through petal to petal tip
    2. Use smooth parametric tapering for adiabatic transitions
    3. Rotate and union to create four symmetric arms

    Args:
        petal_width: Width of petal lobes (μm)
        petal_length: Length of petal lobes (μm)
        junction_width: Width at central junction (μm)
        stem_width: Width in stem region (μm)
        stem_length: Length of stem region (μm)
        port_length: Length of port stub (μm)
        taper_smoothness: Shape parameter for tapers (0-1)
    """
    c = gf.Component()

    # Total arm length: port + stem + petal
    total_length = port_length + stem_length + petal_length

    # Generate centerline path
    num_points = 80
    arm_y = np.linspace(0, total_length, num_points)
    arm_x = np.zeros(num_points)

    # Port region: constant width
    port_end_idx = int(num_points * port_length / total_length)
    arm_x[:port_end_idx] = stem_width / 2

    # Stem region: expand from stem_width to petal_width
    stem_start_idx = port_end_idx
    stem_end_idx = int(num_points * (port_length + stem_length) / total_length)
    stem_indices = np.arange(stem_start_idx, stem_end_idx)
    stem_progress = (stem_indices - stem_start_idx) / (stem_end_idx - stem_start_idx + 1e-8)

    # Smooth expansion in stem region
    stem_x = (stem_width / 2) * (1 - stem_progress) + (petal_width / 2) * stem_progress
    arm_x[stem_start_idx:stem_end_idx] = stem_x

    # Petal region: elliptical bulge (rounded lens shape)
    petal_start_idx = stem_end_idx
    petal_indices = np.arange(petal_start_idx, num_points)
    petal_progress = (petal_indices - petal_start_idx) / (num_points - petal_start_idx + 1e-8)

    # Petal bulges to max width at mid-point, tapers to a tip
    # Use sinusoidal profile for smooth rounded petal
    petal_x = (petal_width / 2) * np.sin(np.pi * petal_progress) ** taper_smoothness
    arm_x[petal_start_idx:num_points] = petal_x

    # Create upper and lower outlines (symmetric arm)
    arm_points_right = np.array([arm_y, arm_x]).T
    arm_points_left = np.array([arm_y, -arm_x]).T

    # Combine into closed polygon
    arm_polygon = np.vstack([arm_points_right, arm_points_left[::-1]])

    # Add base arm to component
    c.add_polygon(arm_polygon, layer=layer)

    # Create three rotated copies (4-fold rotational symmetry)
    for angle_deg in [90, 180, 270]:
        angle_rad = np.radians(angle_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        rotated = np.zeros_like(arm_polygon)
        rotated[:, 0] = arm_polygon[:, 0] * cos_a - arm_polygon[:, 1] * sin_a
        rotated[:, 1] = arm_polygon[:, 0] * sin_a + arm_polygon[:, 1] * cos_a
        c.add_polygon(rotated, layer=layer)

    return c


if __name__ == "__main__":
    device = adiabatic_four_port_splitter()
    device.write_gds("/Users/aadarwal/src/QPG-MIT/homi-anu-powered/experiments/paper_swap/final6/output/recreation_haiku45m/device.gds")
    print(f"GDS written to device.gds")
    print(f"Device bounds: {device.bbox}")
