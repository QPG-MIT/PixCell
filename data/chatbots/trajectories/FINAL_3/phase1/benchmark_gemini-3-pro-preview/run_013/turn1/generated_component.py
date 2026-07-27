import gdsfactory as gf

@gf.cell
def directional_coupler_240x4():
    """
    Parametric reconstruction of a directional coupler based on visual analysis.
    Strictly constrained to a bounding box of 4um (height) x 240um (length).
    """
    c = gf.Component()
    
    # --- Dimensions & Constraints ---
    total_length = 240.0
    total_height = 4.0
    
    wg_width = 0.5
    coupling_gap = 0.2
    
    # --- Length Budget ---
    # Visually, the central coupling region is the longest segment.
    # We distribute the 240um total length to fit the components.
    l_io = 10.0         # Input/Output straight stubs
    l_coupler = 120.0   # Central coupling region
    # Remaining length is split between the two S-bends
    l_sbend = (total_length - l_coupler - (2 * l_io)) / 2  # (240 - 120 - 20)/2 = 50.0
    
    # --- Vertical Positions (Y-Coordinates) ---
    # To satisfy the exact 4.0um height, the outer edges must be at y=+2.0 and y=-2.0
    y_max_edge = total_height / 2
    
    # Center Y positions for the Input/Output waveguides
    y_top_io = y_max_edge - (wg_width / 2)       # 2.0 - 0.25 = 1.75
    y_bot_io = -y_max_edge + (wg_width / 2)      # -2.0 + 0.25 = -1.75
    
    # Center Y positions for the Coupling waveguides (near 0)
    y_top_c = (coupling_gap / 2) + (wg_width / 2) # 0.1 + 0.25 = 0.35
    y_bot_c = -y_top_c                            # -0.35
    
    # Calculate the vertical shift (dy) required for the S-bends
    # Top arm shift: goes from 1.75 down to 0.35
    dy_top = y_top_c - y_top_io  # -1.4
    
    # Bottom arm shift: goes from -1.75 up to -0.35
    dy_bot = y_bot_c - y_bot_io  # +1.4

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width)

    # ==========================================
    # Top Arm Construction
    # ==========================================
    # 1. Input Straight
    t1 = c << gf.components.straight(length=l_io, cross_section=xs)
    t1.movey(y_top_io)
    
    # 2. S-Bend (Converging)
    t2 = c << gf.components.bend_s(size=(l_sbend, dy_top), cross_section=xs)
    t2.connect("o1", t1.ports["o2"])
    
    # 3. Coupling Straight
    t3 = c << gf.components.straight(length=l_coupler, cross_section=xs)
    t3.connect("o1", t2.ports["o2"])
    
    # 4. S-Bend (Diverging) - dy is reversed to go back up
    t4 = c << gf.components.bend_s(size=(l_sbend, -dy_top), cross_section=xs)
    t4.connect("o1", t3.ports["o2"])
    
    # 5. Output Straight
    t5 = c << gf.components.straight(length=l_io, cross_section=xs)
    t5.connect("o1", t4.ports["o2"])

    # ==========================================
    # Bottom Arm Construction
    # ==========================================
    # 1. Input Straight
    b1 = c << gf.components.straight(length=l_io, cross_section=xs)
    b1.movey(y_bot_io)
    
    # 2. S-Bend (Converging)
    b2 = c << gf.components.bend_s(size=(l_sbend, dy_bot), cross_section=xs)
    b2.connect("o1", b1.ports["o2"])
    
    # 3. Coupling Straight
    b3 = c << gf.components.straight(length=l_coupler, cross_section=xs)
    b3.connect("o1", b2.ports["o2"])
    
    # 4. S-Bend (Diverging) - dy is reversed to go back down
    b4 = c << gf.components.bend_s(size=(l_sbend, -dy_bot), cross_section=xs)
    b4.connect("o1", b3.ports["o2"])
    
    # 5. Output Straight
    b5 = c << gf.components.straight(length=l_io, cross_section=xs)
    b5.connect("o1", b4.ports["o2"])

    # --- Expose Ports ---
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    device = directional_coupler_240x4()
    
    # 1. Write the GDS file (This fixes the error)
    gds_filename = "directional_coupler_240x4.gds"
    device.write_gds(gds_filename)
    print(f"Success: GDS file written to '{gds_filename}'")
    
    # 2. Verify Footprint
    print(f"Verified Dimensions: {device.size_info}")
    
    # 3. Attempt visualization (wrapped in try-except to avoid errors in headless environments)
    try:
        device.show()
    except Exception:
        print("Note: Could not open KLayout viewer (expected in headless environments).")