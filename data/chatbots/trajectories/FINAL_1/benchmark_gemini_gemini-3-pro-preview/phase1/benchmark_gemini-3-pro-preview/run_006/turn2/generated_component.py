import gdsfactory as gf

@gf.cell
def inverse_taper_coupler():
    """
    Creates an inverse taper edge coupler.
    
    Structure:
    1. Central taper: High confinement core tapering to a fine tip.
    2. Outer arms: Waveguides that S-bend inwards to capture the optical mode.
       They merge at the output to form a larger waveguide.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Constraint: [40.0, 1.7]
    total_length = 40.0
    
    # Layer definition
    layer = (1, 0)
    
    # Geometry Dimensions
    width_center_in = 0.5     # Input width of central waveguide
    width_center_tip = 0.05   # Tip width (sharp point)
    width_arm = 0.4           # Width of the outer arms
    
    # Taper Length Correction: 
    # The taper must extend almost the full length of the device to match the
    # original image and ensure the tip sits inside the converging outer arms.
    taper_length = 35.0       
    
    # Y-Position Calculations (Height Constraint)
    # Total allowed height = 1.7um (from -0.85 to +0.85)
    # Arm center max = 0.85 - (width_arm / 2) = 0.85 - 0.2 = 0.65
    y_arm_start_offset = 0.65
    
    # Output convergence positions
    # To merge the arms into a single waveguide, they must overlap.
    # Inner edge = center - width/2.
    # If center is 0.15: Inner edge = 0.15 - 0.2 = -0.05.
    # This creates a 0.1um overlap with the mirrored arm.
    y_arm_end_offset = 0.15

    # --- 1. Central Taper ---
    # Linear taper extending deep into the device
    taper = c << gf.components.taper(
        length=taper_length,
        width1=width_center_in,
        width2=width_center_tip,
        layer=layer
    )
    # Taper placed at (0,0) by default
    
    # --- 2. Outer Arms (S-Bends) ---
    xs_arm = gf.cross_section.cross_section(width=width_arm, layer=layer)
    
    # Top Arm S-bend
    dy_top = y_arm_end_offset - y_arm_start_offset # e.g. 0.15 - 0.65 = -0.5
    top_arm = c << gf.components.bend_s(
        size=(total_length, dy_top),
        cross_section=xs_arm
    )
    top_arm.move((0, y_arm_start_offset))
    
    # Bottom Arm S-bend (mirrored)
    dy_bot = -y_arm_end_offset - (-y_arm_start_offset) # e.g. -0.15 - (-0.65) = 0.5
    bot_arm = c << gf.components.bend_s(
        size=(total_length, dy_bot),
        cross_section=xs_arm
    )
    bot_arm.move((0, -y_arm_start_offset))
    
    # --- 3. Ports ---
    c.add_port("o1", port=taper.ports["o1"])
    
    # Synthetic output port at the right edge
    # Effective width is roughly the sum of arms minus overlap
    output_width = (width_arm * 2) - 0.1 
    c.add_port(
        "o2", 
        center=(total_length, 0), 
        width=output_width, 
        orientation=0, 
        layer=layer
    )

    return c

if __name__ == "__main__":
    device = inverse_taper_coupler()
    device.write_gds("inverse_taper_coupler.gds")
    device.show()