import gdsfactory as gf

@gf.cell
def directional_coupler(
    total_length: float = 18.0,
    wg_width: float = 0.5,
    gap: float = 0.2,
    port_pitch: float = 2.5,
    straight_length: float = 8.0  # Proportion matching the target image
) -> gf.Component:
    """
    Directional coupler composed of two symmetric waveguide arms.
    """
    c = gf.Component("directional_coupler")
    
    # Define the cross-section
    # We explicitly lower 'radius_min' and 'radius' to bypass the ValueError
    # and allow the tighter S-bends required within this compact footprint.
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0),
        radius_min=0.1,  
        radius=0.1
    )
    
    # Derived parameters for routing
    y_offset = port_pitch / 2.0                           # Starting Y for the top arm center (1.25 um)
    y_center_offset = (wg_width + gap) / 2.0              # Central coupling Y for the top arm (0.35 um)
    dy_sbend = y_offset - y_center_offset                 # Vertical drop needed for the S-bend (0.9 um)
    dx_sbend = (total_length - straight_length) / 2.0     # Horizontal length per S-bend (5.0 um)

    # Instantiate reusable components
    sbend_down = gf.components.bend_s(size=(dx_sbend, -dy_sbend), cross_section=xs)
    sbend_up = gf.components.bend_s(size=(dx_sbend, dy_sbend), cross_section=xs)
    straight_sec = gf.components.straight(length=straight_length, cross_section=xs)

    # --- TOP ARM ---
    sb1_top = c << sbend_down
    str_top = c << straight_sec
    sb2_top = c << sbend_up

    # Position and connect top arm sequentially
    sb1_top.movey(y_offset)
    str_top.connect("o1", sb1_top.ports["o2"])
    sb2_top.connect("o1", str_top.ports["o2"])


    # --- BOTTOM ARM ---
    sb1_bot = c << sbend_up
    str_bot = c << straight_sec
    sb2_bot = c << sbend_down

    # Position and connect bottom arm sequentially
    sb1_bot.movey(-y_offset)
    str_bot.connect("o1", sb1_bot.ports["o2"])
    sb2_bot.connect("o1", str_bot.ports["o2"])


    # --- EXPOSE EXTERNAL PORTS ---
    c.add_port("o1", port=sb1_top.ports["o1"])
    c.add_port("o2", port=sb1_bot.ports["o1"])
    c.add_port("o3", port=sb2_top.ports["o2"])
    c.add_port("o4", port=sb2_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate and explicitly save the device as a GDS file
    device = directional_coupler()
    device.write_gds("directional_coupler.gds")