import gdsfactory as gf

@gf.cell
def refined_petal_cross():
    """
    Recreates the petal cross with smooth transitions and correct proportions.
    Footprint target: 4.7um x 4.7um
    """
    c = gf.Component("petal_cross_final")
    
    # --- Refined Dimensions ---
    # Radius from center = 2.35um
    total_radius = 2.35
    
    # Rectangle (Tip) dimensions: Thinner and longer for a more needle-like look
    rect_w = 0.16 
    rect_l = 0.55
    
    # Ellipse (Petal) dimensions: Elongated for a smoother "leaf" shape
    # We want the ellipse to overlap the rectangle's base significantly.
    # Rectangle top is at 2.35, base is at 2.35 - 0.55 = 1.80um.
    # We will extend the ellipse tip to 2.05um to create a 0.25um overlap.
    petal_y_radius = 1.65  # Half-length
    petal_x_radius = 0.6   # Half-width
    petal_offset = 0.4     # Shift from center (0.4 + 1.65 = 2.05um)

    # 1. Create a single arm sub-component
    arm = gf.Component()
    
    # Add petal (ellipse)
    p_ref = arm << gf.components.ellipse(radii=(petal_x_radius, petal_y_radius), layer=(1, 0))
    p_ref.movey(petal_offset)
    
    # Add tip (rectangle)
    # Positioned so the outer edge is exactly at the footprint boundary (2.35um)
    t_ref = arm << gf.components.rectangle(size=(rect_w, rect_l), layer=(1, 0), centered=True)
    t_ref.movey(total_radius - rect_l/2)

    # 2. Add four rotated arms to the main component
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)

    # 3. Boolean OR to merge everything into one continuous polygon
    # This removes internal lines and creates the solid shape from the reference
    device = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return device

if __name__ == "__main__":
    # Generate component
    component = refined_petal_cross()
    
    # Save to GDS
    component.write_gds("petal_cross_refined.gds")
    
    # Print stats
    print(f"Final Footprint: {component.xsize:.2f} um x {component.ysize:.2f} um")