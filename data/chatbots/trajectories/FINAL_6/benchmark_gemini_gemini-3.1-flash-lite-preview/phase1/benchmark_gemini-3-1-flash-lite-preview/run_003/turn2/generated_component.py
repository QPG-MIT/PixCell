import gdsfactory as gf

@gf.cell
def flower_device():
    """
    Creates a cross-shaped flower geometry by explicitly placing 
    horizontal and vertical petal components to avoid rotation issues.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define Primitives
    # Cross: 3.0um total length, 0.6um width
    # This leaves 1.5um from center to arm-end
    base_cross = gf.components.cross(length=3.0, width=0.6, layer=layer)
    
    # Petal Horizontal (wider in x)
    p_horiz = gf.components.ellipse(radii=(0.85, 0.6), layer=layer)
    
    # Petal Vertical (wider in y, swapped radii)
    p_vert = gf.components.ellipse(radii=(0.6, 0.85), layer=layer)
    
    # 2. Build the Geometry
    # Add the base cross first
    c << base_cross
    
    # Add petals to the arms (horizontal)
    # Left and Right
    left_petal = c << p_horiz
    left_petal.move((-1.5, 0))
    
    right_petal = c << p_horiz
    right_petal.move((1.5, 0))
    
    # Add petals to the arms (vertical)
    # Top and Bottom
    top_petal = c << p_vert
    top_petal.move((0, 1.5))
    
    bottom_petal = c << p_vert
    bottom_petal.move((0, -1.5))
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = flower_device()
    device.write_gds("flower_device.gds")
    device.show()