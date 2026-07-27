import gdsfactory as gf

@gf.cell
def striped_coupler():
    """
    Recreation of the directional coupler device using GDSFactory parametric functions.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # --- Parameters ---
    total_length = 120.0
    
    # Geometry splits
    # The device consists of an input S-bend, a straight coupling region, and an output S-bend
    straight_length = 40.0
    bend_length = (total_length - straight_length) / 2  # 40.0
    
    # Y-axis positioning
    # The device fits in 4um total height. 
    # We define nominal paths for the top and bottom arms.
    y_input_top = 1.4
    y_center_top = 0.3
    dy_top = y_center_top - y_input_top  # Negative value (path goes down)
    
    y_input_bot = -1.4
    y_center_bot = -0.3
    dy_bot = y_center_bot - y_input_bot  # Positive value (path goes up)

    # Stripe parameters (to create the multi-line bundle shown in the image)
    line_width = 0.08
    line_spacing = 0.18 # Center-to-center pitch
    num_stripes = 5
    
    # Cross section for individual stripes
    xs = gf.cross_section.cross_section(width=line_width, layer=(1, 0))

    # --- 1. Define the Single Strand Template (Top Arm) ---
    # This component represents just ONE of the 5 parallel lines for the top arm
    strand_top = gf.Component("strand_top")
    
    # Left S-Bend (Input -> Center)
    # size = (length, height_change)
    b1_top = strand_top << gf.components.bend_s(
        size=(bend_length, dy_top), 
        cross_section=xs
    )
    
    # Center Straight
    st_top = strand_top << gf.components.straight(
        length=straight_length, 
        cross_section=xs
    )
    
    # Right S-Bend (Center -> Output)
    # The height change is opposite to return to the original y-level
    b2_top = strand_top << gf.components.bend_s(
        size=(bend_length, -dy_top), 
        cross_section=xs
    )
    
    # Connect internal components
    st_top.connect("o1", b1_top.ports["o2"])
    b2_top.connect("o1", st_top.ports["o2"])
    
    # Expose ports
    strand_top.add_port("o1", port=b1_top.ports["o1"])
    strand_top.add_port("o2", port=b2_top.ports["o2"])

    # --- 2. Define the Single Strand Template (Bottom Arm) ---
    strand_bot = gf.Component("strand_bot")
    
    # Left S-Bend (Input -> Center)
    b1_bot = strand_bot << gf.components.bend_s(
        size=(bend_length, dy_bot), 
        cross_section=xs
    )
    
    # Center Straight
    st_bot = strand_bot << gf.components.straight(
        length=straight_length, 
        cross_section=xs
    )
    
    # Right S-Bend (Center -> Output)
    b2_bot = strand_bot << gf.components.bend_s(
        size=(bend_length, -dy_bot), 
        cross_section=xs
    )
    
    # Connect
    st_bot.connect("o1", b1_bot.ports["o2"])
    b2_bot.connect("o1", st_bot.ports["o2"])
    
    strand_bot.add_port("o1", port=b1_bot.ports["o1"])
    strand_bot.add_port("o2", port=b2_bot.ports["o2"])

    # --- 3. Create Arrays Manually ---
    # Replaces 'add_array' with a loop for compatibility with KFactory backend
    
    # Calculate offset to center the bundle of stripes around the nominal path
    array_height = (num_stripes - 1) * line_spacing
    centering_offset = -array_height / 2

    # Generate Top Bundle
    for i in range(num_stripes):
        # Create a reference to the strand template
        ref = c << strand_top
        # Calculate vertical shift for this specific line
        y_shift = i * line_spacing + centering_offset
        # Move: Start X at -L/2, Start Y at input_y + shift
        ref.move(( -total_length/2, y_input_top + y_shift ))

    # Generate Bottom Bundle
    for i in range(num_stripes):
        ref = c << strand_bot
        y_shift = i * line_spacing + centering_offset
        ref.move(( -total_length/2, y_input_bot + y_shift ))

    return c

# Generate and save
if __name__ == "__main__":
    device = striped_coupler()
    device.show() 
    device.write_gds("striped_coupler.gds")
    
    # Verification
    print(f"Device created: {device.name}")
    print(f"Footprint bounds: {device.bbox}")