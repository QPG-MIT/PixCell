import gdsfactory as gf

@gf.cell
def directional_coupler_half(
    length_tail: float = 30.0,
    length_sbend: float = 10.0,
    length_coupler: float = 40.0,
    dy: float = 1.5,
    width: float = 0.4,
):
    """
    Creates one half of a symmetric directional coupler.
    The 'low' part is the coupling section.
    """
    c = gf.Component()
    xs = gf.cross_section.strip(width=width, layer=(1, 0))

    # Create components
    t1 = c << gf.components.straight(length=length_tail, cross_section=xs)
    # S-bend drops from outer tail down to inner coupler
    s1 = c << gf.components.bend_s(size=(length_sbend, -dy), cross_section=xs)
    mid = c << gf.components.straight(length=length_coupler, cross_section=xs)
    # S-bend rises from inner coupler back to outer tail
    s2 = c << gf.components.bend_s(size=(length_sbend, dy), cross_section=xs)
    t2 = c << gf.components.straight(length=length_tail, cross_section=xs)

    # Sequence connections
    s1.connect("o1", t1.ports["o2"])
    mid.connect("o1", s1.ports["o2"])
    s2.connect("o1", mid.ports["o2"])
    t2.connect("o1", s2.ports["o2"])

    # Expose ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=t2.ports["o2"])
    
    # We return the component with the mid section at y=-dy 
    # (since we start at 0 and drop by dy)
    return c

@gf.cell
def symmetric_directional_coupler():
    """
    Refined symmetric directional coupler matching the target aspect ratio.
    Target Footprint: 120um x 4um
    """
    c = gf.Component("directional_coupler_v5")
    
    # Configuration to meet 120x4 footprint with 0.2um gap
    width = 0.4
    gap = 0.2
    total_length = 120.0
    
    # Vertical Math for 4um height:
    # Outer edge = 2.0 -> centerline = 1.8
    # Inner edge = 0.1 -> centerline = 0.3
    dy_val = 1.8 - 0.3
    
    # Length Math for 120um:
    l_tail = 30.0
    l_sbend = 10.0
    l_coupler = total_length - 2*l_tail - 2*l_sbend # 40.0
    
    # Create branches
    half = directional_coupler_half(
        length_tail=l_tail, 
        length_sbend=l_sbend, 
        length_coupler=l_coupler, 
        dy=dy_val, 
        width=width
    )
    
    top = c << half
    bot = c << half
    
    # Positioning
    # The 'half' component's coupling region is at y = -dy_val relative to its start.
    # To place the coupling region at y = +0.3 (centerline):
    top.movey(0.3 + dy_val)
    
    # Mirror bottom branch and place coupling region at y = -0.3
    bot.mirror_y()
    bot.movey(-(0.3 + dy_val))
    
    # Port assignment
    c.add_port("o1", port=bot.ports["o1"])
    c.add_port("o2", port=top.ports["o1"])
    c.add_port("o3", port=top.ports["o2"])
    c.add_port("o4", port=bot.ports["o2"])

    return c

if __name__ == "__main__":
    dc = symmetric_directional_coupler()
    
    # Verification
    bbox = dc.dbbox()
    print(f"Footprint: {bbox.width():.2f} um x {bbox.height():.2f} um")
    
    dc.write_gds("symmetric_directional_coupler_v5.gds")
    dc.show()