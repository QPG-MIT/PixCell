import gdsfactory as gf

@gf.cell
def straight_horizontal_rectangle():
    c = gf.Component()
    
    # Define a cross-section for the waveguide
    xs = gf.cross_section.cross_section(width=3.0, layer=(1, 0))
    
    # Create a straight path
    path = gf.path.straight(length=18.0)
    
    # Extrude the path to create the waveguide
    waveguide = c << gf.path.extrude(path, cross_section=xs)
    
    # Expose ports at the left and right edges
    c.add_port("o1", center=(-9.0, 0), width=3.0, orientation=180, layer=(1, 0))
    c.add_port("o2", center=(9.0, 0), width=3.0, orientation=0, layer=(1, 0))
    
    return c

# Create and save the device
device = straight_horizontal_rectangle()
device.write_gds("straight_horizontal_rectangle.gds")