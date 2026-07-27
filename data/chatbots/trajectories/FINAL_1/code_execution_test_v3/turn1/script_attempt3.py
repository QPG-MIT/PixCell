import gdsfactory as gf
import numpy as np

@gf.cell
def adiabatic_coupler_recreation():
    """
    Recreates the adiabatic coupler shown in the image.
    Footprint constraint: [40.0, 1.7] um.
    """
    c = gf.Component("adiabatic_coupler")
    
    # Define the target layer
    LAYER = (1, 0)
    
    # Global Dimensions
    L_TOTAL = 40.0
    W_TOTAL = 1.7
    
    # 1. Central Waveguide (Taper)
    # Tapers from the left input to a point
    L_CENTER = 26.0
    W_CENTER_START = 0.5
    W_CENTER_END = 0.01  # Effectively a point
    
    center_taper = c << gf.components.taper(
        length=L_CENTER,
        width1=W_CENTER_START,
        width2=W_CENTER_END,
        layer=LAYER
    )
    # Taper starts at (0,0) by default
    center_taper.xmin = 0
    center_taper.y = 0
    
    # 2. Outer Arm Parameters
    L_ARM_START_OFFSET = 3.5  # Where the outer arms begin
    W_ARM_START = 0.22         # Initial width of outer arm
    W_ARM_END = 0.52           # Final width of outer arm
    
    # Y-offsets (measured to waveguide centers)
    # Total width calculation: (Y_ARM_END + W_ARM_END/2) * 2 = (0.59 + 0.26) * 2 = 1.7
    Y_ARM_START = 0.42
    Y_ARM_END = 0.59
    
    L_STRAIGHT = L_CENTER - L_ARM_START_OFFSET
    L_CURVE = L_TOTAL - L_CENTER
    
    # Define CrossSections for correct layer handling
    xs_start = gf.cross_section.cross_section(width=W_ARM_START, layer=LAYER)
    xs_end = gf.cross_section.cross_section(width=W_ARM_END, layer=LAYER)
    
    # Part A: Straight section of the arm
    arm_straight_comp = gf.components.straight(length=L_STRAIGHT, cross_section=xs_start)
    
    # Part B: Curved transition section
    # Manual cubic S-curve path construction for reliability
    t = np.linspace(0, 1, 101)
    # Smooth S-transition formula
    x_path = t * L_CURVE
    y_path = (Y_ARM_END - Y_ARM_START) * (3 * t**2 - 2 * t**3)
    
    points = np.stack([x_path, y_path], axis=1)
    p_curve = gf.Path(points)
    
    # Create the widening transition along the curved path
    trans = gf.path.transition(xs_start, xs_end, width_type='linear')
    arm_curved_comp = gf.path.extrude_transition(p_curve, transition=trans)
    
    # Assembly helper for one full arm
    def create_arm():
        arm_comp = gf.Component()
        s_ref = arm_comp << arm_straight_comp
        c_ref = arm_comp << arm_curved_comp
        # Connect transition start to straight segment end
        c_ref.connect("o1", s_ref.ports["o2"])
        arm_comp.add_port("o1", port=s_ref.ports["o1"])
        return arm_comp

    arm_master = create_arm()
    
    # Add Top Arm
    top_arm = c << arm_master
    top_arm.move((L_ARM_START_OFFSET, Y_ARM_START))
    
    # Add Bottom Arm (Mirrored across X-axis)
    bot_arm = c << arm_master
    bot_arm.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis
    bot_arm.move((L_ARM_START_OFFSET, -Y_ARM_START))
    
    return c

if __name__ == "__main__":
    # Instantiate component
    device = adiabatic_coupler_recreation()
    
    # Save as GDS file
    device.write_gds("adiabatic_coupler_recreation.gds")
