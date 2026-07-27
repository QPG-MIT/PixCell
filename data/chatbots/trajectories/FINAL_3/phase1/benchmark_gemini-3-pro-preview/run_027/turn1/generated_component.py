import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreates the directional coupler from the image within a 4um x 240um footprint
    using standard GDSFactory primitives.
    """
    c = gf.Component()

    # --- 1. Define Parameters ---
    # Global dimensions
    total_length = 240.0
    total_height = 4.0
    
    # Waveguide geometry
    wg_width = 0.5
    gap_coupling = 0.2
    
    # Vertical Positions (Y-axis)
    # Coupling region: waveguides are close to y=0
    # Center position = (gap/2) + (width/2)
    y_center_couple = (gap_coupling / 2) + (wg_width / 2) # 0.1 + 0.25 = 0.35
    
    # Input/Output region: waveguides are at the edges of the 4um box
    # Center position = (height/2) - (width/2)
    y_center_io = (total_height / 2) - (wg_width / 2)     # 2.0 - 0.25 = 1.75
    
    # Calculate the vertical shift required for the S-bend
    dy = y_center_io - y_center_couple # 1.4 um

    # Length Distribution (Total = 240)
    # We estimate these based on the visual proportions of the image
    l_io_straight = 20.0  # Lead-in/out straights
    l_sbend = 60.0        # Length of the S-bend transition
    l_coupling = 80.0     # Length of the parallel coupling region
    
    # Verification: 20 + 60 + 80 + 60 + 20 = 240 um
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Build Top Arm ---
    
    # A. Input Straight
    # Start at x=0 for simplicity, we will move components relative to each other
    t_in = c << gf.components.straight(length=l_io_straight, cross_section=xs)
    t_in.move((0, y_center_io))
    
    # B. S-Bend (Downwards)
    # The bend goes from high Y to low Y, so dy is negative
    t_bend_in = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    t_bend_in.connect("o1", t_in.ports["o2"])
    
    # C. Coupling Straight
    t_couple = c << gf.components.straight(length=l_coupling, cross_section=xs)
    t_couple.connect("o1", t_bend_in.ports["o2"])
    
    # D. S-Bend (Upwards)
    # The bend goes from low Y to high Y, so dy is positive
    t_bend_out = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    t_bend_out.connect("o1", t_couple.ports["o2"])
    
    # E. Output Straight
    t_out = c << gf.components.straight(length=l_io_straight, cross_section=xs)
    t_out.connect("o1", t_bend_out.ports["o2"])

    # --- 3. Build Bottom Arm ---
    # We repeat the process mirrored.
    
    # A. Input Straight (Bottom)
    b_in = c << gf.components.straight(length=l_io_straight, cross_section=xs)
    b_in.move((0, -y_center_io))
    
    # B. S-Bend (Upwards)
    # Goes from low Y (-1.75) to higher Y (-0.35), so change is positive dy
    b_bend_in = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    b_bend_in.connect("o1", b_in.ports["o2"])
    
    # C. Coupling Straight (Bottom)
    b_couple = c << gf.components.straight(length=l_coupling, cross_section=xs)
    b_couple.connect("o1", b_bend_in.ports["o2"])
    
    # D. S-Bend (Downwards)
    # Goes from higher Y to low Y, so change is negative dy
    b_bend_out = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    b_bend_out.connect("o1", b_couple.ports["o2"])
    
    # E. Output Straight (Bottom)
    b_out = c << gf.components.straight(length=l_io_straight, cross_section=xs)
    b_out.connect("o1", b_bend_out.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=t_in.ports["o1"])   # Top Input
    c.add_port("o2", port=b_in.ports["o1"])   # Bottom Input
    c.add_port("o3", port=t_out.ports["o2"])  # Top Output
    c.add_port("o4", port=b_out.ports["o2"])  # Bottom Output

    return c

# Create and save the component
device = directional_coupler_4x240()
device.show() # View in KLayout/GDS viewer
device.write_gds("directional_coupler_4x240.gds")