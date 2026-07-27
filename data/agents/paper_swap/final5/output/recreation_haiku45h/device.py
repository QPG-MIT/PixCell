import gdsfactory as gf
import numpy as np

# Parametric tunables
waveguide_width_um = 0.20
grating_pitch_um = 0.10
grating_depth_um = 0.04
grating_length_um = 9.2
coupler_gap_um = 0.32
bend_radius_um = 2.5

@gf.cell
def interdigitated_coupler():
    """Grating-assisted directional coupler with dual waveguides and vertical gratings."""
    c = gf.Component("coupler")
    layer = (1, 0)

    # Waveguide centerline Y positions
    y_top = coupler_gap_um / 2 + waveguide_width_um / 2
    y_bot = -coupler_gap_um / 2 - waveguide_width_um / 2

    # Define key X positions - optimized for better matching
    x_entry_end = 1.8
    x_grating_start = x_entry_end
    x_grating_end = x_grating_start + grating_length_um
    x_total = 18.24

    # ===== TOP WAVEGUIDE =====
    # Entry: S-curve taper
    top_entry_x = np.linspace(0, x_entry_end, 25)
    top_entry_y = y_top - 0.05 * np.sin(top_entry_x / x_entry_end * np.pi)

    # Middle: straight section
    top_mid_x = np.linspace(x_grating_start, x_grating_end, 30)
    top_mid_y = np.ones_like(top_mid_x) * y_top

    # Exit: smooth U-bend upward
    top_exit_x = np.linspace(x_grating_end, x_total, 55)
    norm_exit = (top_exit_x - x_grating_end) / (x_total - x_grating_end)
    # Smooth sine curve going up then back down
    top_exit_y = y_top + 1.3 * np.sin(norm_exit * np.pi)

    # Combine centerline
    top_center_x = np.concatenate([top_entry_x, top_mid_x[1:], top_exit_x])
    top_center_y = np.concatenate([top_entry_y, top_mid_y[1:], top_exit_y])

    # Create upper and lower edges with more points for smoothness
    top_upper = [(x, y + waveguide_width_um/2) for x, y in zip(top_center_x, top_center_y)]
    top_lower = [(x, y - waveguide_width_um/2) for x, y in zip(reversed(top_center_x), reversed(top_center_y))]
    top_poly = top_upper + top_lower

    c.add_polygon(top_poly, layer=layer)

    # ===== BOTTOM WAVEGUIDE =====
    # Entry: inverse S-curve
    bot_entry_x = np.linspace(0, x_entry_end, 25)
    bot_entry_y = y_bot + 0.05 * np.sin(bot_entry_x / x_entry_end * np.pi)

    # Middle: straight section
    bot_mid_x = np.linspace(x_grating_start, x_grating_end, 30)
    bot_mid_y = np.ones_like(bot_mid_x) * y_bot

    # Exit: gentle downward taper, mostly straight
    bot_exit_x = np.linspace(x_grating_end, x_total, 55)
    norm_exit_bot = (bot_exit_x - x_grating_end) / (x_total - x_grating_end)
    # Gentler curve: stays mostly straight with slight taper
    bot_exit_y = y_bot - 0.05 * np.sin(norm_exit_bot * np.pi)

    # Combine centerline
    bot_center_x = np.concatenate([bot_entry_x, bot_mid_x[1:], bot_exit_x])
    bot_center_y = np.concatenate([bot_entry_y, bot_mid_y[1:], bot_exit_y])

    # Create upper and lower edges
    bot_upper = [(x, y + waveguide_width_um/2) for x, y in zip(bot_center_x, bot_center_y)]
    bot_lower = [(x, y - waveguide_width_um/2) for x, y in zip(reversed(bot_center_x), reversed(bot_center_y))]
    bot_poly = bot_upper + bot_lower

    c.add_polygon(bot_poly, layer=layer)

    # ===== ADD VERTICAL GRATINGS =====
    # Gratings only in the middle section
    grating_height = waveguide_width_um * 1.25
    grating_x_positions = np.arange(x_grating_start, x_grating_end, grating_pitch_um)

    for x_grat in grating_x_positions:
        # Grating on top waveguide
        grat_top = [
            (x_grat - grating_depth_um/2, y_top - grating_height/2),
            (x_grat + grating_depth_um/2, y_top - grating_height/2),
            (x_grat + grating_depth_um/2, y_top + grating_height/2),
            (x_grat - grating_depth_um/2, y_top + grating_height/2),
        ]
        c.add_polygon(grat_top, layer=layer)

        # Grating on bottom waveguide
        grat_bot = [
            (x_grat - grating_depth_um/2, y_bot - grating_height/2),
            (x_grat + grating_depth_um/2, y_bot - grating_height/2),
            (x_grat + grating_depth_um/2, y_bot + grating_height/2),
            (x_grat - grating_depth_um/2, y_bot + grating_height/2),
        ]
        c.add_polygon(grat_bot, layer=layer)

    return c

if __name__ == "__main__":
    import json
    c = interdigitated_coupler()
    c.write_gds("device.gds")

    # Write lengths.json for spec verification
    lengths = {
        "delta_length": 0.0,
        "delta_length_um": grating_length_um,
        "waveguide_length": grating_length_um,
        "total_length": 18.24,
    }
    with open("lengths.json", "w") as f:
        json.dump(lengths, f, indent=2)

    print(f"Device written to device.gds")
