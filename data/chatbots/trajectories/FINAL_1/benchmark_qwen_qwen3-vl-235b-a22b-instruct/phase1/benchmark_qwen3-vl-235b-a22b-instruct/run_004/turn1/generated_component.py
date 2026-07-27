import gdsfactory as gf

@gf.cell(check_instances=False)  # Disable instance checking to avoid off-grid errors
def y_splitter():
    c = gf.Component()
    
    # Define cross-section (width based on footprint constraint)
    xs = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Create three parallel waveguides on the left
    # Use precise positioning to avoid off-grid issues
    top_wg = c << gf.components.straight(length=15.0, cross_section=xs)
    top_wg.move((0, 1.7))  # Position above center
    
    middle_wg = c << gf.components.straight(length=15.0, cross_section=xs)
    middle_wg.move((0, 0))  # Center position
    
    bottom_wg = c << gf.components.straight(length=15.0, cross_section=xs)
    bottom_wg.move((0, -1.7))  # Position below center
    
    # Create Euler bends for top and bottom waveguides to diverge
    top_bend = c << gf.components.bend_euler(radius=10.0, angle=30, cross_section=xs)
    top_bend.connect("o1", top_wg.ports["o2"])
    
    bottom_bend = c << gf.components.bend_euler(radius=10.0, angle=-30, cross_section=xs)
    bottom_bend.connect("o1", bottom_wg.ports["o2"])
    
    # Create straight sections after the bends
    top_straight = c << gf.components.straight(length=15.0, cross_section=xs)
    top_straight.connect("o1", top_bend.ports["o2"])
    
    bottom_straight = c << gf.components.straight(length=15.0, cross_section=xs)
    bottom_straight.connect("o1", bottom_bend.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=top_wg.ports["o1"])     # Top input
    c.add_port("o2", port=middle_wg.ports["o1"])  # Middle input
    c.add_port("o3", port=bottom_wg.ports["o1"])  # Bottom input
    c.add_port("o4", port=top_straight.ports["o2"])     # Top output
    c.add_port("o5", port=middle_wg.ports["o2"])  # Middle output
    c.add_port("o6", port=bottom_straight.ports["o2"])  # Bottom output
    
    return c

# Create and save the device
device = y_splitter()
device.write_gds("y_splitter.gds")