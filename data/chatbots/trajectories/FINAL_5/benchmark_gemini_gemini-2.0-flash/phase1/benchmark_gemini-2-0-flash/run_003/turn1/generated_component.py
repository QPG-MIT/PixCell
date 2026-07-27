import gdsfactory as gf
from gdsfactory.components import rectangle


@gf.cell
def device():
    c = gf.Component()

    # Define parameters based on the image analysis
    wg_width = 0.3  # Estimate from the image
    wg_length = 6.8 # Estimate from footprint
    gap = 0.1  # Estimate from the image
    coupler_length = 5  # Estimate from the image
    bend_radius = 5.0  # Estimate from the image, must be greater than or equal to radius_min in cross_section
    taper_length = 1.5 # Estimate from image
    rib_wg_length = 3.0

    # Define cross section
    xs = gf.cross_section.strip(width=wg_width)
    xs_wide = gf.cross_section.strip(width=0.6)

    # Top part
    # 1. Upper straight waveguide
    top_wg = c << gf.components.straight(length=wg_length, cross_section=xs)
    top_wg.movex(- wg_length/2 + 0.1)
    top_wg.movey(0.5)
    c.add_port("o1", port=top_wg.ports["o1"])

    # 2. Taper
    taper1 = c << gf.components.taper(length=taper_length, width1=wg_width, width2=0.6)
    taper1.connect("o1", top_wg.ports["o2"])

    # 3. Bend
    bend1 = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs_wide)
    bend1.connect("o1", taper1.ports["o2"])

    # 4. Lower part of the top loop
    lower_top_wg = c << gf.components.straight(length=coupler_length, cross_section=xs_wide)
    lower_top_wg.connect("o1", bend1.ports["o2"])

    # Middle section

    # Middle straight section with period grates.

    rib_wg = c << gf.components.straight(length=rib_wg_length, cross_section=xs_wide)
    rib_wg.movey(-0.1)
    rib_wg.movex(-rib_wg_length/2)

    # Define grating parameters
    period = 0.04
    dc = 0.5  # duty cycle
    n_periods = 48

    # Add rectangle grating
    for i in range(n_periods):
        x = (i - n_periods / 2) * period + period / 2
        rect = c << rectangle(size=(period * dc, 0.1), layer=(1, 0), centered=True)
        rect.movex(x)
        rect.movey(-0.1) # Move it to match the center.


    # Bottom part (mirrored)

    # 1. Upper straight waveguide
    bot_wg = c << gf.components.straight(length=wg_length, cross_section=xs)
    bot_wg.movex(- wg_length/2 + 0.1)
    bot_wg.movey(-0.5)
    c.add_port("o2", port=bot_wg.ports["o1"])


    # 2. Taper
    taper2 = c << gf.components.taper(length=taper_length, width1=wg_width, width2=0.6)
    taper2.connect("o1", bot_wg.ports["o2"])

    # 3. Bend
    bend2 = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs_wide)
    bend2.connect("o2", taper2.ports["o2"])
    bend2.rotate(180) # Flip

    # 4. Lower part of the top loop
    lower_bot_wg = c << gf.components.straight(length=coupler_length, cross_section=xs_wide)
    lower_bot_wg.connect("o2", bend2.ports["o1"])
    lower_bot_wg.rotate(180) #Flip

    return c


if __name__ == "__main__":
    dev = device()
    dev.show(show_ports=True)
    dev.write_gds("device.gds")