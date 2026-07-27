import gdsfactory as gf

@gf.cell
def mmi_1x4_optimized():
    """
    Creates a 1x4 MMI with geometry matched to the visual reference.
    Refined dimensions to fix 'spike' appearance and match arm thickness.
    """
    c = gf.Component()
    
    # 1. Main Body Dimensions
    # Footprint constraint 25x10 is the reference anchor.
    mmi_width = 25.0
    mmi_height = 10.0
    layer = (1, 0)
    
    # Create the rectangular body
    body = c << gf.components.rectangle(
        size=(mmi_width, mmi_height), 
        layer=layer, 
        centered=True
    )

    # 2. Output Arms (Top)
    # Pitch for 4 arms across 25um width
    pitch = mmi_width / 4  # 6.25um
    
    # Dimensions derived from image analysis:
    # Base width set to 4.8 to leave ~1.45um gaps (distinct V-notches).
    arm_w_base = 4.8  
    # Tip width increased to 1.8 to create the 'tower' look rather than sharp points.
    arm_w_tip = 1.8   
    # Taper length (angled part)
    arm_taper_len = 9.0 
    # Straight extension length (parallel part)
    arm_straight_len = 6.0 
    
    # Create a sub-component for the single output arm
    arm = gf.Component()
    
    # Taper section
    taper = arm << gf.components.taper(
        length=arm_taper_len, 
        width1=arm_w_base, 
        width2=arm_w_tip, 
        layer=layer
    )
    
    # Straight section
    xs_arm = gf.cross_section.cross_section(width=arm_w_tip, layer=layer)
    straight = arm << gf.components.straight(
        length=arm_straight_len, 
        cross_section=xs_arm
    )
    
    # Connect straight section to the narrow end of taper
    straight.connect("o1", taper.ports["o2"])
    
    # Expose the wide base as the main port
    arm.add_port("o1", port=taper.ports["o1"])
    
    # Place 4 arms
    # Calculate offsets to center the group of 4
    offsets = [(i - 1.5) * pitch for i in range(4)]
    
    for x_pos in offsets:
        ref = c << arm
        ref.rotate(90)  # Point Up
        ref.move((x_pos, mmi_height / 2)) # Attach to top edge

    # 3. Input Arm (Bottom)
    # Shorter, stubbier taper distinct from the top arms.
    input_len = 4.0
    input_w_base = 3.6
    input_w_tip = 1.5
    
    input_taper = gf.components.taper(
        length=input_len,
        width1=input_w_base,
        width2=input_w_tip,
        layer=layer
    )
    
    ref_in = c << input_taper
    ref_in.rotate(-90) # Point Down
    ref_in.move((0, -mmi_height / 2)) # Attach to bottom edge

    return c

if __name__ == "__main__":
    component = mmi_1x4_optimized()
    component.write_gds("mmi_1x4_optimized.gds")
    component.show()