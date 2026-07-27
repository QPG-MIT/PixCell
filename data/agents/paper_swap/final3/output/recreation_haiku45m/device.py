import gdsfactory as gf
import json
import numpy as np

# Parametric tunable knobs
wg_width = 1.96
coupling_gap = 0.12
coupling_length = 60.0
input_length = 15.0
output_length = 15.0
sbend_curve_length = 15.0

@gf.cell
def directional_coupler():
    """Directional coupler with smooth S-bends."""
    c = gf.Component()

    y_bottom_mid = 1.01
    y_top_mid = 3.04
    # Coupling region guides move closer by coupling_gap
    y_bottom_couple = 2.0 - coupling_gap / 2.0
    y_top_couple = 2.0 + coupling_gap / 2.0
    delta_y = y_bottom_mid - y_bottom_couple

    x_pos = 0

    # Input section (straight)
    rect_in_bot = [(x_pos, y_bottom_mid - wg_width/2),
                   (x_pos + input_length, y_bottom_mid - wg_width/2),
                   (x_pos + input_length, y_bottom_mid + wg_width/2),
                   (x_pos, y_bottom_mid + wg_width/2)]
    c.add_polygon(rect_in_bot, layer=(1, 0))

    rect_in_top = [(x_pos, y_top_mid - wg_width/2),
                   (x_pos + input_length, y_top_mid - wg_width/2),
                   (x_pos + input_length, y_top_mid + wg_width/2),
                   (x_pos, y_top_mid + wg_width/2)]
    c.add_polygon(rect_in_top, layer=(1, 0))

    x_pos += input_length

    # S-bend bottom using smooth polynomial
    num_pts = 50
    sbend_pts_bot_bottom = []
    sbend_pts_bot_top = []

    for i in range(num_pts + 1):
        t = i / num_pts
        # Smooth easing: sin(pi*t/2) gives smooth start and smooth end
        ease = (1 - np.cos(np.pi * t)) / 2
        y = y_bottom_mid - delta_y * ease
        x = x_pos + sbend_curve_length * t
        sbend_pts_bot_bottom.append((x, y - wg_width/2))
        sbend_pts_bot_top.append((x, y + wg_width/2))

    # Polygon: bottom edge + top edge reversed
    sbend_poly_bottom = sbend_pts_bot_bottom + list(reversed(sbend_pts_bot_top))
    c.add_polygon(sbend_poly_bottom, layer=(1, 0))

    # S-bend top (opposite curvature)
    sbend_pts_top_bottom = []
    sbend_pts_top_top = []

    for i in range(num_pts + 1):
        t = i / num_pts
        ease = (1 - np.cos(np.pi * t)) / 2
        y = y_top_mid + delta_y * ease
        x = x_pos + sbend_curve_length * t
        sbend_pts_top_bottom.append((x, y - wg_width/2))
        sbend_pts_top_top.append((x, y + wg_width/2))

    sbend_poly_top = sbend_pts_top_bottom + list(reversed(sbend_pts_top_top))
    c.add_polygon(sbend_poly_top, layer=(1, 0))

    x_pos += sbend_curve_length

    # Coupling section
    rect_couple_bot = [(x_pos, y_bottom_couple - wg_width/2),
                       (x_pos + coupling_length, y_bottom_couple - wg_width/2),
                       (x_pos + coupling_length, y_bottom_couple + wg_width/2),
                       (x_pos, y_bottom_couple + wg_width/2)]
    c.add_polygon(rect_couple_bot, layer=(1, 0))

    rect_couple_top = [(x_pos, y_top_couple - wg_width/2),
                       (x_pos + coupling_length, y_top_couple - wg_width/2),
                       (x_pos + coupling_length, y_top_couple + wg_width/2),
                       (x_pos, y_top_couple + wg_width/2)]
    c.add_polygon(rect_couple_top, layer=(1, 0))

    x_pos += coupling_length

    # S-bend out bottom (reverse of in)
    sbend_out_bot_bottom = []
    sbend_out_bot_top = []

    for i in range(num_pts + 1):
        t = i / num_pts
        ease = (1 - np.cos(np.pi * t)) / 2
        y = y_bottom_couple + delta_y * ease
        x = x_pos + sbend_curve_length * t
        sbend_out_bot_bottom.append((x, y - wg_width/2))
        sbend_out_bot_top.append((x, y + wg_width/2))

    sbend_poly_out_bottom = sbend_out_bot_bottom + list(reversed(sbend_out_bot_top))
    c.add_polygon(sbend_poly_out_bottom, layer=(1, 0))

    # S-bend out top
    sbend_out_top_bottom = []
    sbend_out_top_top = []

    for i in range(num_pts + 1):
        t = i / num_pts
        ease = (1 - np.cos(np.pi * t)) / 2
        y = y_top_couple - delta_y * ease
        x = x_pos + sbend_curve_length * t
        sbend_out_top_bottom.append((x, y - wg_width/2))
        sbend_out_top_top.append((x, y + wg_width/2))

    sbend_poly_out_top = sbend_out_top_bottom + list(reversed(sbend_out_top_top))
    c.add_polygon(sbend_poly_out_top, layer=(1, 0))

    x_pos += sbend_curve_length

    # Output section
    rect_out_bot = [(x_pos, y_bottom_mid - wg_width/2),
                    (x_pos + output_length, y_bottom_mid - wg_width/2),
                    (x_pos + output_length, y_bottom_mid + wg_width/2),
                    (x_pos, y_bottom_mid + wg_width/2)]
    c.add_polygon(rect_out_bot, layer=(1, 0))

    rect_out_top = [(x_pos, y_top_mid - wg_width/2),
                    (x_pos + output_length, y_top_mid - wg_width/2),
                    (x_pos + output_length, y_top_mid + wg_width/2),
                    (x_pos, y_top_mid + wg_width/2)]
    c.add_polygon(rect_out_top, layer=(1, 0))

    return c

if __name__ == "__main__":
    cell = directional_coupler()
    cell.write_gds("device.gds")
    print(f"Device created: {cell.name}")

    total_length_um = input_length + sbend_curve_length + coupling_length + sbend_curve_length + output_length

    lengths_data = {
        "arms": {
            "bottom": total_length_um,
            "top": total_length_um
        },
        "delta_length_um": 0.0,
        "coupling_length_um": coupling_length
    }

    with open("lengths.json", "w") as f:
        json.dump(lengths_data, f, indent=2)
