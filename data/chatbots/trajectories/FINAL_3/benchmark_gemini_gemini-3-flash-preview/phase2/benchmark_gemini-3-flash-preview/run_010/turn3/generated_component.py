import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Refined directional coupler matching the 120x4 um footprint.
    Uses narrower waveguides and explicit mirroring to avoid crossing issues.
    """
    c = gf.Component("directional_coupler_refined")
    
    # 1. Dimensions for [120, 4] footprint
    width = 0.5        # Narrower width for a cleaner visual match
    gap = 0.2          # Coupling gap
    length_mid = 60.0  # Interaction region length (half of total width)
    dx = 30.0          # S-bend horizontal transition (30 + 60 + 30 = 120)
    
    # Vertical calculation for exact 4.0 um edge-to-edge height:
    # Interaction centers are at +/- (gap/2 + width/2) = +/- 0.35 um
    # Target outer edges at +/- 2.0 um -> centers at +/- (2.0 - width/2) = +/- 1.75 um
    # Required vertical shift (dy) = 1.75 - 0.35 = 1.4 um
    dy = 1.4
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 2. Central Coupling Region
    # Ports: o1(top-left), o2(bot-left), o3(bot-right), o4(top-right)
    coupler = c << gf.components.coupler_straight(
        length=length_mid, 
        gap=gap, 
        cross_section=xs
    )
    
    # 3. Transition Components
    # We define one base s-bend and mirror it where needed to ensure correct topology
    s_up = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # --- Left Side ---
    # Top-Left: Needs to come from y=1.75 DOWN to coupler o1 (y=0.35). Mirror vertically.
    tl = c << s_up
    tl.mirror_y()
    tl.connect("o2", coupler.ports["o1"])
    
    # Bottom-Left: Needs to come from y=-1.75 UP to coupler o2 (y=-0.35). Standard s-bend.
    bl = c << s_up
    bl.connect("o2", coupler.ports["o2"])
    
    # --- Right Side ---
    # Top-Right: Needs to go from coupler o4 (y=0.35) UP to y=1.75. Standard s-bend.
    tr = c << s_up
    tr.connect("o1", coupler.ports["o4"])
    
    # Bottom-Right: Needs to go from coupler o3 (y=-0.35) DOWN to y=-1.75. Mirror vertically.
    br = c << s_up
    br.mirror_y()
    br.connect("o1", coupler.ports["o3"])
    
    # 4. Add External Ports
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the device
    device = directional_coupler_refined()
    
    # Verify exact footprint matches [120, 4]
    print(f"Footprint: {device.xsize:.1f} um x {device.ysize:.1f} um")
    
    # Save and show
    device.write_gds("refined_coupler.gds")
    device.show()