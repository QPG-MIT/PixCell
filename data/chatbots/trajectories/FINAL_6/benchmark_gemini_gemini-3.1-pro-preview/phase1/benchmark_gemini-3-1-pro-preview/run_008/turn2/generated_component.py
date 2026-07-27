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
    total_footprint = 4.7 
    cross_width = 0.16
    
    # Ellipse parameters for the 4 distinct petals.
    # We offset them outward so they meet and pinch deeply at the center.
    petal_major_radius = 0.95 
    petal_minor_radius = 0.55
    petal_offset = 0.90
    
    # --- Primitives ---
    # 1. Central thin cross (defines the full footprint and straight tips)
    central_cross = gf.components.cross(
        length=total_footprint, 
        width=cross_width, 
        layer=layer
    )
    
    # 2. Four distinct offset petals to create the deep armpits
    # Right petal
    c_right = gf.Component("petal_right")
    e_right = c_right << gf.components.ellipse(radii=(petal_major_radius, petal_minor_radius), layer=layer)
    e_right.movex(petal_offset)
    
    # Left petal
    c_left = gf.Component("petal_left")
    e_left = c_left << gf.components.ellipse(radii=(petal_major_radius, petal_minor_radius), layer=layer)
    e_left.movex(-petal_offset)
    
    # Top petal
    c_top = gf.Component("petal_top")
    e_top = c_top << gf.components.ellipse(radii=(petal_minor_radius, petal_major_radius), layer=layer)
    e_top.movey(petal_offset)
    
    # Bottom petal
    c_bot = gf.Component("petal_bot")
    e_bot = c_bot << gf.components.ellipse(radii=(petal_minor_radius, petal_major_radius), layer=layer)
    e_bot.movey(-petal_offset)
    
    # --- Boolean Operations ---
    # Merge the petals together seamlessly
    u1 = gf.boolean(A=c_right, B=c_left, operation="or", layer=layer)
    u2 = gf.boolean(A=c_top, B=c_bot, operation="or", layer=layer)
    fused_petals = gf.boolean(A=u1, B=u2, operation="or", layer=layer)
    
    # Fuse the resulting 4-petal flower shape with the central straight cross
    final_geometry = gf.boolean(
        A=fused_petals,
        B=central_cross,
        operation="or",
        layer=layer
    )
    
    # Add the cleanly fused geometry to our main component
    c << final_geometry
    
    return c

if __name__ == "__main__":
    # Create the component
    device = petal_cross_device()
    
    # Write the geometry to a GDS file
    device.write_gds("petal_cross_device.gds")