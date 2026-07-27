import gdsfactory as gf

@gf.cell
def trident_edge_coupler():
    """
    Parametric assembly of a trident edge coupler.
    Refined to create a constant, narrow gap in the taper region 
    to match the target rendering precisely.
    Footprint constraint: 40.0um x 1.7um.
    """
    c = gf.Component("trident_coupler")

    # --- Refined Proportional Length Parameters ---
    # Extending the taper and shortening the bend to match the image's smooth swoop
    l_taper = 22.0     
    l_bend = 12.0      
    l_straight = 6.0   
    # Total X length = 22.0 + 12.0 + 6.0 = 40.0 um

    # --- Width Parameters ---
    w_center_in = 0.5    # Central waveguide starting width
    w_center_out = 0.05  # Central waveguide ending sharp tip
    
    w_outer_in = 0.05    # Outer waveguides starting sharp tip
    w_outer_out = 0.5    # Outer waveguides finalized width

    # --- Constant Gap Alignment ---
    # The target image features a very thin, consistent white gap.
    # To keep the gap perfectly constant while all arms taper, the sum of 
    # the half-widths must be constant, and we use a fixed center offset.
    gap = 0.05 
    
    # Calculate required Y offset for outer tapers to achieve the exact gap at the start
    # y_center = gap + (outer_half_width) + (center_half_width)
    y_start_outer = gap + (w_outer_in / 2) + (w_center_in / 2)
    # y_start_outer evaluates to: 0.05 + 0.025 + 0.25 = 0.325 um
    
    # Mathematical check: Gap at the end of the taper = 0.325 - (0.5/2) - (0.05/2) = 0.05 um. 
    # This guarantees the inner edges are perfectly parallel to the center arm's edges.

    # --- Target Footprint Y Alignment ---
    # To hit exactly 1.7 um total height: max Y = 0.85 um.
    # Max Y = y_end_outer + (w_outer_out / 2) -> 0.85 = y_end_outer + 0.25
    y_end_outer = 0.6
    dy_bend = y_end_outer - y_start_outer

    # Standardized cross-section for the S-bends and final straight segments
    xs_outer = gf.cross_section.cross_section(width=w_outer_out)

    # 1. --- Central Arm ---
    c << gf.components.taper(
        length=l_taper,
        width1=w_center_in,
        width2=w_center_out
    )

    # 2. --- Top Arm ---
    top_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_outer_in,
        width2=w_outer_out
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
    # Symmetric reflection 
    bottom_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_outer_in,
        width2=w_outer_out
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
    device = trident_edge_coupler()
    device.write_gds("trident_edge_coupler.gds")