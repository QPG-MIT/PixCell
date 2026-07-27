import gdsfactory as gf

@gf.cell
def leaf_cross_device():
    """
    Recreates the 4-lobed device with fat petals and stubby tips.
    
    Refinements for Turn 3:
    - Increased petal width (ry) for a bulkier, more organic appearance.
    - Adjusted petal center shift to sharpen the central 'clover' hub.
    - Shortened and widened the tips to match the target proportions.
    
    Footprint: 4.7um x 4.7um (Radius = 2.35um)
    """
    layer = (1, 0)
    
    # --- Dimensions ---
    total_radius = 2.35
    
    # Petal parameters (Optimized for the "fat leaf" look)
    # rx is longitudinal, ry is transverse
    petal_rx = 1.15
    petal_ry = 0.82  # Significantly widened from 0.45
    petal_center_pos = 1.12 # Position along the axis to control center merge
    
    # Tip parameters (Stubby rectangle)
    tip_length = 0.40
    tip_width = 0.28
    tip_center_pos = total_radius - (tip_length / 2)
    
    # --- Build a Single Arm ---
    arm = gf.Component("single_arm")
    
    # 1. The Petal body (Ellipse)
    # Spans from ~-0.03um to ~2.27um, providing a solid central union
    p = arm << gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    p.movex(petal_center_pos)
    
    # 2. The Tip stub (Rectangle)
    # Positioned to end exactly at the footprint boundary (2.35um)
    t = arm << gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t.movex(tip_center_pos)

    # --- Assemble Full Device ---
    # We create two axis components to perform a robust Boolean Union
    h_axis = gf.Component("h_axis")
    h_axis << arm
    ref_180 = h_axis << arm
    ref_180.rotate(180)
    
    v_axis = gf.Component("v_axis")
    ref_90 = v_axis << arm
    ref_90.rotate(90)
    ref_270 = v_axis << arm
    ref_270.rotate(270)
    
    # Final Union: Merges horizontal and vertical axes into one silhouette
    device = gf.boolean(A=h_axis, B=v_axis, operation="or", layer=layer)
    device.name = "leaf_cross_refined_v3"
    
    return device

if __name__ == "__main__":
    # Create the component
    c = leaf_cross_device()
    
    # Export GDS
    filename = "leaf_cross_turn3.gds"
    c.write_gds(filename)
    
    print(f"SUCCESS: Generated '{filename}'")
    print(f"Calculated Footprint: {c.xsize:.2f}um x {c.ysize:.2f}um")
    
    # Optional: Preview in KLayout if installed
    # c.show()