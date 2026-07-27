import gdsfactory as gf

@gf.cell
def recreate_straight_vertical_device():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a straight waveguide with the total length from footprint
    total_length = 120.0  # from footprint
    
    # Create straight waveguide (horizontal by default)
    waveguide = c << gf.components.straight(length=total_length, cross_section=xs)
    
    # Rotate 90 degrees to make it vertical
    waveguide.rotate(90)
    
    # Add ports at the beginning and end
    # After rotation, ports need to be updated
    c.add_port("o1", port=waveguide.ports["o1"])
    c.add_port("o2", port=waveguide.ports["o2"])
    
    return c

# Create and save the device
device = recreate_straight_vertical_device()
device.write_gds("recreated_straight_vertical_device.gds")