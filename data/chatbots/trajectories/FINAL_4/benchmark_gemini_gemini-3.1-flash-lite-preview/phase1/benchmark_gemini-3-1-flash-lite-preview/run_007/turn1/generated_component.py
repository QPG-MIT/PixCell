import gdsfactory as gf

@gf.cell
def wave_coupler():
    """
    Creates the symmetric waveguide wave structure.
    Constructed using two 'bend_s' primitives per waveguide 
    to create the wave curvature.
    """
    c = gf.Component()
    
    # Define a standard cross_section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Waveguide Segment Lengths (Total length 18, so 9 per bend)
    L = 9
    # Vertical offset (Total footprint height 3, Y-amplitude of 1 gives sufficient clearance)
    dy = 1.0

    # --- Top Waveguide ---
    # First half: Curves down
    top1 = c << gf.components.bend_s(size=(L, -dy), cross_section=xs)
    # Second half: Curves back up
    top2 = c << gf.components.bend_s(size=(L, dy), cross_section=xs)
    
    # Align and connect
    top1.movey(dy) # Position start at y=1.0
    top2.connect("o1", top1.ports["o2"])

    # --- Bottom Waveguide ---
    # First half: Curves up
    bot1 = c << gf.components.bend_s(size=(L, dy), cross_section=xs)
    # Second half: Curves back down
    bot2 = c << gf.components.bend_s(size=(L, -dy), cross_section=xs)
    
    # Align and connect
    bot1.movey(-dy) # Position start at y=-1.0
    bot2.connect("o1", bot1.ports["o2"])

    return c

# Generate and save the device
if __name__ == "__main__":
    device = wave_coupler()
    device.write_gds("wave_device.gds")
    # To view: device.show()