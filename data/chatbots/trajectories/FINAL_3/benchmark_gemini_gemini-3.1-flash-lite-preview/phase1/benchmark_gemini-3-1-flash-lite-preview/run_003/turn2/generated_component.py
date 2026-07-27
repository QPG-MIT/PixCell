import gdsfactory as gf

@gf.cell
def custom_coupler():
    c = gf.Component()
    
    # 1. Increase width to match the visual 'thickness' of the original image
    xs = gf.cross_section.cross_section(width=1.5, layer=(1, 0))

    # 2. Use longer S-bends (30um length) to create smooth, sweeping curves
    # We set dy=0.75 so the waveguides are very close (0.75 * 2 = 1.5 total vertical separation)
    # With width=1.5, this creates a tight coupling region.
    bend_down = gf.components.bend_s(size=(30, -0.75), cross_section=xs)
    bend_up = gf.components.bend_s(size=(30, 0.75), cross_section=xs)

    # 3. Define Straights to fill the remaining length of the 120um footprint
    # (30 + 30 = 60um used by bends). Remaining = 60um. 
    # Let's split this into: 15um outer, 30um center, 15um outer.
    wg_outer = gf.components.straight(length=15, cross_section=xs)
    wg_mid = gf.components.straight(length=30, cross_section=xs)

    # --- Top Waveguide Assembly ---
    t1 = c << wg_outer
    t2 = c << bend_down
    t3 = c << wg_mid
    t4 = c << bend_up
    t5 = c << wg_outer
    
    t1.movey(0.75) # Align top waveguide center
    
    t2.connect("o1", t1.ports["o2"])
    t3.connect("o1", t2.ports["o2"])
    t4.connect("o1", t3.ports["o2"])
    t5.connect("o1", t4.ports["o2"])

    # --- Bottom Waveguide Assembly ---
    b1 = c << wg_outer
    b2 = c << bend_up
    b3 = c << wg_mid
    b4 = c << bend_down
    b5 = c << wg_outer
    
    b1.movey(-0.75) # Align bottom waveguide center
    
    b2.connect("o1", b1.ports["o2"])
    b3.connect("o1", b2.ports["o2"])
    b4.connect("o1", b3.ports["o2"])
    b5.connect("o1", b4.ports["o2"])

    return c

# Generate and save
if __name__ == "__main__":
    device = custom_coupler()
    device.write_gds("coupler_improved.gds")
    print("GDS file 'coupler_improved.gds' created with optimized parameters.")