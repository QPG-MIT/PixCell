import gdsfactory as gf

@gf.cell
def trident_coupler_fixed() -> gf.Component:
    """
    Parametric creation of a trident spot-size converter/edge coupler.
    Corrected for accurate visual proportions matching the target geometry.
    """
    c = gf.Component("trident_edge_coupler_fixed")

    # --- Constraints & Dimensions ---
    total_length = 40.0
    total_height = 1.7

    # Adjusted section lengths across the X-axis for better proportion
    l_taper = 26.0      # Long, gradual taper for the center WG
    l_bend = 8.0        # Smooth S-bend
    l_straight = 6.0    # Final straight parallel section

    assert l_taper + l_bend + l_straight == total_length

    layer = (1, 0)

    # --- Calibrated Waveguide Widths ---
    # Center WG is much thinner on the left in the original image
    w_center_left = 0.25
    w_center_right = 0.005 # Almost sharp tip
    
    # Outer WGs start very thin and taper up to their final width
    w_outer_left = 0.08
    w_outer_mid = 0.25     
    w_outer_right = 0.25

    # Gap at the left edge between center and outer WGs
    gap_left = 0.04
    
    # Calculate the Y-centerline for the outer waveguides at the left edge
    y_outer_left = (w_center_left / 2) + gap_left + (w_outer_left / 2)

    # Positioning on the right edge (Constrained by total_height footprint)
    # The top edge of the top waveguide must exactly touch total_height / 2
    y_outer_right = (total_height / 2) - (w_outer_right / 2)


    # --- 1. Center Waveguide ---
    c << gf.components.taper(
        length=l_taper,
        width1=w_center_left,
        width2=w_center_right,
        layer=layer
    )

    # --- Cross-sections for Outer Waveguides ---
    xs_mid = gf.cross_section.cross_section(width=w_outer_mid, layer=layer)
    xs_right = gf.cross_section.cross_section(width=w_outer_right, layer=layer)


    # --- 2. Top Waveguide Assembly ---
    # Taper Section
    top_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_outer_left,
        width2=w_outer_mid,
        layer=layer
    )
    top_taper.move((0, y_outer_left))

    # S-bend Section
    dy = y_outer_right - y_outer_left
    top_bend = c << gf.components.bend_s(
        size=(l_bend, dy),
        cross_section=xs_mid
    )
    top_bend.connect("o1", top_taper.ports["o2"])

    # Straight Section
    top_straight = c << gf.components.straight(
        length=l_straight,
        cross_section=xs_right
    )
    top_straight.connect("o1", top_bend.ports["o2"])


    # --- 3. Bottom Waveguide Assembly (Symmetric) ---
    # Taper Section
    bot_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_outer_left,
        width2=w_outer_mid,
        layer=layer
    )
    bot_taper.move((0, -y_outer_left))

    # S-bend Section
    bot_bend = c << gf.components.bend_s(
        size=(l_bend, -dy),
        cross_section=xs_mid
    )
    bot_bend.connect("o1", bot_taper.ports["o2"])

    # Straight Section
    bot_straight = c << gf.components.straight(
        length=l_straight,
        cross_section=xs_right
    )
    bot_straight.connect("o1", bot_bend.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the device
    device = trident_coupler_fixed()
    
    # Save the GDS file for evaluation
    device.write_gds("trident_coupler.gds")