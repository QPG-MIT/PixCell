import gdsfactory as gf

@gf.cell
def directional_coupler_custom():
    """
    Creates a symmetric directional coupler based on the provided image and footprint.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # --- Dimensions & Constants ---
    total_length = 120.0
    total_height = 4.0
    wg_width = 0.5
    
    # Estimated lengths for sections to sum to 120um
    l_io = 10.0      # Input/Output straight length
    l_bend = 30.0    # S-bend horizontal length
    l_couple = 40.0  # Coupling region length
    
    # Vertical calculations
    # Inputs at top/bottom limits. Center y = (Total Height / 2) - (Width / 2)
    y_in_abs = (total_height / 2) - (wg_width / 2) # 1.75 um
    
    # Coupling region gap (estimated 0.2um)
    gap = 0.2
    # Center y at coupling = (Gap / 2) + (Width / 2)
    y_couple_abs = (gap / 2) + (wg_width / 2)      # 0.35 um
    
    # Vertical displacement for S-bends
    dy = y_couple_abs - y_in_abs # -1.4 um (Negative means shifting down)

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Define Primitives ---
    straight_io = gf.components.straight(length=l_io, cross_section=xs)
    straight_couple = gf.components.straight(length=l_couple, cross_section=xs)
    
    # S-bends: bend_s size parameter is (length, height_change)
    # Bend dropping down (Top-Left, Bottom-Right)
    bend_drop = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    # Bend rising up (Top-Right, Bottom-Left) - dy is negative, so -dy is positive
    bend_raise = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)

    # --- Assemble Top Arm ---
    # 1. Input Straight
    t1 = c << straight_io
    t1.movey(y_in_abs) # Start at y = +1.75
    
    # 2. S-Bend Down
    t2 = c << bend_drop
    t2.connect("o1", t1.ports["o2"])
    
    # 3. Coupling Straight
    t3 = c << straight_couple
    t3.connect("o1", t2.ports["o2"])
    
    # 4. S-Bend Up
    t4 = c << bend_raise
    t4.connect("o1", t3.ports["o2"])
    
    # 5. Output Straight
    t5 = c << straight_io
    t5.connect("o1", t4.ports["o2"])

    # --- Assemble Bottom Arm ---
    # 1. Input Straight
    b1 = c << straight_io
    b1.movey(-y_in_abs) # Start at y = -1.75
    
    # 2. S-Bend Up (Converge towards center)
    b2 = c << bend_raise
    b2.connect("o1", b1.ports["o2"])
    
    # 3. Coupling Straight
    b3 = c << straight_couple
    b3.connect("o1", b2.ports["o2"])
    
    # 4. S-Bend Down (Diverge away from center)
    b4 = c << bend_drop
    b4.connect("o1", b3.ports["o2"])
    
    # 5. Output Straight
    b5 = c << straight_io
    b5.connect("o1", b4.ports["o2"])

    # Expose ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])

    return c

# Create and save the device
device = directional_coupler_custom()
device.write_gds("directional_coupler.gds")
device.show()