import gdsfactory as gf

@gf.cell
def directional_coupler_240x4():
    """
    Creates a directional coupler fitting a 240um x 4um footprint.
    Constructed using straight waveguides and S-bends.
    """
    c = gf.Component()
    
    # 1. Define Cross Section (Standard 500nm width)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define Dimensions based on Footprint (240 x 4)
    total_length = 240.0
    coupling_length = 40.0      # Length of the parallel interaction region
    io_length = 10.0            # Short straight sections at input/output
    
    # Calculate bend length to fill the remaining space
    # Total = 2*io + 2*bend + coupling
    bend_length = (total_length - coupling_length - (2 * io_length)) / 2

    # Vertical Geometry
    # Constraint: Must fit in 4um height.
    wg_width = 0.5
    gap = 0.2
    
    # Calculate positions
    # Inputs are spaced wider, coupling region is tight
    y_couple_top = (gap + wg_width) / 2
    y_couple_bot = -y_couple_top
    
    # Place inputs at +/- 1.25um (Total span 2.5um center-to-center, < 4um total)
    y_input_top = 1.25
    y_input_bot = -1.25
    
    # Calculate the vertical shift (dy) required for the S-bend
    dy = y_input_top - y_couple_top

    # 3. Create Primitives
    # Straight sections
    s_io = gf.components.straight(length=io_length, cross_section=xs)
    s_couple = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # S-Bends (Transition)
    # Top arm needs to go DOWN (-dy), Bottom arm needs to go UP (+dy)
    bend_down = gf.components.bend_s(size=(bend_length, -dy), cross_section=xs)
    bend_up = gf.components.bend_s(size=(bend_length, dy), cross_section=xs)

    # 4. Assembly - Top Arm
    # Input Straight
    t1 = c << s_io
    t1.movey(y_input_top)
    
    # S-Bend (Converge)
    t2 = c << bend_down
    t2.connect("o1", t1.ports["o2"])
    
    # Coupling Straight
    t3 = c << s_couple
    t3.connect("o1", t2.ports["o2"])
    
    # S-Bend (Diverge)
    t4 = c << bend_up
    t4.connect("o1", t3.ports["o2"])
    
    # Output Straight
    t5 = c << s_io
    t5.connect("o1", t4.ports["o2"])

    # 5. Assembly - Bottom Arm
    # Input Straight
    b1 = c << s_io
    b1.movey(y_input_bot)
    
    # S-Bend (Converge - moving UP this time)
    b2 = c << bend_up
    b2.connect("o1", b1.ports["o2"])
    
    # Coupling Straight
    b3 = c << s_couple
    b3.connect("o1", b2.ports["o2"])
    
    # S-Bend (Diverge - moving DOWN)
    b4 = c << bend_down
    b4.connect("o1", b3.ports["o2"])
    
    # Output Straight
    b5 = c << s_io
    b5.connect("o1", b4.ports["o2"])

    # 6. Expose Ports
    c.add_port("o1", port=t1.ports["o1"]) # Top Input
    c.add_port("o2", port=b1.ports["o1"]) # Bottom Input
    c.add_port("o3", port=t5.ports["o2"]) # Top Output
    c.add_port("o4", port=b5.ports["o2"]) # Bottom Output

    return c

# Generate and Save
device = directional_coupler_240x4()
device.write_gds("directional_coupler.gds")
device.show()