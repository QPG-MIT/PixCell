import gdsfactory as gf

@gf.cell
def directional_coupler_240x4():
    """
    Creates a symmetric directional coupler fitting a 240um x 4um footprint.
    """
    c = gf.Component()
    
    # 1. Define Geometry Parameters
    # Total constraints
    total_length = 240.0
    total_height = 4.0
    
    # Waveguide specs
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Design Dimensions
    bend_length = 60.0
    straight_length = total_length - (2 * bend_length) # 120.0
    
    # Vertical positioning
    # We place inputs at y = +/- 1.5 to fit comfortably inside the 4um height limit
    # (1.5 + 0.5/2 = 1.75 outer edge, which is < 2.0 boundary)
    y_input = 1.5
    
    # Gap configuration
    gap = 0.2
    # The center y-position for the coupled waveguides
    y_coupled = (gap + wg_width) / 2  # 0.35
    
    # Calculate the vertical shift required for the S-bend (dy)
    dy = y_input - y_coupled # 1.15

    # 2. Create Primitives (Top Arm)
    # Input S-bend (bends down from input to coupler)
    top_sbend_in = c << gf.components.bend_s(
        size=(bend_length, -dy), 
        cross_section=xs
    )
    # Straight coupling section
    top_straight = c << gf.components.straight(
        length=straight_length, 
        cross_section=xs
    )
    # Output S-bend (bends up from coupler to output)
    top_sbend_out = c << gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=xs
    )

    # 3. Create Primitives (Bottom Arm)
    # Input S-bend (bends up from input to coupler)
    bot_sbend_in = c << gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=xs
    )
    # Straight coupling section
    bot_straight = c << gf.components.straight(
        length=straight_length, 
        cross_section=xs
    )
    # Output S-bend (bends down from coupler to output)
    bot_sbend_out = c << gf.components.bend_s(
        size=(bend_length, -dy), 
        cross_section=xs
    )

    # 4. Assembly and Placement
    
    # Position the starting points (Input Ports)
    # We move the input bends to their absolute starting positions
    top_sbend_in.move((0, y_input))
    bot_sbend_in.move((0, -y_input))

    # Connect the Top sequence
    # Connect straight section to end of input bend
    top_straight.connect("o1", top_sbend_in.ports["o2"])
    # Connect output bend to end of straight section
    top_sbend_out.connect("o1", top_straight.ports["o2"])

    # Connect the Bottom sequence
    bot_straight.connect("o1", bot_sbend_in.ports["o2"])
    bot_sbend_out.connect("o1", bot_straight.ports["o2"])

    # 5. Expose Ports
    c.add_port("o1", port=top_sbend_in.ports["o1"])   # Top Left
    c.add_port("o2", port=bot_sbend_in.ports["o1"])   # Bottom Left
    c.add_port("o3", port=top_sbend_out.ports["o2"])  # Top Right
    c.add_port("o4", port=bot_sbend_out.ports["o2"])  # Bottom Right

    return c

# Generate and save
device = directional_coupler_240x4()
device.write_gds("directional_coupler.gds")
device.show()