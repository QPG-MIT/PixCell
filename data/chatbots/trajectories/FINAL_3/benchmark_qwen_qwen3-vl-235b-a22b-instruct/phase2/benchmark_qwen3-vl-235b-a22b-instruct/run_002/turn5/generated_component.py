import gdsfactory as gf

@gf.cell
def recreate_straight_horizontal_device():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a straight waveguide with the total length from footprint
    total_length = 120.0  # from footprint
    
    # Create straight waveguide (horizontal by default)
    waveguide = c << gf.components.straight(length=total_length, cross_section=xs)
    
    # No rotation needed since we want it horizontal
    
    # Add ports at the beginning and end
    c.add_port("o1", port=waveguide.ports["o1"])
    c.add_port("o2", port=waveguide.ports["o2"])
    
    return c

# Create and save the device
device = recreate_straight_horizontal_device()
device.write_gds("recreated_straight_horizontal_device.gds")