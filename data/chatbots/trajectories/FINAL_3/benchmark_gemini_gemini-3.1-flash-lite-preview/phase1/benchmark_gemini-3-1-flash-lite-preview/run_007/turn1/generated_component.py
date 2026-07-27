import gdsfactory as gf

@gf.cell
def waveguide_arm(y_displacement=1.75):
    """
    Creates one arm of the device.
    Uses S-bends to transition the waveguide up or down and back.
    Total length = 20 + 30 + 20 + 30 + 20 = 120um
    """
    c = gf.Component()
    
    # Define standard cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Define segments
    # Each S-bend is 30um long. We distribute the remaining 60um into 3 straight parts.
    seg_length = 20
    bend_length = 30
    
    # 1. Straight input
    w1 = c << gf.components.straight(length=seg_length, cross_section=xs)
    
    # 2. S-bend up (or down)
    s1 = c << gf.components.bend_s(size=(bend_length, y_displacement), cross_section=xs)
    s1.connect("o1", w1.ports["o2"])
    
    # 3. Middle straight
    w2 = c << gf.components.straight(length=seg_length, cross_section=xs)
    w2.connect("o1", s1.ports["o2"])
    
    # 4. S-bend back to centerline
    s2 = c << gf.components.bend_s(size=(bend_length, -y_displacement), cross_section=xs)
    s2.connect("o1", w2.ports["o2"])
    
    # 5. Output straight
    w3 = c << gf.components.straight(length=seg_length, cross_section=xs)
    w3.connect("o1", s2.ports["o2"])
    
    # Expose ports for the arm
    c.add_port("o1", port=w1.ports["o1"])
    c.add_port("o2", port=w3.ports["o2"])
    
    return c

@gf.cell
def coupled_device():
    """
    Assembles the two arms to form the final structure.
    """
    c = gf.Component()
    
    # Top arm (displaces +1.75um)
    top = c << waveguide_arm(y_displacement=1.75)
    
    # Bottom arm (displaces -1.75um)
    bottom = c << waveguide_arm(y_displacement=-1.75)
    
    return c

# Generate and save
if __name__ == "__main__":
    device = coupled_device()
    device.write_gds("coupled_device.gds")
    device.show()