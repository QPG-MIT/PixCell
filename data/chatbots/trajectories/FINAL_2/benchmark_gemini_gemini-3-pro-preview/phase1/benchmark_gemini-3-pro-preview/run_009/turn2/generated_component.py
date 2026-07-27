import gdsfactory as gf

@gf.cell
def mmi_1x4_fixed():
    """
    Creates a 1x4 MMI with geometry matched to the visual reference.
    Fixed: Uses cross_section for straight waveguides to avoid TypeError.
    """
    c = gf.Component()
    
    # 1. Define MMI Body Dimensions
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
    # Parameters for the "funnel" shape
    arm_taper_len = 4.0      # Length of the tapered transition
    arm_straight_len = 8.0   # Length of the straight extension
    w_base = 4.8             # Wide base at MMI interface
    w_tip = 1.5              # Waveguide width
    
    # Define a cross_section for the straight waveguide parts
    # This encapsulates the width and layer information
    xs_arm = gf.cross_section.cross_section(width=w_tip, layer=layer)
    
    # Create a sub-component for the output arm
    arm = gf.Component()
    
    # Taper: transitions from wide base to waveguide width
    # Note: 'taper' typically accepts 'layer' directly in most versions
    taper = arm << gf.components.taper(
        length=arm_taper_len, 
        width1=w_base, 
        width2=w_tip, 
        layer=layer
    )
    
    # Straight: extension using the cross_section
    straight = arm << gf.components.straight(
        length=arm_straight_len, 
        cross_section=xs_arm
    )
    
    # Connect the straight section to the narrow end (o2) of the taper
    straight.connect("o1", taper.ports["o2"])
    
    # Expose the base port "o1" for connection to the main body
    arm.add_port("o1", port=taper.ports["o1"])
    
    # Place the 4 output arms
    # Offsets: ±1/8*W and ±3/8*W
    offsets = [
        -3 * mmi_width / 8,
        -1 * mmi_width / 8,
         1 * mmi_width / 8,
         3 * mmi_width / 8
    ]
    
    for x_pos in offsets:
        ref = c << arm
        ref.rotate(90)  # Point upwards
        ref.move((x_pos, mmi_height / 2)) # Position at top edge of MMI body

    # 3. Define Input Arm (Bottom)
    input_len = 5.0
    input_w_base = 5.0
    input_w_tip = 1.5
    
    input_taper = gf.components.taper(
        length=input_len,
        width1=input_w_base,
        width2=input_w_tip,
        layer=layer
    )
    
    ref_in = c << input_taper
    ref_in.rotate(-90) # Point downwards
    ref_in.move((0, -mmi_height / 2)) # Position at bottom edge of MMI body

    return c

# Create and write the GDS
component = mmi_1x4_fixed()
component.write_gds("mmi_1x4_fixed.gds")
component.show()