import gdsfactory as gf

@gf.cell
def s_bend_device():
    c = gf.Component()
    
    # Create a cross-section for the waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a path for the S-bend
    # Start with a straight segment, then add smooth curves to form the S-shape
    p = gf.path.straight(length=3)  # Start with a short straight segment
    p.append(gf.path.euler(radius=5, angle=90, p=0.5))  # First bend (90 degrees)
    p.append(gf.path.euler(radius=5, angle=-90, p=0.5))  # Second bend (-90 degrees)
    p.append(gf.path.straight(length=3))  # End with a short straight segment
    
    # Extrude the path to create the waveguide
    wg1 = c << gf.path.extrude(p, cross_section=xs)
    
    # Create a second waveguide below the first one (parallel)
    wg2 = c << gf.path.extrude(p, cross_section=xs)
    wg2.movey(-1.0)  # Move the second waveguide down by 1.0 µm
    
    # Expose the input and output ports
    # For the first waveguide
    c.add_port("o1_1", port=wg1.ports["o1"])
    c.add_port("o2_1", port=wg1.ports["o2"])
    
    # For the second waveguide
    c.add_port("o1_2", port=wg2.ports["o1"])
    c.add_port("o2_2", port=wg2.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_device()
device.write_gds("s_bend_device.gds")