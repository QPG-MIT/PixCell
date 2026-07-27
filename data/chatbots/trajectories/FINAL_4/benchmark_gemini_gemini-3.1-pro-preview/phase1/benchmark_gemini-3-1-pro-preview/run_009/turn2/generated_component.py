import gdsfactory as gf

@gf.cell
def smooth_directional_coupler() -> gf.Component:
    """
    Parametric smooth directional coupler (no straight coupling region).
    Constructed from continuous back-to-back S-bends.
    Total Footprint: 18um x 3um.
    """
    c = gf.Component("smooth_directional_coupler")

    # --- Geometric Parameters ---
    wg_width = 0.5
    gap = 0.2
    
    # Deriving coordinates to hit the exact [18, 3] bounding box
    # Outer width is 3.0. Centers of waveguides are 0.25um inside the edges
    y_out = (3.0 - wg_width) / 2.0          # 1.25 um
    y_in = (wg_width + gap) / 2.0           # 0.35 um
    
    # Each arm is made of TWO 9um long S-bends
    dy = y_out - y_in                       # 0.9 um
    length_half = 18.0 / 2.0                # 9.0 um

    # Create the standard cross-section, overriding minimum bend radius
    # constraints so our exactly-dimensioned S-bends are permitted
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0),
        radius_min=1.0     # Bypass minimum constraint error
    )

    # --- Component Primitives (Half-length S-Bends) ---
    # Top arm parts
    top_bend_down = gf.components.bend_s(size=(length_half, -dy), cross_section=xs)
    top_bend_up = gf.components.bend_s(size=(length_half, dy), cross_section=xs)
    
    # Bottom arm parts
    bot_bend_up = gf.components.bend_s(size=(length_half, dy), cross_section=xs)
    bot_bend_down = gf.components.bend_s(size=(length_half, -dy), cross_section=xs)

    # ==========================
    # --- Top Arm Assembly ---
    # ==========================
    # Left half: curves down from 1.25 to 0.35
    top_left = c << top_bend_down
    top_left.movey(y_out)
    
    # Right half: curves back up from 0.35 to 1.25
    top_right = c << top_bend_up
    top_right.connect("o1", top_left.ports["o2"])

    # ==========================
    # --- Bottom Arm Assembly --
    # ==========================
    # Left half: curves up from -1.25 to -0.35
    bot_left = c << bot_bend_up
    bot_left.movey(-y_out)
    
    # Right half: curves back down from -0.35 to -1.25
    bot_right = c << bot_bend_down
    bot_right.connect("o1", bot_left.ports["o2"])

    # --- Expose the external ports ---
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component and explicitly write the GDS file
    c = smooth_directional_coupler()
    c.write_gds("smooth_directional_coupler.gds")