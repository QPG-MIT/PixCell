import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    gap = 0.2
    interaction_length = 4.0
    sep_ends = 2.5
    sep_middle = gap + 0.5
    dy_offset = (sep_ends - sep_middle) / 2
    dx_half = (18 - interaction_length) / 2

    # Middle coupler
    coupler = gf.components.coupler_straight(
        length=interaction_length, gap=gap, cross_section=xs
    )
    coup_ref = c << coupler

    # Bottom left bend
    bl = gf.components.bend_s(size=(dx_half, dy_offset), cross_section=xs)
    bl_ref = c << bl
    bl_ref.connect("o2", coup_ref.ports["o1"])

    # Top left bend
    tl = gf.components.bend_s(size=(dx_half, -dy_offset), cross_section=xs)
    tl_ref = c << tl
    tl_ref.connect("o2", coup_ref.ports["o2"])

    # Bottom right bend
    br = gf.components.bend_s(size=(dx_half, -dy_offset), cross_section=xs)
    br_ref = c << br
    br_ref.connect("o1", coup_ref.ports["o3"])

    # Top right bend
    tr = gf.components.bend_s(size=(dx_half, dy_offset), cross_section=xs)
    tr_ref = c << tr
    tr_ref.connect("o1", coup_ref.ports["o4"])

    # Expose ports
    c.add_port("o1", port=bl_ref.ports["o1"])
    c.add_port("o2", port=tl_ref.ports["o1"])
    c.add_port("o3", port=br_ref.ports["o2"])
    c.add_port("o4", port=tr_ref.ports["o2"])

    # Shift to start at y=0
    c.move((0, -c.ymin))

    return c

dev = device()
dev.write_gds("device.gds")