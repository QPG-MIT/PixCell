import gdsfactory as gf

@gf.cell
def y_splitter():
    c = gf.Component()
    
    # Define cross-section (width based on footprint constraint)
    xs = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Create the main straight waveguide (middle)
    main_wg = c << gf.components.straight(length=40.0, cross_section=xs)
    main_wg.move((0, 0))
    
    # Create the top waveguide that curves away
    # Start with a straight section parallel to main waveguide
    top_straight = c << gf.components.straight(length=10.0, cross_section=xs)
    top_straight.move((0, 1.7))  # Position above main waveguide
    
    # Create Euler bend to curve away
    top_bend = c << gf.components.bend_euler(radius=10.0, angle=30, cross_section=xs)
    top_bend.connect("o1", top_straight.ports["o2"])
    
    # Create final straight section
    top_final = c << gf.components.straight(length=20.0, cross_section=xs)
    top_final.connect("o1", top_bend.ports["o2"])
    
    # Create the bottom waveguide that curves away
    # Start with a straight section parallel to main waveguide
    bottom_straight = c << gf.components.straight(length=10.0, cross_section=xs)
    bottom_straight.move((0, -1.7))  # Position below main waveguide
    
    # Create Euler bend to curve away
    bottom_bend = c << gf.components.bend_euler(radius=10.0, angle=-30, cross_section=xs)
    bottom_bend.connect("o1", bottom_straight.ports["o2"])
    
    # Create final straight section
    bottom_final = c << gf.components.straight(length=20.0, cross_section=xs)
    bottom_final.connect("o1", bottom_bend.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=main_wg.ports["o1"])      # Main input
    c.add_port("o2", port=top_straight.ports["o1"]) # Top input
    c.add_port("o3", port=bottom_straight.ports["o1"]) # Bottom input
    c.add_port("o4", port=main_wg.ports["o2"])      # Main output
    c.add_port("o5", port=top_final.ports["o2"])    # Top output
    c.add_port("o6", port=bottom_final.ports["o2"]) # Bottom output
    
    # Flatten to avoid off-grid instance issues
    c.flatten()
    
    return c

# Create and save the device
device = y_splitter()
device.write_gds("y_splitter.gds")