import gdsfactory as gf

@gf.cell
def racetrack_device():
    c = gf.Component()
    
    # 1. Define custom cross-section
    # We explicitly override radius_min to 0.5 to allow our 1.5 radius bends.
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0), 
        radius=1.5, 
        radius_min=0.5
    )
    
    # 2. Geometry Parameters
    # Total Height = 3.0um (Radius = 1.5)
    # Total Width = 5.5um (Straight length = 5.5 - 2*Radius = 2.5)
    radius = 1.5
    straight_len = 2.5
    
    # 3. Build the Racetrack Loop
    # We use explicit component assembly to ensure a perfect closed loop
    s1 = c << gf.components.straight(length=straight_len, cross_section=xs)
    s2 = c << gf.components.straight(length=straight_len, cross_section=xs)
    
    # Create the 4 bends
    b_lt = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
    b_lb = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
    b_rt = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
    b_rb = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
    
    # Position the straights (Centered vertically at +radius and -radius)
    s1.movey(radius)
    s2.movey(-radius)
    
    # Connect everything
    b_lt.connect("o2", s1.ports["o1"]) # Top-left
    b_lb.connect("o2", s2.ports["o1"]) # Bottom-left
    b_rt.connect("o1", s1.ports["o2"]) # Top-right
    b_rb.connect("o1", s2.ports["o2"]) # Bottom-right
    
    # Close the loops (left and right)
    b_lt.connect("o1", b_lb.ports["o1"])
    b_rt.connect("o2", b_rb.ports["o2"])
    
    # 4. Add the Rectangular Features
    # The straights are centered at (x=0, y=1.5) and (x=0, y=-1.5)
    rect = gf.components.rectangle(size=(0.6, 0.8), layer=(1, 0), centered=True)
    
    # Top rail rectangles
    r1 = c << rect
    r1.movex(-0.6).movey(radius)
    r2 = c << rect
    r2.movex(0.6).movey(radius)
    
    # Bottom rail rectangles
    r3 = c << rect
    r3.movex(-0.6).movey(-radius)
    r4 = c << rect
    r4.movex(0.6).movey(-radius)
    
    return c

# Generate and save
device = racetrack_device()
device.write_gds("racetrack_device.gds")