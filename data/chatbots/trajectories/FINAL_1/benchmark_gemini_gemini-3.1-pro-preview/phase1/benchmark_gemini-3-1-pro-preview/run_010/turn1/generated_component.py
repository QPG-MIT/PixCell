import gdsfactory as gf

@gf.cell
def trident_edge_coupler():
    """
    Parametric assembly of a trident edge coupler / spot size converter.
    Matches a precise footprint of 40.0um x 1.7um.
    """
    c = gf.Component("trident_coupler")

    # Layer definition to ensure consistency
    layer = (1, 0)

    # --- Length Parameters ---
    # Total X length = 24.0 + 10.0 + 6.0 = 40.0 um
    l_taper = 24.0     # Initial tapering region
    l_bend = 10.0      # Outward S-bend transition
    l_straight = 6.0   # Final parallel routing

    # --- Width Parameters ---
    w_center_in = 0.5   # Central waveguide starting width
    w_center_out = 0.05 # Central waveguide ending tip width (sharp point)
    
    w_outer_in = 0.1    # Outer waveguides starting tip width
    w_outer_out = 0.5   # Outer waveguides finalized width

    # --- Y-Axis Positioning Parameters ---
    # Max Y spread calculates to exactly 1.7um footprint height
    # Top WG end center Y = 0.6, width = 0.5 -> max Y = 0.6 + 0.25 = 0.85
    # Bottom WG end center Y = -0.6, width = 0.5 -> min Y = -0.6 - 0.25 = -0.85
    # Total height = 0.85 - (-0.85) = 1.7 um
    y_start_outer = 0.4  # Starting center offset for outer tapers
    y_end_outer = 0.6    # Ending center offset for parallel straights
    dy_bend = y_end_outer - y_start_outer

    # Standardized cross-section for the S-bends and final straight segments
    xs_outer = gf.cross_section.cross_section(width=w_outer_out, layer=layer)

    # 1. --- Central Arm ---
    # Straight taper decaying to a tip
    c << gf.components.taper(
        length=l_taper,
        width1=w_center_in,
        width2=w_center_out,
        layer=layer
    )

    # 2. --- Top Arm ---
    # Tapering up, expanding away via S-bend, then going straight
    top_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_outer_in,
        width2=w_outer_out,
        layer=layer
    )
    top_taper.movey(y_start_outer)

    top_bend = c << gf.components.bend_s(
        size=(l_bend, dy_bend),
        cross_section=xs_outer
    )
    top_bend.connect("o1", top_taper.ports["o2"])

    top_straight = c << gf.components.straight(
        length=l_straight,
        cross_section=xs_outer
    )
    top_straight.connect("o1", top_bend.ports["o2"])

    # 3. --- Bottom Arm ---
    # Symmetric reflection of the Top Arm behavior
    bottom_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_outer_in,
        width2=w_outer_out,
        layer=layer
    )
    bottom_taper.movey(-y_start_outer)

    bottom_bend = c << gf.components.bend_s(
        size=(l_bend, -dy_bend),
        cross_section=xs_outer
    )
    bottom_bend.connect("o1", bottom_taper.ports["o2"])

    bottom_straight = c << gf.components.straight(
        length=l_straight,
        cross_section=xs_outer
    )
    bottom_straight.connect("o1", bottom_bend.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the component and write to GDS file
    device = trident_edge_coupler()
    device.write_gds("trident_edge_coupler.gds")