import gdsfactory as gf

@gf.cell
def tapered_triplet():
    c = gf.Component()
    
    # 1. Define common cross-section
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))
    
    # 2. Central Taper (Center point of the device)
    # Tapers from 0.4um to 0.1um over 40um length
    center_wg = c << gf.components.taper(length=40, width1=0.4, width2=0.1)
    
    # 3. Helper to build flared arms (Straight -> Bend -> Straight)
    # This creates the "flaring out" effect seen in the original image
    def create_arm(angle):
        # We start with a straight section
        s1 = gf.components.straight(length=15, cross_section=xs)
        # Add a gentle euler bend to flare out
        b = gf.components.bend_euler(radius=50, angle=angle, cross_section=xs)
        # Finish with a straight section to complete the length
        s2 = gf.components.straight(length=15, cross_section=xs)
        
        # Connect them in a chain
        c_arm = gf.Component()
        s1_ref = c_arm << s1
        b_ref = c_arm << b
        s2_ref = c_arm << s2
        
        b_ref.connect("o1", s1_ref.ports["o2"])
        s2_ref.connect("o1", b_ref.ports["o2"])
        
        c_arm.add_port("o1", port=s1_ref.ports["o1"])
        c_arm.add_port("o2", port=s2_ref.ports["o2"])
        return c_arm

    # 4. Assemble the top and bottom arms
    # Use the helper to create arms that flare up (+10 deg) and down (-10 deg)
    top_arm = c << create_arm(angle=10)
    bot_arm = c << create_arm(angle=-10)
    
    # Position them vertically relative to the center taper
    # Spacing of 0.6um ensures a clear separation
    top_arm.movey(0.6)
    bot_arm.movey(-0.6)
    
    return c

# Generate GDS
if __name__ == "__main__":
    device = tapered_triplet()
    device.write_gds("triplet_device.gds")
    # device.show() # Uncomment to view in KLayout