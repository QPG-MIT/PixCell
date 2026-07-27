import gdsfactory as gf

@gf.cell
def custom_waveguide_coupler():
    c = gf.Component()
    
    # 1. Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define the S-bend parameters
    # Total length is 18um. We split it into two 9um halves for each waveguide.
    # The waveguide moves 0.5um vertically to narrow the gap in the middle.
    half_length = 9
    vertical_offset = 0.5 

    # 3. Create the top waveguide path
    # First half goes down: (9, -0.5), Second half goes up: (9, 0.5)
    top_s1 = c << gf.components.bend_s(size=(half_length, -vertical_offset), cross_section=xs)
    top_s2 = c << gf.components.bend_s(size=(half_length, vertical_offset), cross_section=xs)
    
    # Connect the two halves
    top_s2.connect("o1", top_s1.ports["o2"])

    # 4. Create the bottom waveguide path
    # First half goes up: (9, 0.5), Second half goes down: (9, -0.5)
    # We use a mirror or just flip the offsets to create the symmetric bottom shape
    bot_s1 = c << gf.components.bend_s(size=(half_length, vertical_offset), cross_section=xs)
    bot_s2 = c << gf.components.bend_s(size=(half_length, -vertical_offset), cross_section=xs)
    
    # Connect the bottom halves
    bot_s2.connect("o1", bot_s1.ports["o2"])
    
    # Position the bottom waveguide relative to the top waveguide
    # Align the starting port of the bottom waveguide to be 2um below the top
    bot_s1.movey(-2.0)

    # 5. Expose ports
    c.add_port("o1_top", port=top_s1.ports["o1"])
    c.add_port("o2_top", port=top_s2.ports["o2"])
    c.add_port("o1_bot", port=bot_s1.ports["o1"])
    c.add_port("o2_bot", port=bot_s2.ports["o2"])

    return c

# Generate the component
device = custom_waveguide_coupler()

# Display or save the device
device.show()
device.write_gds("waveguide_coupler.gds")