import gdsfactory as gf

@gf.cell
def coupler_device():
    """
    Creates the coupler geometry. The waveguides start with a wide gap, 
    bend INWARD (towards each other), run parallel in the coupling region, 
    then bend OUTWARD to their original separation.
    """
    c = gf.Component()
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Configuration
    # Total length = 30 + 10 + 40 + 10 + 30 = 120um
    len_in = 30
    len_mid = 40
    len_out = 30
    bend_x = 10
    bend_dy = 0.5 # The waveguides will shift by 0.5um vertically to narrow the gap
    
    # --- Top Arm ---
    # 1. Starts high (y = 1.0)
    s1_top = c << gf.components.straight(length=len_in, cross_section=xs)
    s1_top.movey(1.0)
    
    # 2. Bend INWARD (downwards by 0.5um)
    b1_top = c << gf.components.bend_s(size=(bend_x, -bend_dy), cross_section=xs)
    b1_top.connect("o1", s1_top.ports["o2"])
    
    # 3. Middle straight section (now at y = 0.5)
    s2_top = c << gf.components.straight(length=len_mid, cross_section=xs)
    s2_top.connect("o1", b1_top.ports["o2"])
    
    # 4. Bend OUTWARD (upwards by 0.5um)
    b2_top = c << gf.components.bend_s(size=(bend_x, bend_dy), cross_section=xs)
    b2_top.connect("o1", s2_top.ports["o2"])
    
    # 5. Final straight
    s3_top = c << gf.components.straight(length=len_out, cross_section=xs)
    s3_top.connect("o1", b2_top.ports["o2"])
    
    # --- Bottom Arm ---
    # 1. Starts low (y = -1.0)
    s1_bot = c << gf.components.straight(length=len_in, cross_section=xs)
    s1_bot.movey(-1.0)
    
    # 2. Bend INWARD (upwards by 0.5um)
    b1_bot = c << gf.components.bend_s(size=(bend_x, bend_dy), cross_section=xs)
    b1_bot.connect("o1", s1_bot.ports["o2"])
    
    # 3. Middle straight section (now at y = -0.5)
    s2_bot = c << gf.components.straight(length=len_mid, cross_section=xs)
    s2_bot.connect("o1", b1_bot.ports["o2"])
    
    # 4. Bend OUTWARD (downwards by 0.5um)
    b2_bot = c << gf.components.bend_s(size=(bend_x, -bend_dy), cross_section=xs)
    b2_bot.connect("o1", s2_bot.ports["o2"])
    
    # 5. Final straight
    s3_bot = c << gf.components.straight(length=len_out, cross_section=xs)
    s3_bot.connect("o1", b2_bot.ports["o2"])

    return c

# Create and save
if __name__ == "__main__":
    device = coupler_device()
    device.write_gds("coupler_device.gds")
    device.show()