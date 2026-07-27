import gdsfactory as gf

@gf.cell
def device_mmi_1x4_optimized():
    """
    Optimized 1x4 MMI device geometry - Iteration 5.
    
    Adjustments:
    - Reduced Top Finger Total Length from 16.0um to 12.0um to match the target's 
      visual aspect ratio (finger height ~ body height).
    - Widened Top Finger Base (5.5um) and narrowed Tip (1.8um) to create the 
      distinct "bottleneck" taper shape seen in the reference image.
    - Adjusted Bottom Finger to be a stubby triangular taper (4.0um length), 
      matching the input port geometry.
    """
    c = gf.Component("MMI_1x4_Optimized")

    # 1. Define Dimensions
    # Main interference region
    body_width = 25.0
    body_height = 10.0
    
    # Top Output Fingers (Tapered waveguides)
    # Taper + Straight section to form the "chimney" shape
    tf_taper_len = 7.0
    tf_straight_len = 5.0
    
    # Widths tuned to create the distinct taper profile
    tf_width_base = 5.5
    tf_width_tip = 1.8
    
    # Bottom Input Finger
    bf_length = 4.0
    bf_width_base = 6.0
    bf_width_tip = 2.0

    # Layer definition
    layer_wg = (1, 0)
    
    # Cross-sections for consistent extrusion
    xs_tip = gf.cross_section.cross_section(width=tf_width_tip, layer=layer_wg)
    xs_bot = gf.cross_section.cross_section(width=bf_width_tip, layer=layer_wg)

    # 2. Create the Central Body
    body = c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=layer_wg, 
        centered=True
    )

    # 3. Create Custom Top Finger Component
    # Defined as a reusable component to ensure symmetry and identical geometry
    def create_finger():
        cmp = gf.Component()
        
        # Taper section: Wide Base (Left) -> Narrow Tip (Right)
        # Note: We create it horizontally then rotate it later
        taper = cmp << gf.components.taper(
            length=tf_taper_len,
            width1=tf_width_base,
            width2=tf_width_tip,
            layer=layer_wg
        )
        
        # Straight section: Extends from the tip
        straight = cmp << gf.components.straight(
            length=tf_straight_len,
            cross_section=xs_tip
        )
        
        # Connect straight start (o1) to taper end (o2)
        straight.connect("o1", taper.ports["o2"])
        
        # Expose the base port (o1 of taper) for connection to the main body
        cmp.add_port("o1", port=taper.ports["o1"])
        return cmp

    finger_template = create_finger()

    # 4. Place Top Fingers
    # Calculate symmetric positions for 4 ports distributed across 25um width
    # Pitch = 25 / 4 = 6.25um
    offsets = [3.125, 9.375]
    x_positions = [-x for x in reversed(offsets)] + offsets

    for x in x_positions:
        ref = c << finger_template
        ref.rotate(90) # Rotate 90 degrees CCW to point UP
        ref.move((x, body_height / 2)) # Move to the top edge of the body

    # 5. Create and Place Bottom Finger
    # Input taper (Wide Base -> Narrow Tip)
    # Note: taper default flows Left -> Right.
    bot_taper = gf.components.taper(
        length=bf_length,
        width1=bf_width_base,
        width2=bf_width_tip,
        layer=layer_wg
    )

    ref_bot = c << bot_taper
    ref_bot.rotate(-90) # Rotate 90 degrees CW to point DOWN
    ref_bot.move((0, -body_height / 2)) # Move to the bottom edge of the body

    return c

if __name__ == "__main__":
    device = device_mmi_1x4_optimized()
    device.write_gds("mmi_1x4_optimized.gds")
    print("GDS file generated successfully.")