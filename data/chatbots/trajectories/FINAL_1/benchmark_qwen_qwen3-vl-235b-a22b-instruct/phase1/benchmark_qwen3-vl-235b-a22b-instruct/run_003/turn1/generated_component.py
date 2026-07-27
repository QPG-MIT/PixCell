import gdsfactory as gf

@gf.cell
def y_junction():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create two straight waveguides on the left
    wg1 = c << gf.components.straight(length=10, cross_section=xs)
    wg2 = c << gf.components.straight(length=10, cross_section=xs)
    
    # Position wg2 below wg1 with a small gap
    wg2.movey(-0.7)  # Assuming 0.7μm from center to center, giving 0.2μm gap if width=0.5μm
    
    # Create two Euler bends to separate the waveguides
    # Upper bend (going up and right)
    bend_upper = c << gf.components.bend_euler(radius=15, angle=30, cross_section=xs)
    bend_upper.connect("o1", wg1.ports["o2"])
    
    # Lower bend (going down and right)
    bend_lower = c << gf.components.bend_euler(radius=15, angle=-30, cross_section=xs)
    bend_lower.connect("o1", wg2.ports["o2"])
    
    # Add ports for the output
    c.add_port("o1", port=bend_upper.ports["o2"])
    c.add_port("o2", port=bend_lower.ports["o2"])
    
    # Add input ports
    c.add_port("o3", port=wg1.ports["o1"])
    c.add_port("o4", port=wg2.ports["o1"])
    
    return c

# Create the device
device = y_junction()

# Write to GDS file
device.write_gds("y_junction.gds")