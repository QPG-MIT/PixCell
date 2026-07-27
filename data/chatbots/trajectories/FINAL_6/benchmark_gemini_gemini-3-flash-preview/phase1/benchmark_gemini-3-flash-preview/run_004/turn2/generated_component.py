import gdsfactory as gf

@gf.cell
def leaf_cross_device():
    """
    Recreates the 4-lobed device with high fidelity and smooth transitions.
    Footprint: 4.7um x 4.7um (Radius = 2.35um)
    """
    layer = (1, 0)
    
    # --- Dimensions (Optimized for leaf-like taper) ---
    total_radius = 2.35
    tip_length = 0.6
    tip_width = 0.16
    petal_max_half_width = 0.45 # ry
    
    # We define the petal (ellipse) to bulge away from the center
    # Center at 0.85um, radius 1.2um -> spans from -0.35um to 2.05um
    petal_rx = 1.2
    petal_ry = petal_max_half_width
    petal_center_x = 0.85
    
    # Tip starts at 1.75um and ends at 2.35um
    tip_center_x = total_radius - (tip_length / 2)
    
    # --- Build a Single Arm ---
    arm = gf.Component("single_arm")
    
    # 1. The Petal (shifted ellipse)
    p = arm << gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    p.movex(petal_center_x)
    
    # 2. The Tip (rectangle with explicit overlap)
    # The petal ends at 2.05um, tip starts at 1.75um. Overlap = 0.3um.
    t = arm << gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t.movex(tip_center_x)

    # --- Combine into Horizontal and Vertical Axes ---
    # We use two separate components to feed into the Boolean operation
    h_axis = gf.Component("h_axis")
    h_axis << arm
    ref180 = h_axis << arm
    ref180.rotate(180)
    
    v_axis = gf.Component("v_axis")
    ref90 = v_axis << arm
    ref90.rotate(90)
    ref270 = v_axis << arm
    ref270.rotate(270)
    
    # --- Final Union ---
    # Boolean OR merges the overlapping ellipses into one continuous silhouette
    device = gf.boolean(A=h_axis, B=v_axis, operation="or", layer=layer)
    device.name = "leaf_cross_final"
    
    return device

if __name__ == "__main__":
    c = leaf_cross_device()
    
    # Export GDS
    filename = "leaf_cross_improved.gds"
    c.write_gds(filename)
    
    print(f"SUCCESS: '{filename}' generated.")
    print(f"Dimensions: {c.xsize:.2f}um x {c.ysize:.2f}um")
    
    # Optional preview
    # c.show()