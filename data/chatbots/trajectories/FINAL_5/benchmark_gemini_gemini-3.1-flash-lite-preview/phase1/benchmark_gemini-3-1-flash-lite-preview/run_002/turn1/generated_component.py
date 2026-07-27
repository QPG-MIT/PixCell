import gdsfactory as gf

@gf.cell
def custom_coupled_grating_device(
    length=15.0, 
    gap=1.0, 
    bend_radius=2.0, 
    rib_width=0.05, 
    rib_period=0.2, 
    waveguide_width=0.5
):
    """
    Recreates the coupled waveguide device with a periodic rib structure
    and U-bend terminations.
    """
    c = gf.Component()
    
    # 1. Create the cross-section
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    
    # FIX: Update the attribute directly after creation to bypass the default 10um constraint
    xs.min_bend_radius = bend_radius

    # 2. Create the central parallel waveguides
    # We use straight segments for the coupling region
    s_top = c << gf.components.straight(length=length, cross_section=xs)
    s_bot = c << gf.components.straight(length=length, cross_section=xs)
    
    # Calculate vertical offset so top/bottom align with U-bends
    # A 180-degree bend's total width is 2 * radius.
    # Therefore, the waveguides need to be separated by 2 * radius (or similar logic).
    # We adjust the bend radius to match the spacing
    vertical_offset = bend_radius
    
    s_top.movey(vertical_offset)
    s_bot.movey(-vertical_offset)

    # 3. Add the periodic rib structure (Grating)
    num_ribs = int(length / rib_period)
    for i in range(num_ribs):
        x_pos = -length/2 + (i + 0.5) * rib_period
        # Ribs fill the gap between the two parallel waveguides
        rib = c << gf.components.rectangle(
            size=(rib_width, gap), 
            layer=(1, 0), 
            centered=True
        )
        rib.move((x_pos, 0))

    # 4. Add U-bends (Euler bends) at the ends
    # Connect the top right to bottom right
    top_bend = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    top_bend.connect("o1", s_top.ports["o2"])
    
    # Connect the top left to bottom left
    bot_bend = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    bot_bend.rotate(180)
    bot_bend.connect("o1", s_bot.ports["o1"])

    # 5. Add input/output tapers
    # Connect to the remaining free ports
    taper_top = c << gf.components.taper(length=1.0, width1=waveguide_width, width2=0.8)
    taper_top.connect("o1", s_top.ports["o1"])
    
    taper_bot = c << gf.components.taper(length=1.0, width1=waveguide_width, width2=0.8)
    taper_bot.connect("o1", s_bot.ports["o2"])

    # Expose external ports
    c.add_port("o1", port=taper_top.ports["o2"])
    c.add_port("o2", port=taper_bot.ports["o2"])

    return c

# Instantiate and generate the GDS
device = custom_coupled_grating_device()
device.write_gds("custom_coupler_fixed.gds")