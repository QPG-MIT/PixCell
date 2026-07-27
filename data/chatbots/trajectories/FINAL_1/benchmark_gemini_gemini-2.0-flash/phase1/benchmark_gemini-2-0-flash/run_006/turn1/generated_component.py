import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=10)
    xs_wide = gf.cross_section.cross_section(width=1.0, layer=(1, 0), radius=10)  # Cross section for wider waveguides

    # Define parameters
    length_straight = 10
    length_taper = 5
    width_narrow = 0.5
    width_wide = 1.0
    gap_coupler = 0.2
    bend_radius = 10

    # 1. Input waveguides
    straight1 = c << gf.components.straight(length=length_straight, cross_section=xs)
    straight2 = c << gf.components.straight(length=length_straight, cross_section=xs)
    straight3 = c << gf.components.straight(length=length_straight, cross_section=xs)

    # Position input waveguides
    straight2.movey(-width_narrow - gap_coupler/2)
    straight3.movey(-2*width_narrow - gap_coupler)
    
    # 2. Tapers to widen waveguides
    taper1 = c << gf.components.taper(length=length_taper, width1=width_narrow, width2=width_wide)
    taper2 = c << gf.components.taper(length=length_taper, width1=width_narrow, width2=width_wide)
    taper3 = c << gf.components.taper(length=length_taper, width1=width_narrow, width2=width_wide)

    taper1.connect("o1", straight1.ports["o2"])
    taper2.connect("o1", straight2.ports["o2"])
    taper3.connect("o1", straight3.ports["o2"])

    # 3. Bends to split signal
    bend1 = c << gf.components.bend_euler(radius=bend_radius, angle=45, cross_section=xs_wide)
    bend2 = c << gf.components.bend_euler(radius=bend_radius, angle=-45, cross_section=xs_wide)
    bend3 = c << gf.components.bend_euler(radius=bend_radius, angle=45, cross_section=xs_wide)
    bend4 = c << gf.components.bend_euler(radius=bend_radius, angle=-45, cross_section=xs_wide)

    bend1.connect("o1", taper1.ports["o2"])
    bend2.connect("o1", taper1.ports["o2"])
    bend3.connect("o1", taper3.ports["o2"])
    bend4.connect("o1", taper3.ports["o2"])

    # Move second bend down
    bend2.movey(width_narrow + gap_coupler/2)
    bend4.movey(-width_narrow - gap_coupler/2)
    
    # 4. Output waveguides
    straight_output1 = c << gf.components.straight(length=length_straight, cross_section=xs_wide)
    straight_output2 = c << gf.components.straight(length=length_straight, cross_section=xs_wide)

    straight_output1.connect("o1", bend1.ports["o2"])
    straight_output2.connect("o1", bend3.ports["o2"])

    # Add Ports
    c.add_port("o1", port=straight1.ports["o1"])
    c.add_port("o2", port=straight2.ports["o1"])
    c.add_port("o3", port=straight3.ports["o1"])
    c.add_port("o4", port=straight_output1.ports["o2"])
    c.add_port("o5", port=straight_output2.ports["o2"])

    return c

device = my_device()
device.show(show_ports=True)