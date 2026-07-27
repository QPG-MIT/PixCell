import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic directional coupler.
    Replicates the visual geometry of the provided image with a 18um x 3um footprint.
    Adjusted waveguide width and gap for smoother curvature and correct proportions.
    """
    c = gf.Component()
    
    # 1. Define Constraints & Parameters
    length = 18.0
    total_height = 3.0
    
    # Tuned parameters to match image pixel ratios:
    # - Original lines appear thicker (approx 1/4 of height) -> 0.75um width
    # - Gap is tight but distinct -> 0.3um
    wg_width = 0.75   
    gap = 0.3         
    
    # 2. Derive Coordinates
    # We ensure the outer bounding box is exactly 3.0um tall (+1.5 to -1.5)
    
    # Y-coordinates at Input/Output (Widest separation)
    # Center = Edge - (Width / 2)
    y_top_start = (total_height / 2) - (wg_width / 2)   # 1.5 - 0.375 = 1.125
    y_bot_start = -y_top_start                          # -1.125
    
    # Y-coordinates at Waist (Narrowest separation)
    # Center = (Gap / 2) + (Width / 2)
    y_top_waist = (gap / 2) + (wg_width / 2)            # 0.15 + 0.375 = 0.525
    y_bot_waist = -y_top_waist                          # -0.525
    
    # S-bend Parameters
    # Each arm consists of two S-bends: Converging -> Diverging
    half_length = length / 2
    dy_top = y_top_waist - y_top_start  # Displacement for top converging section
    dy_bot = y_bot_waist - y_bot_start  # Displacement for bot converging section
    
    # Cross-section
    xs = gf.cross_section.cross_section(width=wg_width)

    # 3. Construct Geometry
    
    # --- Top Arm ---
    # Converging section (Input -> Waist)
    t_in = c << gf.components.bend_s(size=(half_length, dy_top), cross_section=xs)
    t_in.movey(y_top_start)
    
    # Diverging section (Waist -> Output)
    # The displacement is opposite (-dy_top) to return to the original height
    t_out = c << gf.components.bend_s(size=(half_length, -dy_top), cross_section=xs)
    t_out.connect("o1", t_in.ports["o2"])
    
    # --- Bottom Arm ---
    # Converging section
    b_in = c << gf.components.bend_s(size=(half_length, dy_bot), cross_section=xs)
    b_in.movey(y_bot_start)
    
    # Diverging section
    b_out = c << gf.components.bend_s(size=(half_length, -dy_bot), cross_section=xs)
    b_out.connect("o1", b_in.ports["o2"])
    
    # 4. Expose Ports
    c.add_port("o1", port=t_in.ports["o1"])   # Top Left
    c.add_port("o2", port=b_in.ports["o1"])   # Bottom Left
    c.add_port("o3", port=t_out.ports["o2"])  # Top Right
    c.add_port("o4", port=b_out.ports["o2"])  # Bottom Right

    return c

if __name__ == "__main__":
    device = adiabatic_coupler()
    device.write_gds("adiabatic_coupler.gds")
    device.show()