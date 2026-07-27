import gdsfactory as gf

@gf.cell
def straight_vertical_waveguide():
    c = gf.Component()
    
    # Define cross-section for waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a straight waveguide segment
    wg = c << gf.components.straight(length=40, cross_section=xs)
    
    # Rotate the waveguide 90 degrees to make it vertical
    wg.rotate(90)
    
    # Add ports for external connections (now top and bottom)
    c.add_port("o1", port=wg.ports["o1"])  # Top port
    c.add_port("o2", port=wg.ports["o2"])  # Bottom port
    
    return c

# Create the device
device = straight_vertical_waveguide()

# Write to GDS file
device.write_gds("straight_vertical_waveguide.gds")