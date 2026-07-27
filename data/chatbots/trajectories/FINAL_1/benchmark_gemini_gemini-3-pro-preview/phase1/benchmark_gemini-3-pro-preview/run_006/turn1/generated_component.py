import gdsfactory as gf

@gf.cell
def inverse_taper_coupler():
    """
    Creates an inverse taper edge coupler based on visual analysis.
    
    Structure:
    1. Central taper: High confinement core tapering to a tip.
    2. Outer arms: Waveguides that S-bend inwards to capture the mode 
       from the central taper and merge at the output.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Derived from footprint constraint [40.0, 1.7]
    total_length = 40.0
    
    # Layer definition
    layer = (1, 0)
    
    # Geometry Dimensions
    width_center_in = 0.5    # Input width of central waveguide
    width_center_tip = 0.05  # Tip width of central waveguide
    width_arm = 0.4          # Width of the outer arms
    taper_length = 22.0      # Length of the central taper (shorter than total length)
    
    # Y-Position Calculations
    # To satisfy the 1.7um height constraint with 0.4um wide arms:
    # Top edge approx y=0.85, Bottom edge approx y=-0.85
    # Center of top arm = 0.85 - (0.4/2) = 0.65
    y_arm_start_offset = 0.65
    
    # Output convergence
    # The arms merge at the output. To form a solid waveguide, they must overlap.
    # Targeted center position: +/- 0.15 gives overlap
    # (Center 0.15 - Width/2 0.2 = -0.05 inner edge, ensuring merge)
    y_arm_end_offset = 0.15

    # --- 1. Central Taper ---
    # Creates the central inverse taper structure
    taper = c << gf.components.taper(
        length=taper_length,
        width1=width_center_in,
        width2=width_center_tip,
        layer=layer
    )
    # Taper is placed at (0,0) by default
    
    # --- 2. Outer Arms (S-Bends) ---
    # Define the cross-section for the outer arms
    xs_arm = gf.cross_section.cross_section(width=width_arm, layer=layer)
    
    # Top Arm
    # S-bend transition from y_start to y_end
    # The bend_s component draws from (0,0) to (length, dy)
    dy_top = y_arm_end_offset - y_arm_start_offset # e.g. 0.15 - 0.65 = -0.5
    
    top_arm = c << gf.components.bend_s(
        size=(total_length, dy_top),
        cross_section=xs_arm
    )
    # Move the arm to its starting vertical position
    top_arm.move((0, y_arm_start_offset))
    
    # Bottom Arm
    # S-bend transition mirroring the top
    dy_bot = -y_arm_end_offset - (-y_arm_start_offset) # e.g. -0.15 - (-0.65) = 0.5
    
    bot_arm = c << gf.components.bend_s(
        size=(total_length, dy_bot),
        cross_section=xs_arm
    )
    bot_arm.move((0, -y_arm_start_offset))
    
    # --- 3. Ports ---
    # Expose the input port from the central taper
    c.add_port("o1", port=taper.ports["o1"])
    
    # Create a synthetic output port at the right edge where arms merge
    # The effective output width is roughly (width_arm * 2) - overlap
    c.add_port(
        "o2", 
        center=(total_length, 0), 
        width=width_arm*2, 
        orientation=0, 
        layer=layer
    )

    return c

if __name__ == "__main__":
    # Create the device
    device = inverse_taper_coupler()
    
    # Save to GDS
    device.write_gds("inverse_taper_coupler.gds")
    
    # Display the component
    device.show()