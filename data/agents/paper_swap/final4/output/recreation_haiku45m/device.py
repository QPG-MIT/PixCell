import gdsfactory as gf
import numpy as np

# Parametric knobs for directional coupler
coupling_length_um = 18.0
gap_um = 0.4
wg_width_center_um = 1.3
wg_width_edge_um = 0.8

@gf.cell
def directional_coupler():
    """
    Directional coupler with tapered parallel waveguides.
    Function knobs:
    - coupling_length_um: length of interaction region
    - gap_um: gap between waveguides (edge-to-edge)
    - wg_width_center_um: waveguide width at center
    - wg_width_edge_um: waveguide width at edges
    """
    c = gf.Component()

    n_pts = 300
    x_vals = np.linspace(0, coupling_length_um, n_pts)

    # Taper profile: width varies from edge to center
    def get_width(x):
        t = x / coupling_length_um
        # Minimum at edges (t=0 or t=1), maximum at center (t=0.5)
        width = wg_width_edge_um + (wg_width_center_um - wg_width_edge_um) * np.sin(np.pi * t) ** 2
        return width

    # Upper waveguide
    y_upper_center = 0.85
    pts_upper_top = []
    for x in x_vals:
        width = get_width(x)
        y = y_upper_center + width / 2
        pts_upper_top.append([x, y])

    pts_upper_bottom = []
    for x in reversed(x_vals):
        width = get_width(x)
        y = y_upper_center - width / 2
        pts_upper_bottom.append([x, y])

    pts_upper = pts_upper_top + pts_upper_bottom
    c.add_polygon(pts_upper, layer=(1, 0))

    # Lower waveguide (symmetric)
    y_lower_center = -0.85
    pts_lower_top = []
    for x in x_vals:
        width = get_width(x)
        y = y_lower_center + width / 2
        pts_lower_top.append([x, y])

    pts_lower_bottom = []
    for x in reversed(x_vals):
        width = get_width(x)
        y = y_lower_center - width / 2
        pts_lower_bottom.append([x, y])

    pts_lower = pts_lower_top + pts_lower_bottom
    c.add_polygon(pts_lower, layer=(1, 0))

    return c

if __name__ == "__main__":
    c = directional_coupler()
    c.write_gds("device.gds")
    print("GDS written to device.gds")
