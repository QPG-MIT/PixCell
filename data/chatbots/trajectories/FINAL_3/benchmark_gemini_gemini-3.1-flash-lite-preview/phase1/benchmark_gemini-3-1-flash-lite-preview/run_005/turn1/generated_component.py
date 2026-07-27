import gdsfactory as gf

@gf.cell
def custom_coupler():
    c = gf.Component()
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Geometry parameters to match the 120um x 4um footprint
    total_len = 120
    transition_len = 30
    coupling_len = total_len - (2 * transition_len)
    
    # Define vertical offset for the S-bends (shifting waveguides inward/outward)
    # Total height of 4um implies the outer waveguides are at roughly y=1.5 and y=-1.5
    # Let's shift by 1.0um to create the coupling gap
    y_offset = 1.0 

    # --- Build Top Arm ---
    # 1. Start straight section
    straight_in = c << gf.components.straight(length=transition_len, cross_section=xs)
    
    # 2. S-bend down
    bend_down = c << gf.components.bend_s(size=(transition_len, -y_offset), cross_section=xs)
    bend_down.connect("o1", straight_in.ports["o2"])
    
    # 3. Middle straight section
    straight_mid = c << gf.components.straight(length=coupling_len, cross_section=xs)
    straight_mid.connect("o1", bend_down.ports["o2"])
    
    # 4. S-bend up (to return to original height)
    bend_up = c << gf.components.bend_s(size=(transition_len, y_offset), cross_section=xs)
    bend_up.connect("o1", straight_mid.ports["o2"])
    
    # 5. End straight section
    straight_out = c << gf.components.straight(length=transition_len, cross_section=xs)
    straight_out.connect("o1", bend_up.ports["o2"])

    # --- Build Bottom Arm ---
    # Mirror the top arm geometry structure, but invert the y-offsets
    # 1. Straight input
    bottom_in = c << gf.components.straight(length=transition_len, cross_section=xs)
    bottom_in.movey(-y_offset * 2) # Position the start lower
    
    # 2. S-bend up (to meet the coupling section)
    bottom_bend_up = c << gf.components.bend_s(size=(transition_len, y_offset), cross_section=xs)
    bottom_bend_up.connect("o1", bottom_in.ports["o2"])
    
    # 3. Middle straight section
    bottom_mid = c << gf.components.straight(length=coupling_len, cross_section=xs)
    bottom_mid.connect("o1", bottom_bend_up.ports["o2"])
    
    # 4. S-bend down (to return to original height)
    bottom_bend_down = c << gf.components.bend_s(size=(transition_len, -y_offset), cross_section=xs)
    bottom_bend_down.connect("o1", bottom_mid.ports["o2"])
    
    # 5. End straight section
    bottom_out = c << gf.components.straight(length=transition_len, cross_section=xs)
    bottom_out.connect("o1", bottom_bend_down.ports["o2"])
    
    return c

# Generate and visualize/save
device = custom_coupler()
device.write_gds("coupler.gds")