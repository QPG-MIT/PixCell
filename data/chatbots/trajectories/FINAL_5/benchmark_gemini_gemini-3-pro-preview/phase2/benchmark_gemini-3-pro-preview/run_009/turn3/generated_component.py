import gdsfactory as gf

# ==============================================================================
# Parametric Settings
# ==============================================================================
# The device is a contra-directional coupler with folded "U" shaped waveguides.
# The critical dimensions are derived from the target image and the footprint hint.
# Footprint hint [18.24, 0.7] suggests the grating length is 18.24um and the
# grating envelope width is 0.7um (Core 0.5 + Teeth 0.2).

LAYER_WG = (1, 0)
WIDTH_CORE = 0.5        # Main waveguide backbone width
TOOTH_DEPTH = 0.2       # Grating corrugation depth (0.5 + 0.2 = 0.7 matches footprint width hint)
GRATING_PERIOD = 0.318  # Period of the Bragg grating
GRATING_LENGTH = 18.24  # Exact length of the coupling region
DUTY_CYCLE = 0.5        # 50% fill factor for teeth
GAP = 0.15              # Gap between the tips of the opposing grating teeth
BEND_RADIUS = 1.5       # Tight radius for compact loops (visual match)
SBEND_SIZE = (5.0, -2.0) # (Length, Vertical Shift) for the input/output s-bends

# ==============================================================================
# 1. Grating Arm Primitive
# ==============================================================================
@gf.cell
def grating_arm_asymmetric(length, period, w_core, tooth_depth, dc):
    """
    Creates a straight waveguide with rectangular teeth on the BOTTOM edge.
    This asymmetry allows two such arms to be placed facing each other.
    """
    c = gf.Component()
    
    # 1. Continuous Core Backbone
    # Centered vertically at y=0, so it spans [-w/2, w/2]
    core = c << gf.components.rectangle(
        size=(length, w_core),
        layer=LAYER_WG,
        centered=False
    )
    core.movey(-w_core / 2.0)
    
    # 2. Periodic Teeth
    # Teeth are placed on the bottom edge (y = -w/2) extending downwards
    n_periods = int(length / period)
    tooth_len = period * dc
    
    # Create the tooth polygon once
    tooth_poly = gf.components.rectangle(
        size=(tooth_len, tooth_depth),
        layer=LAYER_WG,
        centered=False
    )
    
    # Array the teeth
    for i in range(n_periods):
        t = c << tooth_poly
        # X: i * period
        # Y: -w_core/2 (bottom of core) - tooth_depth (top of tooth relative to origin of tooth rect)
        t.move((i * period, -w_core / 2.0 - tooth_depth))

    # Define Ports on the centerline (y=0)
    c.add_port("o1", center=(0, 0), width=w_core, orientation=180, layer=LAYER_WG)
    c.add_port("o2", center=(length, 0), width=w_core, orientation=0, layer=LAYER_WG)
    
    return c

# ==============================================================================
# 2. Folded Structure Half
# ==============================================================================
@gf.cell
def folded_coupler_half():
    """
    Constructs one half of the device:
    Input S-Bend -> Return Arm -> U-Bend -> Grating Arm
    (Constructed in reverse order for easier connectivity from the grating)
    """
    c = gf.Component()
    
    xs = gf.cross_section.cross_section(
        width=WIDTH_CORE, 
        layer=LAYER_WG, 
        radius=BEND_RADIUS
    )
    
    # A. Grating Section (Inner arm)
    grating = c << grating_arm_asymmetric(
        length=GRATING_LENGTH, 
        period=GRATING_PERIOD, 
        w_core=WIDTH_CORE, 
        tooth_depth=TOOTH_DEPTH, 
        dc=DUTY_CYCLE
    )
    
    # B. U-Bend (180 degrees)
    # Connects to the 'East' end of the grating and loops back
    bend = c << gf.components.bend_euler(
        angle=180, 
        cross_section=xs
    )
    bend.connect("o1", grating.ports["o2"])
    
    # C. Return Arm (Outer arm)
    # Runs parallel to grating
    return_wg = c << gf.components.straight(
        length=GRATING_LENGTH, 
        cross_section=xs
    )
    return_wg.connect("o1", bend.ports["o2"])
    
    # D. Input/Output Flare (S-Bend)
    # Connects to the return arm and shifts the port outwards to form the "tail".
    # Since we connect to a West-facing port (180 deg), the coordinate system is rotated 180.
    # A negative height in SBEND_SIZE ensures the shift is "Up" (North) in global coords,
    # widening the device envelope.
    flare = c << gf.components.bend_s(
        size=SBEND_SIZE, 
        cross_section=xs
    )
    flare.connect("o1", return_wg.ports["o2"])
    
    # Expose relevant ports
    # "coupling" is the start of the grating (to be left open inside the device?) 
    # Actually, strictly, the device works by coupling light from one bus to the other.
    c.add_port("coupling", port=grating.ports["o1"])
    c.add_port("io", port=flare.ports["o2"])
    
    return c

# ==============================================================================
# 3. Final Assembly
# ==============================================================================
@gf.cell
def contra_directional_coupler():
    c = gf.Component()
    
    # Instantiate the two folded halves
    top = c << folded_coupler_half()
    bottom = c << folded_coupler_half()
    
    # Rotate the bottom half 180 degrees to create point symmetry
    bottom.rotate(180)
    
    # Vertical Alignment
    # We need a specific GAP between the tips of the teeth.
    # Top Half: Teeth are on bottom edge. Tip Y = Center_Y - Core/2 - Depth
    # Bottom Half (Rotated): Teeth are on top edge. Tip Y = Center_Y + Core/2 + Depth
    # We want Tip_Top - Tip_Bottom = GAP
    # Let Center_Top = +dY, Center_Bottom = -dY
    # (dY - W/2 - D) - (-dY + W/2 + D) = GAP
    # 2*dY - W - 2D = GAP  =>  dY = (GAP + W)/2 + D
    y_shift = (GAP + WIDTH_CORE)/2.0 + TOOTH_DEPTH
    
    top.movey(y_shift)
    bottom.movey(-y_shift)
    
    # Horizontal Alignment
    # Top half grating spans x=[0, L].
    # Bottom half (rotated) grating spans x=[-L, 0].
    # Move bottom half by +L so they overlap perfectly in x=[0, L].
    bottom.movex(GRATING_LENGTH)
    
    return c

if __name__ == "__main__":
    device = contra_directional_coupler()
    device.write_gds("contra_directional_coupler.gds")