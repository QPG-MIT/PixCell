import gdsfactory as gf

# 1. Configuration
# Define custom cross_section with small radius_min to allow tight bends
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius_min=2.0 
)

@gf.cell
def grating_section(length=8, period=0.4, duty_cycle=0.5, width=0.5):
    """Creates a periodic grating structure and correctly exposes ports."""
    c = gf.Component()
    
    # 1. Base waveguide
    base = c << gf.components.straight(length=length, cross_section=xs)
    
    # 2. Add grating teeth (rectangles)
    num_teeth = int(length / period)
    tooth_width = period * duty_cycle
    for i in range(num_teeth):
        # Calculate position
        x_pos = (i * period) - (length / 2) + (tooth_width / 2)
        tooth = c << gf.components.rectangle(size=(tooth_width, width * 2), layer=(1, 0), centered=True)
        tooth.movex(x_pos)
    
    # 3. CRITICAL FIX: Expose the ports of the base waveguide to the parent component
    c.add_port("o1", port=base.ports["o1"])
    c.add_port("o2", port=base.ports["o2"])
    
    return c

@gf.cell
def u_arm():
    """Assembles one U-shaped arm."""
    c = gf.Component()
    
    # 1. Define primitives
    taper_in = c << gf.components.taper(length=2, width1=0.2, width2=0.5)
    bend = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    grating = c << grating_section(length=8, period=0.4, width=0.5)
    taper_out = c << gf.components.taper(length=2, width1=0.5, width2=0.2)
    
    # 2. Connect
    # Taper_in -> Bend
    bend.connect("o1", taper_in.ports["o2"])
    # Bend -> Grating
    grating.connect("o1", bend.ports["o2"])
    # Grating -> Taper_out
    taper_out.connect("o1", grating.ports["o2"])
    
    # 3. Expose the main ports
    c.add_port("o1", port=taper_in.ports["o1"])
    c.add_port("o2", port=taper_out.ports["o2"])
    
    return c

@gf.cell
def build_device():
    """Assembles the full device."""
    c = gf.Component()
    
    # Add top arm
    top = c << u_arm()
    
    # Add bottom arm (mirrored)
    bottom = c << u_arm()
    # Mirroring to get the bottom U-shape
    bottom.mirror(p1=(0, -0.7), p2=(1, -0.7))
    bottom.movey(-1.4) 
    
    # Add central straight line
    center_wg = c << gf.components.straight(length=18.24, cross_section=xs)
    center_wg.movey(-0.7)
    
    return c

# Create and export
device = build_device()
device.write_gds("device_geometry.gds")