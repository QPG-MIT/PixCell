import gdsfactory as gf

@gf.cell
def directional_coupler_2x2():
    """
    2x2 Directional coupler with S-bend waveguides.
    Two waveguides approach each other for evanescent coupling,
    then separate again symmetrically.
    
    Footprint: approximately 120 µm x 4 µm
    """
    c = gf.Component()
    
    # Define cross-section
    width = 0.5
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Design parameters adjusted to match target
    port_separation = 3.5    # Larger vertical separation at I/O ports
    coupling_gap = 0.4       # Slightly larger gap in coupling region
    coupling_length = 46.0   # Length of parallel coupling section
    sbend_length = 32.0      # Horizontal length of each S-bend
    io_length = 5.0          # Length of I/O straight sections
    
    # Calculate key positions
    port_y = port_separation / 2  # Y-position of port centers (±1.75 µm)
    coupling_y = (coupling_gap + width) / 2  # Y-position in coupling region (±0.45 µm)
    y_offset = port_y - coupling_y  # Vertical transition in S-bend (1.3 µm)
    
    # Build upper waveguide arm
    in_straight_top = c << gf.components.straight(length=io_length, cross_section=xs)
    in_straight_top.move((0, port_y))
    
    in_sbend_top = c << gf.components.bend_s(size=(sbend_length, -y_offset), cross_section=xs)
    in_sbend_top.connect("o1", in_straight_top.ports["o2"])
    
    coupling_straight_top = c << gf.components.straight(length=coupling_length, cross_section=xs)
    coupling_straight_top.connect("o1", in_sbend_top.ports["o2"])
    
    out_sbend_top = c << gf.components.bend_s(size=(sbend_length, y_offset), cross_section=xs)
    out_sbend_top.connect("o1", coupling_straight_top.ports["o2"])
    
    out_straight_top = c << gf.components.straight(length=io_length, cross_section=xs)
    out_straight_top.connect("o1", out_sbend_top.ports["o2"])
    
    # Build lower waveguide arm
    in_straight_bot = c << gf.components.straight(length=io_length, cross_section=xs)
    in_straight_bot.move((0, -port_y))
    
    in_sbend_bot = c << gf.components.bend_s(size=(sbend_length, y_offset), cross_section=xs)
    in_sbend_bot.connect("o1", in_straight_bot.ports["o2"])
    
    coupling_straight_bot = c << gf.components.straight(length=coupling_length, cross_section=xs)
    coupling_straight_bot.connect("o1", in_sbend_bot.ports["o2"])
    
    out_sbend_bot = c << gf.components.bend_s(size=(sbend_length, -y_offset), cross_section=xs)
    out_sbend_bot.connect("o1", coupling_straight_bot.ports["o2"])
    
    out_straight_bot = c << gf.components.straight(length=io_length, cross_section=xs)
    out_straight_bot.connect("o1", out_sbend_bot.ports["o2"])
    
    # Add ports to component
    c.add_port("o1", port=in_straight_top.ports["o1"])
    c.add_port("o2", port=in_straight_bot.ports["o1"])
    c.add_port("o3", port=out_straight_top.ports["o2"])
    c.add_port("o4", port=out_straight_bot.ports["o2"])
    
    return c


# Create the device and save to GDS
if __name__ == "__main__":
    device = directional_coupler_2x2()
    device.write_gds("directional_coupler_2x2.gds")