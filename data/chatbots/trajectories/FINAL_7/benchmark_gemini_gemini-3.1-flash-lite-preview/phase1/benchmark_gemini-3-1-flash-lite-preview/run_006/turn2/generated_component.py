import gdsfactory as gf

# 1. Define Cross-Sections with radius_min to avoid initial setup errors
# xs_wide (1.0um) for the outer loop and blocks, xs_thin (0.4um) for the gap
xs_wide = gf.cross_section.cross_section(width=1.0, layer=(1, 0), radius_min=0.5)
xs_thin = gf.cross_section.cross_section(width=0.4, layer=(1, 0), radius_min=0.5)

@gf.cell
def build_arm():
    """Builds a horizontal arm: Wide -> Taper -> Thin -> Taper -> Wide."""
    c = gf.Component()
    
    # Segment lengths (Total length must sum to 2.5um to fit 5.5um footprint)
    w_len = 0.5   # Wide block length
    t_len = 0.5   # Taper length
    thin_len = 0.5 # Gap length
    
    # Create components
    wide1 = c << gf.components.straight(length=w_len, cross_section=xs_wide)
    taper1 = c << gf.components.taper(length=t_len, width1=1.0, width2=0.4)
    thin = c << gf.components.straight(length=thin_len, cross_section=xs_thin)
    taper2 = c << gf.components.taper(length=t_len, width1=0.4, width2=1.0)
    wide2 = c << gf.components.straight(length=w_len, cross_section=xs_wide)
    
    # Chain components together
    # Transition: Wide -> Taper1 -> Thin -> Taper2 -> Wide
    taper1.connect("o1", wide1.ports["o2"])
    thin.connect("o1", taper1.ports["o2"])
    taper2.connect("o1", thin.ports["o2"])
    wide2.connect("o1", taper2.ports["o2"])
    
    # Expose outer ports
    c.add_port("o1", port=wide1.ports["o1"])
    c.add_port("o2", port=wide2.ports["o2"])
    return c

@gf.cell
def custom_device():
    c = gf.Component()
    
    # Create arms
    arm_top = c << build_arm()
    arm_bot = c << build_arm()
    
    # Use wide cross section for the outer loop bends
    bend_radius = 1.5
    
    # Bends (180 degree loops, formed by two 90 degree bends)
    b_tl = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_wide)
    b_bl = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_wide)
    b_tr = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_wide)
    b_br = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_wide)
    
    # Assemble Left Side
    b_tl.connect("o1", arm_top.ports["o1"])
    b_bl.connect("o2", b_tl.ports["o2"])
    arm_bot.connect("o1", b_bl.ports["o1"])
    
    # Assemble Right Side
    b_tr.connect("o2", arm_top.ports["o2"])
    b_br.connect("o1", b_tr.ports["o1"])
    arm_bot.connect("o2", b_br.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = custom_device()
    device.write_gds("racetrack_device.gds")
    print("GDS file generated: racetrack_device.gds")