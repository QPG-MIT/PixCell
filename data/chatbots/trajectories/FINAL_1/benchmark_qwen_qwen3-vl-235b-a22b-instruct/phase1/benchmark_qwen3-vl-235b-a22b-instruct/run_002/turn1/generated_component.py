import gdsfactory as gf

@gf.cell
def curved_waveguide_device():
    c = gf.Component()
    
    # Define cross-section (1.7um wide as per footprint constraint)
    xs = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Create central straight waveguide
    central_wg = c << gf.components.straight(length=40.0, cross_section=xs)
    central_wg.move((0, 0))
    
    # Create top curved waveguide
    # Start with a straight segment, then add an Euler bend
    top_straight = c << gf.components.straight(length=20.0, cross_section=xs)
    top_straight.move((0, 1.7))  # Position above central waveguide
    
    # Create Euler bend for top waveguide
    top_bend = c << gf.components.bend_euler(radius=10.0, angle=45, cross_section=xs)
    top_bend.connect("o1", top_straight.ports["o2"])
    
    # Create bottom curved waveguide (mirror of top)
    bottom_straight = c << gf.components.straight(length=20.0, cross_section=xs)
    bottom_straight.move((0, -1.7))  # Position below central waveguide
    
    # Create Euler bend for bottom waveguide
    bottom_bend = c << gf.components.bend_euler(radius=10.0, angle=-45, cross_section=xs)
    bottom_bend.connect("o1", bottom_straight.ports["o2"])
    
    # Add ports for all waveguides
    c.add_port("central_in", port=central_wg.ports["o1"])
    c.add_port("central_out", port=central_wg.ports["o2"])
    c.add_port("top_in", port=top_straight.ports["o1"])
    c.add_port("top_out", port=top_bend.ports["o2"])
    c.add_port("bottom_in", port=bottom_straight.ports["o1"])
    c.add_port("bottom_out", port=bottom_bend.ports["o2"])
    
    return c

# Create and save the device
device = curved_waveguide_device()
device.write_gds("curved_waveguide_device.gds")