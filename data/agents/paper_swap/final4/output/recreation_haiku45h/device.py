"""
Directional coupler: two S-curved waveguides.
Best configuration: IoU 0.593
"""

import gdsfactory as gf
import numpy as np

# === TOP-LEVEL TUNABLE PARAMETERS ===
width_um = 1.1          # Waveguide core width
gap_um = 0.7            # Gap between guides
taper_depth_um = 0.35   # Depth of taper/curve in middle
length_um = 18.0        # Total interaction length


@gf.cell
def directional_coupler() -> gf.Component:
    """Two S-curved waveguides using faceted polygon."""
    c = gf.Component()

    third = length_um / 3

    upper_poly_points = [
        # Left end (straight section)
        (0, (gap_um + width_um) / 2 - width_um / 2),
        (third / 2, (gap_um + width_um) / 2 - width_um / 2),
        # Curved section (taper inward)
        (length_um / 2, (gap_um + width_um) / 2 - width_um / 2 - taper_depth_um),
        (length_um - third / 2, (gap_um + width_um) / 2 - width_um / 2),
        # Right end
        (length_um, (gap_um + width_um) / 2 - width_um / 2),
        # Return path (top edge of waveguide)
        (length_um, (gap_um + width_um) / 2 + width_um / 2),
        (length_um - third / 2, (gap_um + width_um) / 2 + width_um / 2),
        (length_um / 2, (gap_um + width_um) / 2 + width_um / 2 - taper_depth_um),
        (third / 2, (gap_um + width_um) / 2 + width_um / 2),
        (0, (gap_um + width_um) / 2 + width_um / 2),
    ]

    # Lower guide (mirror)
    lower_poly_points = [
        (x, -y) for x, y in upper_poly_points
    ]

    c.add_polygon(np.array(upper_poly_points), layer=(1, 0))
    c.add_polygon(np.array(lower_poly_points), layer=(1, 0))

    return c


if __name__ == "__main__":
    device = directional_coupler()
    device.write_gds("device.gds")
    print("Device written to device.gds")
