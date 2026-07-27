import gdsfactory as gf

@gf.cell
def curved_coupler():
    """Recreates the curved coupler from the image using S-bend primitives."""
    c = gf.Component("curved_coupler")
    
    # 1. Define Parameters
    width = 0.5      # Waveguide width
    dx = 9.0         # Half-length (9um + 9um = 18um total)
    dy = 0.9         # Vertical offset for each half-bend
    layer = (1, 0)
    
    # 2. Define Cross Section
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # 3. Create the Top Waveguide
    # It consists of an S-bend going down, then an S-bend going back up.
    t1 = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    t2 = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    top_left = c << t1
    top_right = c << t2
    top_right.connect("o1", top_left.ports["o2"])
    
    # 4. Create the Bottom Waveguide
    # It consists of an S-bend going up, then an S-bend going back down.
    b1 = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    b2 = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    bot_left = c << b1
    bot_right = c << b2
    bot_right.connect("o1", bot_left.ports["o2"])
    
    # 5. Position the waveguides to meet the 18x3um footprint
    # Center-to-center vertical distance at ends is 2.5um (1.25 - (-1.25))
    top_left.movey(1.25)
    top_right.movey(1.25)
    bot_left.movey(-1.25)
    bot_right.movey(-1.25)
    
    # Define external ports
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = curved_coupler()
    
    # Output GDS
    component.write_gds("curved_coupler.gds")
    
    # Optional: View the footprint to verify
    print(f"Component size: {component.size_info.width} x {component.size_info.height} um")
    component.show()