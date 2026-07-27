import gdsfactory as gf

@gf.cell
def mmi_1x4_final():
    """
    Creates a 1x4 MMI matched to the specific target geometry.
    Key features:
    - 25x10um rectangular body.
    - 4 Output arms with 'chimney' shape (Taper + Straight).
    - 1 Input arm (Taper).
    - Precise pitch and width control to match gaps and proportions.
    """
    c = gf.Component()
    
    # Dimensions derived from image analysis
    mmi_width = 25.0
    mmi_height = 10.0
    layer = (1, 0)
    
    # 1. Main Body
    # Centered at (0,0) for easier symmetric placement
    body = c << gf.components.rectangle(
        size=(mmi_width, mmi_height), 
        layer=layer, 
        centered=True
    )

    # 2. Output Arms (Top)
    # Parameters for the 'chimney' shape
    num_arms = 4
    pitch = mmi_width / num_arms  # 6.25 um
    
    # Base width: Close to pitch to create thin slits between arms.
    # Pitch 6.25 - 5.7 width = 0.55um gap.
    arm_w_base = 5.7
    
    # Top/Straight width: Defines the 'chimney' neck. 
    # Visually ~1/3 of base width.
    arm_w_top = 1.8
    
    # Lengths: The arm structure looks taller than the MMI body (10um).
    # Divided into a tapered transition and a straight extension.
    taper_length = 12.0
    straight_length = 8.0
    
    # Build the single arm sub-component
    arm = gf.Component()
    
    # Taper part (Base -> Top width)
    taper = arm << gf.components.taper(
        length=taper_length,
        width1=arm_w_base,
        width2=arm_w_top,
        layer=layer
    )
    
    # Straight part (Constant Top width)
    # Create a cross-section for the straight part
    xs_arm = gf.cross_section.cross_section(width=arm_w_top, layer=layer)
    straight = arm << gf.components.straight(
        length=straight_length, 
        cross_section=xs_arm
    )
    
    # Connect straight to taper tip
    # straight port 'o1' connects to taper port 'o2' (the narrow end)
    straight.connect("o1", taper.ports["o2"])
    
    # Expose the base port (o1 of taper) as the arm's connection point
    arm.add_port("o1", port=taper.ports["o1"])
    
    # Place the 4 arms on the main component
    # Offsets relative to center (0,0) to center the array
    offsets = [(i - (num_arms - 1) / 2) * pitch for i in range(num_arms)]
    
    top_edge_y = mmi_height / 2
    
    for x_off in offsets:
        ref = c << arm
        ref.rotate(90) # Rotate to point Up
        ref.move((x_off, top_edge_y)) # Move base to the top edge of the MMI

    # 3. Input Arm (Bottom)
    # Simple, shorter taper.
    # Base slightly wider than a single pitch, tip standard width.
    input_len = 5.0
    input_w_base = 6.0
    input_w_tip = 2.0
    
    input_taper = gf.components.taper(
        length=input_len,
        width1=input_w_base,
        width2=input_w_tip,
        layer=layer
    )
    
    ref_in = c << input_taper
    ref_in.rotate(-90) # Rotate to point Down
    ref_in.move((0, -mmi_height / 2)) # Move base to bottom edge of MMI

    return c

if __name__ == "__main__":
    component = mmi_1x4_final()
    component.write_gds("mmi_1x4_final.gds")
    component.show()