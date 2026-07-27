import gdsfactory as gf
import numpy as np

@gf.cell
def fork_coupler_refined_v4():
    """
    Refined fork coupler with distinct straight and flared sections.
    Uses manual Bezier point calculation to ensure compatibility and smooth curves.
    
    Footprint Constraint: 40.0 um x 1.7 um
    """
    c = gf.Component("fork_coupler_v4")
    layer = (1, 0)
    
    # --- 1. Central Taper ---
    # Long, slender central 'tongue'
    t_len = 30.0
    taper = c << gf.components.taper(
        length=t_len, 
        width1=0.6, 
        width2=0.01, 
        layer=layer
    )
    taper.xmin = 0
    taper.y = 0

    # --- 2. Side Arm Path Construction ---
    # Vertical Math:
    # Start center y = 0.45 (gives a 0.05um gap between 0.6um taper and 0.2um arm)
    # End center y = 0.60   (reaches 1.7um total width with 0.5um arm: 0.6 + 0.25 = 0.85 half-width)
    dy = 0.15 # Total vertical shift for the flare
    
    # A. Initial straight parallel section (26 um)
    p = gf.path.straight(length=26.0)
    
    # B. S-Bend Flare section (10 um) using Bezier math
    t = np.linspace(0, 1, 40)
    # Define 4 control points for a smooth S-shape: (start, handle1, handle2, end)
    p0, p1, p2, p3 = np.array([0, 0]), np.array([5, 0]), np.array([5, dy]), np.array([10, dy])
    
    # Cubic Bezier formula: (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)t^2*P2 + t^3*P3
    bezier_pts = (
        (1-t[:, None])**3 * p0 + 
        3*(1-t[:, None])**2 * t[:, None] * p1 + 
        3*(1-t[:, None]) * t[:, None]**2 * p2 + 
        t[:, None]**3 * p3
    )
    
    # Convert points to a GDSFactory Path and append to the straight section
    p += gf.Path(bezier_pts)
    
    # C. Final straight exit section (4 um)
    p += gf.path.straight(length=4.0)
    
    # Shift the entire path to its starting vertical offset
    p.move((0, 0.45))
    
    # --- 3. Cross-Section Transition ---
    # Arms thicken linearly from 0.2 um at the start to 0.5 um at the end.
    xs1 = gf.cross_section.cross_section(width=0.2, layer=layer)
    xs2 = gf.cross_section.cross_section(width=0.5, layer=layer)
    trans = gf.path.transition(xs1, xs2, width_type='linear')
    
    # --- 4. Extrude and Assemble ---
    # Extrude top arm and mirror it to create the fork.
    arm_top = c << gf.path.extrude_transition(p, trans)
    arm_bottom = c << gf.path.extrude_transition(p, trans)
    arm_bottom.mirror_y()

    return c

if __name__ == "__main__":
    # Generate the device
    device = fork_coupler_refined_v4()
    
    # Write to GDS file
    output_name = "fork_coupler_final_v4.gds"
    device.write_gds(output_name)
    
    # Print verification info
    print(f"GDS file successfully generated: {output_name}")
    print(f"Final Dimensions: {device.xsize:.2f} um x {device.ysize:.2f} um")
    print("Match Status: Pathing refined for 'straight-then-flare' look.")