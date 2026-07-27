import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreation of the Directional Coupler from the image.
    Constraint: 4 um x 240 um footprint.
    """
    c = gf.Component("Directional_Coupler_4x240")

    # ---------------------------------------------------------
    # 1. Parameters & Geometry Calculation
    # ---------------------------------------------------------
    # Total device bounds
    L_total = 240.0
    H_total = 4.0
    
    # Waveguide specs
    wg_width = 0.5
    gap = 0.2  # Gap in the coupling region
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Calculate vertical positions (y-coordinates) based on 4um height
    # Inputs/Outputs are aligned to the outer edges of the 4um footprint
    # Top y center = (Height / 2) - (WG_Width / 2)
    y_in_top = (H_total / 2) - (wg_width / 2)   # +1.75 um
    y_in_bot = -y_in_top                        # -1.75 um
    
    # Coupling region y positions (centered around y=0)
    y_coup_top = (gap / 2) + (wg_width / 2)     # +0.35 um
    y_coup_bot = -y_coup_top                    # -0.35 um
    
    # Calculate S-bend vertical shift (dy)
    # The bend needs to move from the input height to the coupling height
    dy = y_in_top - y_coup_top                  # 1.4 um
    
    # Horizontal length distribution
    # Total 240um. Visually, the device has substantial bend lengths.
    # We allocate 80um for the coupler and split the rest for bends.
    L_straight = 80.0
    L_sbend = (L_total - L_straight) / 2  # 80.0 um

    # ---------------------------------------------------------
    # 2. Instantiate Primitives
    # ---------------------------------------------------------
    
    # --- Input S-Bends (Left Side) ---
    # Top Left: Bends down (-dy)
    sbend_in_top = c << gf.components.bend_s(
        size=(L_sbend, -dy), 
        cross_section=xs
    )
    # Bottom Left: Bends up (+dy)
    sbend_in_bot = c << gf.components.bend_s(
        size=(L_sbend, dy), 
        cross_section=xs
    )

    # --- Coupling Region (Center) ---
    # Two parallel straight waveguides
    wg_coup_top = c << gf.components.straight(
        length=L_straight, 
        cross_section=xs
    )
    wg_coup_bot = c << gf.components.straight(
        length=L_straight, 
        cross_section=xs
    )

    # --- Output S-Bends (Right Side) ---
    # Top Right: Bends up (+dy) to return to original height
    sbend_out_top = c << gf.components.bend_s(
        size=(L_sbend, dy), 
        cross_section=xs
    )
    # Bottom Right: Bends down (-dy)
    sbend_out_bot = c << gf.components.bend_s(
        size=(L_sbend, -dy), 
        cross_section=xs
    )

    # ---------------------------------------------------------
    # 3. Assembly (Connections)
    # ---------------------------------------------------------
    
    # 1. Move Inputs to starting positions
    sbend_in_top.movey(y_in_top)
    sbend_in_bot.movey(y_in_bot)
    
    # 2. Connect Coupling Straights to Input S-bends
    wg_coup_top.connect("o1", sbend_in_top.ports["o2"])
    wg_coup_bot.connect("o1", sbend_in_bot.ports["o2"])
    
    # 3. Connect Output S-bends to Coupling Straights
    sbend_out_top.connect("o1", wg_coup_top.ports["o2"])
    sbend_out_bot.connect("o1", wg_coup_bot.ports["o2"])

    # ---------------------------------------------------------
    # 4. Expose Ports
    # ---------------------------------------------------------
    c.add_port("o1", port=sbend_in_top.ports["o1"])
    c.add_port("o2", port=sbend_in_bot.ports["o1"])
    c.add_port("o3", port=sbend_out_top.ports["o2"])
    c.add_port("o4", port=sbend_out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    device = directional_coupler_4x240()
    
    # Save the GDS file explicitly
    gdspath = device.write_gds("directional_coupler.gds")
    print(f"GDS file successfully written to: {gdspath}")