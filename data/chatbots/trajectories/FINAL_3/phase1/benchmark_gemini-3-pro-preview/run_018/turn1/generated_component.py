import gdsfactory as gf

@gf.cell
def directional_coupler_240x4():
    """
    Recreates the directional coupler from the image with a 240x4 um footprint.
    Includes tapered ports, s-bends, and a central coupling region.
    """
    c = gf.Component()

    # --- Parameters ---
    # Global Dimensions
    total_length = 240.0
    footprint_height = 4.0
    
    # Waveguide Dimensions
    width_core = 0.5        # Width in the coupling region
    width_port = 1.0        # Width at the input/output (tapered)
    gap = 0.2               # Coupling gap
    
    # Y-axis positioning
    # We position the ports to maximize use of the 4um height while staying inside it.
    # Center y of the top port: 1.4, Bottom port: -1.4. (Span = 2.8)
    # Edges will be at +/- (1.4 + 1.0/2) = +/- 1.9, which fits in +/- 2.0 (4um total).
    y_port_offset = 1.4
    y_couple_offset = (width_core + gap) / 2
    
    # Calculate vertical shift required for the S-bend
    dy_bend = y_port_offset - y_couple_offset

    # Length Budget Calculation
    # We distribute the 240um total length into segments.
    l_taper = 20.0
    l_couple = 80.0
    # Remaining length is split between the two S-bends
    l_bend = (total_length - l_couple - (2 * l_taper)) / 2

    # --- Define Primitives ---
    xs_core = gf.cross_section.cross_section(width=width_core)
    
    # 1. Taper (flared ports seen in image)
    taper = gf.components.taper(
        length=l_taper, 
        width1=width_port, 
        width2=width_core
    )
    
    # 2. S-Bend (transition)
    # size is (length, height_change). A positive height connects (0,0) to (L, H)
    bend_primitive = gf.components.bend_s(
        size=(l_bend, dy_bend), 
        cross_section=xs_core
    )
    
    # 3. Straight (coupling region)
    straight_couple = gf.components.straight(
        length=l_couple, 
        cross_section=xs_core
    )

    # --- Assembly: Top Arm ---
    # 1. Input Taper
    t_in_top = c << taper
    t_in_top.move((-total_length/2, y_port_offset))
    
    # 2. Input S-Bend
    # The primitive goes UP, but top arm needs to go DOWN to the center.
    # We use mirror() to flip the geometry vertically.
    b_in_top = c << bend_primitive
    b_in_top.mirror() 
    b_in_top.connect("o1", t_in_top.ports["o2"])
    
    # 3. Coupling Straight
    s_top = c << straight_couple
    s_top.connect("o1", b_in_top.ports["o2"])
    
    # 4. Output S-Bend (Needs to go UP away from center)
    b_out_top = c << bend_primitive
    b_out_top.connect("o1", s_top.ports["o2"])
    
    # 5. Output Taper (Connect narrow end o2 to the bend)
    t_out_top = c << taper
    t_out_top.connect("o2", b_out_top.ports["o2"])

    # --- Assembly: Bottom Arm ---
    # We follow the same logic but mirrored coordinates/directions
    
    # 1. Input Taper
    t_in_bot = c << taper
    t_in_bot.move((-total_length/2, -y_port_offset))
    
    # 2. Input S-Bend (Bottom needs to go UP towards center)
    b_in_bot = c << bend_primitive
    b_in_bot.connect("o1", t_in_bot.ports["o2"])
    
    # 3. Coupling Straight
    s_bot = c << straight_couple
    s_bot.connect("o1", b_in_bot.ports["o2"])
    
    # 4. Output S-Bend (Bottom needs to go DOWN away from center)
    b_out_bot = c << bend_primitive
    b_out_bot.mirror()
    b_out_bot.connect("o1", s_bot.ports["o2"])
    
    # 5. Output Taper
    t_out_bot = c << taper
    t_out_bot.connect("o2", b_out_bot.ports["o2"])

    return c

# Create and save the device
device = directional_coupler_240x4()
device.write_gds("directional_coupler.gds")

# Optional: Visualize if running in a notebook/supported environment
try:
    device.show()
except:
    pass