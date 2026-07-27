import gdsfactory as gf

@gf.cell
def directional_coupler():
    """
    2x2 Directional coupler with S-bend transitions.
    Fits in 120 x 4 μm footprint.
    """
    c = gf.Component()
    
    # Cross-section definition
    waveguide_width = 0.5
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=layer)
    
    # Geometry parameters for 120 x 4 μm footprint
    port_separation = 3.0  # vertical center-to-center at I/O ports
    coupling_gap = 0.2     # small gap in coupling region
    coupling_center_spacing = coupling_gap + waveguide_width  # 0.7 μm
    
    # Length allocations (total = 120 μm)
    straight_io = 5.0      # short I/O straight sections
    sbend_dx = 30.0        # horizontal span of S-bends
    coupling_length = 50.0 # parallel coupling region
    
    # S-bend vertical offset (how much each waveguide moves vertically)
    sbend_dy = (port_separation - coupling_center_spacing) / 2  # ~1.15 μm
    
    # Port y-positions
    y_top = port_separation / 2   # +1.5 μm
    y_bot = -port_separation / 2  # -1.5 μm
    
    # === TOP WAVEGUIDE ===
    # Input straight
    in_str_top = c << gf.components.straight(length=straight_io, cross_section=xs)
    in_str_top.move((0, y_top))
    
    # Input S-bend (goes DOWN toward coupling region)
    sb_top_in = c << gf.components.bend_s(size=(sbend_dx, -sbend_dy), cross_section=xs)
    sb_top_in.connect("o1", in_str_top.ports["o2"])
    
    # Coupling straight section
    coup_top = c << gf.components.straight(length=coupling_length, cross_section=xs)
    coup_top.connect("o1", sb_top_in.ports["o2"])
    
    # Output S-bend (goes UP away from coupling region)
    sb_top_out = c << gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    sb_top_out.connect("o1", coup_top.ports["o2"])
    
    # Output straight
    out_str_top = c << gf.components.straight(length=straight_io, cross_section=xs)
    out_str_top.connect("o1", sb_top_out.ports["o2"])
    
    # === BOTTOM WAVEGUIDE ===
    # Input straight
    in_str_bot = c << gf.components.straight(length=straight_io, cross_section=xs)
    in_str_bot.move((0, y_bot))
    
    # Input S-bend (goes UP toward coupling region)
    sb_bot_in = c << gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    sb_bot_in.connect("o1", in_str_bot.ports["o2"])
    
    # Coupling straight section
    coup_bot = c << gf.components.straight(length=coupling_length, cross_section=xs)
    coup_bot.connect("o1", sb_bot_in.ports["o2"])
    
    # Output S-bend (goes DOWN away from coupling region)
    sb_bot_out = c << gf.components.bend_s(size=(sbend_dx, -sbend_dy), cross_section=xs)
    sb_bot_out.connect("o1", coup_bot.ports["o2"])
    
    # Output straight
    out_str_bot = c << gf.components.straight(length=straight_io, cross_section=xs)
    out_str_bot.connect("o1", sb_bot_out.ports["o2"])
    
    # Expose external ports
    c.add_port("o1", port=in_str_top.ports["o1"])
    c.add_port("o2", port=in_str_bot.ports["o1"])
    c.add_port("o3", port=out_str_top.ports["o2"])
    c.add_port("o4", port=out_str_bot.ports["o2"])
    
    return c

# Create and save
device = directional_coupler()
device.write_gds("directional_coupler.gds")