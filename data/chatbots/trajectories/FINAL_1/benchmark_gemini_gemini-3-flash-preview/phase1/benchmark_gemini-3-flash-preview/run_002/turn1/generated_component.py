import gdsfactory as gf

@gf.cell
def fork_coupler_geometry():
    """
    Recreates the device geometry using GDSFactory parametric primitives.
    Target Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component("fork_coupler")
    layer = (1, 0)
    
    # --- 1. Central Taper (Parametric Primitive) ---
    # The central 'tongue' starts at x=0 and tapers down.
    taper_len = 26.0
    w_start_center = 0.6
    w_end_center = 0.01 # Near-zero width at the tip
    
    taper = c << gf.components.taper(
        length=taper_len, 
        width1=w_start_center, 
        width2=w_end_center, 
        layer=layer
    )
    # Align to the left edge (x=0) and center (y=0)
    taper.xmin = 0
    taper.y = 0

    # --- 2. Side Arms (Parametric Path and Transition) ---
    # We define a path for the top arm.
    # Total footprint width is 1.7um -> max y-extent is +/- 0.85um.
    # If the arm is 0.5um wide at the end, the center should be at 0.6um.
    
    total_len = 40.0
    y_start = 0.55  # Initial center y-offset (width_center/2 + gap + width_arm/2)
    y_end = 0.60    # Final center y-offset to reach the 1.7um outer boundary
    
    # Path coordinates for the arm: straight segment followed by a smooth curve out
    pts = [
        (0.0, y_start),
        (24.0, y_start),
        (33.0, y_end),
        (total_len, y_end)
    ]
    
    # Create smooth path with curvature radius for adiabatic transition
    path = gf.path.smooth(pts, radius=8)
    
    # Define width transition: arms thicken slightly toward the right
    xs_start = gf.cross_section.cross_section(width=0.3, layer=layer)
    xs_end = gf.cross_section.cross_section(width=0.5, layer=layer)
    trans = gf.path.transition(xs_start, xs_end, width_type='sine')
    
    # Extrude the top arm using the path and transition
    arm_top = c << gf.path.extrude_transition(path, trans)
    
    # Create the bottom arm by mirroring the top arm reference
    arm_bottom = c << gf.path.extrude_transition(path, trans)
    arm_bottom.mirror_y()

    return c

if __name__ == "__main__":
    # Initialize the component
    component = fork_coupler_geometry()
    
    # Save the output GDS file
    filename = "fork_coupler.gds"
    component.write_gds(filename)
    
    # Output status and dimensions using correct attribute names for current GDSFactory
    print(f"GDS file successfully produced: {filename}")
    print(f"Final Footprint: {component.xsize:.2f} um (Length) x {component.ysize:.2f} um (Width)")