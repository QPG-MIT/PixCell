import gdsfactory as gf

# Define a clean, small cross-section to ensure standard waveguide sizing
# Width = 0.5um is standard for photonic waveguides
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=5.0)

@gf.cell
def u_turn_arm(straight_length=3.0):
    """
    Creates an arm: Taper -> Straight -> 180-degree U-turn -> Straight -> Coupler connection
    """
    c = gf.Component()
    
    # 1. Taper at the input/output tip
    taper = c << gf.components.taper(length=2.0, width1=0.2, width2=0.5, cross_section=xs)
    
    # 2. Straight section
    s1 = c << gf.components.straight(length=straight_length, cross_section=xs)
    s1.connect("o1", taper.ports["o2"])
    
    # 3. U-turn (two 90-degree bends)
    b1 = c << gf.components.bend_euler(radius=5.0, angle=90, cross_section=xs)
    b2 = c << gf.components.bend_euler(radius=5.0, angle=90, cross_section=xs)
    b1.connect("o1", s1.ports["o2"])
    b2.connect("o1", b1.ports["o2"])
    
    # 4. Final straight piece to connect to coupler
    s2 = c << gf.components.straight(length=straight_length, cross_section=xs)
    s2.connect("o1", b2.ports["o2"])
    
    # Expose the coupler-facing port
    c.add_port("o1", port=s2.ports["o2"])
    return c

@gf.cell
def folded_coupler():
    c = gf.Component()
    
    # Central coupler region
    # coupler_straight ports: o1(bottom-left), o2(top-left), o3(top-right), o4(bottom-right)
    coupler = c << gf.components.coupler_straight(length=8.0, gap=0.2, cross_section=xs)
    
    # Top arm (Connects to top-right port 'o3')
    top_arm = c << u_turn_arm()
    top_arm.connect("o1", coupler.ports["o3"])
    
    # Bottom arm (Connects to bottom-left port 'o1')
    bottom_arm = c << u_turn_arm()
    bottom_arm.mirror() # Flip to orient correctly
    bottom_arm.connect("o1", coupler.ports["o1"])
    
    return c

if __name__ == "__main__":
    device = folded_coupler()
    device.write_gds("folded_coupler.gds")
    print("Successfully generated folded_coupler.gds")