import gdsfactory as gf

@gf.cell
def coupled_waveguides():
    c = gf.Component()
    
    # 1. Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Construct the S-curve
    # The coupler is formed by two S-bends meeting in the middle.
    # Total length is 18um, so each half is 9um.
    # We create one S-bend component: size=(9, 1.25)
    # This transitions the waveguide from the input height to the center waist.
    bend_part = gf.components.bend_s(size=(9, 1.25), cross_section=xs)

    # 3. Assemble the Top Waveguide
    # First half: Bend down
    top_left = c << bend_part
    # Second half: Bend up (achieved by mirroring)
    top_right = c << bend_part
    top_right.mirror()
    
    # Connect the two halves
    top_right.connect("o1", top_left.ports["o2"])

    # 4. Assemble the Bottom Waveguide (Mirrored vertically)
    # We simply mirror the top waveguide assembly
    bot_wg = c << c.copy()
    bot_wg.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X axis
    
    # Shift slightly to ensure proper positioning relative to the top
    # The bend_s creates the curve; the assembly creates the full shape.
    
    return c

# Generate the device
device = coupled_waveguides()
device.write_gds("coupled_waveguides.gds")