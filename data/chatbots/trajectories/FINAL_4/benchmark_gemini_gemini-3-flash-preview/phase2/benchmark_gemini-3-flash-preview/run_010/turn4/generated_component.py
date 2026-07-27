import gdsfactory as gf

@gf.cell
def recreate_curved_waveguides():
    """
    Turn 4: Refined recreation of the converging curved waveguides.
    Significantly increases the vertical displacement (dy) and optimizes 
    waveguide width to match the visual 'swing' and proportions of the target image.
    Strictly adheres to the 18um x 3um footprint constraint.
    """
    # 1. Global Dimensions (Footprint Constraint)
    L = 18.0
    H = 3.0
    
    # 2. Design Parameters for Visual Matching
    # A width of 0.85um provides the right balance between thickness and curvature room.
    width = 0.85
    center_gap = 0.10 
    
    # --- Vertical Coordinate Math ---
    # To fill the 3.0um height, the outer edges at the ends should touch +/- 1.5um.
    # Center y-coord at ends = 1.5 - (width / 2) = 1.075
    y_end_center = (H / 2) - (width / 2)
    
    # At the midpoint (x=9), we want the specified gap.
    # Center y-coord at middle = (gap / 2) + (width / 2) = 0.475
    y_mid_center = (center_gap / 2) + (width / 2)
    
    # Vertical displacement (dy) for the 9um transition segment
    dy = y_end_center - y_mid_center  # 0.6 um (doubled from Turn 3)
    dx = L / 2                        # 9.0 um
    
    c = gf.Component("refined_convergence_coupler")
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 3. Create Arm Template
    # We build an arm component that spans the full 18um length.
    arm = gf.Component("arm_template")
    
    # First half: S-bend dipping down from end-height to mid-height
    # npoints=512 ensures high-resolution smoothness for the curve.
    s1 = arm << gf.components.bend_s(size=(dx, -dy), cross_section=xs, npoints=512)
    
    # Second half: S-bend returning from mid-height back up to end-height
    s2 = arm << gf.components.bend_s(size=(dx, dy), cross_section=xs, npoints=512)
    s2.connect("o1", s1.ports["o2"])
    
    # 4. Assemble the Pair
    # Place the Top Arm
    top_ref = c << arm
    top_ref.movey(y_end_center)
    
    # Place the Bottom Arm (Vertical Mirror)
    # This creates the perfectly symmetrical 'converging' look.
    bot_ref = c << arm
    bot_ref.mirror_y()
    bot_ref.movey(-y_end_center)
    
    # 5. Export GDS
    # Note: Component is centered vertically at y=0 and spans x=[0, 18].
    c.write_gds("recreated_geometry.gds")
    
    return c

if __name__ == "__main__":
    # Generate the refined GDS file
    device = recreate_curved_waveguides()
    print("GDS file 'recreated_geometry.gds' updated with Turn 4 refinements (enhanced curvature).")