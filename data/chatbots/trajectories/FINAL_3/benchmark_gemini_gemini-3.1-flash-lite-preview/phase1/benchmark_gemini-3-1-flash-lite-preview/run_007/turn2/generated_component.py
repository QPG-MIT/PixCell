import gdsfactory as gf

@gf.cell
def mach_zehnder_interferometer():
    """
    Creates an MZI-like structure by composing S-bends and straight waveguides.
    """
    c = gf.Component()
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters for the split
    split_length = 20
    vertical_offset = 3  # The arms will be offset by 3um (6um total separation)
    arm_length = 40
    
    # 1. Input waveguide
    input_wg = c << gf.components.straight(length=10, cross_section=xs)
    
    # 2. Splitter (Two S-bends)
    # Top goes up, bottom goes down
    top_split = c << gf.components.bend_s(size=(split_length, vertical_offset), cross_section=xs)
    bot_split = c << gf.components.bend_s(size=(split_length, -vertical_offset), cross_section=xs)
    
    top_split.connect("o1", input_wg.ports["o2"])
    bot_split.connect("o1", input_wg.ports["o2"])
    
    # 3. Arm sections
    top_arm = c << gf.components.straight(length=arm_length, cross_section=xs)
    bot_arm = c << gf.components.straight(length=arm_length, cross_section=xs)
    
    top_arm.connect("o1", top_split.ports["o2"])
    bot_arm.connect("o1", bot_split.ports["o2"])
    
    # 4. Combiner (Two S-bends to rejoin)
    # Top comes back down, bottom comes back up
    top_combine = c << gf.components.bend_s(size=(split_length, -vertical_offset), cross_section=xs)
    bot_combine = c << gf.components.bend_s(size=(split_length, vertical_offset), cross_section=xs)
    
    top_combine.connect("o1", top_arm.ports["o2"])
    bot_combine.connect("o1", bot_arm.ports["o2"])
    
    # 5. Output waveguide
    # Since the S-bends are perfectly symmetric, top_combine and bot_combine 
    # output ports will align at the center (y=0).
    # We can connect the output to either port.
    output_wg = c << gf.components.straight(length=10, cross_section=xs)
    output_wg.connect("o1", top_combine.ports["o2"])
    
    return c

# Generate and save
if __name__ == "__main__":
    device = mach_zehnder_interferometer()
    device.write_gds("mzi_device.gds")
    device.show()