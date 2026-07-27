import gdsfactory as gf

@gf.cell
def leaf_cross_device():
    """
    Refined Turn 4:
    - Petals transformed into slender 'eye' shapes with high aspect ratios.
    - Tips are lengthened and thinned to match the rectangular 'stub' look.
    - Hub overlap tuned to create a defined central clover-intersection.
    
    Footprint Target: 4.7um x 4.7um (Radius = 2.35um)
    """
    layer = (1, 0)
    
    # --- Dimensions ---
    total_radius = 2.35  # Half of 4.7um
    
    # Tip parameters (Now much slimmer and more prominent)
    tip_length = 0.65
    tip_width = 0.18
    tip_center_pos = total_radius - (tip_length / 2) # Positions edge at 2.35um
    
    # Petal parameters (Elongated 'eye' shape)
    # Tuning rx/ry and position creates the sharp transition to the tip
    petal_rx = 1.30
    petal_ry = 0.52 
    petal_center_pos = 0.95 # Pushed inward to sharpen the hub transition
    
    # --- Build a Single Arm ---
    arm = gf.Component("single_arm")
    
    # 1. The Petal body (Ellipse)
    # Tapers toward the tip and the origin
    p = arm << gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    p.movex(petal_center_pos)
    
    # 2. The Tip stub (Rectangle)
    # Overlaps the end of the petal for a seamless silhouette
    t = arm << gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t.movex(tip_center_pos)

    # --- Assemble Full Device ---
    c = gf.Component()
    
    # Add 4 arms at 90-degree rotations
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
    
    # Boolean Union ensures a single clean perimeter for the GDS file
    device = gf.boolean(A=c, B=c, operation="or", layer=layer)
    device.name = "leaf_cross_refined_v4"
    
    return device

if __name__ == "__main__":
    # Initialize component
    c = leaf_cross_device()
    
    # Final Export
    filename = "leaf_cross_turn4.gds"
    c.write_gds(filename)
    
    print(f"SUCCESS: Generated '{filename}'")
    print(f"Measured Footprint: {c.xsize:.2f}um x {c.ysize:.2f}um")
    # c.show() # Uncomment to view in KLayout