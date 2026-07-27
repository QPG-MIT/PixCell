import gdsfactory as gf

@gf.cell
def trident_mode_converter() -> gf.Component:
    """
    Parametric generation of a trident spot-size converter / directional coupler.
    Adheres to a bounding footprint of 40.0 um x 1.7 um.
    """
    c = gf.Component("trident_spot_size_converter")

    # Constraint parameters
    footprint_x = 40.0
    footprint_y = 1.7

    # X-axis length segmentation
    len_taper = 24.0
    len_bend = 8.0
    len_straight = footprint_x - len_taper - len_bend  # 8.0

    # Width parameters
    width_center_in = 0.5
    width_center_out = 0.05  # Sharp taper tip
    
    width_outer_in = 0.1
    width_outer_out = 0.4

    # Y-axis positioning logic
    # Calculate target center Y for the outer straight sections (right side)
    # The top edge should exactly hit footprint_y / 2
    y_straight_top = (footprint_y / 2.0) - (width_outer_out / 2.0)
    y_straight_bot = -y_straight_top

    # Position the outer tapers (left side)
    # Chosen to maintain a visible and appropriate gap with the center taper
    y_taper_top = 0.38
    y_taper_bot = -0.38

    # Define common cross sections for constant width extrusion paths
    xs_outer = gf.cross_section.cross_section(width=width_outer_out, layer=(1, 0))

    # --- 1. Central Taper ---
    c << gf.components.taper(
        length=len_taper,
        width1=width_center_in,
        width2=width_center_out,
        layer=(1, 0)
    )

    # --- 2. Top Outer Arm ---
    # Taper section
    top_taper = c << gf.components.taper(
        length=len_taper,
        width1=width_outer_in,
        width2=width_outer_out,
        layer=(1, 0)
    )
    top_taper.movey(y_taper_top)

    # S-Bend section (shifts outward to final Y position)
    top_bend = c << gf.components.bend_s(
        size=(len_bend, y_straight_top - y_taper_top),
        cross_section=xs_outer
    )
    top_bend.connect("o1", top_taper.ports["o2"])

    # Straight routing output section
    top_straight = c << gf.components.straight(
        length=len_straight,
        cross_section=xs_outer
    )
    top_straight.connect("o1", top_bend.ports["o2"])

    # --- 3. Bottom Outer Arm ---
    # Taper section
    bot_taper = c << gf.components.taper(
        length=len_taper,
        width1=width_outer_in,
        width2=width_outer_out,
        layer=(1, 0)
    )
    bot_taper.movey(y_taper_bot)

    # S-Bend section (shifts outward to final negative Y position)
    bot_bend = c << gf.components.bend_s(
        size=(len_bend, y_straight_bot - y_taper_bot),
        cross_section=xs_outer
    )
    bot_bend.connect("o1", bot_taper.ports["o2"])

    # Straight routing output section
    bot_straight = c << gf.components.straight(
        length=len_straight,
        cross_section=xs_outer
    )
    bot_straight.connect("o1", bot_bend.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component and write it to GDS
    device = trident_mode_converter()
    device.write_gds("trident_device.gds")