import gdsfactory as gf

@gf.cell
def mmi_1x4_optimized():
    """
    Creates a 1x4 MMI with geometry matched to the visual reference.
    """
    c = gf.Component()
    
    # 1. Define MMI Body Dimensions
    # Based on the 25x10 footprint constraint and visual proportions
    mmi_width = 25.0
    mmi_height = 10.0
    layer = (1, 0)
    
    # Create the rectangular body
    body = c << gf.components.rectangle(
        size=(mmi_width, mmi_height), 
        layer=layer, 
        centered=True
    )

    # 2. Define Output Arms (Top)
    # The target image shows long, slender tapers leading into straight waveguides.
    arm_taper_len = 10.0     # Long taper for a gradual, 'slender' transition
    arm_straight_len = 5.0   # Straight extension waveguide
    w_base = 5.6             # Wide base to nearly fill the channel pitch (Gap ~0.65um)
    w_tip = 1.0              # Narrow output waveguide width
    
    # Define cross_section for the straight extensions
    xs_arm = gf.cross_section.cross_section(width=w_tip, layer=layer)
    
    # Create a sub-component for the output arm to replicate
    arm = gf.Component()
    
    # Taper section: Transitions from wide base at MMI to narrow waveguide
    taper = arm << gf.components.taper(
        length=arm_taper_len, 
        width1=w_base, 
        width2=w_tip, 
        layer=layer
    )
    
    # Straight section: Extends from the taper tip
    straight = arm << gf.components.straight(
        length=arm_straight_len, 
        cross_section=xs_arm
    )
    
    # Connect the straight section to the narrow end (o2) of the taper
    straight.connect("o1", taper.ports["o2"])
    
    # Expose the wide base (o1) as the main port for this sub-component
    arm.add_port("o1", port=taper.ports["o1"])
    
    # Calculate positions for the 4 arms
    # The 25um width is divided into 4 equal slots (pitch = 6.25um)
    pitch = mmi_width / 4
    # Calculate center x-coordinates relative to the MMI center (0,0)
    offsets = [(i - 1.5) * pitch for i in range(4)]
    
    # Place the 4 arms
    for x_pos in offsets:
        ref = c << arm
        ref.rotate(90)  # Rotate to point upwards
        ref.move((x_pos, mmi_height / 2)) # Attach to the top edge of the MMI

    # 3. Define Input Arm (Bottom)
    # The target shows a shorter, distinct taper at the bottom input
    input_len = 4.0
    input_w_base = 3.5
    input_w_tip = 1.0
    
    input_taper = gf.components.taper(
        length=input_len,
        width1=input_w_base,
        width2=input_w_tip,
        layer=layer
    )
    
    ref_in = c << input_taper
    ref_in.rotate(-90) # Point downwards
    ref_in.move((0, -mmi_height / 2)) # Attach to the bottom edge of the MMI

    return c

# Create and write the GDS
component = mmi_1x4_optimized()
component.write_gds("mmi_1x4_optimized.gds")
component.show()