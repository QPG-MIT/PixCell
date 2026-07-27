import gdsfactory as gf
import numpy as np

# Tunables - function-defining parameters
input_width = 1.48  # Width at input/output ports (slightly wider)
taper_width = 1.28  # Width in coupling region
gap = 0.08  # Vertical separation in coupling region (tighter)
coupling_length = 10.0  # Length of parallel coupling section (reduced)
taper_length = 4.0  # Length of transition (longer for more curve)

@gf.cell
def smooth_taper_segment(length, width1, width2, y_center, n_points=50):
    """Create a smooth taper using cosine transition for width."""
    c = gf.Component()

    x = np.linspace(0, length, n_points)

    # Smooth width transition using cosine (S-curve)
    t = x / length  # Normalized position 0 to 1
    width_t = width1 + (width2 - width1) * (1 - np.cos(np.pi * t)) / 2

    # Build top and bottom edge points
    top_points = np.column_stack([x, y_center + width_t/2])
    bottom_points = np.column_stack([x, y_center - width_t/2])

    # Create closed polygon: top edge forward, bottom edge backward
    points = np.vstack([top_points, bottom_points[::-1]])

    c.add_polygon(points, layer=(1, 0))
    return c

@gf.cell
def straight_segment(length, width, y_center):
    """Create a straight waveguide."""
    c = gf.Component()

    points = [
        (0, y_center - width/2),
        (length, y_center - width/2),
        (length, y_center + width/2),
        (0, y_center + width/2),
    ]

    c.add_polygon(points, layer=(1, 0))
    return c

@gf.cell
def directional_coupler():
    c = gf.Component()

    # Calculate vertical positions
    upper_y = gap/2 + taper_width/2
    lower_y = -(gap/2 + taper_width/2)

    # Upper waveguide - left taper
    upper_left = c << smooth_taper_segment(taper_length, input_width, taper_width, upper_y)
    upper_left.move((0, 0))

    # Upper waveguide - coupling section
    upper_coupling = c << straight_segment(coupling_length, taper_width, upper_y)
    upper_coupling.move((taper_length, 0))

    # Upper waveguide - right taper
    upper_right = c << smooth_taper_segment(taper_length, taper_width, input_width, upper_y)
    upper_right.move((taper_length + coupling_length, 0))

    # Lower waveguide - left taper
    lower_left = c << smooth_taper_segment(taper_length, input_width, taper_width, lower_y)
    lower_left.move((0, 0))

    # Lower waveguide - coupling section
    lower_coupling = c << straight_segment(coupling_length, taper_width, lower_y)
    lower_coupling.move((taper_length, 0))

    # Lower waveguide - right taper
    lower_right = c << smooth_taper_segment(taper_length, taper_width, input_width, lower_y)
    lower_right.move((taper_length + coupling_length, 0))

    return c

if __name__ == "__main__":
    c = directional_coupler()
    c.write_gds("experiments/paper_swap/final4/output/recreation_sonnet45m/device.gds")
    print("GDS written successfully")
