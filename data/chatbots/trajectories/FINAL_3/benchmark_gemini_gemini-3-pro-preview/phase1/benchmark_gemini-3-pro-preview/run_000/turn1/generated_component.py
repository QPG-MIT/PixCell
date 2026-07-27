import gdsfactory as gf

@gf.cell
def device_coupler():
    """
    Creates a directional coupler based on the provided image and footprint constraints.
    Footprint: 120um x 4um
    """
    c = gf.Component()

    # --- Parameters ---
    total_length = 120.0
    total_height = 4.0
    
    wg_width = 0.5
    coupling_gap = 0.2
    
    # Longitudinal dimensions derived from visual aspect ratios and total length
    l_io = 10.0      # Length of straight input/output sections
    l_bend = 30.0    # Length of S-bends
    l_coup = 40.0    # Length of straight coupling region
    # Check: 10 + 30 + 40 + 30 + 10 = 120.0 (Matches constraint)

    # Vertical dimensions
    # Calculate input/output y-positions to maximize usage of the 4um height
    # Outer edges at y = +/- 2.0. Centers at +/- (2.0 - width/2)
    y_io_offset = (total_height - wg_width) / 2  # = 1.75
    
    # Calculate coupling region y-positions
    # Separated by gap. Centers at +/- (gap + width)/2
    y_coup_offset = (coupling_gap + wg_width) / 2 # = 0.35
    
    # Calculate vertical shift required for S-bends
    # Top arm goes down (negative shift), Bottom arm goes up (positive shift)
    dy = y_io_offset - y_coup_offset  # 1.75 - 0.35 = 1.4
    
    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Component Primitives ---
    
    # Straight sections
    s_io = gf.components.straight(length=l_io, cross_section=xs)
    s_coup = gf.components.straight(length=l_coup, cross_section=xs)
    
    # S-Bends
    # Top In: goes down by dy
    bend_top_in = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    # Top Out: goes up by dy
    bend_top_out = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    
    # Bottom In: goes up by dy
    bend_bot_in = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    # Bottom Out: goes down by dy
    bend_bot_out = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)

    # --- Assembly ---

    # 1. Top Arm Construction
    # Input Straight
    t1 = c << s_io
    t1.move((0, y_io_offset))
    
    # Converging Bend
    t2 = c << bend_top_in
    t2.connect("o1", t1.ports["o2"])
    
    # Coupling Straight
    t3 = c << s_coup
    t3.connect("o1", t2.ports["o2"])
    
    # Diverging Bend
    t4 = c << bend_top_out
    t4.connect("o1", t3.ports["o2"])
    
    # Output Straight
    t5 = c << s_io
    t5.connect("o1", t4.ports["o2"])

    # 2. Bottom Arm Construction
    # Input Straight
    b1 = c << s_io
    b1.move((0, -y_io_offset))
    
    # Converging Bend
    b2 = c << bend_bot_in
    b2.connect("o1", b1.ports["o2"])
    
    # Coupling Straight
    b3 = c << s_coup
    b3.connect("o1", b2.ports["o2"])
    
    # Diverging Bend
    b4 = c << bend_bot_out
    b4.connect("o1", b3.ports["o2"])
    
    # Output Straight
    b5 = c << s_io
    b5.connect("o1", b4.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])

    return c

# Generate and save
if __name__ == "__main__":
    device = device_coupler()
    device.write_gds("directional_coupler.gds")
    device.show()