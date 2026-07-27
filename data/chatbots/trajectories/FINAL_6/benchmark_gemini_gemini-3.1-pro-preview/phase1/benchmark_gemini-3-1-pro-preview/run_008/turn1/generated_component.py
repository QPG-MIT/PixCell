import gdsfactory as gf

@gf.cell
def petal_cross_device() -> gf.Component:
    """
    Creates a cross-like device with plump, curved petals and straight thin tips.
    The total footprint is bounded strictly to 4.7 x 4.7 um.
    """
    c = gf.Component()
    
    layer = (1, 0)
    
    # --- Parameters ---
    # Overall footprint constraint
    total_footprint = 4.7 
    
    # Central cross parameters (defines the straight tips)
    cross_width = 0.2
    
    # Ellipse parameters (defines the plump 'petal' shape)
    # The major radius is slightly less than half the footprint 
    # to let the straight cross tips protrude.
    petal_major_radius = 1.9 
    petal_minor_radius = 0.6
    
    # --- Primitives ---
    # 1. Central thin cross
    central_cross = gf.components.cross(
        length=total_footprint, 
        width=cross_width, 
        layer=layer
    )
    
    # 2. Horizontal petal (ellipse)
    ellipse_horizontal = gf.components.ellipse(
        radii=(petal_major_radius, petal_minor_radius), 
        layer=layer
    )
    
    # 3. Vertical petal (ellipse)
    ellipse_vertical = gf.components.ellipse(
        radii=(petal_minor_radius, petal_major_radius), 
        layer=layer
    )
    
    # --- Boolean Operations ---
    # Fuse the two ellipses to form the central 4-petal flower shape
    fused_petals = gf.boolean(
        A=ellipse_horizontal,
        B=ellipse_vertical,
        operation="or",
        layer=layer
    )
    
    # Fuse the flower shape with the central cross to add the straight narrow tips
    final_geometry = gf.boolean(
        A=fused_petals,
        B=central_cross,
        operation="or",
        layer=layer
    )
    
    # Add the result to our main component
    c << final_geometry
    
    return c

if __name__ == "__main__":
    # Create the component
    device = petal_cross_device()
    
    # Write the geometry to a GDS file
    device.write_gds("petal_cross_device.gds")