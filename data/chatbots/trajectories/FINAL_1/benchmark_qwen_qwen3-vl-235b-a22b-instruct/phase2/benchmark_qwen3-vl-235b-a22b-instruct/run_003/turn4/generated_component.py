import gdsfactory as gf

@gf.cell
def curved_waveguide():
    c = gf.Component()
    
    # Define cross-section for waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a straight waveguide segment
    wg_straight = c << gf.components.straight(length=10, cross_section=xs)
    
    # Create a smooth bend (Euler bend) that curves upward
    bend = c << gf.components.bend_euler(radius=15, angle=45, cross_section=xs)
    
    # Connect the bend to the straight waveguide
    bend.connect("o1", wg_straight.ports["o2"])
    
    # Add ports for external connections
    c.add_port("o1", port=wg_straight.ports["o1"])  # Input port
    c.add_port("o2", port=bend.ports["o2"])  # Output port
    
    return c

# Create the device
device = curved_waveguide()

# Write to GDS file
device.write_gds("curved_waveguide.gds")