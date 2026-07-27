import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Refined directional coupler matching the target visual proportions.
    Footprint: 18um x 3um.
    
    Adjustments:
    - Reduced width (w=0.6) to match the visual 'thinness' in the 3um height.
    - Added a central coupling length (L_waist) for the parallel section.
    - Maximized S-bend length for smoother curvature.
    """
    c = gf.Component("directional_coupler_v3")
    
    # 1. Geometry Parameters
    L_total = 18.0
    H_total = 3.0
    w = 0.6        # Reduced from 1.0 for better visual match
    g_center = 0.2  # Defined gap at the center
    
    # Longitudinal segments (Total must = 18.0)
    L_straight_ends = 1.0
    L_waist = 2.0
    L_curve = (L_total - 2 * L_straight_ends - L_waist) / 2 # 7.0 um each
    
    # Vertical offset (dy)
    # The waveguide centers at ends are at +/- (H_total/2 - w/2) = +/- 1.2
    # The waveguide centers at waist are at +/- (g_center/2 + w/2) = +/- 0.4
    dy = (H_total / 2 - w / 2) - (g_center / 2 + w / 2) # 0.8 um
    
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # 2. Build Top Waveguide
    # Left straight
    t1 = c << gf.components.straight(length=L_straight_ends, cross_section=xs)
    t1.movey(H_total / 2 - w / 2)
    t1.movex(-L_total / 2)
    
    # Curve down
    t2 = c << gf.components.bend_s(size=(L_curve, -dy), cross_section=xs)
    t2.connect("o1", t1.ports["o2"])
    
    # Center straight (waist)
    t3 = c << gf.components.straight(length=L_waist, cross_section=xs)
    t3.connect("o1", t2.ports["o2"])
    
    # Curve up
    t4 = c << gf.components.bend_s(size=(L_curve, dy), cross_section=xs)
    t4.connect("o1", t3.ports["o2"])
    
    # Right straight
    t5 = c << gf.components.straight(length=L_straight_ends, cross_section=xs)
    t5.connect("o1", t4.ports["o2"])
    
    # 3. Build Bottom Waveguide (Mirrored symmetrically)
    # Left straight
    b1 = c << gf.components.straight(length=L_straight_ends, cross_section=xs)
    b1.movey(-(H_total / 2 - w / 2))
    b1.movex(-L_total / 2)
    
    # Curve up
    b2 = c << gf.components.bend_s(size=(L_curve, dy), cross_section=xs)
    b2.connect("o1", b1.ports["o2"])
    
    # Center straight (waist)
    b3 = c << gf.components.straight(length=L_waist, cross_section=xs)
    b3.connect("o1", b2.ports["o2"])
    
    # Curve down
    b4 = c << gf.components.bend_s(size=(L_curve, -dy), cross_section=xs)
    b4.connect("o1", b3.ports["o2"])
    
    # Right straight
    b5 = c << gf.components.straight(length=L_straight_ends, cross_section=xs)
    b5.connect("o1", b4.ports["o2"])
    
    # 4. Expose Ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = directional_coupler_refined()
    device.write_gds("refined_coupler.gds")
    
    print(f"Final Footprint: {device.dxsize:.2f} um x {device.dysize:.2f} um")
    device.show()