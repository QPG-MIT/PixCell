import gdsfactory as gf

# 1. Define a standard cross-section with reduced radius_min to allow tight U-turns
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=2.0)

@gf.cell
def grating_section(length=8.0, period=0.4, duty_cycle=0.4):
    """Creates a waveguide section with periodic grating teeth."""
    c = gf.Component()
    
    # 1. Base waveguide
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # 2. Add periodic teeth
    # We add rectangles perpendicular to the waveguide
    tooth_width = period * duty_cycle
    num_teeth = int(length / period)
    
    for i in range(num_teeth):
        # Calculate position relative to the center of the waveguide
        x_pos = (i * period) - (length / 2) + (period / 2)
        
        # Create a thin tooth (1.2um height ensures it crosses the 0.5um waveguide)
        tooth = c << gf.components.rectangle(
            size=(tooth_width, 1.2), 
            layer=(1, 0), 
            centered=True
        )
        tooth.movex(x_pos)
        
    # 3. Explicitly expose ports
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_arm():
    """Assembles a U-shape arm with a grating on the top section."""
    c = gf.Component()
    
    # Primitives
    taper = c << gf.components.taper(length=2, width1=0.2, width2=0.5)
    grating = c << grating_section(length=8.0)
    bend = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    straight_plain = c << gf.components.straight(length=8.0, cross_section=xs)
    
    # Assembly sequence: Taper -> Grating -> Bend -> Plain Straight
    # Connecting them
    grating.connect("o1", taper.ports["o2"])
    bend.connect("o1", grating.ports["o2"])
    straight_plain.connect("o1", bend.ports["o2"])
    
    # Expose ports
    c.add_port("in", port=taper.ports["o1"])
    c.add_port("out", port=straight_plain.ports["o2"])
    
    return c

@gf.cell
def build_device():
    """Assembles the final device pattern."""
    c = gf.Component()
    
    # Top arm
    top = c << u_arm()
    
    # Bottom arm (mirrored and spaced)
    bottom = c << u_arm()
    bottom.mirror(p1=(0, -1), p2=(1, -1))
    bottom.movey(-1.5)
    
    # Central straight waveguide (the dividing line in the image)
    center_line = c << gf.components.straight(length=18.24, cross_section=xs)
    center_line.movey(-0.75)
    
    return c

# Generate and save
device = build_device()
device.write_gds("final_device.gds")