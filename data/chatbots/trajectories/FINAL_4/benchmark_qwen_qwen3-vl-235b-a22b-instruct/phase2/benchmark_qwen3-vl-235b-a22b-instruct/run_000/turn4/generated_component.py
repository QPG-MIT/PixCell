import gdsfactory as gf

@gf.cell
def straight_horizontal_rectangle():
    c = gf.Component()
    
    # Create a solid rectangle with dimensions matching the footprint constraint
    # 18μm length (X-direction) × 3μm width (Y-direction)
    rect = c << gf.components.rectangle(size=(18.0, 3.0), layer=(1, 0), centered=True)
    
    # Expose ports at the left and right edges
    # Create ports at the center of the left and right edges
    c.add_port("o1", center=(-9.0, 0), width=3.0, orientation=180, layer=(1, 0))
    c.add_port("o2", center=(9.0, 0), width=3.0, orientation=0, layer=(1, 0))
    
    return c

# Create and save the device
device = straight_horizontal_rectangle()
device.write_gds("straight_horizontal_rectangle.gds")