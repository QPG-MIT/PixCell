import gdsfactory as gf

@gf.cell
def waveguide_crossing():
    """
    2x2 waveguide structure with smooth S-bends.
    Two waveguides converge to the center and diverge again.
    Footprint: 120 um x 4 um
    """
    c = gf.Component()
    
    # Parameters
    width = 0.5
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Geometry - adjusted for visible smooth curves
    total_length = 120
    port_offset = 1.5  # Vertical offset from center
    sbend_length = 30  # Horizontal span of each S-bend
    middle_length = total_length - 2 * sbend_length  # 60 um straight section
    
    # === Upper waveguide ===
    # S-bend: upper-left down to center
    sbend_in_up = c << gf.components.bend_s(
        size=(sbend_length, -port_offset), 
        cross_section=xs
    )
    sbend_in_up.move((0, port_offset))
    
    # Straight middle section
    straight_up = c << gf.components.straight(length=middle_length, cross_section=xs)
    straight_up.connect("o1", sbend_in_up.ports["o2"])
    
    # S-bend: center up to upper-right
    sbend_out_up = c << gf.components.bend_s(
        size=(sbend_length, port_offset), 
        cross_section=xs
    )
    sbend_out_up.connect("o1", straight_up.ports["o2"])
    
    # === Lower waveguide ===
    # S-bend: lower-left up to center
    sbend_in_lo = c << gf.components.bend_s(
        size=(sbend_length, port_offset), 
        cross_section=xs
    )
    sbend_in_lo.move((0, -port_offset))
    
    # Straight middle section
    straight_lo = c << gf.components.straight(length=middle_length, cross_section=xs)
    straight_lo.connect("o1", sbend_in_lo.ports["o2"])
    
    # S-bend: center down to lower-right
    sbend_out_lo = c << gf.components.bend_s(
        size=(sbend_length, -port_offset), 
        cross_section=xs
    )
    sbend_out_lo.connect("o1", straight_lo.ports["o2"])
    
    # Add ports
    c.add_port("o1", port=sbend_in_up.ports["o1"])
    c.add_port("o2", port=sbend_out_up.ports["o2"])
    c.add_port("o3", port=sbend_in_lo.ports["o1"])
    c.add_port("o4", port=sbend_out_lo.ports["o2"])
    
    return c

# Create and save
device = waveguide_crossing()
device.write_gds("waveguide_crossing.gds")