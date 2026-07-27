import gdsfactory as gf

@gf.cell
def petal_cross_v4():
    """
    Fourth iteration of the petal cross.
    Uses a custom polygon for the arms to achieve a precise 'leaf' shape with 
    sharp central junctions and thin rectangular tips.
    
    Footprint target: 4.7um x 4.7um
    """
    c = gf.Component("petal_cross_v4")
    
    # --- Dimensions & Scaling ---
    # Half-extent to fit 4.7um x 4.7um total footprint
    limit = 2.35 
    
    # Parameters to tune the leaf silhouette
    w_max = 0.46       # Half-width of the leaf belly (total petal width ~0.92um)
    w_tip = 0.06       # Half-width of the rectangular tip (total width 0.12um)
    y_belly = 0.95     # Vertical position of the widest part
    y_neck = 1.70      # Vertical position where the rectangular tip starts
    
    # 1. Define the right-hand profile of a single vertical arm
    # (x, y) coordinates
    profile = [
        (0.00, 0.00),     # Point at origin for sharp clefts
        (0.25, 0.40),     # Lower taper (flare out from center)
        (w_max, y_belly), # Widest part of the petal
        (0.32, 1.50),     # Upper taper (narrowing toward tip)
        (w_tip, y_neck),  # Neck down to the tip width
        (w_tip, limit),   # End of the rectangular tip
    ]
    
    # Create the full arm by mirroring the profile across x=0
    full_x = [p[0] for p in profile] + [-p[0] for p in reversed(profile)]
    full_y = [p[1] for p in profile] + [p[1] for p in reversed(profile)]
    arm_points = list(zip(full_x, full_y))
    
    # Create the template arm component
    arm = gf.Component("arm_template")
    arm.add_polygon(arm_points, layer=(1, 0))
    
    # 2. Add four rotated arm references to the main component
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        
    # 3. Add a small central core circle
    # A small radius (0.22um) matches the subtle central solid core of the target 
    # while preserving the deep "V" shapes between petals.
    c << gf.components.circle(radius=0.22, layer=(1, 0))

    # 4. Merge overlapping geometries into a single clean polygon
    # This removes internal boundaries for a production-ready GDS file.
    device = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return device

if __name__ == "__main__":
    # Generate the component
    component = petal_cross_v4()
    
    # Export to GDS for fabrication/inspection
    component.write_gds("petal_cross_v4.gds")
    
    # Output stats for verification
    print(f"Device Name: {component.name}")
    print(f"Final Footprint: {component.xsize:.2f} um x {component.ysize:.2f} um")
    print(f"Target Footprint: 4.70 um x 4.70 um")