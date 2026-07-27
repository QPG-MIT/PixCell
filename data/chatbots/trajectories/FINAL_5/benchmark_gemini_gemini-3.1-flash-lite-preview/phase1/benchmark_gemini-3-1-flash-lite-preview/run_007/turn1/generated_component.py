import gdsfactory as gf

# 1. Define the cross-section with a radius that satisfies the min_bend_radius requirement.
# Setting radius=0.5 allows the euler bends to function without triggering the 10.0um default error.
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=0.5)

@gf.cell
def folded_arm(straight_length=4.0):
    """
    Creates a folded arm structure: Bend -> Straight -> Bend.
    This creates the U-turn.
    """
    c = gf.Component()
    
    # 1. U-turn construction using Euler bends
    b1 = c << gf.components.bend_euler(radius=0.5, angle=90, cross_section=xs)
    b2 = c << gf.components.bend_euler(radius=0.5, angle=90, cross_section=xs)
    
    # Place a straight section between the bends to determine the "width" of the fold
    s_mid = c << gf.components.straight(length=0.5, cross_section=xs)
    
    # Connect them: Port o1 of b2 to o2 of s_mid, o1 of s_mid to o2 of b1
    s_mid.connect("o1", b1.ports["o2"])
    b2.connect("o1", s_mid.ports["o2"])
    
    # 2. Add the long straight section of the arm
    s_long = c << gf.components.straight(length=straight_length, cross_section=xs)
    s_long.connect("o1", b2.ports["o2"])
    
    # 3. Add taper at the end
    taper = c << gf.components.taper(length=2.0, width1=0.5, width2=0.2, cross_section=xs)
    taper.connect("o1", s_long.ports["o2"])
    
    # Expose the input port (where this connects to the coupler)
    c.add_port("o1", port=b1.ports["o1"])
    return c

@gf.cell
def folded_coupler():
    c = gf.Component()
    
    # Parameters tuned to fit the approximate 18.24um footprint
    coupler_len = 10.0
    arm_len = 3.0
    
    # Central coupler region
    coupler = c << gf.components.coupler_straight(length=coupler_len, gap=0.2, cross_section=xs)
    
    # Add top arm (U-turn)
    # The image shows one arm folding one way, the other folding the other
    top_arm = c << folded_arm(straight_length=arm_len)
    top_arm.mirror() # Flip to create the U-turn facing left/right as needed
    top_arm.connect("o1", coupler.ports["o2"])
    
    # Add bottom arm (U-turn)
    bottom_arm = c << folded_arm(straight_length=arm_len)
    bottom_arm.connect("o1", coupler.ports["o1"])
    
    return c

if __name__ == "__main__":
    # Create the component
    device = folded_coupler()
    
    # Write the GDS file explicitly
    filename = "folded_coupler.gds"
    device.write_gds(filename)
    
    print(f"Successfully generated {filename}")
    
    # Optionally open in KLayout if installed
    # device.show()