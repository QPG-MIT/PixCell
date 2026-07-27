import gdsfactory as gf

@gf.cell
def directional_coupler_v5() -> gf.Component:
    """
    Directional coupler iteration 5.
    Adjustments: Thinner waveguides, longer coupling region, and tighter S-bends 
    to match the target image's sleek proportions.
    
    Footprint: 120um x 4um
    """
    c = gf.Component("directional_coupler_v5")
    
    # 1. Design Parameters
    L_TOTAL = 120.0
    W_WG = 0.45      # Thinner waveguide for better visual fidelity
    GAP = 0.3        # Clear interaction gap
    
    # Segment lengths summing to 120um
    L_STRAIGHT_END = 10.0  # Horizontal segments at ports
    L_SBEND = 12.0         # Compact S-bend for sharper transitions
    L_COUPLE = 76.0        # Long central interaction region
    # Verification: 10 + 12 + 76 + 12 + 10 = 120.0um
    
    # 2. Vertical geometry
    # Centerline of waveguides in the coupling region
    y_inner = (W_WG + GAP) / 2  # 0.375um
    # Centerline of waveguides at the device ends (Total span ~3.25um)
    y_outer = 1.4               
    # Vertical offset for the S-bend
    dy = y_outer - y_inner      # 1.025um
    
    # 3. Define Cross Section
    xs = gf.cross_section.cross_section(width=W_WG, layer=(1, 0))
    
    # 4. Construct a Single Branch
    # We build the top half then mirror it for perfect symmetry.
    branch = gf.Component("branch_half")
    
    # a. Central coupling straight
    mid = branch << gf.components.straight(length=L_COUPLE, cross_section=xs)
    
    # b. Left S-bend (size=(dx, dy))
    sb_left = branch << gf.components.bend_s(size=(L_SBEND, dy), cross_section=xs)
    sb_left.connect("o2", mid.ports["o1"])
    
    # c. Right S-bend (mirrored vertically via negative dy)
    sb_right = branch << gf.components.bend_s(size=(L_SBEND, -dy), cross_section=xs)
    sb_right.connect("o1", mid.ports["o2"])
    
    # d. Outer straight segments
    st_left = branch << gf.components.straight(length=L_STRAIGHT_END, cross_section=xs)
    st_left.connect("o2", sb_left.ports["o1"])
    
    st_right = branch << gf.components.straight(length=L_STRAIGHT_END, cross_section=xs)
    st_right.connect("o1", sb_right.ports["o2"])
    
    # 5. Assemble the full device
    top = c << branch
    top.movey(y_inner)
    
    bot = c << branch
    bot.mirror_y()
    bot.movey(-y_inner)
    
    # 6. Center the component at (0,0)
    c.movex(-c.center[0])
    c.movey(-c.center[1])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = directional_coupler_v5()
    
    # Export GDS for verification
    component.write_gds("directional_coupler_v5.gds")
    
    # Display in layout viewer
    component.show()