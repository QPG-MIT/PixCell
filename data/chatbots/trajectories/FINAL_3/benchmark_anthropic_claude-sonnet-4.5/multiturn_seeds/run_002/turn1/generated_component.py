import gdsfactory as gf

@gf.cell
def parallel_waveguide_device():
    """Creates a parallel waveguide device with S-bends at both ends."""
    c = gf.Component()
    
    # Parameters to match 120 x 4 um footprint
    wg_width = 0.5  # waveguide width in um
    gap_center = 0.5  # gap between waveguides in center (coupling region)
    gap_ends = 3.0  # vertical separation at input/output
    coupling_length = 50.0  # length of parallel coupling section
    sbend_dx = 35.0  # horizontal length of S-bend transition (increased for larger radius)
    
    # Create cross-section with explicit min radius
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius=10)
    
    # Calculate vertical offsets
    y_center = (gap_center + wg_width) / 2  # center position of waveguide
    y_end = (gap_ends + wg_width) / 2  # end position of waveguide
    dy = y_end - y_center  # vertical displacement in S-bend
    
    # Top waveguide components
    top_sbend_left = c << gf.components.bend_s(
        size=(sbend_dx, -dy), 
        cross_section=xs
    )
    top_sbend_left.movey(y_end)
    
    top_center = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs
    )
    top_center.connect("o1", top_sbend_left.ports["o2"])
    
    top_sbend_right = c << gf.components.bend_s(
        size=(sbend_dx, dy), 
        cross_section=xs
    )
    top_sbend_right.connect("o1", top_center.ports["o2"])
    
    # Bottom waveguide (mirror of top)
    bot_sbend_left = c << gf.components.bend_s(
        size=(sbend_dx, dy), 
        cross_section=xs
    )
    bot_sbend_left.movey(-y_end)
    
    bot_center = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs
    )
    bot_center.connect("o1", bot_sbend_left.ports["o2"])
    
    bot_sbend_right = c << gf.components.bend_s(
        size=(sbend_dx, -dy), 
        cross_section=xs
    )
    bot_sbend_right.connect("o1", bot_center.ports["o2"])
    
    # Add ports
    c.add_port("top_in", port=top_sbend_left.ports["o1"])
    c.add_port("top_out", port=top_sbend_right.ports["o2"])
    c.add_port("bot_in", port=bot_sbend_left.ports["o1"])
    c.add_port("bot_out", port=bot_sbend_right.ports["o2"])
    
    return c

# Create the device
device = parallel_waveguide_device()

# Save to GDS
device.write_gds("parallel_waveguide_device.gds")

# Optional: show the device
device.show()