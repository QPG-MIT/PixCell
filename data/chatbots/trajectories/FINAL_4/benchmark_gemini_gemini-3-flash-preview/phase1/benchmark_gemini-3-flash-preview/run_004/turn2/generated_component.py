import gdsfactory as gf

@gf.cell
def recreated_coupler_optimized():
    """
    Recreates the symmetric curved waveguide geometry from the image.
    Footprint: 18um x 3um.
    
    Uses a thicker waveguide and concentrated S-bends to match the 
    visual proportions and smooth curvature of the original image.
    """
    c = gf.Component("symmetric_coupler")
    
    # 1. Define Geometry Parameters
    L_total = 18.0
    H_total = 3.0
    w = 1.0       # Increased width for visual match
    g_center = 0.1 # Narrow gap at the waist
    
    # Segment lengths: 3um straight at ends, 12um total for the curved center
    L_straight = 3.0
    L_curve_half = (L_total - 2 * L_straight) / 2 # 6.0 um
    
    # Vertical offset calculation:
    # At ends, center must be at +/- (H_total/2 - w/2) = +/- 1.0
    # At center, center must be at +/- (g_center/2 + w/2) = +/- 0.55
    # Required vertical travel (dy) = 1.0 - 0.55 = 0.45 um
    dy = (H_total / 2 - w / 2) - (g_center / 2 + w / 2)
    
    # 2. Define Cross-Section
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # 3. Construct Top Waveguide (Left to Right)
    # Start at the top-left boundary
    t1 = c << gf.components.straight(length=L_straight, cross_section=xs)
    t1.movey(H_total / 2 - w / 2)
    t1.movex(-L_total / 2)
    
    # Curve down to the center
    t2 = c << gf.components.bend_s(size=(L_curve_half, -dy), cross_section=xs)
    t2.connect("o1", t1.ports["o2"])
    
    # Curve back up to the right
    t3 = c << gf.components.bend_s(size=(L_curve_half, dy), cross_section=xs)
    t3.connect("o1", t2.ports["o2"])
    
    # Finish with straight
    t4 = c << gf.components.straight(length=L_straight, cross_section=xs)
    t4.connect("o1", t3.ports["o2"])
    
    # 4. Construct Bottom Waveguide (Left to Right)
    # Start at the bottom-left boundary
    b1 = c << gf.components.straight(length=L_straight, cross_section=xs)
    b1.movey(-(H_total / 2 - w / 2))
    b1.movex(-L_total / 2)
    
    # Curve up to the center
    b2 = c << gf.components.bend_s(size=(L_curve_half, dy), cross_section=xs)
    b2.connect("o1", b1.ports["o2"])
    
    # Curve back down to the right
    b3 = c << gf.components.bend_s(size=(L_curve_half, -dy), cross_section=xs)
    b3.connect("o1", b2.ports["o2"])
    
    # Finish with straight
    b4 = c << gf.components.straight(length=L_straight, cross_section=xs)
    b4.connect("o1", b3.ports["o2"])
    
    # 5. Add Ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t4.ports["o2"])
    c.add_port("o4", port=b4.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    device = recreated_coupler_optimized()
    
    # Explicitly write GDS file
    device.write_gds("optimized_coupler.gds")
    
    # Print dimensions for verification
    print(f"Final Footprint: {device.dxsize:.2f} um x {device.dysize:.2f} um")
    
    # Show in viewer
    device.show()