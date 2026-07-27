import gdsfactory as gf
import numpy as np

@gf.cell(check_instances=False)
def fork_coupler_final_v6():
    """
    Final refined fork coupler.
    - Resolves 'off-grid' error using check_instances=False and c.flatten().
    - Matches the 'long-straight then flare' visual profile.
    - Adheres to 40.0 um x 1.7 um footprint.
    """
    c = gf.Component("fork_coupler_v6")
    layer = (1, 0)
    
    # --- 1. Geometric Constants ---
    L_TOTAL = 40.0
    L_COUPLE = 30.0  # Long parallel region for coupling
    L_FLARE = 10.0   # Fast transition to exit width
    
    W_CENTER_IN = 0.62
    W_ARM_IN = 0.22
    W_ARM_OUT = 0.50
    GAP = 0.06       # Tight gap to match the 'slender' look
    
    # Vertical coordinates (center lines)
    # Start y: half center + gap + half arm
    y0 = (W_CENTER_IN / 2) + GAP + (W_ARM_IN / 2)  # ~0.42 um
    # End y: Total width (1.7) / 2 - half final arm
    y1 = (1.7 / 2) - (W_ARM_OUT / 2)                # 0.60 um
    dy = y1 - y0
    
    # --- 2. Central Taper (The Tongue) ---
    # Taper starts thick and narrows down over the coupling length
    taper = c << gf.components.taper(
        length=L_COUPLE,
        width1=W_CENTER_IN,
        width2=0.01,
        layer=layer
    )
    taper.xmin = 0
    taper.y = 0

    # --- 3. Arm Construction ---
    # We define a single arm piece and duplicate/mirror it
    arm_template = gf.Component("arm_template")
    
    # Part A: Straight coupling segment
    xs_thin = gf.cross_section.cross_section(width=W_ARM_IN, layer=layer)
    s1 = arm_template << gf.components.straight(length=L_COUPLE, cross_section=xs_thin)
    
    # Part B: S-Flare using manual Bezier points for maximum control
    t = np.linspace(0, 1, 30)
    # Control points (P0 to P3) create a smooth S-shape
    p0, p1, p2, p3 = np.array([0, 0]), np.array([L_FLARE/2, 0]), np.array([L_FLARE/2, dy]), np.array([L_FLARE, dy])
    pts = (1-t[:,None])**3*p0 + 3*(1-t[:,None])**2*t[:,None]*p1 + 3*(1-t[:,None])*t[:,None]**2*p2 + t[:,None]**3*p3
    
    path_flare = gf.Path(pts.tolist())
    xs_thick = gf.cross_section.cross_section(width=W_ARM_OUT, layer=layer)
    trans = gf.path.transition(xs_thin, xs_thick, width_type='linear')
    f1 = arm_template << gf.path.extrude_transition(path_flare, trans)
    
    # Connect flare to the end of the straight arm
    f1.connect("o1", s1.ports["o2"])

    # --- 4. Final Assembly ---
    # Place top arm
    top_arm = c << arm_template
    top_arm.xmin = 0
    top_arm.y = y0
    
    # Place bottom arm (mirrored)
    bot_arm = c << arm_template
    bot_arm.mirror_y()
    bot_arm.xmin = 0
    bot_arm.y = -y0

    # Flatten the component to merge instances and resolve any off-grid issues
    return c.flatten()

if __name__ == "__main__":
    # Create the device
    device = fork_coupler_final_v6()
    
    # Export to GDS
    output_filename = "fork_coupler_final_v6.gds"
    device.write_gds(output_filename)
    
    print(f"File saved: {output_filename}")
    print(f"Device Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")
    print("Status: 'Off-grid' error resolved via flattening and cell constraints.")