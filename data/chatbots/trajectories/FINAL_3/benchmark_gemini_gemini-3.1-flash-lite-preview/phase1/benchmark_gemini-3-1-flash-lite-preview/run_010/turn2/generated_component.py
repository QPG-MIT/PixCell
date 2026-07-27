import gdsfactory as gf

@gf.cell
def coupler():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Parameters
    # We want a total length of 120um
    # Middle straight section = 40um
    # Each S-bend section = 40um
    # Total = 40 + 40 + 40 = 120um
    
    # Define building blocks
    # bend_s creates the S-bend transition. 
    # Size (40, 1.75) means it travels 40um in X and 1.75um in Y
    bend_left = gf.components.bend_s(size=(40, 1.75), cross_section=xs)
    center_wg = gf.components.straight(length=40, cross_section=xs)
    bend_right = gf.components.bend_s(size=(40, 1.75), cross_section=xs)

    # 1. Build Top Waveguide
    # Connect: left bend -> center straight -> right bend
    top_left = c << bend_left
    top_center = c << center_wg
    top_right = c << bend_right

    top_center.connect("o1", top_left.ports["o2"])
    top_right.connect("o1", top_center.ports["o2"])

    # 2. Build Bottom Waveguide
    # We use the same components, but rotate/mirror them to create the bottom arm
    bot_left = c << bend_left
    bot_center = c << center_wg
    bot_right = c << bend_right

    # Reflect the bottom arms to mirror the top arm structure
    bot_left.mirror()
    bot_center.mirror()
    bot_right.mirror()

    # Move them down to form the parallel section at y=0
    # (The S-bend transition is 1.75um, so we shift down by ~3.5um total offset)
    bot_left.movey(-3.5)
    bot_center.movey(-3.5)
    bot_right.movey(-3.5)

    # Connect the bottom arm (ensure they line up with the center)
    bot_center.connect("o1", bot_left.ports["o2"])
    bot_right.connect("o1", bot_center.ports["o2"])

    return c

if __name__ == "__main__":
    device = coupler()
    device.write_gds("coupler.gds")
    device.show()