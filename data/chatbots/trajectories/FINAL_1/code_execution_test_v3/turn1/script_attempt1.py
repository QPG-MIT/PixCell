import gdsfactory as gf

@gf.cell
def adiabatic_coupler_recreation():
    """
    Recreates the adiabatic coupler/splitter shown in the image.
    Footprint constraint: [40.0, 1.7] um.
    """
    c = gf.Component("adiabatic_coupler")
    
    # Parameters derived from footprint and visual analysis
    L_TOTAL = 40.0
    W_TOTAL = 1.7
    
    # Central waveguide: a long taper from the left edge
    L_CENTER = 26.0
    W_CENTER_START = 0.5
    W_CENTER_END = 0.01  # Tapers to a point
    
    # Outer arm parameters
    L_ARM_START = 3.5     # Offset from the left where outer arms begin
    W_ARM_START = 0.22    # Initial width of outer arms
    W_ARM_END = 0.52      # Final width of outer arms
    
    # Y-offsets for arms (center of the waveguides)
    # Chosen so that at the end, total width is exactly 1.7um
    # Top edge = Y_ARM_END + W_ARM_END/2 = 0.59 + 0.26 = 0.85
    # Bottom edge = -0.59 - 0.26 = -0.85
    # Total W = 0.85 - (-0.85) = 1.7
    Y_ARM_START = 0.42
    Y_ARM_END = 0.59
    
    # 1. Central Taper
    # ----------------
    center_taper = c << gf.components.taper(
        length=L_CENTER,
        width1=W_CENTER_START,
        width2=W_CENTER_END,
        layer=(1, 0)
    )
    # Default origin of taper is (0,0) at the center of width1 port.
    
    # 2. Outer Arms Construction
    # --------------------------
    # The arms consist of a straight section and a curved transition section.
    L_straight = L_CENTER - L_ARM_START
    L_curve = L_TOTAL - L_CENTER
    
    # Path for the arm
    p_straight = gf.path.straight(length=L_straight)
    
    # Curve using a Bezier path for a smooth S-bend transition
    dx = L_curve
    dy = Y_ARM_END - Y_ARM_START
    # Control points ensure 0 slope at start and end of the curve
    p_curve = gf.path.bezier(control_points=[(0, 0), (dx * 0.5, 0), (dx * 0.5, dy), (dx, dy)])
    
    # Define CrossSections for the width transition
    xs_start = gf.CrossSection(width=W_ARM_START, layer=(1, 0))
    xs_end = gf.CrossSection(width=W_ARM_END, layer=(1, 0))
    trans = gf.path.transition(xs_start, xs_end, width_type='linear')
    
    # Extrude the paths into components
    arm_straight_comp = gf.path.extrude(p_straight, cross_section=xs_start)
    arm_curve_comp = gf.path.extrude_transition(p_curve, transition=trans)
    
    # Assemble one arm component
    def create_full_arm():
        arm = gf.Component()
        s_ref = arm << arm_straight_comp
        c_ref = arm << arm_curve_comp
        c_ref.connect("o1", s_ref.ports["o2"])
        return arm

    arm_master = create_full_arm()
    
    # Add Top Arm
    top_arm = c << arm_master
    top_arm.move((L_ARM_START, Y_ARM_START))
    
    # Add Bottom Arm (Mirror of Top)
    bot_arm = c << arm_master
    bot_arm.mirror((1, 0)) # Mirror across X axis
    bot_arm.move((L_ARM_START, -Y_ARM_START))
    
    return c

if __name__ == "__main__":
    # Create the component
    my_device = adiabatic_coupler_recreation()
    
    # Save the GDS file
    my_device.write_gds("adiabatic_coupler.gds")
    
    # Optional: print summary to verify footprint
    print(f"Device size: {my_device.size}")
