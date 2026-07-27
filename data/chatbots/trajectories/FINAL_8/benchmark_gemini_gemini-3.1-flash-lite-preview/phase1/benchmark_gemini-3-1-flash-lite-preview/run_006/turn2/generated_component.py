import gdsfactory as gf

@gf.cell
def flared_device():
    """
    Creates the flared waveguide structure by assembling
    discrete primitives (bends and straights).
    """
    c = gf.Component()
    
    # Use the default strip cross-section
    xs = gf.cross_section.strip()
    
    # Parameters for the geometry
    num_waveguides = 5
    spacing = 5.0 # um
    bend_radius = 20.0
    
    # Build 5 parallel strands
    for i in range(num_waveguides):
        # Calculate vertical position of the center of this waveguide
        # i=0 to 4 => offset: -10, -5, 0, 5, 10
        offset = (i - 2) * spacing
        
        # 1. Central straight section
        s_mid = c << gf.components.straight(length=30, cross_section=xs)
        s_mid.movey(offset)
        
        # 2. Add Top Bend (flaring outwards)
        # Using a fixed angle of 30 degrees avoids 0-angle issues
        b_top = c << gf.components.bend_euler(radius=bend_radius, angle=30, cross_section=xs)
        b_top.connect("o1", s_mid.ports["o2"])
        
        # 3. Add Bottom Bend (flaring outwards)
        b_bot = c << gf.components.bend_euler(radius=bend_radius, angle=-30, cross_section=xs)
        b_bot.connect("o1", s_mid.ports["o1"])
        
        # 4. Add straight segments to the ends to complete the shape
        s_top = c << gf.components.straight(length=10, cross_section=xs)
        s_top.connect("o1", b_top.ports["o2"])
        
        s_bot = c << gf.components.straight(length=10, cross_section=xs)
        s_bot.connect("o2", b_bot.ports["o2"])
        
    return c

if __name__ == "__main__":
    # Create the device
    device = flared_device()
    
    # GDSFactory automatically handles grid snapping during .connect()
    # Write to GDS
    device.write_gds("flared_device.gds")
    
    print(f"Device created: {device.xsize:.2f} um x {device.ysize:.2f} um")
    
    # Optional: view the device
    # device.show()