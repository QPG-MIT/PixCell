import gdsfactory as gf

@gf.cell
def final_refined_petal_cross():
    """
    Refines the petal cross to match the target's leaf-like arms and thin tips.
    Footprint target: 4.7um x 4.7um
    """
    c = gf.Component("petal_cross_v3")
    
    # --- Precise Dimensions ---
    # Half-extent of the device
    total_radius = 2.35 
    
    # Rectangle (Tip) dimensions: Narrower for a needle-like look
    rect_w = 0.12 
    rect_l = 0.65
    
    # Petal (Ellipse) dimensions: 
    # Making it wider (x) and shorter (y) relative to the previous version
    # and offsetting it creates that distinct 'petal' bulge.
    petal_x_radius = 0.72   # Width of the leaf
    petal_y_radius = 1.05   # Length of the leaf body
    petal_offset = 0.85     # Distance from center to ellipse center
    
    # Apex of ellipse is at 0.85 + 1.05 = 1.90um
    # Base of rectangle is at 2.35 - 0.65 = 1.70um
    # This creates a 0.2um overlap for a smooth transition.

    # 1. Create a single arm sub-component
    arm = gf.Component()
    
    # Add petal (ellipse)
    p_ref = arm << gf.components.ellipse(radii=(petal_x_radius, petal_y_radius), layer=(1, 0))
    p_ref.movey(petal_offset)
    
    # Add tip (rectangle)
    t_ref = arm << gf.components.rectangle(size=(rect_w, rect_l), layer=(1, 0), centered=True)
    t_ref.movey(total_radius - rect_l/2)

    # 2. Add a central core circle to smooth the junction where petals meet
    c << gf.components.circle(radius=0.45, layer=(1, 0))

    # 3. Add four rotated arms to the main component
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)

    # 4. Use Boolean OR to merge the overlapping shapes into one solid polygon
    # This removes internal edges and produces the final clean silhouette.
    device = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return device

if __name__ == "__main__":
    # Generate the component
    component = final_refined_petal_cross()
    
    # Export to GDS
    component.write_gds("petal_cross_final_v3.gds")
    
    # Output stats for verification
    print(f"Final Footprint: {component.xsize:.2f} um x {component.ysize:.2f} um")