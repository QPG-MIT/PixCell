import gdsfactory as gf

@gf.cell
def waveguide_y_splitter():
    """
    Y-splitter waveguide device.
    Two parallel waveguides that diverge via S-bends.
    Footprint: 40.0 x 1.7 um
    """
    c = gf.Component()
    
    # Cross-section parameters
    wg_width = 0.5
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Geometry parameters - adjusted for better match
    straight_length = 22.0  # Longer parallel coupling section
    sbend_dx = 18.0  # S-bend horizontal extent
    sbend_dy = 0.45  # Larger vertical offset per arm for more divergence
    input_gap = 0.2  # Gap between waveguides at input
    
    # Calculate y-offset for waveguide centers
    y_offset = (input_gap + wg_width) / 2  # = 0.35
    
    # === TOP WAVEGUIDE ARM ===
    # Straight section
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_straight.move((0, y_offset))
    
    # S-bend curving upward
    top_sbend = c << gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    top_sbend.connect("o1", top_straight.ports["o2"])
    
    # === BOTTOM WAVEGUIDE ARM ===
    # Straight section
    bot_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    bot_straight.move((0, -y_offset))
    
    # S-bend curving downward
    bot_sbend = c << gf.components.bend_s(size=(sbend_dx, -sbend_dy), cross_section=xs)
    bot_sbend.connect("o1", bot_straight.ports["o2"])
    
    # Add external ports
    c.add_port("o1", port=top_straight.ports["o1"])
    c.add_port("o2", port=bot_straight.ports["o1"])
    c.add_port("o3", port=top_sbend.ports["o2"])
    c.add_port("o4", port=bot_sbend.ports["o2"])
    
    return c

# Create and save the device
device = waveguide_y_splitter()
device.write_gds("waveguide_y_splitter.gds")