"""
Parametric directional coupler with grating couplers (final, optimized).
Recreated from paper_swap/final5/device_bw.png
Footprint: 18.24 um (length) x 0.7 um (height)
"""

import gdsfactory as gf

# === Function-defining knobs (top-level tunables) ===
width_um = 0.41  # Waveguide core width
gap_um = 0.27  # Gap between waveguides
entrance_curve_length_um = 1.6  # Entrance taper length
exit_curve_length_um = 2.3  # Exit taper length
grating_pitch_um = 0.38  # Grating period
grating_duty_cycle = 0.53  # Grating fill fraction
grating_tooth_depth_um = 0.09  # Tooth depth

LAYER = (1, 0)

@gf.cell
def directional_coupler_with_grating() -> gf.Component:
    """
    Two-waveguide directional coupler with grating couplers.
    """
    c = gf.Component()
    y_upper = gap_um / 2

    # Upper waveguide entrance
    entrance_end_x = entrance_curve_length_um
    c.add_polygon(
        [
            [0, y_upper],
            [entrance_end_x, y_upper - width_um/2],
            [entrance_end_x, y_upper + width_um/2]
        ],
        layer=LAYER
    )

    # Grating section positions
    grating_start_x = entrance_end_x
    grating_end_x = 18.24 - exit_curve_length_um
    grating_length = grating_end_x - grating_start_x

    # Upper core waveguide
    c.add_polygon(
        [
            [grating_start_x, y_upper - width_um/2],
            [grating_end_x, y_upper - width_um/2],
            [grating_end_x, y_upper + width_um/2],
            [grating_start_x, y_upper + width_um/2]
        ],
        layer=LAYER
    )

    # Upper grating teeth
    num_teeth = int(grating_length / grating_pitch_um)
    tooth_width = grating_pitch_um * grating_duty_cycle

    for i in range(num_teeth):
        x_t = grating_start_x + i * grating_pitch_um
        if x_t + tooth_width > grating_end_x:
            break
        c.add_polygon(
            [
                [x_t, y_upper + width_um/2],
                [x_t + tooth_width, y_upper + width_um/2],
                [x_t + tooth_width, y_upper + width_um/2 + grating_tooth_depth_um],
                [x_t, y_upper + width_um/2 + grating_tooth_depth_um]
            ],
            layer=LAYER
        )

    # Upper exit taper
    exit_start_x = grating_end_x
    exit_end_x = 18.24
    c.add_polygon(
        [
            [exit_start_x, y_upper - width_um/2],
            [exit_start_x, y_upper + width_um/2],
            [exit_end_x, y_upper]
        ],
        layer=LAYER
    )

    # ===== LOWER WAVEGUIDE (mirror) =====
    y_lower = -gap_um / 2

    # Lower entrance
    c.add_polygon(
        [
            [0, y_lower],
            [entrance_end_x, y_lower + width_um/2],
            [entrance_end_x, y_lower - width_um/2]
        ],
        layer=LAYER
    )

    # Lower core waveguide
    c.add_polygon(
        [
            [grating_start_x, y_lower - width_um/2],
            [grating_end_x, y_lower - width_um/2],
            [grating_end_x, y_lower + width_um/2],
            [grating_start_x, y_lower + width_um/2]
        ],
        layer=LAYER
    )

    # Lower grating teeth
    for i in range(num_teeth):
        x_t = grating_start_x + i * grating_pitch_um
        if x_t + tooth_width > grating_end_x:
            break
        c.add_polygon(
            [
                [x_t, y_lower - width_um/2],
                [x_t + tooth_width, y_lower - width_um/2],
                [x_t + tooth_width, y_lower - width_um/2 - grating_tooth_depth_um],
                [x_t, y_lower - width_um/2 - grating_tooth_depth_um]
            ],
            layer=LAYER
        )

    # Lower exit taper
    c.add_polygon(
        [
            [exit_start_x, y_lower + width_um/2],
            [exit_start_x, y_lower - width_um/2],
            [exit_end_x, y_lower]
        ],
        layer=LAYER
    )

    # Central connection bar
    c.add_polygon(
        [
            [grating_start_x, -0.05],
            [grating_end_x, -0.05],
            [grating_end_x, 0.05],
            [grating_start_x, 0.05]
        ],
        layer=LAYER
    )

    return c

if __name__ == "__main__":
    c = directional_coupler_with_grating()
    c.write_gds("device.gds")
    print(f"GDS written to device.gds")
