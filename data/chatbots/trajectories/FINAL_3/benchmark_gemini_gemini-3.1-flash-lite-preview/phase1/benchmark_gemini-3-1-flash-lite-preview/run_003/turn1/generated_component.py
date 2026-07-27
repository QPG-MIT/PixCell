import gdsfactory as gf

@gf.cell
def symmetric_coupler():
    c = gf.Component()
    
    # Define standard cross-section
    xs = gf.cross_section.strip()

    # Define building blocks
    # Lengths chosen to total 120um: 20 (in) + 20 (bend) + 40 (mid) + 20 (bend) + 20 (out)
    wg_in_out = gf.components.straight(length=20, cross_section=xs)
    wg_mid = gf.components.straight(length=40, cross_section=xs)
    
    # S-bends with size=(20, 1) and (20, -1) to create the vertical shift
    bend_down = gf.components.bend_s(size=(20, -1), cross_section=xs)
    bend_up = gf.components.bend_s(size=(20, 1), cross_section=xs)

    # --- Top Waveguide Assembly ---
    # Path: straight -> bend_down -> straight -> bend_up -> straight
    t1 = c << wg_in_out
    t2 = c << bend_down
    t3 = c << wg_mid
    t4 = c << bend_up
    t5 = c << wg_in_out

    # Set initial position for top waveguide
    t1.movey(1) 

    # Connect ports sequentially
    t2.connect("o1", t1.ports["o2"])
    t3.connect("o1", t2.ports["o2"])
    t4.connect("o1", t3.ports["o2"])
    t5.connect("o1", t4.ports["o2"])

    # --- Bottom Waveguide Assembly ---
    # Path: straight -> bend_up -> straight -> bend_down -> straight
    b1 = c << wg_in_out
    b2 = c << bend_up
    b3 = c << wg_mid
    b4 = c << bend_down
    b5 = c << wg_in_out

    # Set initial position for bottom waveguide
    b1.movey(-1)

    # Connect ports sequentially
    b2.connect("o1", b1.ports["o2"])
    b3.connect("o1", b2.ports["o2"])
    b4.connect("o1", b3.ports["o2"])
    b5.connect("o1", b4.ports["o2"])

    return c

# Generate and save the device
if __name__ == "__main__":
    device = symmetric_coupler()
    # Save the GDS file
    device.write_gds("symmetric_coupler.gds")
    print("GDS file 'symmetric_coupler.gds' successfully created.")