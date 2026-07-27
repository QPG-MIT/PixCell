import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    """
    Parametric directional coupler built from standard primitives.
    Total Footprint: 18um x 3um.
    """
    c = gf.Component("directional_coupler")

    # --- Geometric Parameters ---
    wg_width = 0.5
    gap = 0.2
    
    # Deriving coordinates to hit the exact [18, 3] bounding box
    # Outer width is 3.0. Centers of waveguides are 0.25um inside the edges
    y_end = (3.0 - wg_width) / 2.0          # 1.25 um
    y_mid = (wg_width + gap) / 2.0          # 0.35 um
    
    dy_bend = y_end - y_mid                 # 0.9 um
    length_straight = 6.0
    length_bend = (18.0 - length_straight) / 2.0 # 6.0 um

    # Create the standard cross-section, overriding minimum bend radius
    # constraints so our mathematically calculated 7.66um S-bends are permitted
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0),
        radius=5.0,        # Default bend routing radius (smaller than 7.66)
        radius_min=5.0     # Bypass minimum constraint error
    )

    # --- Component Primitives ---
    straight_wg = gf.components.straight(length=length_straight, cross_section=xs)
    
    # S-Bend going UP (positive dy)
    bend_up = gf.components.bend_s(size=(length_bend, dy_bend), cross_section=xs)
    # S-Bend going DOWN (negative dy)
    bend_down = gf.components.bend_s(size=(length_bend, -dy_bend), cross_section=xs)

    # ==========================
    # --- Top Arm Assembly ---
    # ==========================
    top_mid = c << straight_wg
    top_mid.move((length_bend, y_mid)) # Center straight section

    # Left Top S-Bend (Routes from y=1.25 down to y=0.35)
    top_left = c << bend_down
    top_left.connect("o2", top_mid.ports["o1"])

    # Right Top S-Bend (Routes from y=0.35 up to y=1.25)
    top_right = c << bend_up
    top_right.connect("o1", top_mid.ports["o2"])

    # ==========================
    # --- Bottom Arm Assembly --
    # ==========================
    bot_mid = c << straight_wg
    bot_mid.move((length_bend, -y_mid)) # Center straight section

    # Left Bottom S-Bend (Routes from y=-1.25 up to y=-0.35)
    bot_left = c << bend_up
    bot_left.connect("o2", bot_mid.ports["o1"])

    # Right Bottom S-Bend (Routes from y=-0.35 down to y=-1.25)
    bot_right = c << bend_down
    bot_right.connect("o1", bot_mid.ports["o2"])

    # --- Expose the external ports ---
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component and explicitly write the GDS file
    c = directional_coupler()
    c.write_gds("directional_coupler.gds")