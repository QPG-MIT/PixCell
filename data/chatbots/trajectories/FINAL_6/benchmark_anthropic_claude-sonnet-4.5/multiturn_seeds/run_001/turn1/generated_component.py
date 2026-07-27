import gdsfactory as gf

@gf.cell
def four_way_cross():
    """
    Creates a four-way cross pattern with elliptical arms.
    The device consists of two perpendicular ellipses that overlap
    at the center to form a symmetric cross.
    
    Returns:
        gf.Component: Component containing the cross structure
    """
    c = gf.Component()
    
    # Parameters matching the footprint constraint
    total_span = 4.7  # Total footprint in micrometers (4.7 x 4.7 µm)
    arm_width = 1.0   # Width of each arm in micrometers
    layer = (1, 0)    # Main device layer
    
    # Create vertical ellipse (forms top and bottom arms)
    # Radii: (x_radius, y_radius) = (narrow width, tall height)
    vertical = c << gf.components.ellipse(
        radii=(arm_width/2, total_span/2), 
        layer=layer
    )
    
    # Create horizontal ellipse (forms left and right arms)
    # Radii: (x_radius, y_radius) = (wide width, narrow height)
    horizontal = c << gf.components.ellipse(
        radii=(total_span/2, arm_width/2), 
        layer=layer
    )
    
    return c

# Generate and save the device
device = four_way_cross()
device.write_gds("four_way_cross.gds")
print(f"Device created with footprint: {device.bbox}")