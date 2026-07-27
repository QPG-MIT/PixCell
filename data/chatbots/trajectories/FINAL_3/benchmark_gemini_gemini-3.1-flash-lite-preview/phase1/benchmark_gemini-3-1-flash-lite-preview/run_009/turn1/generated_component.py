import gdsfactory as gf

@gf.cell
def create_coupler_geometry():
    """
    Constructs a waveguide coupler with two arms that converge and diverge,
    fitting within a 120um x 4um footprint.
    """
    c = gf.Component()
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Define segments to fit 120um total length:
    # 30um (straight) + 20um (bend) + 20um (center) + 20um (bend) + 30um (straight) = 120um
    
    # We build the arms relative to the center line
    # Top arm moves from y=1.0 to y=0.5
    # Bottom arm moves from y=-1.0 to y=-0.5
    
    def build_arm(y_start, y_end):
        # 1. Start straight segment
        s1 = c << gf.components.straight(length=30, cross_section=xs)
        s1.movey(y_start)
        
        # 2. First bend (converging)
        dy = y_end - y_start
        b1 = c << gf.components.bend_s(size=(20, dy), cross_section=xs)
        b1.connect("o1", s1.ports["o2"])
        
        # 3. Coupling region straight
        s2 = c << gf.components.straight(length=20, cross_section=xs)
        s2.connect("o1", b1.ports["o2"])
        
        # 4. Second bend (diverging)
        b2 = c << gf.components.bend_s(size=(20, -dy), cross_section=xs)
        b2.connect("o1", s2.ports["o2"])
        
        # 5. End straight segment
        s3 = c << gf.components.straight(length=30, cross_section=xs)
        s3.connect("o1", b2.ports["o2"])
        
        return s1, s3

    # Build the two arms
    top_start, top_end = build_arm(y_start=1.0, y_end=0.5)
    bot_start, bot_end = build_arm(y_start=-1.0, y_end=-0.5)
    
    return c

# Execute and save to GDS
if __name__ == "__main__":
    device = create_coupler_geometry()
    
    # Save the file
    filename = "coupler.gds"
    device.write_gds(filename)
    print(f"Successfully generated: {filename}")