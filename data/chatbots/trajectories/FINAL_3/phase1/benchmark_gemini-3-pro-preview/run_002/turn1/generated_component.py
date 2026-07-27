import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler based on image analysis and parametric primitives.
    Constraints: 4um x 240um footprint.
    """
    c = gf.Component("Directional_Coupler")

    # 1. Define Design Parameters
    # ---------------------------
    # Using specific catalog syntax for cross_section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    total_length = 240.0
    footprint_height = 4.0
    wg_width = 0.5
    gap = 0.2
    
    # Calculate geometric derived parameters
    # Input/Output Port Pitch (Center-to-Center)
    # To fit within 4um height: (4.0 - 0.5) = 3.5um
    io_pitch = footprint_height - wg_width 
    
    # Coupling Region Pitch (Center-to-Center)
    coupling_pitch = wg_width + gap        # 0.7um
    
    # Vertical shift (dy) required for the S-bends for a single arm
    dy = (io_pitch - coupling_pitch) / 2   # 1.4um

    # Length distribution (Split 240um into 3 segments: 80-80-80)
    l_coupling = 80.0
    l_sbend = (total_length - l_coupling) / 2 # 80.0

    # 2. Create Primitives
    # --------------------
    
    # A. Central Straight Coupler
    # Catalog Function: gf.components.coupler_straight
    core = c << gf.components.coupler_straight(
        length=l_coupling,
        gap=gap,
        cross_section=xs
    )

    # B. Input S-Bends (Converging)
    # Catalog Function: gf.components.bend_s
    # Top arm must go DOWN (-dy), Bottom arm must go UP (+dy)
    bend_in_top = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_in_bot = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)

    # C. Output S-Bends (Diverging)
    # Top arm must go UP (+dy), Bottom arm must go DOWN (-dy)
    bend_out_top = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_out_bot = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)

    # 3. Assembly (Place and Connect)
    # -------------------------------
    
    # Connect Input Bends to the Core
    # Connecting the 'o2' (end) of the S-bend to the input ports of the straight coupler
    bend_in_top.connect("o2", core.ports["o1"])
    bend_in_bot.connect("o2", core.ports["o2"])

    # Connect Output Bends to the Core
    # Connecting the 'o1' (start) of the S-bend to the output ports of the straight coupler
    bend_out_top.connect("o1", core.ports["o3"])
    bend_out_bot.connect("o1", core.ports["o4"])

    # 4. Expose Ports
    # ---------------
    c.add_port("o1", port=bend_in_top.ports["o1"])   # Input Top
    c.add_port("o2", port=bend_in_bot.ports["o1"])   # Input Bottom
    c.add_port("o3", port=bend_out_top.ports["o2"])  # Output Top
    c.add_port("o4", port=bend_out_bot.ports["o2"])  # Output Bottom

    return c

if __name__ == "__main__":
    # Create the device
    device = directional_coupler_4x240()
    
    # WRITE GDS FILE
    filename = "directional_coupler_4x240.gds"
    device.write_gds(filename)
    
    print(f"Success: GDS file '{filename}' has been created.")
    print(f"Device Footprint: {device.size_info}")