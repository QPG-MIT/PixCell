"""4-port star coupler with 4-fold symmetric lobes, asymmetric port lengths."""
import gdsfactory as gf
from gdsfactory.typings import LayerSpec
import numpy as np

# === TUNABLES (function-defining knobs) ===
lobe_major_um = 1.00     # ellipse major axis (slightly smaller)
lobe_minor_um = 0.50     # ellipse minor axis (thinner lobes)
lobe_overlap_um = 0.25   # how much lobes overlap at center

# Port parameters (asymmetric lengths)
h_port_width_um = 0.18   # horizontal port width
h_port_length_um = 0.68  # horizontal port length (extend more)
v_port_width_um = 0.18   # vertical port width
v_port_length_um = 0.55  # vertical port length (shortened)

# === FIXED PARAMETERS ===
layer: LayerSpec = (1, 0)


@gf.cell
def star_coupler_4port() -> gf.Component:
    """4-port star coupler with symmetric lobes and asymmetric port lengths."""
    c = gf.Component()
    n_pts = 64
    theta = np.linspace(0, 2 * np.pi, n_pts)

    # Create base ellipse points (horizontal orientation)
    x_base = lobe_major_um * np.cos(theta)
    y_base = lobe_minor_um * np.sin(theta)

    offset = lobe_major_um - lobe_overlap_um

    # Right lobe (horizontal)
    pts_right = np.column_stack([x_base + offset, y_base])
    c.add_polygon(pts_right, layer=layer)

    # Left lobe (horizontal)
    pts_left = np.column_stack([-x_base - offset, y_base])
    c.add_polygon(pts_left, layer=layer)

    # Top lobe (vertical - rotate the ellipse 90 degrees)
    pts_top = np.column_stack([y_base, x_base + offset])
    c.add_polygon(pts_top, layer=layer)

    # Bottom lobe (vertical)
    pts_bot = np.column_stack([y_base, -x_base - offset])
    c.add_polygon(pts_bot, layer=layer)

    # Horizontal port waveguides (short, straight)
    h_wg_start = lobe_major_um + offset - 0.02
    # Right port
    c.add_polygon([
        (h_wg_start, -h_port_width_um / 2),
        (h_wg_start + h_port_length_um, -h_port_width_um / 2),
        (h_wg_start + h_port_length_um, h_port_width_um / 2),
        (h_wg_start, h_port_width_um / 2),
    ], layer=layer)
    # Left port
    c.add_polygon([
        (-h_wg_start, -h_port_width_um / 2),
        (-h_wg_start - h_port_length_um, -h_port_width_um / 2),
        (-h_wg_start - h_port_length_um, h_port_width_um / 2),
        (-h_wg_start, h_port_width_um / 2),
    ], layer=layer)

    # Vertical port waveguides (long, tapered from lobe width)
    v_wg_start = lobe_major_um + offset - 0.02
    taper_start_w = lobe_minor_um * 0.55  # start wider at lobe junction

    # Top port - tapered
    c.add_polygon([
        (-taper_start_w / 2, v_wg_start),
        (taper_start_w / 2, v_wg_start),
        (v_port_width_um / 2, v_wg_start + v_port_length_um),
        (-v_port_width_um / 2, v_wg_start + v_port_length_um),
    ], layer=layer)

    # Bottom port - tapered
    c.add_polygon([
        (-taper_start_w / 2, -v_wg_start),
        (taper_start_w / 2, -v_wg_start),
        (v_port_width_um / 2, -v_wg_start - v_port_length_um),
        (-v_port_width_um / 2, -v_wg_start - v_port_length_um),
    ], layer=layer)

    return c


if __name__ == "__main__":
    c = star_coupler_4port()
    c.write_gds("experiments/paper_swap/final6/output/recreation_opus45m/device.gds")
    print(f"GDS written. Bounds: {c.dbbox()}")
