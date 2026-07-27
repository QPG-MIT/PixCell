import gdsfactory as gf

@gf.cell
def parallel_waveguide_device():
    """Creates a parallel waveguide device matching the target image."""
    c = gf.Component()
    
    # Adjusted parameters to match target appearance
    wg_width = 1.2  # Wider waveguides to match target
    gap_center = 0.6  # gap between waveguides in coupling region
    gap_ends = 3.0  # vertical separation at input/output
    coupling_length = 60.0  # length of parallel coupling section
    sbend_dx = 30.0  # horizontal length of each S-bend transition
    
    # Create cross-section with wider waveguide
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius=10)
    
    # Calculate vertical offsets for waveguide centers
    # At the ends, waveguides are separated by gap_ends
    # In the middle, they are separated by gap_center
    y_end = (gap_ends) / 2  # distance from centerline at ends
    y_center = (gap_center) / 2  # distance from centerline in middle
    dy = y_end - y_center  # vertical displacement needed in S-bend
    
    # Top waveguide: starts high, bends down to center, stays parallel, bends back up
    top_sbend_left = c << gf.components.bend_s(
        size=(sbend_dx, -dy),  # negative dy: move downward toward center
        cross_section=xs
    )
    top_sbend_left.movey(y_end)  # start at upper position
    
    top_center = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs
    )
    top_center.connect("o1", top_sbend_left.ports["o2"])
    
    top_sbend_right = c << gf.components.bend_s(
        size=(sbend_dx, dy),  # positive dy: move upward away from center
        cross_section=xs
    )
    top_sbend_right.connect("o1", top_center.ports["o2"])
    
    # Bottom waveguide: starts low, bends up to center, stays parallel, bends back down
    bot_sbend_left = c << gf.components.bend_s(
        size=(sbend_dx, dy),  # positive dy: move upward toward center
        cross_section=xs
    )
    bot_sbend_left.movey(-y_end)  # start at lower position
    
    bot_center = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs
    )
    bot_center.connect("o1", bot_sbend_left.ports["o2"])
    
    bot_sbend_right = c << gf.components.bend_s(
        size=(sbend_dx, -dy),  # negative dy: move downward away from center
        cross_section=xs
    )
    bot_sbend_right.connect("o1", bot_center.ports["o2"])
    
    # Add ports for connectivity
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