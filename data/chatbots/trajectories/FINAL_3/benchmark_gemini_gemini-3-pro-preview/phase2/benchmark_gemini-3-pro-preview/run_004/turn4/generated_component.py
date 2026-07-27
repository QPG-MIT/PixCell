import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v3():
    """
    Creates a symmetric directional coupler matching the target image proportions.
    Constraint: 120um x 4um footprint.
    
    Refinements based on visual feedback:
    1. Reduced waveguide width to 0.5um for a sleeker look matching the target.
    2. Increased coupling length to 50um (approx 40% of total length).
    3. Shortened S-bends to 15um for a steeper transition profile.
    4. Tightened gap to 0.2um to maintain coupling ratio visualization with thinner guides.
    """
    c = gf.Component()

    # --- Dimensions & Constants ---
    total_length = 120.0
    total_height = 4.0
    
    # Refined width and gap
    wg_width = 0.5
    gap = 0.2
    
    # Length Distribution
    # Target proportions: Long central region, distinct straight legs, sharp bends.
    # Formula: 2*l_io + 2*l_bend + l_couple = 120
    l_io = 20.0           # Straight input/output sections
    l_bend = 15.0         # S-bend transition length (shorter = steeper)
    l_couple = 50.0       # Central coupling region length
    
    # --- Vertical Position Calculations ---
    # The device fits within y = [-2.0, 2.0]
    
    # Top Arm Input (Outer)
    # Center y = Top Edge - Half Width
    y_top_in = (total_height / 2.0) - (wg_width / 2.0)  # 2.0 - 0.25 = 1.75
    
    # Top Arm Coupling (Inner)
    # Center y = Half Gap + Half Width
    y_top_couple = (gap / 2.0) + (wg_width / 2.0)       # 0.1 + 0.25 = 0.35
    
    # Vertical displacement for S-bends (Top arm drops down)
    dy = y_top_couple - y_top_in  # 0.35 - 1.75 = -1.40

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Define Primitives ---
    straight_io = gf.components.straight(length=l_io, cross_section=xs)
    straight_couple = gf.components.straight(length=l_couple, cross_section=xs)
    
    # Bends
    # bend_down drops the waveguide (y change is negative)
    bend_down = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    # bend_up raises the waveguide (y change is positive)
    bend_up = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)

    # --- Assemble Top Arm ---
    # 1. Input Straight
    t1 = c << straight_io
    t1.movey(y_top_in)
    
    # 2. S-Bend Down (to coupling region)
    t2 = c << bend_down
    t2.connect("o1", t1.ports["o2"])
    
    # 3. Coupling Straight
    t3 = c << straight_couple
    t3.connect("o1", t2.ports["o2"])
    
    # 4. S-Bend Up (to output)
    t4 = c << bend_up
    t4.connect("o1", t3.ports["o2"])
    
    # 5. Output Straight
    t5 = c << straight_io
    t5.connect("o1", t4.ports["o2"])

    # --- Assemble Bottom Arm ---
    # Bottom input y is symmetric to top input
    y_bot_in = -y_top_in
    
    # 1. Input Straight
    b1 = c << straight_io
    b1.movey(y_bot_in)
    
    # 2. S-Bend Up (bends UP to meet coupling region)
    b2 = c << bend_up
    b2.connect("o1", b1.ports["o2"])
    
    # 3. Coupling Straight
    b3 = c << straight_couple
    b3.connect("o1", b2.ports["o2"])
    
    # 4. S-Bend Down (bends DOWN to output)
    b4 = c << bend_down
    b4.connect("o1", b3.ports["o2"])
    
    # 5. Output Straight
    b5 = c << straight_io
    b5.connect("o1", b4.ports["o2"])

    # --- Expose Ports ---
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])

    return c

# Create and save
device = directional_coupler_refined_v3()
device.write_gds("directional_coupler_refined_v3.gds")
device.show()