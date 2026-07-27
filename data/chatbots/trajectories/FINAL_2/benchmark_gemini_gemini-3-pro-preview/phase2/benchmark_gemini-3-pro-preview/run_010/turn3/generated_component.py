import gdsfactory as gf

@gf.cell
def mmi_1x4_vertical_corrected():
    """
    Vertical 1x4 MMI.
    Refined based on visual analysis to match target aspect ratios and gap details.
    """
    c = gf.Component()
    
    # Layer definition
    layer_wg = (1, 0)

    # --- Geometric Parameters ---
    
    # 1. MMI Body
    # Target shows a wide rectangle. We constrain width to 10.0um.
    # Height is adjusted to create the observed wide aspect ratio.
    body_width = 10.0
    body_height = 6.4
    
    # 2. Output Arms (Top)
    # Modeled as a short linear taper transitioning to a straight waveguide
    # to match the "finger" appearance with parallel tops in the reference.
    out_pitch = 2.4      # Spacing between centers
    out_base_width = 1.3 # Reduced base width to ensure clear gaps between arms
    out_tip_width = 0.6  # Standard waveguide width
    out_taper_len = 3.5  # Length of the tapered transition
    out_straight_len = 8.5 # Length of the straight extension
    
    # 3. Input Taper (Bottom)
    # Short, wide-base taper (stubby appearance)
    in_base_width = 2.6
    in_tip_width = 0.6
    in_taper_len = 2.8

    # --- Construction ---

    # 1. Place Body
    # Centered at (0,0)
    body = c << gf.components.rectangle(
        size=(body_width, body_height),
        layer=layer_wg,
        centered=True
    )

    # 2. Build and Place Output Arms
    # We create a sub-component for a single arm (Taper + Straight)
    arm = gf.Component()
    
    # Taper section
    t_out = arm << gf.components.taper(
        length=out_taper_len,
        width1=out_base_width,
        width2=out_tip_width,
        layer=layer_wg
    )
    
    # Straight section
    # Using taper with constant width is a robust way to make a straight 
    # segment without needing specific cross_section definitions.
    s_out = arm << gf.components.taper(
        length=out_straight_len,
        width1=out_tip_width,
        width2=out_tip_width,
        layer=layer_wg
    )
    # Connect straight section to the narrow end of the taper
    s_out.connect("o1", t_out.ports["o2"])
    
    # Expose the base port for placement
    arm.add_port("base", port=t_out.ports["o1"])

    # Place 4 instances of the arm
    n_outputs = 4
    # Calculate centered indices: e.g., -1.5, -0.5, 0.5, 1.5
    indices = [i - (n_outputs - 1) / 2 for i in range(n_outputs)]
    
    for i in indices:
        x_pos = i * out_pitch
        ref = c << arm
        
        # Rotate 90 degrees to point UP (+y)
        ref.rotate(90)
        
        # Move to the top edge of the body
        ref.move((x_pos, body_height / 2))

    # 3. Build and Place Input Taper
    taper_in = gf.components.taper(
        length=in_taper_len,
        width1=in_base_width,
        width2=in_tip_width,
        layer=layer_wg
    )
    ref_in = c << taper_in
    
    # Rotate -90 degrees to point DOWN (-y)
    ref_in.rotate(-90)
    
    # Move to the bottom edge of the body
    ref_in.move((0, -body_height / 2))

    return c

if __name__ == "__main__":
    device = mmi_1x4_vertical_corrected()
    device.write_gds("mmi_1x4_v2.gds")
    device.show()