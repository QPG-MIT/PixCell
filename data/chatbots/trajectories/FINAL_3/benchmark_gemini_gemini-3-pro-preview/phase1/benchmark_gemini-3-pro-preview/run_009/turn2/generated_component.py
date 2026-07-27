import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler matching the 120um x 4um footprint.
    Geometry adjusted to match visual reference:
    - Longer central straight section (60um).
    - Compact S-bends (30um) for distinct curvature.
    """
    c = gf.Component()
    
    # === Parameters ===
    # Footprint constraints
    total_length = 120.0
    total_height = 4.0
    
    # Waveguide parameters
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal Dimensions (Length)
    # Analysis of the target image suggests the straight coupling region 
    # is roughly 50% of the total length.
    l_coupling = 60.0
    l_sbend = (total_length - l_coupling) / 2  # 30.0 um
    
    # Vertical Dimensions (Height)
    # 1. Inner separation at coupling region (center-to-center)
    # y = +/- (gap/2 + width/2)
    y_coup_offset = (gap + wg_width) / 2  # 0.35 um
    
    # 2. Outer separation at IO ports (center-to-center)
    # Constrained by total_height = 4.0um (bounding box)
    # Top center = 2.0 - 0.25 = 1.75
    # Bottom center = -2.0 + 0.25 = -1.75
    y_io_offset = total_height / 2 - wg_width / 2 # 1.75 um
    
    # Vertical shift for S-bends
    dy = y_io_offset - y_coup_offset # 1.4 um

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # === Component Creation ===
    
    # 1. Central Coupling Region
    coupler_core = c << gf.components.coupler_straight(
        length=l_coupling,
        gap=gap,
        cross_section=xs
    )
    
    # 2. Define S-Bend Primitives
    # Downward S-bend (Input Top -> Coupler Top)
    bend_down = gf.components.bend_s(
        size=(l_sbend, -dy),
        cross_section=xs
    )
    
    # Upward S-bend (Input Bot -> Coupler Bot)
    bend_up = gf.components.bend_s(
        size=(l_sbend, dy),
        cross_section=xs
    )
    
    # 3. Instantiate and Place Bends
    
    # Input Side (Left)
    # Top input: Starts high, bends down to connect to West-Top of coupler
    in_top = c << bend_down
    in_top.connect("o2", coupler_core.ports["o1"])
    
    # Bottom input: Starts low, bends up to connect to West-Bottom of coupler
    in_bot = c << bend_up
    in_bot.connect("o2", coupler_core.ports["o2"])
    
    # Output Side (Right)
    # Top output: Connects to East-Top of coupler, bends up to exit high
    out_top = c << bend_up
    out_top.connect("o1", coupler_core.ports["o3"])
    
    # Bottom output: Connects to East-Bottom of coupler, bends down to exit low
    out_bot = c << bend_down
    out_bot.connect("o1", coupler_core.ports["o4"])
    
    # === Add Ports ===
    c.add_port("o1", port=in_top.ports["o1"]) # Top Input
    c.add_port("o2", port=in_bot.ports["o1"]) # Bot Input
    c.add_port("o3", port=out_top.ports["o2"]) # Top Output
    c.add_port("o4", port=out_bot.ports["o2"]) # Bot Output
    
    return c

# Generate and save the device
device = directional_coupler_120x4()
device.write_gds("directional_coupler_120x4.gds")