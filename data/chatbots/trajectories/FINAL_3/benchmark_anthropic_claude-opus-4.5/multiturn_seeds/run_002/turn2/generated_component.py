import gdsfactory as gf

@gf.cell
def directional_coupler_2x2():
    """
    2x2 Directional coupler with S-bend transitions.
    Two waveguides approach for evanescent coupling, then separate.
    Footprint: 120 um x 4 um
    """
    c = gf.Component()
    
    # Design parameters - adjusted for better match
    waveguide_width = 0.5        # um
    coupling_gap = 0.2           # um - gap between waveguides in coupling region
    sbend_length = 15.0          # um - shorter S-bends
    coupling_length = 90.0       # um - longer coupling section
    port_separation = 3.5        # um - vertical center-to-center at ports
    # Total length: 15 + 90 + 15 = 120 um
    
    # Cross-section definition
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    
    # Calculate vertical displacement for S-bends
    # In coupling region, waveguides are closer together
    coupling_center_spacing = coupling_gap + waveguide_width  # 0.7 um
    vertical_offset = (port_separation - coupling_center_spacing) / 2  # 1.4 um
    
    # === TOP WAVEGUIDE ARM ===
    # Input S-bend: curves downward toward coupling region
    top_sbend_in = c << gf.components.bend_s(
        size=(sbend_length, -vertical_offset), 
        cross_section=xs
    )
    top_sbend_in.move((0, port_separation / 2))
    
    # Straight coupling section
    top_coupling = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs
    )
    top_coupling.connect("o1", top_sbend_in.ports["o2"])
    
    # Output S-bend: curves back upward
    top_sbend_out = c << gf.components.bend_s(
        size=(sbend_length, vertical_offset), 
        cross_section=xs
    )
    top_sbend_out.connect("o1", top_coupling.ports["o2"])
    
    # === BOTTOM WAVEGUIDE ARM ===
    # Input S-bend: curves upward toward coupling region
    bot_sbend_in = c << gf.components.bend_s(
        size=(sbend_length, vertical_offset), 
        cross_section=xs
    )
    bot_sbend_in.move((0, -port_separation / 2))
    
    # Straight coupling section
    bot_coupling = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs
    )
    bot_coupling.connect("o1", bot_sbend_in.ports["o2"])
    
    # Output S-bend: curves back downward
    bot_sbend_out = c << gf.components.bend_s(
        size=(sbend_length, -vertical_offset), 
        cross_section=xs
    )
    bot_sbend_out.connect("o1", bot_coupling.ports["o2"])
    
    # === EXTERNAL PORTS ===
    c.add_port("o1", port=top_sbend_in.ports["o1"])
    c.add_port("o2", port=bot_sbend_in.ports["o1"])
    c.add_port("o3", port=top_sbend_out.ports["o2"])
    c.add_port("o4", port=bot_sbend_out.ports["o2"])
    
    return c


# Generate and save the device
device = directional_coupler_2x2()
device.write_gds("directional_coupler_2x2.gds")