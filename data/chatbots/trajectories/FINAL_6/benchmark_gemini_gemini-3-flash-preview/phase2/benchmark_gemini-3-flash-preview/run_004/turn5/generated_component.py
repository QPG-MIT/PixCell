import gdsfactory as gf

@gf.cell
def leaf_cross_device():
    """
    Refined Turn 5:
    - Optimized the 'hub waist' by shifting petal ellipses further from the center (petal_center_pos = 1.15).
    - Significantly lengthened the end stubs (tip_length = 1.0) to match the prominent rectangular tips in the target.
    - Widened the stubs slightly (tip_width = 0.28) for better visual weight balance.
    - Adjusted petal aspect ratio and positioning to create a sharper, more leaf-like silhouette.
    
    Footprint Target: 4.7um x 4.7um (Radius = 2.35um)
    """
    layer = (1, 0)
    
    # --- Dimensions ---
    total_radius = 2.35  # Target footprint / 2
    
    # Tip parameters (Prominent rectangular stubs)
    # Increased length to create the distinct 'protruding' look
    tip_length = 1.0    
    tip_width = 0.28     
    tip_center_pos = total_radius - (tip_length / 2) # Align edge exactly at 2.35um
    
    # Petal parameters (The leaf-like ellipse)
    # petal_rx: semi-major axis (lengthwise)
    # petal_ry: semi-minor axis (width-wise)
    petal_rx = 1.25      
    petal_ry = 0.55      
    
    # Positioning the center further out (1.15um vs 0.95um) 
    # This reduces the center overlap, creating a 'pinched' junction.
    petal_center_pos = 1.15 
    
    # Hub intersection check: 
    # Inner edge of petal = 1.15 - 1.25 = -0.10um.
    # Total hub width = 0.2um. This creates a tight, defined center.
    
    # --- Build a Single Arm ---
    arm = gf.Component("single_arm")
    
    # 1. The Petal body (Ellipse)
    # This forms the main bulge of each arm. 
    p = arm << gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    p.movex(petal_center_pos)
    
    # 2. The Tip stub (Rectangle)
    # Overlaps the end of the ellipse to create the sharp rectangular termination.
    t = arm << gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t.movex(tip_center_pos)

    # --- Assemble Full Device ---
    c = gf.Component()
    
    # Add 4 arms at 90-degree rotations
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
    
    # Boolean Union ensures a single clean perimeter for the GDS file
    # This merges the overlapping ellipses and rectangles into the final cross shape
    device = gf.boolean(A=c, B=c, operation="or", layer=layer)
    device.name = "leaf_cross_v5"
    
    return device

if __name__ == "__main__":
    # Initialize component
    c = leaf_cross_device()
    
    # Final Export
    filename = "leaf_cross_turn5.gds"
    c.write_gds(filename)
    
    print(f"SUCCESS: Generated '{filename}'")
    print(f"Measured Footprint: {c.xsize:.2f}um x {c.ysize:.2f}um")
    # c.show() # Uncomment to view in KLayout