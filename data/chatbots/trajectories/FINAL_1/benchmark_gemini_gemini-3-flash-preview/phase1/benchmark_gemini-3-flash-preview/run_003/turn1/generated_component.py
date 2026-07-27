import gdsfactory as gf

@gf.cell
def tapered_coupler_device():
    """
    Recreates the tapered coupler geometry from the image.
    Footprint: 40um x 1.7um
    """
    c = gf.Component("tapered_coupler")
    
    # 1. Configuration Parameters
    l_straight = 5.0
    l_taper = 25.0
    l_bend = 10.0  # Total length = 40.0um
    
    w_core = 0.5
    w_core_tip = 0.05
    w_side_in = 0.1
    w_side_out = 0.45
    gap = 0.075 # Initial gap between core and side arm
    
    # Calculate offsets for 1.7um total height
    # Final center y = (Total Height / 2) - (Final Arm Width / 2)
    y_final_center = (1.7 / 2) - (w_side_out / 2) # 0.85 - 0.225 = 0.625
    # Initial center y
    y_start_center = (w_core / 2) + gap + (w_side_in / 2) # 0.25 + 0.075 + 0.05 = 0.375
    # Required S-bend vertical displacement
    dy = y_final_center - y_start_center # 0.25
    
    # Define Cross-Sections
    xs_side = gf.cross_section.cross_section(width=w_side_out, layer=(1, 0))

    # 2. Build Central Waveguide (Core)
    core_straight = c << gf.components.straight(length=l_straight, width=w_core)
    core_taper = c << gf.components.taper(length=l_taper, width1=w_core, width2=w_core_tip)
    core_taper.connect("o1", core_straight.ports["o2"])

    # 3. Build Top Side Arm
    # Initial straight part
    side_s_top = c << gf.components.straight(length=l_straight, width=w_side_in)
    side_s_top.movey(y_start_center)
    
    # Tapered part
    side_t_top = c << gf.components.taper(length=l_taper, width1=w_side_in, width2=w_side_out)
    side_t_top.connect("o1", side_s_top.ports["o2"])
    
    # S-bend part
    side_b_top = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs_side)
    side_b_top.connect("o1", side_t_top.ports["o2"])

    # 4. Build Bottom Side Arm (Mirror of top)
    side_s_bot = c << gf.components.straight(length=l_straight, width=w_side_in)
    side_s_bot.movey(-y_start_center)
    
    side_t_bot = c << gf.components.taper(length=l_taper, width1=w_side_in, width2=w_side_out)
    side_t_bot.connect("o1", side_s_bot.ports["o2"])
    
    side_b_bot = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs_side)
    side_b_bot.connect("o1", side_t_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the device
    device = tapered_coupler_device()
    
    # Export and visualize
    device.write_gds("tapered_coupler.gds")
    device.show() # Opens in KLayout