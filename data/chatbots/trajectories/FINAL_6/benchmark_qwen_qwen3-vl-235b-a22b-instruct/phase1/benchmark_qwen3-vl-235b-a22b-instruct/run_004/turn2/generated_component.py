import gdsfactory as gf

@gf.cell
def create_petal_cross_final():
    c = gf.Component()
    layer = (1, 0)
    
    # Define cross-section for the paths
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Create one petal using a path that forms a teardrop shape
    # This path will start at center, go out, curve around, and return to center
    def create_petal_path():
        path = gf.Path()
        # Start at center (0,0)
        # Go out to a point, then curve back to center with a smooth transition
        path.append(gf.path.straight(length=1.0))  # Go straight out
        path.append(gf.path.euler(radius=0.5, angle=90, p=0.5))  # Curve 90 degrees
        path.append(gf.path.euler(radius=0.5, angle=-90, p=0.5))  # Curve back
        path.append(gf.path.straight(length=1.0))  # Return to center
        return path
    
    # Create the petal shape
    petal_path = create_petal_path()
    petal_component = gf.path.extrude(petal_path, cross_section=xs)
    
    # Create four instances of the petal, rotated to form the cross
    # Right petal (0 degrees)
    right_petal = c << petal_component
    right_petal.move((0, 0))
    
    # Top petal (90 degrees)
    top_petal = c << petal_component
    top_petal.rotate(90)
    top_petal.move((0, 0))
    
    # Left petal (180 degrees)
    left_petal = c << petal_component
    left_petal.rotate(180)
    left_petal.move((0, 0))
    
    # Bottom petal (270 degrees)
    bottom_petal = c << petal_component
    bottom_petal.rotate(270)
    bottom_petal.move((0, 0))
    
    return c

# Create the device
device = create_petal_cross_final()

# Write to GDS
device.write_gds("petal_cross_final.gds")