import gdsfactory as gf

@gf.cell
def create_cross_petal_device_v2():
    c = gf.Component()
    layer = (1, 0)
    
    # Define the size parameters based on the 4.7μm footprint
    total_size = 4.7  # μm
    
    # Create the four curved "petal" shapes using ellipses
    # Each ellipse will be elongated along one axis
    ellipse_width = total_size * 0.6  # Width along the petal direction
    ellipse_height = total_size * 0.3  # Height perpendicular to petal direction
    
    # Create a single ellipse component
    ellipse_component = gf.components.ellipse(radii=(ellipse_width/2, ellipse_height/2), layer=layer)
    
    # Create four references of the ellipse, rotated appropriately
    # Top petal (0° rotation - elongated vertically)
    top_ellipse = c << ellipse_component
    top_ellipse.rotate(90)  # Rotate 90° to make it vertical
    
    # Right petal (90° rotation - elongated horizontally)
    right_ellipse = c << ellipse_component
    right_ellipse.rotate(0)  # Already horizontal
    
    # Bottom petal (180° rotation - elongated vertically, pointing down)
    bottom_ellipse = c << ellipse_component
    bottom_ellipse.rotate(270)  # Rotate 270° to make it vertical, pointing down
    
    # Left petal (270° rotation - elongated horizontally, pointing left)
    left_ellipse = c << ellipse_component
    left_ellipse.rotate(180)  # Rotate 180° to make it horizontal, pointing left
    
    # Position the ellipses so they overlap at the center
    # The ellipses are already centered, so we just need to ensure they're positioned correctly
    
    # Combine all four ellipses using boolean OR operation
    # Start with the top ellipse
    combined = top_ellipse
    
    # Add the right ellipse
    combined = c << gf.boolean(combined, right_ellipse, operation="or", layer=layer)
    
    # Add the bottom ellipse
    combined = c << gf.boolean(combined, bottom_ellipse, operation="or", layer=layer)
    
    # Add the left ellipse
    combined = c << gf.boolean(combined, left_ellipse, operation="or", layer=layer)
    
    # Add ports at the ends of each petal for connectivity
    # Top port
    c.add_port("o1", center=(0, ellipse_width/2), width=0.5, orientation=90, layer=layer)
    # Bottom port
    c.add_port("o2", center=(0, -ellipse_width/2), width=0.5, orientation=270, layer=layer)
    # Right port
    c.add_port("o3", center=(ellipse_width/2, 0), width=0.5, orientation=0, layer=layer)
    # Left port
    c.add_port("o4", center=(-ellipse_width/2, 0), width=0.5, orientation=180, layer=layer)
    
    return c

# Create and save the device
device = create_cross_petal_device_v2()
device.write_gds("cross_petal_device_v2.gds")