"""
2x2 Directional Coupler — Parametric GDSFactory implementation.

Function-defining parametric knobs:
- waveguide_width_um: input/output guide width
- coupler_width_um: central region width (mode overlap, coupling strength)
- coupler_length_um: interaction region length
- taper_length_um: taper expansion length
"""

import gdsfactory as gf
import numpy as np

# === Parametric Contract ===
waveguide_width_um = 0.5
coupler_width_um = 2.2
coupler_length_um = 1.9
taper_length_um = 1.0
layer = (1, 0)


@gf.cell
def directional_coupler_2x2():
    """
    Symmetric 2x2 directional coupler with curved tapered arms.
    """
    c = gf.Component()

    center_x = 0
    center_y = 0
    coupler_half_w = coupler_width_um / 2
    coupler_half_l = coupler_length_um / 2

    # === Central coupler core (smooth ellipse) ===
    theta = np.linspace(0, 2*np.pi, 100)
    ellipse_x = coupler_half_w * np.cos(theta)
    ellipse_y = coupler_half_l * np.sin(theta)
    core_points = np.column_stack([ellipse_x, ellipse_y])
    c.add_polygon(core_points, layer=layer)

    port_length = 0.2

    # === Four Curved Taper Arms ===
    def make_curved_taper_polygon(axis='vertical', direction=1):
        """
        Create taper with moderate bulge for smooth lobes.
        """
        n = 40  # More points for smoothness
        points = []

        if axis == 'vertical':
            for i in range(n):
                t = i / (n - 1)
                y = direction * (coupler_half_l + t * taper_length_um)
                width = waveguide_width_um + t * (coupler_width_um - waveguide_width_um)
                hw = width / 2

                # Moderate bulge
                bulge_factor = np.sin(t * np.pi) * 0.15
                bulge = bulge_factor * coupler_width_um

                if i == 0:
                    points.append((center_x - waveguide_width_um/2, direction * coupler_half_l))

                points.append((center_x - hw - bulge, y))

            for i in range(n-1, -1, -1):
                t = i / (n - 1)
                y = direction * (coupler_half_l + t * taper_length_um)
                width = waveguide_width_um + t * (coupler_width_um - waveguide_width_um)
                hw = width / 2
                bulge_factor = np.sin(t * np.pi) * 0.15
                bulge = bulge_factor * coupler_width_um

                points.append((center_x + hw + bulge, y))

            points.append((center_x + waveguide_width_um/2, direction * coupler_half_l))

        else:  # horizontal
            for i in range(n):
                t = i / (n - 1)
                x = direction * (coupler_half_w + t * taper_length_um)
                width = waveguide_width_um + t * (coupler_width_um - waveguide_width_um)
                hw = width / 2
                bulge_factor = np.sin(t * np.pi) * 0.15
                bulge = bulge_factor * coupler_width_um

                if i == 0:
                    points.append((direction * coupler_half_w, center_y - waveguide_width_um/2))

                points.append((x, center_y - hw - bulge))

            for i in range(n-1, -1, -1):
                t = i / (n - 1)
                x = direction * (coupler_half_w + t * taper_length_um)
                width = waveguide_width_um + t * (coupler_width_um - waveguide_width_um)
                hw = width / 2
                bulge_factor = np.sin(t * np.pi) * 0.15
                bulge = bulge_factor * coupler_width_um

                points.append((x, center_y + hw + bulge))

            points.append((direction * coupler_half_w, center_y + waveguide_width_um/2))

        return np.array(points)

    # Add all four tapers
    top_taper_poly = make_curved_taper_polygon('vertical', 1)
    c.add_polygon(top_taper_poly, layer=layer)

    bottom_taper_poly = make_curved_taper_polygon('vertical', -1)
    c.add_polygon(bottom_taper_poly, layer=layer)

    left_taper_poly = make_curved_taper_polygon('horizontal', -1)
    c.add_polygon(left_taper_poly, layer=layer)

    right_taper_poly = make_curved_taper_polygon('horizontal', 1)
    c.add_polygon(right_taper_poly, layer=layer)

    # === Straight input/output ports ===
    top_port_rect = np.array([
        (center_x - waveguide_width_um/2, coupler_half_l + taper_length_um),
        (center_x + waveguide_width_um/2, coupler_half_l + taper_length_um),
        (center_x + waveguide_width_um/2, coupler_half_l + taper_length_um + port_length),
        (center_x - waveguide_width_um/2, coupler_half_l + taper_length_um + port_length),
    ])
    c.add_polygon(top_port_rect, layer=layer)

    bottom_port_rect = np.array([
        (center_x - waveguide_width_um/2, -coupler_half_l - taper_length_um - port_length),
        (center_x + waveguide_width_um/2, -coupler_half_l - taper_length_um - port_length),
        (center_x + waveguide_width_um/2, -coupler_half_l - taper_length_um),
        (center_x - waveguide_width_um/2, -coupler_half_l - taper_length_um),
    ])
    c.add_polygon(bottom_port_rect, layer=layer)

    left_port_rect = np.array([
        (-coupler_half_w - taper_length_um - port_length, center_y - waveguide_width_um/2),
        (-coupler_half_w - taper_length_um, center_y - waveguide_width_um/2),
        (-coupler_half_w - taper_length_um, center_y + waveguide_width_um/2),
        (-coupler_half_w - taper_length_um - port_length, center_y + waveguide_width_um/2),
    ])
    c.add_polygon(left_port_rect, layer=layer)

    right_port_rect = np.array([
        (coupler_half_w + taper_length_um, center_y - waveguide_width_um/2),
        (coupler_half_w + taper_length_um + port_length, center_y - waveguide_width_um/2),
        (coupler_half_w + taper_length_um + port_length, center_y + waveguide_width_um/2),
        (coupler_half_w + taper_length_um, center_y + waveguide_width_um/2),
    ])
    c.add_polygon(right_port_rect, layer=layer)

    return c


if __name__ == "__main__":
    device = directional_coupler_2x2()
    device.write_gds("device.gds")
    print(f"Device written to device.gds")
