import gdsfactory as gf

@gf.cell
def y_splitter():
    c = gf.Component()
    
    # Define cross-section (width based on footprint constraint)
    xs = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Create the input waveguide (straight section)
    input_wg = c << gf.components.straight(length=15.0, cross_section=xs)
    input_wg.move((0, 0))
    
    # Create the top output waveguide with bend
    # Start with a short straight section at the branching point
    top_straight = c << gf.components.straight(length=5.0, cross_section=xs)
    top_straight.move((15.0, 0))  # Position at end of input waveguide
    
    # Create Euler bend to curve the top output away
    top_bend = c << gf.components.bend_euler(radius=10.0, angle=30, cross_section=xs)
    top_bend.connect("o1", top_straight.ports["o2"])
    
    # Create final straight section for top output
    top_final = c << gf.components.straight(length=20.0, cross_section=xs)
    top_final.connect("o1", top_bend.ports["o2"])
    
    # Create the bottom output waveguide with bend
    # Start with a short straight section at the branching point
    bottom_straight = c << gf.components.straight(length=5.0, cross_section=xs)
    bottom_straight.move((15.0, 0))  # Position at end of input waveguide
    
    # Create Euler bend to curve the bottom output away
    bottom_bend = c << gf.components.bend_euler(radius=10.0, angle=-30, cross_section=xs)
    bottom_bend.connect("o1", bottom_straight.ports["o2"])
    
    # Create final straight section for bottom output
    bottom_final = c << gf.components.straight(length=20.0, cross_section=xs)
    bottom_final.connect("o1", bottom_bend.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=input_wg.ports["o1"])      # Input port
    c.add_port("o2", port=top_final.ports["o2"])     # Top output port
    c.add_port("o3", port=bottom_final.ports["o2"])  # Bottom output port
    
    # Flatten to avoid off-grid instance issues
    c.flatten()
    
    return c

# Create and save the device
device = y_splitter()
device.write_gds("y_splitter.gds")