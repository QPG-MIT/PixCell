import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Creates a symmetric directional coupler matching the reference image.
    Footprint constraint: 120um x 4um.
    Adjusted waveguide width and section lengths for better visual match.
    """
    c = gf.Component()

    # --- Dimensions & Constants ---
    total_length = 120.0
    total_height = 4.0
    
    # Tuned parameters to match visual proportions of the reference image
    # Increased width to 0.8um gives the "thicker" look observed in the original
    wg_width = 0.8        
    gap = 0.2             # Keep tight coupling gap
    
    # Length distribution (Total 120)
    # The reference shows prominent S-bends and a moderate coupling region.
    l_io = 10.0           # Input/Output straight length
    l_couple = 30.0       # Central coupling region
    # Calculate bend length to satisfy total length constraint:
    # (120 - 2*10 - 30) / 2 = 35.0
    l_bend = (total_length - 2*l_io - l_couple) / 2 
    
    # --- Vertical Position Calculations ---
    # Constraint: Total height is 4.0um (Edges at +2.0 and -2.0)
    
    # Input y-centers (Outer positions)
    # Center = (Total Height / 2) - (Waveguide Width / 2)
    y_top_in = (total_height / 2) - (wg_width / 2) # 2.0 - 0.4 = 1.6
    y_bot_in = -y_top_in                           # -1.6
    
    # Coupling y-centers (Inner positions)
    # Center = (Gap / 2) + (Waveguide Width / 2)
    y_top_couple = (gap / 2) + (wg_width / 2)      # 0.1 + 0.4 = 0.5
    y_bot_couple = -y_top_couple                   # -0.5
    
    # Vertical displacement for S-bends
    dy = y_top_couple - y_top_in # 0.5 - 1.6 = -1.1 (Drop distance)

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Define Primitives ---
    straight_io = gf.components.straight(length=l_io, cross_section=xs)
    straight_couple = gf.components.straight(length=l_couple, cross_section=xs)
    
    # S-bends
    # Top arm drops down (dy is negative)
    bend_down = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    # Top arm rises up (symmetric, dy is positive magnitude because -(-1.1) = +1.1)
    bend_up = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)

    # --- Assemble Top Arm ---
    # 1. Input Straight
    t1 = c << straight_io
    t1.movey(y_top_in)
    
    # 2. S-Bend Down (converge)
    t2 = c << bend_down
    t2.connect("o1", t1.ports["o2"])
    
    # 3. Coupling Straight
    t3 = c << straight_couple
    t3.connect("o1", t2.ports["o2"])
    
    # 4. S-Bend Up (diverge)
    t4 = c << bend_up
    t4.connect("o1", t3.ports["o2"])
    
    # 5. Output Straight
    t5 = c << straight_io
    t5.connect("o1", t4.ports["o2"])

    # --- Assemble Bottom Arm ---
    # We define bends for the bottom arm. 
    # Moving from Input (-1.6) to Couple (-0.5) is a POSITIVE shift of +1.1.
    # This is exactly -dy.
    bend_bottom_up = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    bend_bottom_down = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)

    # 1. Input Straight
    b1 = c << straight_io
    b1.movey(y_bot_in)
    
    # 2. S-Bend Up (converge)
    b2 = c << bend_bottom_up
    b2.connect("o1", b1.ports["o2"])
    
    # 3. Coupling Straight
    b3 = c << straight_couple
    b3.connect("o1", b2.ports["o2"])
    
    # 4. S-Bend Down (diverge)
    b4 = c << bend_bottom_down
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

# Create and save
device = directional_coupler_refined()
device.write_gds("directional_coupler_refined.gds")
device.show()