import gdsfactory as gf

@gf.cell
def create_cross_petal_device():
    c = gf.Component()
    layer = (1, 0)
    
    # Define the cross section for the components
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Create the central cross
    # The cross will have arms extending to the edges of our footprint
    cross_length = 4.7  # μm
    cross_width = 0.5   # μm (same as waveguide width)
    central_cross = gf.components.cross(length=cross_length, width=cross_width, layer=layer)
    central_cross_ref = c << central_cross
    
    # Create the four petal shapes using ellipses
    # Each petal will be an ellipse positioned at the end of each cross arm
    petal_width = 1.5   # width of petal (along the cross arm)
    petal_height = 2.0  # height of petal (perpendicular to cross arm)
    
    # Create a single petal ellipse
    petal_ellipse = gf.components.ellipse(radii=(petal_width/2, petal_height/2), layer=layer)
    
    # Position and rotate the four petals
    petal_refs = []
    
    # Top petal (already oriented correctly)
    top_petal = c << petal_ellipse
    top_petal.move((0, cross_length/2 + petal_height/2))
    petal_refs.append(top_petal)
    
    # Bottom petal (rotate 180 degrees)
    bottom_petal = c << petal_ellipse
    bottom_petal.move((0, -(cross_length/2 + petal_height/2)))
    bottom_petal.rotate(180)
    petal_refs.append(bottom_petal)
    
    # Right petal (rotate 90 degrees)
    right_petal = c << petal_ellipse
    right_petal.move((cross_length/2 + petal_height/2, 0))
    right_petal.rotate(90)
    petal_refs.append(right_petal)
    
    # Left petal (rotate 270 degrees or -90 degrees)
    left_petal = c << petal_ellipse
    left_petal.move((-(cross_length/2 + petal_height/2), 0))
    left_petal.rotate(270)
    petal_refs.append(left_petal)
    
    # Combine all elements using boolean OR operation
    # First, combine the central cross with all petals
    combined = c << gf.boolean(central_cross_ref, petal_refs[0], operation="or", layer=layer)
    
    # Add remaining petals
    for i in range(1, 4):
        combined = c << gf.boolean(combined, petal_refs[i], operation="or", layer=layer)
    
    # Add ports for connectivity (if needed for future use)
    # Top port
    c.add_port("o1", center=(0, cross_length/2), width=0.5, orientation=90, layer=layer)
    # Bottom port
    c.add_port("o2", center=(0, -cross_length/2), width=0.5, orientation=270, layer=layer)
    # Right port
    c.add_port("o3", center=(cross_length/2, 0), width=0.5, orientation=0, layer=layer)
    # Left port
    c.add_port("o4", center=(-cross_length/2, 0), width=0.5, orientation=180, layer=layer)
    
    return c

# Create and save the device
device = create_cross_petal_device()
device.write_gds("cross_petal_device.gds")