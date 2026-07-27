import gdsfactory as gf

@gf.cell
def optical_splitter_1x4():
    """
    Creates a 1x4 optical splitter geometry using parametric primitives.
    Light propagation is assumed bottom-to-top.
    """
    c = gf.Component("optical_splitter_1x4")
    layer = (1, 0)
    
    # --- 1. Central Body (MMI Region) ---
    # Based on footprint constraint, the central core is 25 wide and 10 high.
    body_width = 25.0
    body_height = 10.0
    c << gf.components.rectangle(size=(body_width, body_height), layer=layer, centered=True)

    # --- 2. Bottom Input Taper ---
    # Wide end (4.0um) connects flush to the rectangle, narrow end (1.5um) is the input.
    t_bot = c << gf.components.taper(
        length=5.0,
        width1=4.0,  # Base width at MMI body
        width2=1.5   # Input waveguide width
    )
    # Rotate -90 makes wide end (o1) face UP, narrow end (o2) face DOWN. 
    # Move to bottom edge of the rectangle (y = -5).
    t_bot.rotate(-90)
    t_bot.move((0, -body_height / 2))
    
    # Expose the input port
    c.add_port("o1", port=t_bot.ports["o2"])

    # --- 3. Top Output Arms (Taper + Straight) ---
    # 4 output arms. Distributed symmetrically across the 25um width.
    x_centers = [-9.0, -3.0, 3.0, 9.0]
    
    xs_top = gf.cross_section.cross_section(width=1.0, layer=layer)

    for i, x_pos in enumerate(x_centers):
        # A. Output Taper
        t_top = c << gf.components.taper(
            length=8.0,
            width1=4.0,  # Base width at MMI body
            width2=1.0   # Tip width
        )
        # Rotate 90 makes wide end (o1) face DOWN, narrow end (o2) face UP.
        # Move to top edge of rectangle (y = +5).
        t_top.rotate(90)
        t_top.move((x_pos, body_height / 2))

        # B. Straight Extension
        s_top = c << gf.components.straight(
            length=7.0, 
            cross_section=xs_top
        )
        # Automatically rotate and snap the straight section to the top of the taper
        s_top.connect("o1", t_top.ports["o2"])
        
        # Expose output ports (o2, o3, o4, o5)
        c.add_port(f"o{i+2}", port=s_top.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the component
    device = optical_splitter_1x4()
    
    # Save the physical geometry to disk (fixes the "No GDS file produced" error)
    device.write_gds("optical_splitter_1x4.gds")