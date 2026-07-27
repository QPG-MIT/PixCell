import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Recreates the directional coupler with a 120x4 um footprint.
    Fixes the crossing issue by explicitly defining S-bend directions.
    """
    c = gf.Component("directional_coupler_recreated")
    
    # 1. Dimensions for [120, 4] footprint
    width = 0.8        # Thicker waveguide for better visual match
    gap = 0.2          # Narrow interaction gap
    length_mid = 60.0  # Interaction region length
    dx = 30.0          # Transition length (30 + 60 + 30 = 120)
    
    # Calculation for 4um height:
    # Interaction centers are at +/- (0.4 + 0.1) = +/- 0.5 um
    # We want top edge at 2.0 -> center of input at 2.0 - 0.4 = 1.6 um
    # Required vertical shift (dy) = 1.6 - 0.5 = 1.1 um
    dy = 1.1
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 2. Central Coupling Region
    # Ports: o1(top-left), o2(bot-left), o3(bot-right), o4(top-right)
    coupler = c << gf.components.coupler_straight(
        length=length_mid, 
        gap=gap, 
        cross_section=xs
    )
    
    # 3. Transitions (S-Bends)
    # Top-Left: Moves from y=1.6 DOWN to y=0.5. Needs negative dy in the S-bend.
    tl = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    tl.connect("o2", coupler.ports["o1"])
    
    # Bottom-Left: Moves from y=-1.6 UP to y=-0.5. Needs positive dy.
    bl = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bl.connect("o2", coupler.ports["o2"])
    
    # Top-Right: Moves from y=0.5 UP to y=1.6. Needs positive dy.
    tr = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    tr.connect("o1", coupler.ports["o4"])
    
    # Bottom-Right: Moves from y=-0.5 DOWN to y=-1.6. Needs negative dy.
    br = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    br.connect("o1", coupler.ports["o3"])
    
    # 4. Add External Ports
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = directional_coupler_final()
    
    # Save to GDS
    device.write_gds("corrected_coupler.gds")
    
    # Verify footprint
    print(f"Final footprint: {device.xsize:.1f} um x {device.ysize:.1f} um")
    
    # Show the result
    device.show()