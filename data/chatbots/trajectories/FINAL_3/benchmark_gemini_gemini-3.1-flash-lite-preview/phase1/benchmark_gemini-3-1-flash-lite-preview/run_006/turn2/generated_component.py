import gdsfactory as gf

@gf.cell
def coupled_waveguides_device():
    """
    Creates a symmetric coupled waveguide structure.
    By setting center_separation to 0, the waveguides merge in the center,
    creating the fused coupling region shown in the target image.
    """
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Dimensions
    total_length = 120
    coupling_length = 20
    arm_length = 20
    # Length remaining for the S-bend sections
    s_bend_length = (total_length - coupling_length - (2 * arm_length)) / 2
    
    # Offsets
    input_separation = 2.0  
    # Setting this to 0 forces the two waveguides to overlap in the center, 
    # creating the fused bar visual.
    center_separation = 0.0 
    
    delta_y = (input_separation - center_separation) / 2

    # Helper function to build one arm
    def add_arm(y_start, direction_sign):
        # 1. Start straight section
        start_wg = c << gf.components.straight(length=arm_length, cross_section=xs)
        start_wg.movey(y_start)

        # 2. First S-bend (Move towards center)
        sb1 = c << gf.components.bend_s(size=(s_bend_length, -direction_sign * delta_y), cross_section=xs)
        sb1.connect("o1", start_wg.ports["o2"])

        # 3. Center straight (Coupling region)
        # Because we merged the waveguides, this section will look like a single bar
        center_wg = c << gf.components.straight(length=coupling_length, cross_section=xs)
        center_wg.connect("o1", sb1.ports["o2"])

        # 4. Second S-bend (Move back to original Y)
        sb2 = c << gf.components.bend_s(size=(s_bend_length, direction_sign * delta_y), cross_section=xs)
        sb2.connect("o1", center_wg.ports["o2"])

        # 5. Output straight
        end_wg = c << gf.components.straight(length=arm_length, cross_section=xs)
        end_wg.connect("o1", sb2.ports["o2"])

    # Build Top Arm (moves down)
    add_arm(y_start=(input_separation/2), direction_sign=1)
    
    # Build Bottom Arm (moves up)
    add_arm(y_start=-(input_separation/2), direction_sign=-1)

    return c

# Generate and save
device = coupled_waveguides_device()
device.write_gds("coupled_waveguides_merged.gds")