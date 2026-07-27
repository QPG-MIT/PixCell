import gdsfactory as gf

@gf.cell
def optical_splitter_1x4():
    """
    Recreates the vertical 1x4 optical splitter structure.
    Uses robust topological connection (.connect) to avoid version-specific
    translation/rotation issues, and relies entirely on raw primitives.
    """
    c = gf.Component("optical_splitter_1x4")
    layer = (1, 0)
    
    # 1. Main mixing region footprint
    mmi_width = 25.0
    mmi_height = 10.0

    # Draw the central rectangular body
    c << gf.components.rectangle(size=(mmi_width, mmi_height), layer=layer, centered=True)

    # 2. Bottom Input Arm
    bot_taper_len = 6.0
    bot_width1 = 5.0  # Wide base connecting to MMI
    bot_width2 = 2.0  # Narrow input width
    
    # Add an anchor port on the bottom edge (y = -5). Orientation 270 points DOWN.
    c.add_port(name="anchor_bot", center=(0, -mmi_height / 2), width=bot_width1, orientation=270, layer=layer)
    
    # Create the bottom taper
    bot_taper = c << gf.components.taper(
        length=bot_taper_len, 
        width1=bot_width1, 
        width2=bot_width2, 
        layer=layer
    )
    # Connecting to the anchor safely aligns and rotates it downwards
    bot_taper.connect("o1", c.ports["anchor_bot"])
    
    # Expose the final optical input port
    c.add_port("o1", port=bot_taper.ports["o2"])

    # 3. Top Output Arms
    num_arms = 4
    pitch = mmi_width / num_arms
    
    # Calculate x-coordinates so arms are perfectly distributed
    x_positions = [pitch * (i - (num_arms - 1) / 2) for i in range(num_arms)]
    
    top_taper_len = 9.0
    top_straight_len = 7.0
    top_width1 = 4.0  # Base width connecting to MMI
    top_width2 = 1.0  # Narrow waveguide width

    for i, x in enumerate(x_positions):
        anchor_name = f"anchor_top_{i}"
        
        # Add an anchor port on the top edge (y = 5). Orientation 90 points UP.
        c.add_port(name=anchor_name, center=(x, mmi_height / 2), width=top_width1, orientation=90, layer=layer)
        
        # A. Taper section
        top_taper = c << gf.components.taper(
            length=top_taper_len, 
            width1=top_width1, 
            width2=top_width2, 
            layer=layer
        )
        top_taper.connect("o1", c.ports[anchor_name])

        # B. Straight section 
        # By using a taper with width1 == width2, we guarantee a pure polygon generation 
        # on the correct layer, sidestepping any cross_section API failures.
        top_straight = c << gf.components.taper(
            length=top_straight_len, 
            width1=top_width2, 
            width2=top_width2, 
            layer=layer
        )
        top_straight.connect("o1", top_taper.ports["o2"])
        
        # Expose the final optical output port
        c.add_port(f"o{i+2}", port=top_straight.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate the component
    device = optical_splitter_1x4()
    
    # Write directly to GDS file
    device.write_gds("device.gds")